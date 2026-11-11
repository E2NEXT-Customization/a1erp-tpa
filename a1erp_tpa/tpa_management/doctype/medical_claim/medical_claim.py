# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, nowdate, now_datetime

from a1erp_tpa.tpa_management.accounting import cancel_journal_entries
from a1erp_tpa.tpa_management import fwa, posting
from a1erp_tpa.tpa_management.doctype.medical_reviewer.medical_reviewer import assign
from a1erp_tpa.tpa_management.doctype.pre_authorization.pre_authorization import check_level, valid_authorization
from a1erp_tpa.tpa_management.engine import (
	calculate_items,
	check_eligibility,
	default_price,
	rnd,
	settings,
	tariff_for,
)

FINAL = ("Paid", "Closed")


class MedicalClaim(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Add the billed services or drugs."))
		if getdate(self.service_date) > getdate(nowdate()):
			frappe.throw(_("The date of service cannot be in the future."))
		if self.discharge_date and self.admission_date and getdate(self.discharge_date) < getdate(self.admission_date):
			frappe.throw(_("Discharge cannot be before admission."))
		if self.docstatus == 0:
			self.calculate()

	def context(self):
		m = frappe.get_doc("Plan Member", self.member)
		plan = frappe.get_doc("Health Plan", m.plan)
		provider = frappe.get_doc("Medical Provider", self.provider)
		return m, plan, provider

	@frappe.whitelist()
	def calculate(self, exclude_self=True):
		m, plan, provider = self.context()
		for it in self.items:
			if not (it.service or it.drug):
				frappe.throw(_("Row {0}: select a service or a drug.").format(it.idx))
			if not flt(it.unit_price):
				price, _d, _t = tariff_for(provider, plan, it.service_date or self.service_date, it.item_type, it.service, it.drug)
				it.unit_price = price if price is not None else default_price(it.item_type, it.service, it.drug)
		pre = frappe.get_doc("Pre-Authorization", self.pre_auth) if self.pre_auth and valid_authorization(self.pre_auth, self.member, self.provider, self.service_date) else None
		t = calculate_items(self, self.items, m, plan, provider, self.service_date, preauth=pre if self.pre_auth else None, exclude_claim=self.name if exclude_self else None)
		if self.pre_auth and not pre:
			frappe.msgprint(_("The pre-authorization is not valid for this member, provider and date."), indicator="orange", alert=True)
		self.claimed_amount = t.claimed
		self.contractual_discount = t.discount
		self.net_amount = rnd(t.claimed - t.discount)
		self.non_covered_amount = t.non_covered
		self.deductible_amount, self.copay_amount, self.over_limit_amount = t.deductible, t.copay, t.over
		self.member_share = rnd(t.deductible + t.copay + t.over + t.non_covered)
		self.payer_amount = t.payer
		return t

	def before_submit(self):
		m, plan, provider = self.context()
		el = check_eligibility(m, provider.name, self.service_date)
		if not el.ok:
			frappe.throw(_("The claim cannot be accepted: {0}").format("; ".join(str(x) for x in el.reasons)))
		if frappe.db.exists("Medical Claim", {"docstatus": 1, "provider": self.provider, "invoice_no": self.invoice_no, "name": ("!=", self.name),
				"status": ("!=", "Rejected")}):
			frappe.throw(_("Invoice {0} of this provider was already submitted.").format(self.invoice_no))
		self.status = "Received"
		self.received_on = nowdate()
		self.validation_log = "\n".join("{0}: {1}".format(it.service or it.drug, it.note) for it in self.items if it.note)

	def on_submit(self):
		st = settings()
		sp = frappe.db.get_value("Medical Code", self.diagnosis, "specialty") if self.diagnosis else None
		updates = {"medical_reviewer": assign(sp)}
		if cint(st.fwa_enabled):
			score, hold, reject, alerts = fwa.run_rules(self)
			updates.update({"fwa_score": score, "fwa_flag": 1 if alerts else 0})
			if reject:
				updates.update({"status": "Rejected", "rejection_reason": frappe.db.get_value("Claim Rejection Reason", {"category": "Fraud"}), "decided_on": now_datetime()})
			elif hold:
				updates["status"] = "Under Review"
		self.db_set(updates)
		if self.pre_auth:
			frappe.db.set_value("Pre-Authorization", self.pre_auth, "sessions_used", cint(frappe.db.get_value("Pre-Authorization", self.pre_auth, "sessions_used")) + 1)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry", "Journal Entry")
		if self.status in ("Ready for Payment", "Paid", "Closed") or self.settlement:
			frappe.throw(_("A claim in a settlement or already paid cannot be cancelled."))
		cancel_journal_entries(self.doctype, self.name)
		self.db_set("status", "Draft")

	def allowed(self, new):
		rows = settings().transitions
		if new in ("Ready for Payment", "Paid"):
			frappe.throw(_("This status is set by the provider settlement."))
		if self.status in FINAL:
			frappe.throw(_("The claim is {0}.").format(_(self.status)))
		if not rows:
			return
		match = [r for r in rows if r.from_status == self.status and r.to_status == new]
		if not match:
			frappe.throw(_("A claim cannot move from {0} to {1}.").format(_(self.status), _(new)))
		role = match[0].allowed_role
		roles = frappe.get_roles()
		if role and role not in roles and "TPA Manager" not in roles and "System Manager" not in roles:
			frappe.throw(_("Only the role {0} can make this change.").format(role))

	@frappe.whitelist()
	def set_status(self, new_status, notes=None, reason=None, info=None):
		self.check_permission("write")
		if self.docstatus != 1:
			frappe.throw(_("Submit the claim first."))
		self.allowed(new_status)
		updates = {"status": new_status, "review_notes": notes or self.review_notes}
		if new_status == "Pending Information":
			if not info:
				frappe.throw(_("Enter the information requested."))
			updates["info_request"] = info
		elif new_status == "Rejected":
			if not reason:
				frappe.throw(_("Select the rejection reason."))
			updates.update({"rejection_reason": reason, "decided_on": now_datetime(), "payer_amount": 0})
		elif new_status in ("Approved", "Partially Approved"):
			self.approve(new_status, updates)
		self.db_set(updates)
		if new_status in ("Approved", "Partially Approved", "Rejected", "Pending Information"):
			from a1erp_tpa.tpa_management.notifications import notify

			notify("Claim Status Update", self)

	def approve(self, status, updates):
		self.calculate()
		if flt(self.payer_amount) <= 0:
			frappe.throw(_("Nothing is payable. Reject the claim instead."))
		rejected = [i for i in self.items if i.status == "Rejected"]
		if status == "Approved" and (rejected or flt(self.over_limit_amount) > 0.005):
			frappe.throw(_("Some items are rejected or above the limit. Use Partially Approved."))
		check_level("Medical Claim", self.payer_amount)
		m, plan, provider = self.context()
		if plan.funding_model == "Self-Funded" and plan.fund:
			available = posting.refresh_fund(plan.fund).available_balance
			if flt(self.payer_amount) > flt(available) + 0.005:
				frappe.throw(_("The fund {0} has an available balance of {1} only.").format(plan.fund, available))
		for it in self.items:
			frappe.db.set_value("Claim Item", it.name, {k: it.get(k) for k in ("status", "tariff_price", "benefit_category", "discount_amount", "non_covered_amount",
				"deductible_amount", "copay_amount", "payer_amount", "note", "line_total", "unit_price")})
		self.decided_on = now_datetime()
		updates.update({"decided_on": self.decided_on, "claimed_amount": self.claimed_amount, "payer_amount": self.payer_amount,
			"member_share": self.member_share, "contractual_discount": self.contractual_discount, "net_amount": self.net_amount,
			"non_covered_amount": self.non_covered_amount, "deductible_amount": self.deductible_amount, "copay_amount": self.copay_amount,
			"over_limit_amount": self.over_limit_amount, "financial_reviewer": frappe.session.user})
		self.journal_entry = posting.post_claim(self, plan, provider)
		updates["journal_entry"] = self.journal_entry