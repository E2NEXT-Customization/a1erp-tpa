# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TPANotificationTemplate(Document):
	def validate(self):
		if self.channel == "Email" and not self.subject:
			frappe.throw(_("Enter the subject of the email."))
		if self.recipients == "Internal Role" and self.channel not in ("In-App", "Email"):
			frappe.throw(_("Internal notifications use the In-App or Email channel."))
		try:
			frappe.render_template(self.message, {"doc": frappe._dict(name="X"), "customer_name": "X", "company": "X", "extra": {}})
		except Exception as e:  # noqa: BLE001
			frappe.throw(_("The message template is invalid: {0}").format(str(e)))
		if self.enabled and frappe.db.exists("TPA Notification Template", {"event": self.event, "channel": self.channel,
				"language": self.language, "recipients": self.recipients, "name": ("!=", self.name or ""), "enabled": 1}):
			frappe.throw(_("An enabled template already exists for this event, channel, language and recipients."))