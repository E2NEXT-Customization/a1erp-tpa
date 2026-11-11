# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe

from a1erp_tpa.tpa_management.posting import refresh_fund
from a1erp_tpa.tpa_management.report_utils import chart, col, pct


def execute(filters=None):
	f = frappe._dict(filters or {})
	columns = [col("Fund", "fund", "Link", "Health Fund", 180), col("Client", "client", "Link", "TPA Client", 160), col("Status", "status", "Data", None, 90),
		col("Contributions", "contributions", "Currency", None, 130), col("Claims Charged", "claims", "Currency", None, 130),
		col("Administration Fees", "fees", "Currency", None, 120), col("Current Balance", "balance", "Currency", None, 130),
		col("Reserved by Open Authorizations", "reserved", "Currency", None, 140), col("Available Balance", "available", "Currency", None, 130),
		col("Consumed (%)", "consumed", "Percent", None, 100)]
	filt = {"tpa_client": f.tpa_client} if f.tpa_client else {}
	data = []
	for name in frappe.get_all("Health Fund", filters=filt, pluck="name"):
		d = refresh_fund(name)
		data.append({"fund": d.name, "client": d.tpa_client, "status": d.status, "contributions": d.total_contributions, "claims": d.total_claims,
			"fees": d.total_fees, "balance": d.current_balance, "reserved": d.reserved_amount, "available": d.available_balance,
			"consumed": pct(d.total_claims + d.total_fees, d.total_contributions)})
	return columns, data, None, chart([x["fund"] for x in data], [x["available"] for x in data], "Available Balance") if data else None