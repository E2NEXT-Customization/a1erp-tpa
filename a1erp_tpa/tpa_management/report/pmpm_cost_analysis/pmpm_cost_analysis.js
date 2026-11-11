// Copyright (c) 2026, A1ERP and contributors
// For license information, please see license.txt

frappe.query_reports["PMPM Cost Analysis"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
		{ fieldname: "tpa_client", label: __("Client"), fieldtype: "Link", options: "TPA Client" },
		{ fieldname: "plan", label: __("Plan"), fieldtype: "Link", options: "Health Plan" },
		{ fieldname: "group_by", label: __("Group By"), fieldtype: "Select", options: "Client\nPlan\nInsurance Company", default: "Client" },
	],
};
