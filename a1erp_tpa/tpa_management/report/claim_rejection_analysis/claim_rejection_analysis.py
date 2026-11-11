# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe

from a1erp_tpa.tpa_management.report_utils import chart, claim_where, col, pct


def execute(filters=None):
	where, args = claim_where(filters)
	columns = [col("Rejection Reason", "reason", "Data", None, 260), col("Category", "category", "Data", None, 130), col("Claims", "claims", "Int", None, 90),
		col("Claimed Amount", "claimed", "Currency", None, 140), col("Share of Rejected (%)", "share", "Percent", None, 130)]
	data = frappe.db.sql(f"""select coalesce(r.reason_ar, r.reason_en, c.rejection_reason, '-') as reason, r.category, count(*) as claims,
		coalesce(sum(c.claimed_amount), 0) as claimed from `tabMedical Claim` c left join `tabClaim Rejection Reason` r on r.name = c.rejection_reason
		where {where} and c.status = 'Rejected' group by c.rejection_reason, r.reason_ar, r.reason_en, r.category order by claims desc""", args, as_dict=True)
	total = sum(d.claims for d in data)
	for d in data:
		d.share = pct(d.claims, total)
	return columns, data, None, chart([d.reason for d in data[:10]], [d.claims for d in data[:10]], "Claims", "pie") if data else None