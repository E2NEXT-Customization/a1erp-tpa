# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from a1erp_tpa.tpa_management.accounting import JournalBuilder, cancel_journal_entries
from a1erp_tpa.tpa_management.engine import settings
from a1erp_tpa.tpa_management.posting import refresh_fund


class FundContribution(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("The amount must be positive."))
		if frappe.db.get_value("Health Fund", self.fund, "status") != "Active":
			frappe.throw(_("The fund is not active."))

	def on_submit(self):
		acc = frappe.db.get_value("Health Fund", self.fund, "liability_account") or settings().fund_liability_account
		if not acc:
			frappe.throw(_("Set the liability account of the fund."))
		company = settings().company or frappe.db.get_value("Company", {}, "name")
		jb = JournalBuilder(company, self.posting_date, self.doctype, self.name, _("Contribution to fund {0}").format(self.fund))
		jb.dr(self.bank_account, self.amount)
		jb.cr(acc, self.amount)
		self.db_set("journal_entry", jb.post())
		refresh_fund(self.fund)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry", "Journal Entry")
		cancel_journal_entries(self.doctype, self.name)
		refresh_fund(self.fund)