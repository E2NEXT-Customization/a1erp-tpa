"""Portals of the TPA module: every function is scoped to the identity of the signed-in user.

Three kinds of portal users exist: a provider contact (Medical Provider > Contacts), a client user (TPA Client > Portal Users)
and a member (Plan Member > Portal User). Nothing outside the scope of the identity is ever returned."""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, getdate, nowdate

from a1erp_tpa.tpa_management.cards import card_qr
from a1erp_tpa.tpa_management.engine import ADJUDICATED, benefit_row, check_eligibility, family_members, plan_year, usage

OPEN = ("Received", "Under Review", "Medical Review", "Financial Review", "Pending Information")
CLAIM_FIELDS = ["name", "service_date", "invoice_no", "invoice_date", "member_name", "card_no", "provider", "plan", "claim_type", "status", "claimed_amount",
	"contractual_discount", "member_share", "payer_amount", "info_request", "rejection_reason", "settlement", "paid_on", "pre_auth", "currency"]
AUTH_FIELDS = ["name", "request_date", "member_name", "card_no", "provider", "auth_type", "status", "requested_amount", "approved_amount", "member_share",
	"payer_share", "valid_until", "info_request", "decision_notes"]


# ------------------------------------------------------------------ identity
def identity():
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.PermissionError)
	rows = frappe.get_all("Provider Contact", filters={"user": user, "parenttype": "Medical Provider"}, fields=["parent", "portal_role"])
	for r in rows:
		p = frappe.db.get_value("Medical Provider", r.parent, ["status", "contract_to"], as_dict=True)
		if p and p.status in ("Active", "Under Review"):
			branches = frappe.get_all("Medical Provider", filters={"parent_provider": r.parent}, pluck="name")
			return frappe._dict(kind="provider", name=r.parent, providers=[r.parent] + branches, role=r.portal_role)
	clients = frappe.get_all("Client Portal User", filters={"user": user, "active": 1, "parenttype": "TPA Client"}, pluck="parent")
	if clients:
		return frappe._dict(kind="client", name=clients[0], clients=clients)
	mine = frappe.get_all("Plan Member", filters={"user": user}, pluck="name")
	if mine:
		m = frappe.get_doc("Plan Member", mine[0])
		return frappe._dict(kind="member", name=m.member_name, member=m.name, members=family_members(m))
	frappe.throw(_("Your account is not linked to a provider, a client or a member."), frappe.PermissionError)


def need(*kinds):
	me = identity()
	if me.kind not in kinds:
		frappe.throw(_("This page is not available for your account."), frappe.PermissionError)
	return me


def plans_of(clients):
	return frappe.get_all("Health Plan", filters={"is_template": 0}, or_filters={"tpa_client": ("in", clients), "insurer": ("in", clients)}, pluck="name") or [""]


@frappe.whitelist()
def bootstrap():
	me = identity()
	tabs = {"provider": ["dashboard", "eligibility", "new_claim", "claims", "new_preauth", "preauths", "settlements"],
		"client": ["dashboard", "claims", "members", "funds"], "member": ["card", "coverage", "claims", "preauths", "providers", "help"]}[me.kind]
	terms = set()
	for dt, fn in (("Medical Claim", "status"), ("Pre-Authorization", "status"), ("Pre-Authorization", "auth_type"), ("Claim Item", "status"), ("Plan Benefit", "benefit_category"),
			("Plan Member", "relationship"), ("Plan Member", "status"), ("Medical Provider", "provider_type"), ("Medical Provider", "governorate"), ("Health Fund", "status"),
			("Medical Claim", "claim_type")):
		terms.update(o for o in (frappe.get_meta(dt).get_field(fn).options or "").split("\n") if o)
	return {"kind": me.kind, "name": me.name, "tabs": tabs, "tr": {o: _(o) for o in terms}, "currency": frappe.db.get_single_value("TPA Settings", "default_currency") or "IQD",
		"categories": frappe.get_meta("Plan Benefit").get_field("benefit_category").options.split("\n")}


# ------------------------------------------------------------------ provider
def resolve_member(card_no=None, national_id=None):
	f = {"card_no": card_no} if card_no else {"national_id": national_id}
	if not any(f.values()):
		frappe.throw(_("Enter the card number or the national ID."))
	name = frappe.db.get_value("Plan Member", f, "name")
	if not name:
		frappe.throw(_("No member matches the data entered."))
	return frappe.get_doc("Plan Member", name)


@frappe.whitelist()
@rate_limit(limit=120, seconds=60)
def eligibility(card_no=None, national_id=None, category=None, service=None, on_date=None):
	me = need("provider")
	m = resolve_member(card_no, national_id)
	res = check_eligibility(m, me.name, on_date or nowdate(), category or None, service or None)
	plan = frappe.get_cached_doc("Health Plan", m.plan)
	benefits = []
	for b in plan.benefits:
		if b.class_name and m.class_name and b.class_name != m.class_name:
			continue
		benefits.append({"category": b.benefit_category, "covered": cint(b.covered), "copay_percent": flt(b.copay_percent) or flt(plan.member_copay_percent),
			"requires_preauth": cint(b.requires_preauth), "annual_limit": flt(b.annual_limit), "waiting_days": cint(b.waiting_days)})
	return {"member": m.member_name, "card_no": m.card_no, "status": m.status, "plan": plan.plan_name_ar or plan.plan_name, "class_name": m.class_name,
		"ok": bool(res.ok), "reasons": [str(x) for x in res.reasons], "in_network": bool(res.in_network), "copay_percent": flt(res.copay_percent),
		"requires_preauth": bool(res.requires_preauth), "remaining": {k: v for k, v in (res.remaining or {}).items() if k != "deductible_used"},
		"valid_until": m.end_date, "benefits": benefits}


@frappe.whitelist()
def lookup(kind, q=""):
	need("provider")
	q = (q or "").strip()
	if len(q) < 2:
		return []
	like = f"%{q}%"
	if kind == "drug":
		return frappe.db.sql("""select drug_code as code, trade_name as name, price from `tabDrug` where covered = 1 and (drug_code like %s or trade_name like %s
			or generic_name like %s) limit 20""", (like, like, like), as_dict=True)
	return frappe.db.sql("""select service_code as code, service_name as name, default_price as price, benefit_category from `tabMedical Service`
		where service_code like %s or service_name like %s or service_name_ar like %s limit 20""", (like, like, like), as_dict=True)


def build_items(rows, price_field):
	out = []
	for r in frappe.parse_json(rows) if isinstance(rows, str) else (rows or []):
		item_type = r.get("item_type") or "Service"
		code = (r.get("code") or "").strip()
		if item_type == "Drug":
			ref = frappe.db.get_value("Drug", {"drug_code": code}) or frappe.db.get_value("Drug", code)
		else:
			ref = frappe.db.get_value("Medical Service", {"service_code": code}) or frappe.db.get_value("Medical Service", code)
		if not ref:
			frappe.throw(_("The code {0} was not found.").format(code))
		out.append({"item_type": item_type, "service" if item_type == "Service" else "drug": ref, "quantity": flt(r.get("quantity")) or 1,
			price_field: flt(r.get("price"))})
	if not out:
		frappe.throw(_("Add at least one service or drug."))
	return out


def summarise_claim(doc):
	return {"name": doc.name, "status": doc.status, "claimed_amount": doc.claimed_amount, "contractual_discount": doc.contractual_discount,
		"member_share": doc.member_share, "payer_amount": doc.payer_amount,
		"items": [{"item": i.service or i.drug, "status": i.status, "payer_amount": i.payer_amount, "note": i.note} for i in doc.items]}


@frappe.whitelist()
def submit_claim(data):
	me = need("provider")
	d = frappe.parse_json(data) if isinstance(data, str) else data
	provider = d.get("provider") or me.name
	if provider not in me.providers:
		frappe.throw(_("This provider is outside your scope."), frappe.PermissionError)
	m = resolve_member(d.get("card_no"), None)
	doc = frappe.get_doc({"doctype": "Medical Claim", "member": m.name, "provider": provider, "claim_type": d.get("claim_type") or "Outpatient",
		"invoice_no": d.get("invoice_no"), "invoice_date": d.get("invoice_date") or nowdate(), "service_date": d.get("service_date") or nowdate(),
		"diagnosis": d.get("diagnosis") or None, "pre_auth": d.get("pre_auth") or None, "source": "Provider Portal",
		"admission_date": d.get("admission_date") or None, "discharge_date": d.get("discharge_date") or None, "items": build_items(d.get("items"), "unit_price")})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	doc.reload()
	return summarise_claim(doc)


@frappe.whitelist()
def request_preauth(data):
	me = need("provider")
	d = frappe.parse_json(data) if isinstance(data, str) else data
	provider = d.get("provider") or me.name
	if provider not in me.providers:
		frappe.throw(_("This provider is outside your scope."), frappe.PermissionError)
	m = resolve_member(d.get("card_no"), None)
	doc = frappe.get_doc({"doctype": "Pre-Authorization", "member": m.name, "provider": provider, "auth_type": d.get("auth_type") or "Standard",
		"priority": d.get("priority") or "Routine", "diagnosis": d.get("diagnosis") or None, "medical_notes": d.get("notes"),
		"admission_date": d.get("admission_date") or None, "expected_days": cint(d.get("expected_days")) or None,
		"items": build_items(d.get("items"), "requested_price")})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit_request()
	doc.reload()
	return {"name": doc.name, "status": doc.status, "requested_amount": doc.requested_amount, "payer_share": doc.payer_share, "member_share": doc.member_share}


def claim_rows(filters, limit=300, or_filters=None):
	rows = frappe.get_all("Medical Claim", filters={"docstatus": 1, **filters}, or_filters=or_filters, fields=CLAIM_FIELDS, order_by="service_date desc, creation desc",
		limit_page_length=limit)
	for r in rows:
		if r.rejection_reason:
			r.rejection_reason = frappe.db.get_value("Claim Rejection Reason", r.rejection_reason, "reason_ar" if frappe.local.lang == "ar" else "reason_en") or r.rejection_reason
	return rows


@frappe.whitelist()
def list_claims(status=None, limit=300):
	me = need("provider", "client", "member")
	f = {"status": status} if status else {}
	if me.kind == "provider":
		f["provider"] = ("in", me.providers)
	elif me.kind == "client":
		f["plan"] = ("in", plans_of(me.clients))
	else:
		f["member"] = ("in", me.members)
	rows = claim_rows(f, cint(limit) or 300)
	if me.kind == "member":
		for r in rows:  # members see their own share and the status, not the settlement details
			for k in ("settlement", "paid_on", "invoice_no", "contractual_discount"):
				r.pop(k, None)
	return rows


@frappe.whitelist()
def claim_detail(name):
	me = need("provider", "client", "member")
	doc = frappe.get_doc("Medical Claim", name)
	allowed = ((me.kind == "provider" and doc.provider in me.providers) or (me.kind == "client" and doc.plan in plans_of(me.clients))
		or (me.kind == "member" and doc.member in me.members))
	if not allowed or doc.docstatus != 1:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	return {**{k: doc.get(k) for k in CLAIM_FIELDS}, "items": [{"item": i.service or i.drug, "quantity": i.quantity, "unit_price": i.unit_price, "line_total": i.line_total,
		"discount_amount": i.discount_amount, "copay_amount": i.copay_amount, "deductible_amount": i.deductible_amount, "payer_amount": i.payer_amount,
		"status": i.status, "note": i.note} for i in doc.items]}


@frappe.whitelist()
def list_preauths(limit=300):
	me = need("provider", "member")
	f = {"provider": ("in", me.providers)} if me.kind == "provider" else {"member": ("in", me.members)}
	rows = frappe.get_all("Pre-Authorization", filters={"status": ("!=", "Draft"), **f}, fields=AUTH_FIELDS, order_by="creation desc", limit_page_length=cint(limit) or 300)
	return rows


@frappe.whitelist()
def list_settlements():
	me = need("provider")
	return frappe.get_all("Provider Settlement", filters={"provider": ("in", me.providers), "docstatus": 1},
		fields=["name", "posting_date", "period_from", "period_to", "gross_payable", "adjustments_total", "net_payable", "payment_entry", "currency"], order_by="posting_date desc")


@frappe.whitelist()
def dashboard():
	me = need("provider", "client")
	year_start = getdate(nowdate()).replace(month=1, day=1)
	if me.kind == "provider":
		f = {"provider": ("in", me.providers)}
		claims = frappe.get_all("Medical Claim", filters={"docstatus": 1, "service_date": (">=", year_start), **f}, fields=["status", "payer_amount", "claimed_amount"])
		open_auth = frappe.db.count("Pre-Authorization", {"provider": ("in", me.providers), "status": ("in", ["Under Review", "Medical Review", "Pending Information"])})
		payable = sum(flt(c.payer_amount) for c in claims if c.status in ("Approved", "Partially Approved", "Ready for Payment"))
		paid = sum(flt(c.payer_amount) for c in claims if c.status == "Paid")
		return {"claims": len(claims), "in_progress": len([c for c in claims if c.status in OPEN]), "rejected": len([c for c in claims if c.status == "Rejected"]),
			"claimed": sum(flt(c.claimed_amount) for c in claims), "payable": payable, "paid": paid, "open_preauths": open_auth}
	plans = plans_of(me.clients)
	claims = frappe.get_all("Medical Claim", filters={"docstatus": 1, "service_date": (">=", year_start), "plan": ("in", plans)}, fields=["status", "payer_amount", "claimed_amount"])
	return {"members": frappe.db.count("Plan Member", {"plan": ("in", plans), "status": "Active"}), "claims": len(claims),
		"in_progress": len([c for c in claims if c.status in OPEN]), "rejected": len([c for c in claims if c.status == "Rejected"]),
		"claimed": sum(flt(c.claimed_amount) for c in claims),
		"payable": sum(flt(c.payer_amount) for c in claims if c.status in ADJUDICATED), "open_preauths": frappe.db.count("Pre-Authorization", {
			"plan": ("in", plans), "status": ("in", ["Under Review", "Medical Review", "Pending Information"])})}


# ------------------------------------------------------------------ client
@frappe.whitelist()
def list_members(q=None, limit=200):
	me = need("client")
	f = {"plan": ("in", plans_of(me.clients))}
	rows = frappe.get_all("Plan Member", filters=f, or_filters={"member_name": ("like", f"%{q}%"), "card_no": ("like", f"%{q}%")} if q else None,
		fields=["name", "member_name", "card_no", "plan", "class_name", "relationship", "status", "start_date", "end_date"], order_by="member_name", limit_page_length=cint(limit) or 200)
	return rows


@frappe.whitelist()
def list_funds():
	me = need("client")
	from a1erp_tpa.tpa_management.posting import refresh_fund

	out = []
	for n in frappe.get_all("Health Fund", filters={"tpa_client": ("in", me.clients)}, pluck="name"):
		f = refresh_fund(n)
		out.append({"name": f.name, "status": f.status, "contributions": f.total_contributions, "claims": f.total_claims, "fees": f.total_fees,
			"balance": f.current_balance, "reserved": f.reserved_amount, "available": f.available_balance, "currency": f.currency})
	return out


# ------------------------------------------------------------------ member
@frappe.whitelist()
def my_cards():
	me = need("member")
	out = []
	for n in me.members:
		m = frappe.get_doc("Plan Member", n)
		card = frappe.db.get_value("Medical Card", {"member": n, "status": "Active"}, ["name", "valid_until"], as_dict=True)
		plan = frappe.db.get_value("Health Plan", m.plan, ["plan_name", "plan_name_ar"], as_dict=True)
		out.append({"member": n, "name": (m.member_name_ar if frappe.local.lang == "ar" and m.member_name_ar else m.member_name), "relationship": m.relationship,
			"card_no": m.card_no, "status": m.status, "class_name": m.class_name, "plan": (plan.plan_name_ar if frappe.local.lang == "ar" and plan.plan_name_ar else plan.plan_name),
			"valid_until": card.valid_until if card else m.end_date, "qr": card_qr(card.name) if card else None})
	return out


@frappe.whitelist()
def my_coverage(member=None):
	me = need("member")
	name = member if member in me.members else me.member
	m = frappe.get_doc("Plan Member", name)
	plan = frappe.get_cached_doc("Health Plan", m.plan)
	start, end = plan_year(plan, nowdate())
	total = usage(m, plan, nowdate())
	rows = []
	for b in plan.benefits:
		if b.class_name and m.class_name and b.class_name != m.class_name:
			continue
		u = usage(m, plan, nowdate(), b.benefit_category)
		rows.append({"category": b.benefit_category, "covered": cint(b.covered), "copay_percent": flt(b.copay_percent) or flt(plan.member_copay_percent),
			"annual_limit": flt(b.annual_limit), "used": u.paid, "remaining": (flt(b.annual_limit) - u.paid) if flt(b.annual_limit) else None,
			"requires_preauth": cint(b.requires_preauth), "waiting_days": cint(b.waiting_days)})
	overall = flt(plan.annual_limit)
	return {"member": m.member_name, "plan_year": [start, end], "overall_limit": overall, "overall_used": total.paid,
		"overall_remaining": (overall - total.paid) if overall else None, "benefits": rows}


@frappe.whitelist()
def find_providers(q=None, governorate=None, provider_type=None):
	me = need("member")
	m = frappe.get_doc("Plan Member", me.member)
	plan = frappe.get_cached_doc("Health Plan", m.plan)
	f = {"status": "Active"}
	if governorate:
		f["governorate"] = governorate
	if provider_type:
		f["provider_type"] = provider_type
	rows = frappe.get_all("Medical Provider", filters=f, or_filters={"provider_name": ("like", f"%{q}%"), "provider_name_ar": ("like", f"%{q}%")} if q else None,
		fields=["name", "provider_name", "provider_name_ar", "provider_type", "governorate", "city", "address", "phone", "latitude", "longitude"],
		order_by="provider_name", limit_page_length=150)
	out = []
	for r in rows:
		p = frappe.get_cached_doc("Medical Provider", r.name)
		allowed = [c.client for c in p.allowed_clients]
		if allowed and plan.tpa_client not in allowed:
			continue
		if plan.network and not any(n.network == plan.network for n in p.networks):
			continue
		out.append(r)
	return out


@frappe.whitelist()
@rate_limit(limit=10, seconds=3600)
def open_ticket(subject, description=None, ticket_type="Inquiry", claim=None):
	me = need("member")
	if claim and frappe.db.get_value("Medical Claim", claim, "member") not in me.members:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	doc = frappe.get_doc({"doctype": "Service Ticket", "ticket_type": ticket_type if ticket_type in ("Inquiry", "Complaint", "Suggestion") else "Inquiry",
		"channel": "Portal", "subject": (subject or "")[:140], "description": description, "member": me.member, "claim": claim or None})
	doc.flags.ignore_permissions = True
	doc.insert()
	return {"name": doc.name}
