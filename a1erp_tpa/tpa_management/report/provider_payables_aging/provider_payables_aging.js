// Copyright (c) 2026, A1ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Provider Payables Aging"] = {
	filters: [
		{ fieldname: "as_on_date", label: __("As on Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "provider", label: __("Provider"), fieldtype: "Link", options: "Medical Provider" },
	],
};
