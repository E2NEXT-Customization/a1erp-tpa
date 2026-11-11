# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from a1erp_tpa.tpa_management.engine import calculate_items, check_eligibility, default_price, rnd, settings, tariff_for
from a1erp_tpa.tpa_management.doctype.medical_reviewer.medical_reviewer import assign

ITEM_STATUS = {"Accepted": "Approved", "Reduced": "Partial", "Rejected": "Rejected"}


def required_role(document_type, amount):
	rows = sorted([r for r in settings().approval_levels if r.document_type == document_type], key=lambda r: (flt(r.max_amount) == 0, flt(r.max_amount)))
	for r in rows:
		if not flt(r.max_amount) or flt(amount) <= flt(r.max_amount):
			return r.role, cint(r.level)
	return None, 0


def check_level(document_type, amount):
	role, level = required_role(document_type, amount)
	if role and frappe.session.user != "Administrator":
		roles = frappe.get_roles()
		if role not in roles and "TPA Manager" not in roles and "System Manager" not in roles:
			frappe.throw(_("Amounts of {0} need the role {1}.").format(rnd(amount), role), title=_("Approval Required"))
	return level


class PreAuthorization(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Add the services or drugs to authorize."))
		if self.auth_type == "Admission Extension" and not self.parent_auth:
			frappe.throw(_("Select the authorization to extend."))
		self.estimate()

	def estimate(self):
		m = frappe.get_doc("Plan Member", self.member)
		plan = frappe.get_doc("Health Plan", m.plan)
		provider = frappe.get_doc("Medical Provider", self.provider)
		for it in self.items:
			if not (it.service or it.drug):
				frappe.throw(_("Row {0}: select a service or a drug.").format(it.idx))
			if not flt(it.requested_price):
				price, _d, _t = tariff_for(provider, plan, self.request_date, it.item_type, it.service, it.drug)
				it.requested_price = price if price is not None else default_price(it.item_type, it.service, it.drug)
		totals = calculate_items(self, self.items, m, plan, provider, self.request_date)
		self.requested_amount = rnd(sum(flt(i.quantity) * flt(i.requested_price) for i in self.items))
		self.payer_share = totals.payer
		self.member_share = rnd(totals.deductible + totals.copay + totals.over + totals.non_covered)
		for it in self.items:
			it.member_copay = rnd(flt(getattr(it, "deductible_amount", 0)) + flt(getattr(it, "copay_amount", 0)) + flt(getattr(it, "non_covered_amount", 0)))
		return totals

	@frappe.whitelist()
	def submit_request(self):
		self.check_permission("write")
		if self.status != "Draft":
			frappe.throw(_("Only a draft request can be submitted."))
		m = frappe.get_doc("Plan Member", self.member)
		log, ok = [], True
		for it in self.items:
			cat = frappe.db.get_value("Medical Service", it.service, "benefit_category") if it.service else "Pharmacy"
			el = check_eligibility(m, self.provider, self.request_date, cat, it.service, it.drug, self.diagnosis, flt(it.quantity) * flt(it.requested_price))
			log.append("{0}: {1}".format(it.service or it.drug, _("Eligible") if el.ok else "; ".join(str(x) for x in el.reasons)))
			ok = ok and el.ok
		self.eligibility_log = "\n".join(log)
		role, level = required_role("Pre-Authorization", self.requested_amount)
		sp = self.specialty or (frappe.db.get_value("Medical Code", self.diagnosis, "specialty") if self.diagnosis else None)
		self.db_set({"status": "Under Review", "required_level": level, "eligibility_log": self.eligibility_log,
			"assigned_reviewer": self.assigned_reviewer or assign(sp)})
		from a1erp_tpa.tpa_management.notifications import notify

		notify("Pre-Auth Requested", self)
		return {"eligible": ok, "log": log}

	@frappe.whitelist()
	def start_review(self):
		self.check_permission("write")
		if self.status not in ("Under Review", "Submitted", "Pending Information"):
			frappe.throw(_("The request is {0}.").format(_(self.status)))
		self.db_set({"status": "Medical Review", "assigned_reviewer": self.assigned_reviewer or frappe.session.user})

	@frappe.whitelist()
	def decide(self, decision, notes=None, reason=None, info=None, rejected_rows=None):
		self.check_permission("write")
		if self.status not in ("Under Review", "Medical Review", "Pending Information", "Submitted"):
			frappe.throw(_("The request is {0}.").format(_(self.status)))
		if decision not in ("Approve", "Reject", "Request Information"):
			frappe.throw(_("Invalid decision."))
		if decision == "Request Information":
			if not info:
				frappe.throw(_("Enter the information requested."))
			self.db_set({"status": "Pending Information", "info_request": info})
			return
		if decision == "Reject":
			if not reason:
				frappe.throw(_("Select the rejection reason."))
			self.db_set({"status": "Rejected", "rejection_reason": reason, "decision_notes": notes, "decision_by": frappe.session.user, "decision_on": now_datetime()})
			self.notify_decision()
			return
		check_level("Pre-Authorization", self.payer_share or self.requested_amount)
		self.estimate()
		manual = {cint(x) for x in (frappe.parse_json(rejected_rows) if isinstance(rejected_rows, str) else (rejected_rows or []))}
		approved = rejected = 0
		total = 0.0
		for it in self.items:
			rej = it.idx in manual
			engine_status = ITEM_STATUS.get(getattr(it, "calc_status", "Accepted"), "Approved")
			if rej or engine_status == "Rejected":
				it.status, it.approved_amount, it.approved_quantity = "Rejected", 0, 0
				rejected += 1
			else:
				it.status = "Approved" if engine_status == "Approved" else "Partial"
				it.approved_quantity = it.quantity
				it.approved_amount = rnd(getattr(it, "payer_amount", 0))
				total += flt(it.approved_amount)
				approved += 1
		if not approved:
			frappe.throw(_("Nothing can be approved. Reject the request instead."))
		days = cint(settings().preauth_validity_days) or 30
		valid = add_days(nowdate(), days)
		if self.auth_type == "Admission Extension" and self.parent_auth:
			valid = max(getdate(valid), getdate(frappe.db.get_value("Pre-Authorization", self.parent_auth, "valid_until") or valid))
		self.status = "Partially Approved" if rejected else "Approved"
		self.approved_amount = rnd(total)
		self.valid_until = valid
		self.decision_by, self.decision_on, self.decision_notes = frappe.session.user, now_datetime(), notes
		self.db_update()
		for it in self.items:
			frappe.db.set_value("Pre-Auth Item", it.name, {"status": it.status, "approved_quantity": it.approved_quantity, "approved_amount": it.approved_amount})
		self.notify_decision()

	def notify_decision(self):
		from a1erp_tpa.tpa_management.notifications import notify

		notify("Pre-Authorization Decision", self)

	@frappe.whitelist()
	def cancel_auth(self, reason=None):
		self.check_permission("write")
		if self.status in ("Cancelled", "Expired"):
			frappe.throw(_("The authorization is {0}.").format(_(self.status)))
		self.db_set({"status": "Cancelled", "decision_notes": reason})


def valid_authorization(name, member, provider, on_date):
	"""True when the authorization is approved, unexpired and belongs to this member and provider."""
	a = frappe.db.get_value("Pre-Authorization", name, ["status", "member", "provider", "valid_until"], as_dict=True)
	return bool(a and a.status in ("Approved", "Partially Approved") and a.member == member and a.provider == provider
		and (not a.valid_until or getdate(a.valid_until) >= getdate(on_date)))


def expire_authorizations():
	for name in frappe.get_all("Pre-Authorization", filters={"status": ("in", ["Approved", "Partially Approved"]), "valid_until": ("<", nowdate())}, pluck="name"):
		frappe.db.set_value("Pre-Authorization", name, "status", "Expired")