# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

from a1erp_tpa.tpa_management.report_utils import chart, claim_where, col, pct


def execute(filters=None):
	where, args = claim_where(filters)
	columns = [col("Plan", "plan", "Link", "Health Plan", 200), col("Client", "client", "Link", "TPA Client", 150), col("Active Members", "members", "Int", None, 100),
		col("Members with Claims", "claimants", "Int", None, 110), col("Claims", "claims", "Int", None, 80), col("Payable to the Provider", "payable", "Currency", None, 140),
		col("Average per Member", "per_member", "Currency", None, 130), col("Utilization of the Annual Limits (%)", "utilization", "Percent", None, 150)]
	rows = frappe.db.sql(f"""select c.plan, count(*) as claims, count(distinct c.member) as claimants,
		coalesce(sum(case when c.status in ('Approved','Partially Approved','Ready for Payment','Paid','Closed') then c.payer_amount else 0 end), 0) as payable
		from `tabMedical Claim` c where {where} group by c.plan order by payable desc""", args, as_dict=True)
	for d in rows:
		p = frappe.db.get_value("Health Plan", d.plan, ["tpa_client", "annual_limit"], as_dict=True)
		d.client = p.tpa_client
		d.members = frappe.db.count("Plan Member", {"plan": d.plan, "status": "Active"})
		d.per_member = d.payable / d.members if d.members else 0
		d.utilization = pct(d.payable, flt(p.annual_limit) * d.members)
	return columns, rows, None, chart([d.plan for d in rows[:10]], [d.payable for d in rows[:10]], "Payable") if rows else None