// Copyright (c) 2026, A1ERP and contributors
// For license information, please see license.txt

frappe.query_reports["Health Fund Position"] = {
	filters: [
		{ fieldname: "tpa_client", label: __("Client"), fieldtype: "Link", options: "TPA Client" },
	],
};
