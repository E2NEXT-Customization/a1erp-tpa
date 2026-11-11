"""Installation of the TPA app: roles, Journal Entry link fields and default configuration."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from a1erp_tpa.setup.tpa_defaults import TPA_ROLES


def before_install():
	create_roles()


def after_install():
	create_roles()
	make_custom_fields()
	from a1erp_tpa.setup.tpa_defaults import ensure_tpa_defaults

	ensure_tpa_defaults()


def after_migrate():
	create_roles()
	make_custom_fields()


def create_roles():
	for role in TPA_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def make_custom_fields():
	create_custom_fields({
		"Journal Entry": [
			{"fieldname": "tpa_reference_type", "label": "TPA Reference Type", "fieldtype": "Link", "options": "DocType",
				"insert_after": "user_remark", "read_only": 1, "no_copy": 1, "print_hide": 1},
			{"fieldname": "tpa_reference", "label": "TPA Reference", "fieldtype": "Dynamic Link", "options": "tpa_reference_type",
				"insert_after": "tpa_reference_type", "read_only": 1, "no_copy": 1, "in_standard_filter": 1, "search_index": 1},
		]
	}, update=True)
