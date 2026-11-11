import frappe


def execute():
	"""Sites that ran the TPA module inside a1erp_insurance: re-point the module and the Journal Entry links to this app."""
	frappe.db.set_value("Module Def", "TPA Management", "app_name", "a1erp_tpa", update_modified=False)
	if frappe.db.has_column("Journal Entry", "insurance_reference_type") and frappe.db.has_column("Journal Entry", "tpa_reference_type"):
		mine = frappe.get_all("DocType", filters={"module": "TPA Management"}, pluck="name")
		if mine:
			frappe.db.sql("""update `tabJournal Entry` set tpa_reference_type = insurance_reference_type, tpa_reference = insurance_reference,
				insurance_reference_type = null, insurance_reference = null
				where insurance_reference_type in %s""", (tuple(mine),))
	# the TPA message templates used to live among the insurance ones
	if frappe.db.exists("DocType", "Insurance Notification Template"):
		for row in frappe.get_all("Insurance Notification Template", filters={"event": ("in", [
				"Member Activated", "Card Issued", "Coverage Expiring", "Pre-Auth Requested", "Pre-Authorization Decision", "Claim Status Update"])},
				fields=["name"]):
			frappe.delete_doc("Insurance Notification Template", row.name, force=True, ignore_permissions=True)
	# documents of the TPA types kept in the insurance register
	if frappe.db.exists("DocType", "Insurance Document") and frappe.db.exists("DocType", "TPA Document"):
		types = ["Insurer Contract", "Client Contract", "Provider Contract", "Medical Report", "Prescription", "Settlement Document", "Member Document"]
		for name in frappe.get_all("Insurance Document", filters={"document_type": ("in", types)}, pluck="name"):
			row = frappe.db.get_value("Insurance Document", name, "*", as_dict=True)
			supersedes = row.pop("supersedes", None)
			new = frappe.get_doc({**{k: v for k, v in row.items() if k not in ("name", "docstatus", "idx", "modified_by", "owner", "doctype")}, "doctype": "TPA Document"})
			new.flags.ignore_permissions = True
			new.flags.ignore_links = True
			new.insert()
			frappe.db.sql("update `tabTPA Document` set creation=%s, modified=%s where name=%s", (row.creation, row.modified, new.name))
			frappe.db.sql("delete from `tabInsurance Document` where name=%s", name)

	from a1erp_tpa.setup.tpa_defaults import ensure_templates

	ensure_templates()
