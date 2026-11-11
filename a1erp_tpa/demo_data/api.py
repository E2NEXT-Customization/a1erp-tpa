"""Server side of the Demo Data Console page."""

import json

import frappe
from frappe import _
from frappe.utils import cint

from a1erp_tpa.demo_data.builder import PROFILES

MODULE_DOCTYPES = {
	"Health TPA": ["TPA Client", "Provider Network", "Medical Provider", "Medical Code", "Medical Service", "Drug", "Provider Tariff", "Health Fund", "Fund Contribution",
		"Health Plan", "Plan Member", "Medical Card", "Medical Reviewer", "Pre-Authorization", "Medical Claim", "Provider Settlement", "TPA Fee Invoice",
		"FWA Watchlist", "Medical Case", "Service Ticket", "TPA Document", "File"],
}


def guard():
	frappe.only_for(("System Manager",))


def workers():
	try:
		from frappe.utils.background_jobs import get_workers

		return len(get_workers())
	except Exception:  # noqa: BLE001
		return -1


@frappe.whitelist()
def overview():
	guard()
	last = frappe.get_all("TPA Demo Run", fields=["name", "profile", "status", "progress", "current_step", "records", "errors", "started_on", "finished_on",
		"creation"], order_by="creation desc", limit=1)
	last = last[0] if last else None
	created = dict(frappe.db.sql("""select r.ref_doctype, count(*) from `tabTPA Demo Record` r join `tabTPA Demo Run` d on d.name = r.run
		where d.status != 'Cleared' group by r.ref_doctype"""))
	groups = []
	for group, doctypes in MODULE_DOCTYPES.items():
		rows = []
		for dt in doctypes:
			rows.append({"doctype": dt, "label": _(dt), "demo": cint(created.get(dt)), "total": frappe.db.count(dt) if frappe.db.table_exists(dt) else 0,
				"route": frappe.scrub(dt).replace("_", "-")})
		groups.append({"group": _(group), "rows": rows})
	highlights = []
	runs = frappe.get_all("TPA Demo Run", filters={"status": ("in", ["Completed", "Completed with Errors"])}, fields=["highlights"], order_by="creation desc", limit=3)
	for r in runs:
		for h in json.loads(r.highlights or "[]"):
			h["route"] = frappe.scrub(h["doctype"]).replace("_", "-")
			highlights.append(h)
	return {"last": last, "groups": groups, "highlights": highlights, "workers": workers(), "has_data": bool(created),
		"profiles": PROFILES, "log": frappe.db.get_value("TPA Demo Run", last.name, "log") if last else ""}


@frappe.whitelist()
def start(profile="Standard", seed=2026):
	guard()
	if profile not in PROFILES:
		frappe.throw(_("Unknown size."))
	if frappe.db.exists("TPA Demo Run", {"status": ("in", ["Queued", "Running", "Cleaning"])}):
		frappe.throw(_("A demo data job is already running."))
	doc = frappe.get_doc({"doctype": "TPA Demo Run", "profile": profile, "seed": cint(seed) or 2026, "status": "Queued", "current_step": "Waiting for the background worker"})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.enqueue("a1erp_tpa.demo_data.runner.execute", queue="long", timeout=4 * 3600, run=doc.name, job_id=f"demo-data-{doc.name}",
		deduplicate=True, enqueue_after_commit=False)
	return doc.name


@frappe.whitelist()
def clear():
	guard()
	if frappe.db.exists("TPA Demo Run", {"status": ("in", ["Queued", "Running", "Cleaning"])}):
		frappe.throw(_("A demo data job is already running."))
	if not frappe.db.exists("TPA Demo Run", {"status": ("not in", ["Cleared"])}):
		frappe.throw(_("There is no demo data to remove."))
	doc = frappe.get_doc({"doctype": "TPA Demo Run", "profile": "Standard", "status": "Cleaning",
		"current_step": "Waiting for the background worker"})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	frappe.enqueue("a1erp_tpa.demo_data.runner.clear", queue="long", timeout=4 * 3600, job_run=doc.name, job_id=f"demo-clear-{doc.name}",
		deduplicate=True, enqueue_after_commit=False)
	return doc.name
