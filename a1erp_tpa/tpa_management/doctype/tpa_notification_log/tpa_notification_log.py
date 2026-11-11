# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TPANotificationLog(Document):
	@frappe.whitelist()
	def resend(self):
		self.check_permission("write")
		if self.status == "Sent":
			frappe.throw(_("This notification was already sent."))
		from a1erp_tpa.tpa_management.notifications import send_log

		if self.status == "Cancelled":
			self.db_set("status", "Failed")
		send_log(self.name)

	@frappe.whitelist()
	def cancel_sending(self):
		self.check_permission("write")
		if self.status not in ("Scheduled", "Failed"):
			frappe.throw(_("Only a scheduled or failed notification can be cancelled."))
		self.db_set("status", "Cancelled")