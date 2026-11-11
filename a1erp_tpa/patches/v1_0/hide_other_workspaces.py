import frappe

OURS = ("TPA Management",)


def execute():
	"""Show only the TPA workspaces in the sidebar of a TPA-only site; other standard workspaces are hidden (not deleted)."""
	if "a1erp_insurance" in frappe.get_installed_apps():
		return
	for name in frappe.get_all("Workspace", filters={"public": 1, "module": ("not in", OURS), "is_hidden": 0}, pluck="name"):
		frappe.db.set_value("Workspace", name, "is_hidden", 1, update_modified=False)
	frappe.clear_cache()
