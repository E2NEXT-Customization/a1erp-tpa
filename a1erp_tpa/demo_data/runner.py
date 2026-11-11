"""Background jobs of the demo data console: generate a run, or remove everything the runs created."""

import json
import traceback

import frappe
from frappe.utils import add_months, cint, now_datetime, nowdate

from a1erp_tpa.demo_data import tpa
from a1erp_tpa.demo_data.builder import Ctx, ensure_fiscal_years, quiet


def execute(run):
	frappe.set_user("Administrator")
	frappe.flags.in_demo_data = True
	doc = frappe.get_doc("TPA Demo Run", run)
	doc.db_set({"status": "Running", "started_on": now_datetime(), "progress": 0, "current_step": "Starting", "errors": 0}, update_modified=False)
	frappe.db.commit()
	ctx = Ctx(doc)
	status = "Completed"
	try:
		ensure_fiscal_years(ctx.company, add_months(nowdate(), -(cint(ctx.p.months) + 8)))
		frappe.db.commit()
		with quiet():
			ctx.phase = (0, 98)
			tpa.masters(ctx)
			tpa.members(ctx)
			tpa.activity(ctx)
		if ctx.errors:
			status = "Completed with Errors"
	except Exception:  # noqa: BLE001
		frappe.db.rollback()
		status = "Failed"
		ctx.log("Stopped: " + traceback.format_exc().strip().splitlines()[-1], error=True)
		frappe.log_error(title="Demo data run failed", message=traceback.format_exc())
	finally:
		frappe.flags.in_demo_data = False
		summary = frappe.db.sql("select ref_doctype, count(*) from `tabTPA Demo Record` where run = %s group by ref_doctype order by 2 desc", doc.name)
		frappe.db.set_value("TPA Demo Run", doc.name, {"status": status, "finished_on": now_datetime(), "progress": 100 if status != "Failed" else ctx.phase[0],
			"current_step": "Finished" if status != "Failed" else "Stopped", "records": ctx.created, "errors": ctx.errors, "log": "\n".join(ctx.lines),
			"highlights": json.dumps(ctx.highlights, ensure_ascii=False), "backup": json.dumps(ctx.backup, ensure_ascii=False),
			"summary": json.dumps(dict(summary), ensure_ascii=False)}, update_modified=False)
		frappe.db.commit()
		frappe.publish_realtime("tpa_demo_progress", {"run": doc.name, "progress": 100, "step": status, "done": 1})


# ------------------------------------------------------------------- cleanup
def clear(job_run=None):
	"""Remove every record created by the demo runs, newest first, then the journal entries they caused."""
	frappe.set_user("Administrator")
	runs = frappe.get_all("TPA Demo Run", filters={"status": ("not in", ["Cleared"])}, pluck="name")
	if job_run:
		frappe.db.set_value("TPA Demo Run", job_run, {"status": "Cleaning", "current_step": "Removing demo data", "progress": 0}, update_modified=False)
		frappe.db.commit()
	rows = frappe.db.sql("select ref_doctype, ref_name from `tabTPA Demo Record` where run in %s order by seq desc", (runs or [""],))
	names = {}
	for dt, name in rows:
		names.setdefault(dt, set()).add(name)
	all_names = {n for s in names.values() for n in s}
	total = len(rows) or 1
	done = 0
	log = []

	def tick(step):
		if job_run and done % 50 == 0:
			frappe.db.set_value("TPA Demo Run", job_run, {"progress": round(done * 100 / (total * 2 + 1), 1), "current_step": step}, update_modified=False)
			frappe.db.commit()

	frappe.flags.in_test = True  # Frappe then removes versions, comments and shares of each deleted record inline instead of queueing a job per record
	with quiet():
		# 1. cancel submitted documents, newest first (payments before claims before policies)
		for dt, name in rows:
			done += 1
			if not frappe.db.exists(dt, name):
				continue
			meta = frappe.get_meta(dt)
			if meta.is_submittable and frappe.db.get_value(dt, name, "docstatus") == 1:
				try:
					d = frappe.get_doc(dt, name)
					d.flags.ignore_permissions = True
					d.flags.ignore_links = True
					d.cancel()
					frappe.db.commit()
				except Exception as e:  # noqa: BLE001
					frappe.db.rollback()
					log.append(f"cancel {dt} {name}: {str(e)[:120]}")
			tick("Cancelling transactions")
		# 2. journal entries and ledger rows created by those documents
		jes = frappe.get_all("Journal Entry", filters={"tpa_reference": ("in", list(all_names) or [""])}, pluck="name")
		vouchers = [("Journal Entry", j) for j in jes] + [("Payment Entry", p) for p in names.get("Payment Entry", [])]
		for vt, vn in vouchers:
			for t in ("GL Entry", "Payment Ledger Entry"):
				frappe.db.delete(t, {"voucher_type": vt, "voucher_no": vn})
			if vt == "Journal Entry" and frappe.db.exists("Journal Entry", vn):
				frappe.db.delete("Journal Entry Account", {"parent": vn})
				frappe.db.delete("Journal Entry", {"name": vn})
		frappe.db.commit()
		# 3. records the application created on its own
		dependants = [("FWA Alert", "claim", names.get("Medical Claim")), ("FWA Alert", "member", names.get("Plan Member")),
			("Medical Case", "member", names.get("Plan Member")), ("Medical Card", "member", names.get("Plan Member")),
			("TPA Notification Log", "reference_name", all_names), ("TPA Document", "reference_name", all_names),
			("File", "attached_to_name", all_names), ("ToDo", "reference_name", all_names)]
		for dt, field, keys in dependants:
			if not keys or not frappe.db.table_exists(dt):
				continue
			for n in frappe.get_all(dt, filters={field: ("in", list(keys))}, pluck="name"):
				try:
					frappe.delete_doc(dt, n, force=1, ignore_permissions=True, delete_permanently=True)
				except Exception:  # noqa: BLE001
					frappe.db.delete(dt, {"name": n})
		frappe.db.commit()
		# 4. delete the records
		for dt, name in rows:
			done += 1
			if frappe.db.exists(dt, name):
				try:
					frappe.delete_doc(dt, name, force=1, ignore_permissions=True, delete_permanently=True)
					frappe.db.commit()
				except Exception as e:  # noqa: BLE001
					frappe.db.rollback()
					log.append(f"delete {dt} {name}: {str(e)[:120]}")
			tick("Deleting records")
	frappe.flags.in_test = False
	frappe.db.delete("TPA Demo Record", {"run": ("in", runs or [""])})
	for r in runs:
		frappe.db.set_value("TPA Demo Run", r, {"status": "Cleared", "progress": 100, "current_step": "Removed"}, update_modified=False)
	if job_run:
		frappe.db.set_value("TPA Demo Run", job_run, {"log": "\n".join(log[-300:]) or "All demo records were removed."}, update_modified=False)
	frappe.db.commit()
	frappe.publish_realtime("tpa_demo_progress", {"run": job_run, "progress": 100, "step": "Cleared", "done": 1})
	return {"removed": len(rows), "problems": log[:20]}
