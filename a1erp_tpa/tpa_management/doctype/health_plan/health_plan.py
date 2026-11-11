# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class HealthPlan(Document):
	def validate(self):
		if self.from_date and self.to_date and getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("Plan end date cannot be before its start."))
		if self.funding_model == "Self-Funded" and not self.fund:
			frappe.throw(_("Select the health fund of the plan."))
		if self.funding_model == "Multiple Funding Sources":
			total = sum(flt(r.share_percent) for r in self.funding_sources)
			if abs(total - 100) > 0.01:
				frappe.throw(_("Funding shares must total 100% (currently {0}%).").format(flt(total, 2)))
		seen = set()
		for b in self.benefits:
			k = (b.class_name or "", b.benefit_category)
			if k in seen:
				frappe.throw(_("Row {0}: the benefit {1} is already defined for this class.").format(b.idx, _(b.benefit_category)))
			seen.add(k)
			if b.class_name and self.classes and b.class_name not in [c.class_name for c in self.classes]:
				frappe.throw(_("Row {0}: class {1} does not exist.").format(b.idx, b.class_name))
		if self.status == "Active" and not self.is_template and not self.benefits:
			frappe.throw(_("Add the benefits before activating the plan."))
		if self.is_template and self.status == "Active":
			self.status = "Draft"

	@frappe.whitelist()
	def create_plan_from_template(self, plan_name, tpa_client):
		self.check_permission("read")
		if not self.is_template:
			frappe.throw(_("This plan is not a template."))
		new = frappe.copy_doc(self)
		new.plan_name, new.tpa_client, new.is_template, new.status = plan_name, tpa_client, 0, "Draft"
		new.insert()
		return new.name


def expire_plans():
	for name in frappe.get_all("Health Plan", filters={"status": "Active", "to_date": ("<", frappe.utils.nowdate())}, pluck="name"):
		frappe.db.set_value("Health Plan", name, "status", "Expired")