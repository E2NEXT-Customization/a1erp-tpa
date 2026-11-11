# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class MedicalCase(Document):
	def validate(self):
		self.cost_to_date = flt(frappe.db.sql("""select coalesce(sum(payer_amount), 0) from `tabMedical Claim` where docstatus = 1 and member = %s
			and status in ('Approved', 'Partially Approved', 'Ready for Payment', 'Paid', 'Closed') and service_date >= %s""",
			(self.member, self.opened_on or nowdate()))[0][0])
		if self.status == "Closed" and not self.closed_on:
			self.closed_on = nowdate()