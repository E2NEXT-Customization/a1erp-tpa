# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class TPANotificationProvider(Document):
	def validate(self):
		if not self.endpoint_url.lower().startswith(("http://", "https://")):
			frappe.throw(_("The endpoint must be an http(s) URL."))
		if self.extra_headers:
			try:
				json.loads(self.extra_headers)
			except ValueError:
				frappe.throw(_("Extra headers must be valid JSON."))

	@frappe.whitelist()
	def send_test(self, mobile, message=None):
		self.check_permission("write")
		from a1erp_tpa.tpa_management.notifications import http_send

		http_send(self, mobile, message or _("Test message from the health insurance TPA system"))
		return _("The provider accepted the message.")