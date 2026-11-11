# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint, getdate, now_datetime, nowdate

from a1erp_tpa.tpa_management.engine import age_of


class PlanMember(Document):
	def validate(self):
		plan = frappe.get_doc("Health Plan", self.plan)
		self.tpa_client = plan.tpa_client
		if plan.is_template:
			frappe.throw(_("A template plan cannot have members."))
		if self.relationship == "Principal":
			self.principal = None
		else:
			if not self.principal:
				frappe.throw(_("Select the principal member."))
			if frappe.db.get_value("Plan Member", self.principal, "plan") != self.plan:
				frappe.throw(_("The principal member belongs to another plan."))
		if plan.classes and not self.class_name:
			frappe.throw(_("Select the class of the member."))
		if self.class_name and plan.classes and self.class_name not in [c.class_name for c in plan.classes]:
			frappe.throw(_("Class {0} does not exist in the plan.").format(self.class_name))
		self.start_date = self.start_date or plan.from_date or nowdate()
		self.end_date = self.end_date or plan.to_date
		if self.end_date and getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("Coverage end cannot be before the start."))
		self.age = age_of(self, nowdate())
		self.check_duplicates()
		before = self.get_doc_before_save()
		if before and before.status != self.status:
			self.append("status_log", {"changed_on": now_datetime(), "from_status": before.status, "to_status": self.status,
				"reason": self.status_reason, "changed_by": frappe.session.user})
		if not self.card_no:
			self.card_no = make_autoname("MC-.YYYY.-.######")

	def check_duplicates(self):
		"""No duplicate registration and no overlapping coverage under two plans for the same person."""
		others = frappe.get_all("Plan Member", filters={"national_id": self.national_id, "name": ("!=", self.name or ""),
			"status": ("in", ["Pending", "Active", "Suspended"])}, fields=["name", "plan", "start_date", "end_date"])
		for o in others:
			if o.plan == self.plan:
				frappe.throw(_("The person is already registered in this plan ({0}).").format(o.name))
			s2, e2 = getdate(o.start_date), getdate(o.end_date) if o.end_date else getdate("2999-12-31")
			s1, e1 = getdate(self.start_date), getdate(self.end_date) if self.end_date else getdate("2999-12-31")
			if s1 <= e2 and s2 <= e1:
				frappe.throw(_("The person already has overlapping coverage under {0}.").format(o.name))

	def set_status(self, status, reason=None):
		self.status_reason = reason
		self.status = status
		self.save()

	@frappe.whitelist()
	def activate(self):
		self.check_permission("write")
		self.set_status("Active")
		if not frappe.db.exists("Medical Card", {"member": self.name, "status": "Active"}):
			frappe.get_doc({"doctype": "Medical Card", "member": self.name}).insert()
		from a1erp_tpa.tpa_management.notifications import notify

		notify("Member Activated", self)

	@frappe.whitelist()
	def suspend(self, reason):
		self.check_permission("write")
		if not reason:
			frappe.throw(_("Enter the reason."))
		self.set_status("Suspended", reason)

	@frappe.whitelist()
	def reinstate(self):
		self.check_permission("write")
		self.set_status("Active", _("Reinstated"))

	@frappe.whitelist()
	def terminate(self, reason):
		self.check_permission("write")
		if not reason:
			frappe.throw(_("Enter the reason."))
		self.set_status("Terminated", reason)
		for c in frappe.get_all("Medical Card", filters={"member": self.name, "status": "Active"}, pluck="name"):
			frappe.db.set_value("Medical Card", c, "status", "Cancelled")


def expire_members():
	for name in frappe.get_all("Plan Member", filters={"status": "Active", "end_date": ("<", nowdate())}, pluck="name"):
		frappe.get_doc("Plan Member", name).set_status("Expired", _("Coverage period ended"))


def remind_expiring(days=30):
	"""Tell members whose cover ends within $days days (once per end date)."""
	from frappe.utils import add_days

	from a1erp_tpa.tpa_management.notifications import notify

	for name in frappe.get_all("Plan Member", filters={"status": "Active", "end_date": ("between", [nowdate(), add_days(nowdate(), days)])}, pluck="name"):
		notify("Coverage Expiring", frappe.get_doc("Plan Member", name), dedupe=str(frappe.db.get_value("Plan Member", name, "end_date")))
