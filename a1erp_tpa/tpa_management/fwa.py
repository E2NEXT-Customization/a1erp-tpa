"""Fraud, waste and abuse rules engine (configurable thresholds; no machine learning)."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate

WEIGHT = {"Low": 10, "Medium": 25, "High": 50}
REJECTED = ("Rejected", "Draft")


def claims_of(member=None, provider=None, since=None, until=None, exclude=None):
	f = {"docstatus": 1, "status": ("not in", list(REJECTED))}
	if member:
		f["member"] = member
	if provider:
		f["provider"] = provider
	if since:
		f["service_date"] = (">=", since)
	if exclude:
		f["name"] = ("!=", exclude)
	return frappe.get_all("Medical Claim", filters=f, fields=["name", "service_date", "claimed_amount", "invoice_no", "member", "provider"])


def duplicate(c, r):
	same = frappe.db.exists("Medical Claim", {"docstatus": 1, "provider": c.provider, "invoice_no": c.invoice_no, "name": ("!=", c.name), "status": ("!=", "Rejected")})
	if same:
		return _("The invoice {0} of this provider was already submitted ({1})").format(c.invoice_no, same)
	mine = {(i.service or i.drug) for i in c.items}
	for o in claims_of(c.member, c.provider, add_days(c.service_date, -cint(r.window_days or 7)), exclude=c.name):
		theirs = {(i.service or i.drug) for i in frappe.get_all("Claim Item", filters={"parent": o.name}, fields=["service", "drug"])}
		if mine & theirs and abs(date_diff(o.service_date, c.service_date)) <= cint(r.window_days or 7):
			return _("The same service was claimed for this member within {0} days ({1})").format(r.window_days or 7, o.name)


def high_frequency(c, r):
	n = len(claims_of(c.member, None, add_days(c.service_date, -cint(r.window_days or 30)), exclude=c.name)) + 1
	if cint(r.threshold_count) and n >= cint(r.threshold_count):
		return _("{0} claims for this member within {1} days").format(n, r.window_days or 30)


def coverage_mismatch(c, r):
	n = len([i for i in c.items if i.status == "Rejected"])
	if n >= max(cint(r.threshold_count), 1):
		return _("{0} billed items are not covered by the plan").format(n)


def price_above(c, r):
	for i in c.items:
		if flt(i.tariff_price) and flt(i.unit_price) > flt(i.tariff_price) * (1 + flt(r.threshold_percent) / 100) + 0.005:
			return _("Billed price {0} exceeds the tariff {1} ({2})").format(flt(i.unit_price), flt(i.tariff_price), i.service or i.drug)


def provider_spike(c, r):
	"""Volume rule on the provider, not on the claim: one open alert per provider and window, and only once the
	previous period has enough claims to make a percentage meaningful (Count Threshold, 20 by default)."""
	win = cint(r.window_days or 30)
	open_alert = frappe.db.sql("""select a.name from `tabFWA Alert` a join `tabMedical Claim` m on m.name = a.claim
		where a.provider = %s and a.rule = %s and a.status in ('Open', 'Under Investigation') and m.service_date >= %s limit 1""",
		(c.provider, r.name, add_days(c.service_date, -win)))
	if open_alert:
		return None
	recent = claims_of(None, c.provider, add_days(c.service_date, -win))
	both = claims_of(None, c.provider, add_days(c.service_date, -2 * win))
	cur = sum(flt(x.claimed_amount) for x in recent)
	prev = sum(flt(x.claimed_amount) for x in both) - cur
	if flt(r.threshold_amount) and cur >= flt(r.threshold_amount):
		return _("The provider's claims in {0} days reached {1}").format(win, cur)
	if len(both) - len(recent) < (cint(r.threshold_count) or 20):
		return None
	if prev > 0 and flt(r.threshold_percent) and (cur - prev) / prev * 100 >= flt(r.threshold_percent):
		return _("The provider's claims rose by {0}% against the previous period").format(flt((cur - prev) / prev * 100, 1))


def drug_pattern(c, r):
	for i in c.items:
		if i.item_type != "Drug" or not i.drug:
			continue
		gap = cint(frappe.db.get_value("Drug", i.drug, "min_days_between_fills")) or cint(r.window_days or 0)
		for o in claims_of(c.member, None, add_days(c.service_date, -gap), exclude=c.name):
			if frappe.db.exists("Claim Item", {"parent": o.name, "drug": i.drug}):
				return _("The drug {0} was dispensed again within {1} days ({2})").format(i.drug, gap, o.name)


def high_cost(c, r):
	if flt(r.threshold_amount) and flt(c.claimed_amount) >= flt(r.threshold_amount):
		if not frappe.db.exists("Medical Case", {"member": c.member, "status": ("!=", "Closed"), "case_type": "High Cost"}):
			frappe.get_doc({"doctype": "Medical Case", "member": c.member, "diagnosis": c.diagnosis, "case_type": "High Cost",
				"notes": _("Opened automatically by claim {0}").format(c.name)}).insert(ignore_permissions=True)
		return _("High cost claim: {0}").format(flt(c.claimed_amount))


def long_stay(c, r):
	if c.admission_date and c.discharge_date and cint(r.threshold_count) and date_diff(c.discharge_date, c.admission_date) >= cint(r.threshold_count):
		return _("Length of stay of {0} days").format(date_diff(c.discharge_date, c.admission_date))


RULES = {"Duplicate Claim": duplicate, "High Frequency": high_frequency, "Coverage Mismatch": coverage_mismatch, "Price Above Tariff": price_above,
	"Provider Cost Spike": provider_spike, "Drug Pattern": drug_pattern, "High Cost Case": high_cost, "Long Stay": long_stay}


def make_alert(c, rule, severity, details):
	return frappe.get_doc({"doctype": "FWA Alert", "claim": c.name, "member": c.member, "provider": c.provider, "rule": rule, "severity": severity,
		"details": details}).insert(ignore_permissions=True).name


def run_rules(c):
	"""Run every enabled rule and the watchlists on a submitted claim; returns (score, hold, reject, alerts)."""
	score, hold, reject, alerts = 0, False, False, []
	for r in frappe.get_all("FWA Rule", filters={"enabled": 1}, fields=["*"]):
		msg = RULES[r.rule_type](c, frappe._dict(r))
		if not msg:
			continue
		alerts.append(make_alert(c, r.name, r.severity, msg))
		score += WEIGHT.get(r.severity, 10)
		hold = hold or r.action in ("Hold for Review", "Reject")
		reject = reject or r.action == "Reject"
	today = getdate(c.service_date)
	for w in frappe.get_all("FWA Watchlist", filters={"active": 1}, fields=["entity_type", "member", "provider", "reason", "from_date", "to_date"]):
		if (w.entity_type == "Member" and w.member == c.member) or (w.entity_type == "Provider" and w.provider == c.provider):
			if (not w.from_date or getdate(w.from_date) <= today) and (not w.to_date or today <= getdate(w.to_date)):
				alerts.append(make_alert(c, None, "High", _("Watchlist: {0}").format(w.reason)))
				score += WEIGHT["High"]
				hold = True
	return min(score, 100), hold, reject, alerts