// Copyright (c) 2026, A1ERP and contributors
// For license information, please see license.txt

frappe.query_reports["TPA Claims Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{ fieldname: "tpa_client", label: __("Client"), fieldtype: "Link", options: "TPA Client" },
		{ fieldname: "provider", label: __("Provider"), fieldtype: "Link", options: "Medical Provider" },
		{ fieldname: "plan", label: __("Plan"), fieldtype: "Link", options: "Health Plan" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nReceived\nUnder Review\nMedical Review\nFinancial Review\nPending Information\nApproved\nPartially Approved\nRejected\nReady for Payment\nPaid\nClosed" },
	],
};
