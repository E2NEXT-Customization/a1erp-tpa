"""Accounting of the TPA module: claim accrual, funds, contributions and fees (through the shared journal builder)."""

import frappe
from frappe import _
from frappe.utils import flt

from a1erp_tpa.tpa_management.accounting import JournalBuilder, cancel_journal_entries
from a1erp_tpa.tpa_management.engine import rnd, settings


def funding_parties(plan, amount):
	"""Split a payer amount between the funding parties of a plan: list of (kind, target, amount)."""
	if plan.funding_model == "Self-Funded":
		return [("fund", plan.fund, rnd(amount))]
	if plan.funding_model == "Multiple Funding Sources":
		out, allocated = [], 0.0
		for i, s in enumerate(plan.funding_sources):
			part = rnd(amount - allocated) if i == len(plan.funding_sources) - 1 else rnd(amount * flt(s.share_percent) / 100)
			allocated += part
			out.append(("client", s.source, part))
		return out
	return [("client", plan.insurer or plan.tpa_client, rnd(amount))]


def client_customer(client):
	customer = frappe.db.get_value("TPA Client", client, "customer")
	if not customer:
		frappe.throw(_("Client {0} has no customer for receivables.").format(frappe.bold(client)))
	return customer


def post_claim(claim, plan, provider):
	company = settings().company or frappe.db.get_value("Company", {}, "name")
	amount = rnd(claim.payer_amount)
	if not amount:
		return None
	if not provider.supplier:
		frappe.throw(_("Provider {0} has no supplier for payments.").format(frappe.bold(provider.name)))
	jb = JournalBuilder(company, claim.decided_on or frappe.utils.nowdate(), claim.doctype, claim.name, _("Medical claim {0} - {1}").format(claim.name, claim.provider))
	for kind, target, part in funding_parties(plan, amount):
		if kind == "fund":
			acc = frappe.db.get_value("Health Fund", target, "liability_account") or settings().fund_liability_account
			if not acc:
				frappe.throw(_("Set the liability account of fund {0}.").format(target))
			jb.dr(acc, part)
		else:
			jb.party_dr("Customer", client_customer(target), part)
	jb.party_cr("Supplier", provider.supplier, amount)
	return jb.post()


def fund_balance(fund):
	acc = frappe.db.get_value("Health Fund", fund, "liability_account")
	if not acc:
		return 0.0
	return rnd(frappe.db.sql("select coalesce(sum(credit - debit), 0) from `tabGL Entry` where account = %s and is_cancelled = 0", acc)[0][0])


def refresh_fund(fund):
	doc = frappe.get_doc("Health Fund", fund)
	contrib = flt(frappe.db.sql("select coalesce(sum(amount), 0) from `tabFund Contribution` where fund = %s and docstatus = 1", fund)[0][0])
	balance = fund_balance(fund)
	reserved = flt(frappe.db.sql(
		"""select coalesce(sum(pa.payer_share), 0) from `tabPre-Authorization` pa join `tabHealth Plan` p on p.name = pa.plan
		where p.fund = %s and pa.status in ('Approved', 'Partially Approved') and pa.valid_until >= curdate()""", fund)[0][0])
	doc.db_set({"total_contributions": rnd(contrib), "current_balance": balance, "reserved_amount": rnd(reserved),
		"available_balance": rnd(balance - reserved), "total_claims": rnd(contrib - balance - flt(doc.total_fees))}, update_modified=False)
	return doc