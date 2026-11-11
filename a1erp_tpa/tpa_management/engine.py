"""TPA engine: plan year, eligibility, tariffs, benefit usage and claim calculation."""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, date_diff, flt, getdate, nowdate

ADJUDICATED = ("Approved", "Partially Approved", "Ready for Payment", "Paid", "Closed")


def settings():
	return frappe.get_cached_doc("TPA Settings")


def rnd(v):
	return flt(v, 2)


# ------------------------------------------------------------------ plan year and family
def plan_year(plan, on_date):
	"""Start and end of the plan year that contains `on_date`."""
	d = getdate(on_date)
	if plan.from_date and plan.to_date and getdate(plan.from_date) <= d <= getdate(plan.to_date):
		return getdate(plan.from_date), getdate(plan.to_date)
	month = cint(settings().plan_year_start_month) or 1
	start = d.replace(month=month, day=1)
	if start > d:
		start = start.replace(year=d.year - 1)
	return start, add_days(add_months(start, 12), -1)


def family_members(member):
	"""Names of the members whose limits are shared with `member` (the whole family of the principal)."""
	principal = member.principal or member.name
	rows = frappe.get_all("Plan Member", filters={"plan": member.plan}, or_filters={"name": principal, "principal": principal}, pluck="name")
	return rows or [member.name]


def age_of(member, on_date):
	if not member.date_of_birth:
		return None
	dob, d = getdate(member.date_of_birth), getdate(on_date)
	return d.year - dob.year - ((d.month, d.day) < (dob.month, dob.day))


# ------------------------------------------------------------------ benefits and exclusions
def benefit_row(plan, class_name, category):
	"""Benefit row for a category: the row of the member's class, otherwise the general row."""
	general = None
	for r in plan.benefits:
		if r.benefit_category != category:
			continue
		if r.class_name and class_name and r.class_name == class_name:
			return r
		if not r.class_name:
			general = r
	return general


def class_limits(plan, class_name):
	for c in plan.classes:
		if c.class_name == class_name:
			return flt(c.annual_limit), flt(c.family_limit)
	return 0.0, 0.0


def excluded(plan, service=None, drug=None, diagnosis=None, text=""):
	for e in plan.exclusions:
		if e.exclusion_type == "Service" and service and e.service == service:
			return _("Service excluded by the plan")
		if e.exclusion_type == "Drug" and drug and e.drug == drug:
			return _("Drug excluded by the plan")
		if e.exclusion_type == "Diagnosis" and diagnosis and e.diagnosis == diagnosis:
			return _("Diagnosis excluded by the plan")
		if e.exclusion_type == "Keyword" and e.keyword and e.keyword.lower() in (text or "").lower():
			return _("Excluded by the plan ({0})").format(e.keyword)
	return None


def usage(member, plan, on_date, category=None, exclude_claim=None):
	"""Amounts already paid to or on behalf of the member (or the family when limits are shared) in the plan year."""
	start, end = plan_year(plan, on_date)
	names = family_members(member) if plan.limit_mode == "Family Shared" else [member.name]
	cond = "c.docstatus = 1 and c.status in %(st)s and c.member in %(m)s and c.service_date between %(s)s and %(e)s"
	args = {"st": ADJUDICATED, "m": names, "s": start, "e": end, "x": exclude_claim or ""}
	cond += " and c.name != %(x)s"
	cat = " and i.benefit_category = %(cat)s" if category else ""
	args["cat"] = category
	row = frappe.db.sql(
		f"""select coalesce(sum(i.payer_amount), 0), coalesce(sum(i.deductible_amount), 0), count(distinct c.name)
		from `tabClaim Item` i join `tabMedical Claim` c on c.name = i.parent where {cond}{cat}""", args)[0]
	return frappe._dict(paid=flt(row[0]), deductible=flt(row[1]), claims=cint(row[2]))


# ------------------------------------------------------------------ providers and tariffs
def provider_in_network(provider, plan):
	if not plan.network:
		return True
	return any(n.network == plan.network for n in provider.networks)


def tariff_for(provider, plan, on_date, item_type, service=None, drug=None):
	"""Best active tariff line for the item: returns (price, discount_percent, tariff name) or (None, discount, None)."""
	d = getdate(on_date)
	nets = [n.network for n in provider.networks]
	cands = frappe.get_all("Provider Tariff", filters={"status": "Active", "valid_from": ("<=", d)},
		or_filters={"provider": provider.name, **({"network": ("in", nets)} if nets else {})},
		fields=["name", "provider", "network", "tpa_client", "plan", "valid_from", "valid_to", "discount_percent"])
	best, best_score = None, -1
	for t in cands:
		if t.valid_to and getdate(t.valid_to) < d:
			continue
		if t.plan and t.plan != plan.name:
			continue
		if t.tpa_client and t.tpa_client != plan.tpa_client:
			continue
		score = (4 if t.plan else 0) + (2 if t.tpa_client else 0) + (1 if t.provider else 0)
		if (score, str(t.valid_from)) > (best_score, str(best.valid_from) if best else ""):
			if frappe.db.exists("Tariff Item", {"parent": t.name, "item_type": item_type, "service" if item_type == "Service" else "drug": service or drug}):
				best, best_score = t, score
	if not best:
		return None, flt(provider.default_discount_percent), None
	row = frappe.db.get_value("Tariff Item", {"parent": best.name, "item_type": item_type, "service" if item_type == "Service" else "drug": service or drug},
		["price", "discount_percent"], as_dict=True)
	disc = flt(row.discount_percent) or flt(best.discount_percent) or flt(provider.default_discount_percent)
	return flt(row.price), disc, best.name


def default_price(item_type, service=None, drug=None):
	return flt(frappe.db.get_value("Medical Service", service, "default_price")) if item_type == "Service" else flt(frappe.db.get_value("Drug", drug, "price"))


# ------------------------------------------------------------------ eligibility
def check_eligibility(member, provider_name=None, on_date=None, category=None, service=None, drug=None, diagnosis=None, amount=0):
	"""Return a dict: ok, reasons, in_network, remaining limits and cost sharing for the benefit."""
	on_date = getdate(on_date or nowdate())
	m = frappe.get_doc("Plan Member", member) if isinstance(member, str) else member
	plan = frappe.get_cached_doc("Health Plan", m.plan)
	res = frappe._dict(ok=True, reasons=[], in_network=True, plan=plan.name, member=m.name, remaining={}, copay_percent=flt(plan.member_copay_percent),
		deductible=flt(plan.deductible), benefit=None, requires_preauth=False)

	def fail(msg):
		res.ok = False
		res.reasons.append(msg)

	if m.status != "Active":
		fail(_("Membership is {0}").format(_(m.status)))
	if m.start_date and on_date < getdate(m.start_date) or (m.end_date and on_date > getdate(m.end_date)):
		fail(_("The date is outside the coverage period of the member"))
	if plan.status != "Active":
		fail(_("The plan is {0}").format(_(plan.status)))
	if plan.from_date and plan.to_date and not (getdate(plan.from_date) <= on_date <= getdate(plan.to_date)):
		fail(_("The date is outside the plan period"))
	if plan.tpa_client and frappe.db.get_value("TPA Client", plan.tpa_client, "status") != "Active":
		fail(_("The client contract is not active"))
	provider = frappe.get_cached_doc("Medical Provider", provider_name) if provider_name else None
	if provider:
		if provider.status != "Active":
			fail(_("The provider is {0}").format(_(provider.status)))
		if provider.license_expiry and getdate(provider.license_expiry) < on_date:
			fail(_("The license of the provider has expired"))
		allowed = [c.client for c in provider.allowed_clients]
		if allowed and plan.tpa_client not in allowed:
			fail(_("The provider is not contracted for this client"))
		res.in_network = provider_in_network(provider, plan)
	if not category:
		return res
	row = benefit_row(plan, m.class_name, category)
	res.benefit = row
	if not row or not cint(row.covered):
		fail(_("The benefit {0} is not covered").format(_(category)))
		return res
	if not res.in_network and not (cint(plan.outside_network_covered) or cint(row.oon_covered)):
		fail(_("Treatment outside the network is not covered"))
	if row.gender and m.gender and row.gender != m.gender:
		fail(_("The benefit does not apply to this gender"))
	age = age_of(m, on_date)
	if age is not None and ((row.min_age and age < cint(row.min_age)) or (row.max_age and age > cint(row.max_age))):
		fail(_("The benefit does not apply to this age"))
	if m.start_date and cint(row.waiting_days) and date_diff(on_date, m.start_date) < cint(row.waiting_days):
		fail(_("Waiting period of {0} days has not ended").format(row.waiting_days))
	if category == "Maternity" and not cint(plan.maternity_covered):
		fail(_("Pregnancy and delivery are not covered"))
	if category == "Pharmacy" and not cint(plan.pharmacy_covered):
		fail(_("Medicines are not covered"))
	if category == "Emergency" and not cint(plan.emergency_covered):
		fail(_("Emergencies are not covered"))
	chronic = bool(diagnosis and frappe.db.get_value("Medical Code", diagnosis, "is_chronic"))
	if chronic and not cint(plan.chronic_covered):
		fail(_("Chronic conditions are not covered"))
	text = " ".join(filter(None, [diagnosis and frappe.db.get_value("Medical Code", diagnosis, "description_en"),
		service and frappe.db.get_value("Medical Service", service, "service_name"), drug and frappe.db.get_value("Drug", drug, "trade_name")]))
	why = excluded(plan, service, drug, diagnosis, text)
	if why:
		fail(why)
	res.copay_percent = flt(row.oon_copay_percent) if (not res.in_network and flt(row.oon_copay_percent)) else (flt(row.copay_percent) or flt(plan.member_copay_percent))
	if flt(row.deductible):
		res.deductible = flt(row.deductible)
	res.requires_preauth = bool(cint(row.requires_preauth) and (not flt(row.preauth_threshold) or flt(amount) > flt(row.preauth_threshold)))
	# remaining limits
	u_cat = usage(m, plan, on_date, category)
	u_all = usage(m, plan, on_date)
	cls_annual, cls_family = class_limits(plan, m.class_name)
	overall = flt(cls_family if plan.limit_mode == "Family Shared" and cls_family else cls_annual) or flt(
		plan.family_limit if plan.limit_mode == "Family Shared" and flt(plan.family_limit) else plan.annual_limit)
	res.remaining = {"category": (flt(row.annual_limit) - u_cat.paid) if flt(row.annual_limit) else None,
		"overall": (overall - u_all.paid) if overall else None, "per_visit": flt(row.per_visit_limit) or flt(plan.per_visit_limit) or None,
		"deductible_used": usage(m, plan, on_date).deductible}
	if row.sessions_limit and u_cat.claims >= cint(row.sessions_limit):
		fail(_("The sessions limit of {0} has been reached").format(row.sessions_limit))
	for k in ("category", "overall"):
		if res.remaining[k] is not None and res.remaining[k] <= 0:
			fail(_("The {0} limit has been exhausted").format(_(k)))
	return res


# ------------------------------------------------------------------ item and claim calculation
def set_decision(it, value):
	"""Keep the engine decision on the row; only claim items store it in their status field."""
	it.calc_status = value
	if it.doctype == "Claim Item":
		it.status = value


def calculate_items(doc, items, member, plan, provider, on_date, preauth=None, exclude_claim=None):
	"""Fill the amounts of claim / authorization items and return the totals.

	Order of calculation: contractual discount, then deductible, co-payment and the benefit limit
	(or the limit before the deductible and co-payment, depending on TPA Settings)."""
	st = settings()
	limit_first = (st.calculation_order or "").startswith("Discount, Limit")
	tol = flt(st.price_tolerance_percent) / 100
	totals = frappe._dict(claimed=0.0, discount=0.0, non_covered=0.0, deductible=0.0, copay=0.0, over=0.0, payer=0.0)
	rem_cat, rem_all, ded_left, visit_left, cache = {}, None, None, {}, {}
	pre = {}
	if preauth:
		for pi in preauth.items:
			pre[(pi.service or pi.drug)] = pre.get((pi.service or pi.drug), 0) + flt(pi.approved_amount)
	for it in items:
		item_type = it.item_type or "Service"
		key = it.service if item_type == "Service" else it.drug
		it.line_total = rnd(flt(it.quantity or 1) * flt(it.unit_price if hasattr(it, "unit_price") else it.requested_price))
		unit = flt(it.unit_price if hasattr(it, "unit_price") else it.requested_price)
		price, disc, _t = tariff_for(provider, plan, on_date, item_type, it.service, it.drug)
		tariff = price if price is not None else None
		it.tariff_price = tariff or 0
		allowed_unit = unit
		reason = None
		if tariff is not None and unit > tariff * (1 + tol) + 0.005:
			allowed_unit = tariff
		qty = flt(it.quantity or 1)
		base = rnd(qty * allowed_unit)
		discount = rnd(base * flt(disc) / 100)
		it.discount_amount = rnd(it.line_total - base + discount)
		net = rnd(base - discount)
		category = (frappe.db.get_value("Medical Service", it.service, "benefit_category") if item_type == "Service" else
			("Chronic" if frappe.db.get_value("Drug", it.drug, "chronic_drug") and benefit_row(plan, member.class_name, "Chronic") else "Pharmacy"))
		it.benefit_category = category
		el = check_eligibility(member, provider.name, on_date, category, it.service, it.drug, getattr(doc, "diagnosis", None), net)
		it.deductible_amount = it.copay_amount = it.payer_amount = it.non_covered_amount = 0
		it.reason = None
		drug_rule = frappe.db.get_value("Drug", it.drug, ["covered", "max_quantity"], as_dict=True) if item_type == "Drug" and it.drug else None
		if drug_rule and not cint(drug_rule.covered):
			el.ok, el.reasons = False, [_("The drug is not covered")]
		if drug_rule and flt(drug_rule.max_quantity) and qty > flt(drug_rule.max_quantity):
			el.ok, el.reasons = False, [_("Quantity exceeds the maximum per dispensing")]
		needs_pre = el.requires_preauth or (item_type == "Service" and frappe.db.get_value("Medical Service", it.service, "requires_preauth")) or (
			item_type == "Drug" and frappe.db.get_value("Drug", it.drug, "requires_preauth"))
		if el.ok and needs_pre and preauth is not None and key not in pre:
			el.ok, el.reasons = False, [_("Pre-authorization is required")]
		elif el.ok and needs_pre and preauth is None and hasattr(doc, "pre_auth"):
			el.ok, el.reasons = False, [_("Pre-authorization is required")]
		if not el.ok:
			set_decision(it, "Rejected")
			it.non_covered_amount = net
			it.note = "; ".join(str(r) for r in el.reasons)[:140]
			totals.claimed += it.line_total
			totals.discount += it.discount_amount
			totals.non_covered += net
			continue
		if category not in rem_cat:
			rem_cat[category] = el.remaining.get("category")
			visit_left[category] = el.remaining.get("per_visit")
		if rem_all is None:
			rem_all = el.remaining.get("overall") if el.remaining.get("overall") is not None else float("inf")
			ded_left = max(flt(el.deductible) - flt(el.remaining.get("deductible_used")), 0)
		room = min(x for x in (rem_cat[category], rem_all, visit_left[category], float("inf")) if x is not None)
		if key in pre and preauth is not None:
			room = min(room, flt(pre[key]))
		pct = flt(el.copay_percent) / 100
		if limit_first:
			covered = min(net, max(room, 0))
			over = net - covered
			d = min(covered, ded_left)
			c = (covered - d) * pct
			payer = covered - d - c
		else:
			d = min(net, ded_left)
			c = (net - d) * pct
			pre_limit = net - d - c
			payer = min(pre_limit, max(room, 0))
			over = pre_limit - payer
		ded_left -= d
		if rem_cat[category] is not None:
			rem_cat[category] -= payer
		rem_all -= payer
		if visit_left[category] is not None:
			visit_left[category] -= payer
		it.deductible_amount, it.copay_amount, it.payer_amount = rnd(d), rnd(c), rnd(payer)
		it.non_covered_amount = rnd(over)
		if over > 0.005:
			it.note = _("Above the benefit limit")
		set_decision(it, "Reduced" if (allowed_unit < unit or over > 0.005 or discount > 0) else "Accepted")
		totals.claimed += it.line_total
		totals.discount += it.discount_amount
		totals.deductible += d
		totals.copay += c
		totals.over += over
		totals.payer += payer
	for k in totals:
		totals[k] = rnd(totals[k])
	return totals
