# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate


class MedicalProvider(Document):
	def validate(self):
		if self.contract_from and self.contract_to and getdate(self.contract_to) < getdate(self.contract_from):
			frappe.throw(_("Contract end cannot be before the start."))
		if self.license_expiry and getdate(self.license_expiry) < getdate(nowdate()) and self.status == "Active":
			frappe.msgprint(_("The license of the provider has expired."), indicator="orange", alert=True)
		if self.parent_provider == self.name:
			frappe.throw(_("A provider cannot be its own main provider."))
		if self.status == "Active" and not self.supplier:
			frappe.msgprint(_("Link a supplier to be able to pay this provider."), indicator="orange", alert=True)

	@frappe.whitelist()
	def refresh_performance(self):
		rows = frappe.db.sql("""select count(*), sum(status in ('Rejected')) from `tabMedical Claim` where provider = %s and docstatus = 1""", self.name)[0]
		self.db_set({"rejection_rate": flt((rows[1] or 0) / rows[0] * 100, 1) if rows[0] else 0,
			"complaints_count": frappe.db.count("Service Ticket", {"provider": self.name, "ticket_type": "Complaint"})}, update_modified=False)

	@frappe.whitelist()
	def create_supplier(self):
		self.check_permission("write")
		if self.supplier:
			frappe.throw(_("A supplier is already linked."))
		s = frappe.get_doc({"doctype": "Supplier", "supplier_name": self.provider_name, "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}),
			"supplier_type": "Company"}).insert()
		self.db_set("supplier", s.name)
		return s.name