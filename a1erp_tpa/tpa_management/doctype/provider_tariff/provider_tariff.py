# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, nowdate


class ProviderTariff(Document):
	def validate(self):
		if not (self.provider or self.network):
			frappe.throw(_("Select a provider or a network."))
		if self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
			frappe.throw(_("Valid To cannot be before Valid From."))
		seen = set()
		for r in self.items:
			k = (r.item_type, r.service or r.drug)
			if not (r.service or r.drug):
				frappe.throw(_("Row {0}: select the service or the drug.").format(r.idx))
			if k in seen:
				frappe.throw(_("Row {0}: the item appears more than once.").format(r.idx))
			seen.add(k)
		before = self.get_doc_before_save()
		if before and before.status == "Active" and self.status == "Active" and (before.valid_from != self.valid_from or flt(before.discount_percent) != flt(self.discount_percent)
				or self.price_signature() != ProviderTariff.price_signature(before)):
			frappe.throw(_("An active tariff cannot be changed. Create a new tariff with a later start date."))

	def price_signature(self):
		return sorted((r.item_type, r.service or "", r.drug or "", flt(r.price), flt(r.discount_percent)) for r in self.items)

	@frappe.whitelist()
	def activate(self):
		self.check_permission("write")
		if self.status != "Draft":
			frappe.throw(_("Only a draft tariff can be activated."))
		for t in frappe.get_all("Provider Tariff", filters={"status": "Active", "provider": self.provider or ("is", "not set"),
				"network": self.network or ("is", "not set"), "tpa_client": self.tpa_client or ("is", "not set"),
				"plan": self.plan or ("is", "not set"), "name": ("!=", self.name)}, fields=["name", "valid_from"]):
			if getdate(t.valid_from) >= getdate(self.valid_from):
				frappe.throw(_("Tariff {0} already starts on or after this date.").format(t.name))
			frappe.db.set_value("Provider Tariff", t.name, {"status": "Expired", "valid_to": add_days(self.valid_from, -1)})
		self.db_set("status", "Active")


def expire_tariffs():
	for name in frappe.get_all("Provider Tariff", filters={"status": "Active", "valid_to": ("<", nowdate())}, pluck="name"):
		frappe.db.set_value("Provider Tariff", name, "status", "Expired")