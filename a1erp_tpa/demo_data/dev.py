"""Developer helper: run the generator in the foreground (bench execute a1erp_tpa.demo_data.dev.run)."""

import frappe


def run(profile="Quick Tour"):
	doc = frappe.get_doc({"doctype": "TPA Demo Run", "profile": profile, "seed": 2026, "status": "Queued"})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	from a1erp_tpa.demo_data.runner import execute

	execute(doc.name)
	d = frappe.get_doc("TPA Demo Run", doc.name)
	print(d.name, d.status, "records", d.records, "skipped", d.errors)
	print(d.summary)
	print("\n".join(l for l in (d.log or "").split("\n") if "ERROR" in l)[:6000])