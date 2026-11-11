# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe

from a1erp_tpa.tpa_management.report_utils import claim_where, col


def execute(filters=None):
	where, args = claim_where(filters)
	columns = [col("Claim", "claim", "Link", "Medical Claim", 140), col("Date of Service", "service_date", "Date", None, 100),
		col("Invoice No.", "invoice_no", "Data", None, 110), col("Member", "member_name", "Data", None, 160),
		col("Provider", "provider", "Link", "Medical Provider", 160), col("Plan", "plan", "Link", "Health Plan", 120),
		col("Status", "status", "Data", None, 120), col("Claimed Amount", "claimed_amount", "Currency", None, 120),
		col("Contractual Discount", "contractual_discount", "Currency", None, 120), col("Total Borne by the Member", "member_share", "Currency", None, 120),
		col("Payable to the Provider", "payer_amount", "Currency", None, 130)]
	data = frappe.db.sql(f"""select c.name as claim, c.service_date, c.invoice_no, c.member_name, c.provider, c.plan, c.status, c.claimed_amount,
		c.contractual_discount, c.member_share, c.payer_amount from `tabMedical Claim` c where {where} order by c.service_date desc, c.name desc""", args, as_dict=True)
	return columns, data