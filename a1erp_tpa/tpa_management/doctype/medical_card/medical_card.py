# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, getdate, nowdate

from a1erp_tpa.tpa_management.engine import settings


class MedicalCard(Document):
	def validate(self):
		m = frappe.get_doc("Plan Member", self.member)
		if self.is_new() and m.status not in ("Active", "Pending"):
			frappe.throw(_("Cards are issued to active members only."))
		if not self.valid_until:
			months = cint(settings().card_validity_months) or 12
			self.valid_until = m.end_date or add_months(self.issue_date or nowdate(), months)

	def after_insert(self):
		for name in frappe.get_all("Medical Card", filters={"member": self.member, "status": "Active", "name": ("!=", self.name)}, pluck="name"):
			frappe.db.set_value("Medical Card", name, {"status": "Replaced", "replaced_by": self.name})
		from a1erp_tpa.tpa_management.notifications import notify

		notify("Card Issued", self)

	@frappe.whitelist()
	def replace(self, reason, lost=0):
		self.check_permission("write")
		if self.status != "Active":
			frappe.throw(_("Only an active card can be replaced."))
		new = frappe.get_doc({"doctype": "Medical Card", "member": self.member}).insert()
		frappe.db.set_value("Medical Card", self.name, {"status": "Lost" if cint(lost) else "Replaced", "replaced_by": new.name, "reissue_reason": reason})
		return new.name


@frappe.whitelist()
def issue_cards(plan):
	"""Issue a card to every active member of the plan who has none (group issuance); returns the names of the new cards."""
	frappe.has_permission("Medical Card", "create", throw=True)
	out = []
	for m in frappe.get_all("Plan Member", filters={"plan": plan, "status": "Active"}, pluck="name"):
		if not frappe.db.exists("Medical Card", {"member": m, "status": "Active"}):
			out.append(frappe.get_doc({"doctype": "Medical Card", "member": m}).insert().name)
	return out
