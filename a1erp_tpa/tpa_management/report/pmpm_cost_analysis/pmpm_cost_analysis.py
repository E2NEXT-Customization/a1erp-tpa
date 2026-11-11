# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import date_diff, flt, getdate

from a1erp_tpa.tpa_management.report_utils import chart, col

GOOD = ("Approved", "Partially Approved", "Ready for Payment", "Paid", "Closed")


def execute(filters=None):
	f = frappe._dict(filters or {})
	start, end = getdate(f.from_date or "2000-01-01"), getdate(f.to_date)
	by = f.group_by if f.group_by in ("Client", "Plan", "Insurance Company") else "Client"
	columns = [col(by, "key", "Data", None, 220), col("Member Months", "member_months", "Float", None, 120), col("Claims", "claims", "Int", None, 90),
		col("Payable to the Provider", "payable", "Currency", None, 150), col("Cost per Member per Month (PMPM)", "pmpm", "Currency", None, 170),
		col("Cost per Claim", "per_claim", "Currency", None, 130), col("Claims per 1000 Members per Year", "frequency", "Float", None, 150)]
	plan_filter = {"is_template": 0}
	if f.tpa_client:
		plan_filter["tpa_client"] = f.tpa_client
	if f.plan:
		plan_filter["name"] = f.plan
	plans = {p.name: p for p in frappe.get_all("Health Plan", filters=plan_filter, fields=["name", "tpa_client", "insurer"])}
	groups = {}

	def key_of(plan):
		return {"Client": plan.tpa_client, "Plan": plan.name, "Insurance Company": plan.insurer or plan.tpa_client}[by] or "-"

	for m in frappe.get_all("Plan Member", filters={"plan": ("in", list(plans) or [""]), "status": ("in", ["Active", "Suspended", "Expired", "Terminated"])},
			fields=["plan", "start_date", "end_date"]):
		s = max(getdate(m.start_date), start) if m.start_date else start
		e = min(getdate(m.end_date), end) if m.end_date else end
		days = date_diff(e, s) + 1
		if days > 0:
			groups.setdefault(key_of(plans[m.plan]), frappe._dict(member_months=0.0, claims=0, payable=0.0)).member_months += days / 30.4375
	for r in frappe.db.sql("""select plan, count(*) as claims, coalesce(sum(case when status in %(good)s then payer_amount else 0 end), 0) as payable
			from `tabMedical Claim` where docstatus = 1 and service_date between %(a)s and %(b)s and plan in %(plans)s group by plan""",
			{"good": GOOD, "a": start, "b": end, "plans": list(plans) or [""]}, as_dict=True):
		g = groups.setdefault(key_of(plans[r.plan]), frappe._dict(member_months=0.0, claims=0, payable=0.0))
		g.claims += r.claims
		g.payable += flt(r.payable)
	data = []
	for k, g in sorted(groups.items(), key=lambda x: -x[1].payable):
		data.append({"key": k, "member_months": round(g.member_months, 1), "claims": g.claims, "payable": g.payable,
			"pmpm": g.payable / g.member_months if g.member_months else 0, "per_claim": g.payable / g.claims if g.claims else 0,
			"frequency": g.claims / (g.member_months / 12) * 1000 if g.member_months else 0})
	return columns, data, None, chart([d["key"] for d in data[:10]], [d["pmpm"] for d in data[:10]], "PMPM") if data else None