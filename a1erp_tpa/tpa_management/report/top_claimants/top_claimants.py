# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cint

from a1erp_tpa.tpa_management.report_utils import claim_where, col


def execute(filters=None):
	where, args = claim_where(filters)
	args["n"] = cint((filters or {}).get("limit")) or 50
	columns = [col("Member", "member", "Link", "Plan Member", 130), col("Name", "member_name", "Data", None, 180), col("Plan", "plan", "Link", "Health Plan", 150),
		col("Claims", "claims", "Int", None, 80), col("Claimed Amount", "claimed", "Currency", None, 130), col("Payable to the Provider", "payable", "Currency", None, 140)]
	data = frappe.db.sql(f"""select c.member, c.member_name, c.plan, count(*) as claims, coalesce(sum(c.claimed_amount), 0) as claimed,
		coalesce(sum(case when c.status in ('Approved','Partially Approved','Ready for Payment','Paid','Closed') then c.payer_amount else 0 end), 0) as payable
		from `tabMedical Claim` c where {where} group by c.member, c.member_name, c.plan order by payable desc limit %(n)s""", args, as_dict=True)
	return columns, data