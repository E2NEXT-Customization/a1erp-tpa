# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from a1erp_tpa.tpa_management.accounting import cancel_journal_entries, get_payable_outstanding
from a1erp_tpa.tpa_management.doctype.pre_authorization.pre_authorization import check_level
from a1erp_tpa.tpa_management.engine import rnd, settings

OPEN = ("Approved", "Partially Approved")


class ProviderSettlement(Document):
	@frappe.whitelist()
	def fetch_claims(self):
		"""Load the approved claims of the provider that are not in another settlement."""
		self.set("claims", [])
		rows = frappe.get_all("Medical Claim", filters={"docstatus": 1, "provider": self.provider, "status": ("in", list(OPEN)),
			"settlement": ("is", "not set"), "service_date": ("between", [self.period_from, self.period_to]), "currency": self.currency},
			fields=["name", "service_date", "member_name", "payer_amount"], order_by="service_date")
		for r in rows:
			self.append("claims", {"claim": r.name, "service_date": r.service_date, "member_name": r.member_name, "payer_amount": r.payer_amount})
		self.totals()

	def totals(self):
		self.gross_payable = rnd(sum(flt(c.payer_amount) for c in self.claims))
		self.adjustments_total = rnd(sum(flt(a.amount) for a in self.adjustments))
		self.net_payable = rnd(self.gross_payable - self.adjustments_total)

	def validate(self):
		if getdate(self.period_to) < getdate(self.period_from):
			frappe.throw(_("The period end cannot be before its start."))
		for c in self.claims:
			v = frappe.db.get_value("Medical Claim", c.claim, ["provider", "status", "settlement", "currency", "payer_amount", "docstatus"], as_dict=True)
			if v.provider != self.provider or v.currency != self.currency:
				frappe.throw(_("Claim {0} belongs to another provider or currency.").format(c.claim))
			if v.status not in OPEN or (v.settlement and v.settlement != self.name):
				frappe.throw(_("Claim {0} is not available for settlement.").format(c.claim))
			c.payer_amount = v.payer_amount
		if not self.claims:
			frappe.throw(_("Load the claims to settle."))
		self.totals()
		if self.net_payable <= 0:
			frappe.throw(_("The net payable must be positive."))

	def before_submit(self):
		check_level("Provider Settlement", self.net_payable)

	def on_submit(self):
		for c in self.claims:
			frappe.db.set_value("Medical Claim", c.claim, {"settlement": self.name, "status": "Ready for Payment"})

	def on_cancel(self):
		if self.payment_entry and frappe.db.get_value("Payment Entry", self.payment_entry, "docstatus") == 1:
			frappe.throw(_("Cancel the payment entry first."))
		for c in self.claims:
			frappe.db.set_value("Medical Claim", c.claim, {"settlement": None, "status": "Approved"})

	@frappe.whitelist()
	def make_payment(self):
		"""Pay the provider: one payment entry against the claim journals, with the adjustments as deductions."""
		self.check_permission("write")
		if self.docstatus != 1 or self.payment_entry:
			frappe.throw(_("The settlement must be submitted and not yet paid."))
		from erpnext.accounts.party import get_party_account

		st = settings()
		bank = st.provider_payment_account or frappe.get_cached_value("Company", self.company, "default_bank_account") or frappe.get_cached_value("Company", self.company, "default_cash_account")
		if not bank:
			frappe.throw(_("Set the default bank or cash account for provider payments in TPA Settings."))
		supplier = frappe.db.get_value("Medical Provider", self.provider, "supplier")
		pe = frappe.new_doc("Payment Entry")
		pe.payment_type, pe.company, pe.posting_date = "Pay", self.company, nowdate()
		pe.party_type, pe.party, pe.party_name = "Supplier", supplier, frappe.db.get_value("Supplier", supplier, "supplier_name")
		pe.paid_from = bank
		pe.paid_to = get_party_account("Supplier", supplier, self.company)
		pe.paid_from_account_currency = frappe.get_cached_value("Account", bank, "account_currency")
		pe.paid_to_account_currency = frappe.get_cached_value("Account", pe.paid_to, "account_currency")
		pe.paid_amount = pe.received_amount = self.net_payable
		pe.source_exchange_rate = pe.target_exchange_rate = 1
		pe.reference_no, pe.reference_date = self.name, nowdate()
		for c in self.claims:
			je = frappe.db.get_value("Medical Claim", c.claim, "journal_entry")
			outstanding = get_payable_outstanding(je, "Supplier", supplier)
			if outstanding > 0:
				pe.append("references", {"reference_doctype": "Journal Entry", "reference_name": je, "total_amount": outstanding,
					"outstanding_amount": outstanding, "allocated_amount": min(flt(c.payer_amount), outstanding)})
		if flt(self.adjustments_total):
			if not st.adjustments_account:
				frappe.throw(_("Set the settlement adjustments account in TPA Settings."))
			pe.append("deductions", {"account": st.adjustments_account, "cost_center": frappe.get_cached_value("Company", self.company, "cost_center"),
				"amount": -flt(self.adjustments_total)})
		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.flags.ignore_permissions = True
		pe.insert()
		pe.submit()
		self.db_set("payment_entry", pe.name)
		for c in self.claims:
			frappe.db.set_value("Medical Claim", c.claim, {"status": "Paid", "paid_on": nowdate()})
		return pe.name