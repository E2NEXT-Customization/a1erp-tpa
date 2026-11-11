# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe

from a1erp_tpa.tpa_management.report_utils import chart, claim_where, col, pct


def execute(filters=None):
	where, args = claim_where(filters)
	columns = [col("Provider", "provider", "Link", "Medical Provider", 200), col("Claims", "claims", "Int", None, 80),
		col("Claimed Amount", "claimed", "Currency", None, 130), col("Payable to the Provider", "payable", "Currency", None, 130),
		col("Average Claim", "average", "Currency", None, 120), col("Rejected", "rejected", "Int", None, 90),
		col("Claim Rejection Rate (%)", "rejection_rate", "Percent", None, 120), col("Fraud Alerts", "alerts", "Int", None, 90),
		col("Complaints", "complaints", "Int", None, 90)]
	data = frappe.db.sql(f"""select c.provider, count(*) as claims, coalesce(sum(c.claimed_amount), 0) as claimed,
		coalesce(sum(case when c.status in ('Approved','Partially Approved','Ready for Payment','Paid','Closed') then c.payer_amount else 0 end), 0) as payable,
		coalesce(sum(c.status = 'Rejected'), 0) as rejected from `tabMedical Claim` c where {where} group by c.provider order by claimed desc""", args, as_dict=True)
	for d in data:
		d.average = d.claimed / d.claims if d.claims else 0
		d.rejection_rate = pct(d.rejected, d.claims)
		d.alerts = frappe.db.count("FWA Alert", {"provider": d.provider})
		d.complaints = frappe.db.count("Service Ticket", {"provider": d.provider, "ticket_type": "Complaint"})
	return columns, data, None, chart([d.provider for d in data[:10]], [d.claimed for d in data[:10]], "Claimed Amount") if data else None