"""Posting of TPA transactions to the ERPNext general ledger through Journal Entries."""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

PRECISION = 2


def rnd(value):
	return flt(value, PRECISION)


def get_party_account(party_type, party, company):
	from erpnext.accounts.party import get_party_account as _get

	return _get(party_type, party, company)


def get_cost_center(company):
	return frappe.get_cached_value("Company", company, "cost_center")


class JournalBuilder:
	"""Collects debit/credit lines (in company currency) and posts one balanced Journal Entry.

	Positive amounts passed to `dr` are debits, to `cr` are credits. Negative amounts reverse the side automatically.
	"""

	def __init__(self, company, posting_date, reference_doctype, reference_name, remark=None):
		self.company = company
		self.posting_date = posting_date
		self.reference_doctype = reference_doctype
		self.reference_name = reference_name
		self.remark = remark
		self.cost_center = get_cost_center(company)
		self.rows = []

	def _add(self, account, amount, party_type=None, party=None):
		amount = rnd(amount)
		if not amount:
			return
		self.rows.append({"account": account, "amount": amount, "party_type": party_type, "party": party})

	def dr(self, account, amount, party_type=None, party=None):
		self._add(account, amount, party_type, party)

	def cr(self, account, amount, party_type=None, party=None):
		self._add(account, -flt(amount), party_type, party)

	def party_dr(self, party_type, party, amount):
		self.dr(get_party_account(party_type, party, self.company), amount, party_type, party)

	def party_cr(self, party_type, party, amount):
		self.cr(get_party_account(party_type, party, self.company), amount, party_type, party)

	def merged_rows(self):
		merged = {}
		for r in self.rows:
			key = (r["account"], r["party_type"], r["party"])
			merged[key] = rnd(merged.get(key, 0) + r["amount"])
		return [(k, v) for k, v in merged.items() if v]

	def post(self):
		rows = self.merged_rows()
		if not rows:
			return None
		diff = rnd(sum(v for _k, v in rows))
		if abs(diff) > 0.05:
			frappe.throw(_("TPA journal is not balanced (difference {0}).").format(diff))
		if diff:
			# rounding difference: absorb it in the largest line on the opposite side
			idx = max(range(len(rows)), key=lambda i: abs(rows[i][1]) if (rows[i][1] < 0) == (diff > 0) else -1)
			key, value = rows[idx]
			rows[idx] = (key, rnd(value - diff))

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.posting_date = self.posting_date or nowdate()
		je.user_remark = self.remark or _("{0} {1}").format(_(self.reference_doctype), self.reference_name)
		je.tpa_reference_type = self.reference_doctype
		je.tpa_reference = self.reference_name
		for (account, party_type, party), value in rows:
			line = {"account": account, "cost_center": self.cost_center}
			if party_type and party:
				line.update({"party_type": party_type, "party": party})
			if value > 0:
				line["debit_in_account_currency"] = value
			else:
				line["credit_in_account_currency"] = -value
			je.append("accounts", line)
		je.flags.ignore_permissions = True
		je.insert()
		je.submit()
		return je.name


def cancel_journal_entries(reference_doctype, reference_name):
	names = frappe.get_all("Journal Entry", filters={"tpa_reference_type": reference_doctype, "tpa_reference": reference_name, "docstatus": 1},
		pluck="name")
	frappe.flags.tpa_je_cancel = True
	try:
		for name in names:
			je = frappe.get_doc("Journal Entry", name)
			je.flags.ignore_permissions = True
			je.cancel()
	finally:
		frappe.flags.tpa_je_cancel = False


def prevent_direct_cancel(doc, method=None):
	if doc.get("tpa_reference") and not frappe.flags.get("tpa_je_cancel"):
		frappe.throw(_("This Journal Entry was created by {0} {1}. Cancel that document instead.").format(
			_(doc.tpa_reference_type), frappe.bold(doc.tpa_reference)))


def get_payable_outstanding(journal_entry, party_type, party):
	"""Amount still owed to a party (for example a provider) on a journal entry after payments."""
	if not journal_entry:
		return 0.0
	billed = frappe.db.sql(
		"""select coalesce(sum(credit - debit), 0) from `tabGL Entry`
		where voucher_type='Journal Entry' and voucher_no=%s and party_type=%s and party=%s and is_cancelled=0""",
		(journal_entry, party_type, party),
	)[0][0]
	settled = frappe.db.sql(
		"""select coalesce(sum(debit - credit), 0) from `tabGL Entry`
		where against_voucher_type='Journal Entry' and against_voucher=%s and voucher_no != %s
		and party_type=%s and party=%s and is_cancelled=0""",
		(journal_entry, journal_entry, party_type, party),
	)[0][0]
	return rnd(flt(billed) - flt(settled))
