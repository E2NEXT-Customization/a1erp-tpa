// Copyright (c) 2026, A1ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Preauthorization Turnaround"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
	],
};
