// Buttons and dialogs of the TPA module forms. Every action calls a whitelisted method of the document controller.

(function () {
	const run = (frm, method, args, done) =>
		frm.call(method, args || {}).then((r) => {
			frm.reload_doc();
			if (done) done(r);
		});
	const btn = (frm, label, fn, primary) => {
		const b = frm.add_custom_button(__(label), fn);
		if (primary) b.addClass("btn-primary");
		return b;
	};
	const ask = (title, fields, primary, fn) => {
		const d = new frappe.ui.Dialog({ title: __(title), fields: fields, primary_action_label: __(primary), primary_action(v) { d.hide(); fn(v); } });
		d.show();
	};
	const saved = (frm) => !frm.is_new() && !frm.is_dirty();

	frappe.ui.form.on("Plan Member", {
		refresh(frm) {
			if (!saved(frm)) return;
			if (frm.doc.status === "Pending") btn(frm, "Activate", () => run(frm, "activate"), true);
			if (frm.doc.status === "Active") {
				btn(frm, "Suspend", () => ask("Suspend", [{ fieldname: "reason", label: __("Reason"), fieldtype: "Data", reqd: 1 }], "Suspend", (v) => run(frm, "suspend", { reason: v.reason })), false);
				btn(frm, "Terminate", () => ask("Terminate", [{ fieldname: "reason", label: __("Reason"), fieldtype: "Data", reqd: 1 }], "Terminate", (v) => run(frm, "terminate", { reason: v.reason })), false);
			}
			if (frm.doc.status === "Suspended") btn(frm, "Reinstate", () => run(frm, "reinstate"), true);
		},
	});

	frappe.ui.form.on("Medical Card", {
		refresh(frm) {
			if (!saved(frm) || frm.doc.status !== "Active") return;
			btn(frm, "Replace Card", () => ask("Replace Card", [
				{ fieldname: "reason", label: __("Reason for Replacement"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "lost", label: __("Lost"), fieldtype: "Check" },
			], "Replace", (v) => frm.call("replace", { reason: v.reason, lost: v.lost ? 1 : 0 }).then((r) => {
				if (r.message) frappe.set_route("Form", "Medical Card", r.message);
				else frm.reload_doc();
			})));
		},
	});

	frappe.ui.form.on("Provider Tariff", {
		refresh(frm) {
			if (saved(frm) && frm.doc.status === "Draft") btn(frm, "Activate", () => run(frm, "activate"), true);
		},
	});

	frappe.ui.form.on("Medical Provider", {
		refresh(frm) {
			if (!saved(frm)) return;
			if (!frm.doc.supplier) btn(frm, "Create Supplier", () => run(frm, "create_supplier"));
			btn(frm, "Refresh Performance", () => run(frm, "refresh_performance"));
		},
	});

	frappe.ui.form.on("Health Plan", {
		refresh(frm) {
			if (!saved(frm) || !frm.doc.is_template) return;
			btn(frm, "Create Plan from Template", () => ask("Create Plan from Template", [
				{ fieldname: "plan_name", label: __("Plan Name"), fieldtype: "Data", reqd: 1 },
				{ fieldname: "tpa_client", label: __("Client"), fieldtype: "Link", options: "TPA Client", reqd: 1 },
			], "Create", (v) => frm.call("create_plan_from_template", v).then((r) => r.message && frappe.set_route("Form", "Health Plan", r.message))));
		},
	});

	frappe.ui.form.on("Health Fund", {
		refresh(frm) {
			if (saved(frm)) btn(frm, "Refresh Balance", () => run(frm, "refresh"));
		},
	});

	frappe.ui.form.on("Pre-Authorization", {
		refresh(frm) {
			if (!saved(frm)) return;
			const s = frm.doc.status;
			if (s === "Draft") btn(frm, "Submit Request", () => run(frm, "submit_request", {}, (r) => {
				const res = r.message || {};
				frappe.msgprint({ title: __("Eligibility Checks"), message: (res.log || []).map(frappe.utils.escape_html).join("<br>"), indicator: res.eligible ? "green" : "orange" });
			}), true);
			if (["Under Review", "Submitted", "Pending Information"].includes(s)) btn(frm, "Start Review", () => run(frm, "start_review"));
			if (["Under Review", "Submitted", "Medical Review", "Pending Information"].includes(s)) {
				btn(frm, "Decision", () => {
					const d = new frappe.ui.Dialog({
						title: __("Decision"),
						fields: [
							{ fieldname: "decision", label: __("Decision"), fieldtype: "Select", options: "Approve\nReject\nRequest Information", reqd: 1, default: "Approve" },
							{ fieldname: "reason", label: __("Rejection Reason"), fieldtype: "Link", options: "Claim Rejection Reason", depends_on: "eval:doc.decision=='Reject'", mandatory_depends_on: "eval:doc.decision=='Reject'" },
							{ fieldname: "info", label: __("Information Requested"), fieldtype: "Small Text", depends_on: "eval:doc.decision=='Request Information'", mandatory_depends_on: "eval:doc.decision=='Request Information'" },
							{ fieldname: "rejected_rows", label: __("Rows to Reject (e.g. 2,3)"), fieldtype: "Data", depends_on: "eval:doc.decision=='Approve'" },
							{ fieldname: "notes", label: __("Decision Notes"), fieldtype: "Small Text" },
						],
						primary_action_label: __("Save Decision"),
						primary_action(v) {
							d.hide();
							const rows = (v.rejected_rows || "").split(",").map((x) => parseInt(x, 10)).filter((x) => x);
							run(frm, "decide", { decision: v.decision, notes: v.notes, reason: v.reason, info: v.info, rejected_rows: JSON.stringify(rows) });
						},
					});
					d.show();
				}, true);
			}
			if (["Approved", "Partially Approved", "Under Review", "Medical Review"].includes(s)) {
				btn(frm, "Cancel Authorization", () => ask("Cancel Authorization", [{ fieldname: "reason", label: __("Reason"), fieldtype: "Data" }], "Cancel Authorization", (v) => run(frm, "cancel_auth", { reason: v.reason })));
			}
		},
	});

	const CLAIM_NEXT = ["Under Review", "Medical Review", "Financial Review", "Pending Information", "Approved", "Partially Approved", "Rejected"];
	frappe.ui.form.on("Medical Claim", {
		refresh(frm) {
			if (frm.is_new()) return;
			if (frm.doc.docstatus === 0) btn(frm, "Calculate", () => frm.call("calculate").then(() => frm.reload_doc()));
			if (frm.doc.docstatus === 1 && !["Ready for Payment", "Paid", "Closed"].includes(frm.doc.status)) {
				btn(frm, "Change Status", () => {
					const d = new frappe.ui.Dialog({
						title: __("Change Status"),
						fields: [
							{ fieldname: "new_status", label: __("Status"), fieldtype: "Select", options: CLAIM_NEXT.join("\n"), reqd: 1 },
							{ fieldname: "reason", label: __("Rejection Reason"), fieldtype: "Link", options: "Claim Rejection Reason", depends_on: "eval:doc.new_status=='Rejected'", mandatory_depends_on: "eval:doc.new_status=='Rejected'" },
							{ fieldname: "info", label: __("Information Requested"), fieldtype: "Small Text", depends_on: "eval:doc.new_status=='Pending Information'", mandatory_depends_on: "eval:doc.new_status=='Pending Information'" },
							{ fieldname: "notes", label: __("Review Notes"), fieldtype: "Small Text" },
						],
						primary_action_label: __("Save"),
						primary_action(v) {
							d.hide();
							run(frm, "set_status", { new_status: v.new_status, notes: v.notes, reason: v.reason, info: v.info });
						},
					});
					d.show();
				}, true);
			}
		},
	});

	frappe.ui.form.on("Provider Settlement", {
		refresh(frm) {
			if (frm.is_new() || frm.doc.docstatus === 0) {
				if (frm.doc.provider && frm.doc.period_from && frm.doc.period_to) {
					btn(frm, "Fetch Claims", () => frm.call("fetch_claims").then(() => frm.refresh()), true);
				}
			}
			if (frm.doc.docstatus === 1 && !frm.doc.payment_entry) btn(frm, "Make Payment", () => run(frm, "make_payment", {}, (r) => {
				if (r.message) frappe.show_alert({ message: __("Payment Entry") + ": " + r.message, indicator: "green" });
			}), true);
		},
	});
})();
