# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt, getdate

from a1erp_tpa.tpa_management.accounting import JournalBuilder, cancel_journal_entries
from a1erp_tpa.tpa_management.engine import ADJUDICATED, rnd, settings
from a1erp_tpa.tpa_management.posting import client_customer, refresh_fund


class TPAFeeInvoice(Document):
	def validate(self):
		c = frappe.get_doc("TPA Client", self.client)
		if getdate(self.period_to) < getdate(self.period_from):
			frappe.throw(_("The period end cannot be before its start."))
		self.fee_basis, self.fee_rate = c.fee_basis, flt(c.fee_rate)
		plans = frappe.get_all("Health Plan", filters={"tpa_client": self.client}, pluck="name") or [""]
		months = max(date_diff(self.period_to, self.period_from) / 30.4375, 0)
		if c.fee_basis == "Percent of Claims":
			self.base_amount = flt(frappe.db.sql("""select coalesce(sum(payer_amount), 0) from `tabMedical Claim` where docstatus = 1 and plan in %s
				and status in %s and service_date between %s and %s""", (plans, ADJUDICATED, self.period_from, self.period_to))[0][0])
			fee = self.base_amount * flt(c.fee_rate) / 100
		elif c.fee_basis == "Per Member Per Month":
			self.base_amount = frappe.db.count("Plan Member", {"plan": ("in", plans), "status": "Active"})
			fee = self.base_amount * flt(c.fee_rate) * months
		elif c.fee_basis == "Percent of Premium":
			self.base_amount = flt(frappe.db.sql("""select coalesce(sum(amount), 0) from `tabFund Contribution` fc join `tabHealth Fund` f on f.name = fc.fund
				where fc.docstatus = 1 and f.tpa_client = %s and fc.posting_date between %s and %s""", (self.client, self.period_from, self.period_to))[0][0])
			fee = self.base_amount * flt(c.fee_rate) / 100
		else:
			self.base_amount = months
			fee = months * flt(c.fee_rate)
		self.fee_amount = rnd(max(fee, flt(c.fee_minimum)))
		if self.charge_to == "Health Fund" and not self.fund:
			frappe.throw(_("Select the health fund."))

	def on_submit(self):
		st = settings()
		if not st.admin_fee_income_account:
			frappe.throw(_("Set the administration fee income account in TPA Settings."))
		jb = JournalBuilder(self.company, self.posting_date, self.doctype, self.name, _("Administration fee {0} - {1}").format(self.name, self.client))
		if self.charge_to == "Health Fund":
			jb.dr(frappe.db.get_value("Health Fund", self.fund, "liability_account") or st.fund_liability_account, self.fee_amount)
		else:
			jb.party_dr("Customer", client_customer(self.client), self.fee_amount)
		jb.cr(st.admin_fee_income_account, self.fee_amount)
		self.db_set("journal_entry", jb.post())
		if self.fund:
			f = refresh_fund(self.fund)
			f.db_set("total_fees", rnd(flt(f.total_fees) + self.fee_amount))

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry", "Journal Entry")
		cancel_journal_entries(self.doctype, self.name)