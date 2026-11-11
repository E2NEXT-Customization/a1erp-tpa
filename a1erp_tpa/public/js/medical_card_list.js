frappe.listview_settings["Medical Card"] = {
	onload(listview) {
		listview.page.add_inner_button(__("Issue Cards for a Plan"), () => {
			frappe.prompt({ fieldname: "plan", label: __("Plan"), fieldtype: "Link", options: "Health Plan", reqd: 1 }, (v) => {
				frappe.call({
					method: "a1erp_tpa.tpa_management.doctype.medical_card.medical_card.issue_cards",
					args: { plan: v.plan },
					freeze: true,
					callback: (r) => {
						frappe.show_alert({ message: __("{0} cards issued", [(r.message || []).length]), indicator: "green" });
						listview.refresh();
					},
				});
			}, __("Issue Cards for a Plan"), __("Issue"));
		});
	},
};