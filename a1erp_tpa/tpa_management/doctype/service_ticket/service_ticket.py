# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, cint, now_datetime

from a1erp_tpa.tpa_management.engine import settings


class ServiceTicket(Document):
	def validate(self):
		if self.is_new():
			for r in settings().sla_rules:
				if r.priority == self.priority:
					now = now_datetime()
					self.response_due = add_to_date(now, hours=cint(r.response_hours))
					self.resolution_due = add_to_date(now, hours=cint(r.resolution_hours))
		before = self.get_doc_before_save()
		if before and before.status == "Open" and self.status != "Open" and not self.first_response_on:
			self.first_response_on = now_datetime()
		if self.status in ("Resolved", "Closed") and not self.resolved_on:
			if not self.resolution:
				frappe.throw(_("Enter the resolution."))
			self.resolved_on = now_datetime()

	def after_insert(self):
		if self.ticket_type == "Complaint" and self.provider:
			frappe.get_doc("Medical Provider", self.provider).refresh_performance()


def escalate_overdue():
	"""Escalate tickets whose resolution time has passed."""
	for name in frappe.get_all("Service Ticket", filters={"status": ("in", ["Open", "In Progress", "Escalated"]), "resolution_due": ("<", now_datetime())}, pluck="name"):
		t = frappe.get_doc("Service Ticket", name)
		t.db_set({"status": "Escalated", "escalation_level": cint(t.escalation_level) + 1})
		for u in frappe.get_all("Has Role", filters={"role": "TPA Manager", "parenttype": "User"}, pluck="parent"):
			if u != "Administrator" and not frappe.db.exists("ToDo", {"reference_type": "Service Ticket", "reference_name": name, "allocated_to": u, "status": "Open"}):
				frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "reference_type": "Service Ticket", "reference_name": name,
					"description": _("Ticket {0} is overdue and was escalated").format(name)}).insert(ignore_permissions=True)