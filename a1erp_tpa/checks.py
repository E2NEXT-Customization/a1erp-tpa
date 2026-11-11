"""End-to-end checks of the TPA module: plans, eligibility, tariffs, pre-authorization, claims, settlement, funds and fraud rules.

Run:  bench --site <site> execute a1erp_tpa.checks.run
Everything is rolled back at the end.
"""

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from a1erp_tpa.tpa_management.engine import check_eligibility

OK, FAIL = [], []


def check(cond, msg):
	(OK if cond else FAIL).append(msg)
	if not cond:
		print("FAIL:", msg)


def raises(fn, text, msg):
	try:
		fn()
	except Exception as e:  # noqa: BLE001
		check(text.lower() in str(e).lower(), f"{msg} (got: {str(e)[:120]})")
		return
	check(False, f"{msg} (nothing raised)")


def make_user(email, roles, **kw):
	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=True)
	u = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0, **kw})
	u.insert(ignore_permissions=True)
	u.add_roles(*roles)
	return u

TODAY = getdate(nowdate())


def account(company, name, root, parent_name, account_type=None):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	full = f"{name} - {abbr}"
	if frappe.db.exists("Account", full):
		return full
	parent = frappe.db.get_value("Account", {"company": company, "account_name": parent_name, "is_group": 1})
	frappe.get_doc({"doctype": "Account", "account_name": name, "parent_account": parent, "company": company, "root_type": root,
		"account_type": account_type or ""}).insert(ignore_permissions=True)
	return full


def make(doctype, **kw):
	return frappe.get_doc({"doctype": doctype, **kw}).insert()


def masters(company):
	st = frappe.get_doc("TPA Settings")
	acc = {
		"fund": account(company, "TPA Test Fund Account", "Liability", "Current Liabilities"),
		"income": account(company, "TPA Test Fee Income", "Income", "Direct Income"),
		"bank": account(company, "TPA Test Bank", "Asset", "Bank Accounts", "Bank"),
		"adj": account(company, "TPA Test Adjustments", "Income", "Direct Income"),
	}
	st.company = company
	st.fund_liability_account, st.admin_fee_income_account, st.adjustments_account, st.provider_payment_account = acc["fund"], acc["income"], acc["adj"], acc["bank"]
	st.set("transitions", [])
	st.set("approval_levels", [])
	st.save()
	frappe.clear_document_cache("TPA Settings", "TPA Settings")
	if not frappe.db.exists("Customer", "TPA Test Insurer"):
		make("Customer", customer_name="TPA Test Insurer", customer_group=frappe.db.get_value("Customer Group", {"is_group": 0}),
			territory=frappe.db.get_value("Territory", {"is_group": 0}))
	if not frappe.db.exists("Supplier", "TPA Test Hospital"):
		make("Supplier", supplier_name="TPA Test Hospital", supplier_group=frappe.db.get_value("Supplier Group", {"is_group": 0}))
	return acc


def run():
	frappe.flags.in_test = True
	frappe.set_user("Administrator")
	del OK[:], FAIL[:]
	company = frappe.get_doc("TPA Settings").company or frappe.db.get_value("Company", {}, "name")
	try:
		seed_checks()
		acc = masters(company)
		core_checks(company, acc)
	finally:
		frappe.set_user("Administrator")
		frappe.db.rollback()
	print(f"passed {len(OK)}, failed {len(FAIL)}")
	return {"passed": len(OK), "failed": FAIL}


FORM_METHODS = {"Plan Member": ["activate", "suspend", "terminate", "reinstate"], "Medical Card": ["replace"], "Provider Tariff": ["activate"],
	"Medical Provider": ["create_supplier", "refresh_performance"], "Health Plan": ["create_plan_from_template"], "Health Fund": ["refresh"],
	"Pre-Authorization": ["submit_request", "start_review", "decide", "cancel_auth"], "Medical Claim": ["calculate", "set_status"],
	"Provider Settlement": ["fetch_claims", "make_payment"]}


def is_open(ctl, name):
	try:
		frappe.is_whitelisted(getattr(ctl, name))
		return True
	except Exception:  # noqa: BLE001
		return False


def seed_checks():
	from frappe.model.document import get_controller

	for dt, methods in FORM_METHODS.items():
		ctl = get_controller(dt)
		check(all(is_open(ctl, m) for m in methods), f"the form buttons of {dt} call whitelisted methods")
	js = open(frappe.get_app_path("a1erp_tpa", "public", "js", "tpa_forms.js"), encoding="utf-8").read()
	check(all(f'"{m}"' in js for ms in FORM_METHODS.values() for m in ms), "every whitelisted action has a button in tpa_forms.js")
	st = frappe.get_doc("TPA Settings")
	check(len(st.transitions) >= 20 and len(st.approval_levels) >= 8 and len(st.sla_rules) == 4, "default workflow, approval levels and service levels are installed")
	check(all(st.get(k) for k in ("fund_liability_account", "admin_fee_income_account", "adjustments_account")), "default TPA accounts are linked")
	check(frappe.db.count("FWA Rule") >= 8 and frappe.db.count("Claim Rejection Reason") >= 12, "default fraud rules and rejection reasons are installed")
	check(all(frappe.db.exists("Role", r) for r in ("TPA Manager", "TPA Claims Officer", "TPA Medical Reviewer", "TPA Finance", "TPA Customer Service")), "TPA roles exist")
	check(frappe.db.count("TPA Notification Template", {"event": ("in", ["Member Activated", "Card Issued", "Coverage Expiring", "Pre-Auth Requested",
		"Pre-Authorization Decision", "Claim Status Update"])}) == 24, "TPA notification templates are installed")


def core_checks(company, acc):
	client = make("TPA Client", client_name="TPA Test Insurer Co", client_type="Insurance Company", customer="TPA Test Insurer",
		fee_basis="Percent of Claims", fee_rate=5)
	net = make("Provider Network", network_name="TPA Test Network")
	provider = make("Medical Provider", provider_name="TPA Test Hospital", provider_type="Hospital", supplier="TPA Test Hospital",
		networks=[{"network": net.name}])
	outsider = make("Medical Provider", provider_name="TPA Test Outsider", provider_type="Clinic / Medical Center", supplier="TPA Test Hospital")
	svc = make("Medical Service", service_code="T-CONS", service_name="Consultation", category="Consultation", benefit_category="Outpatient", default_price=1000000)
	lab = make("Medical Service", service_code="T-LAB", service_name="Lab Panel", category="Laboratory", benefit_category="Laboratory and Radiology")
	surg = make("Medical Service", service_code="T-SURG", service_name="Surgery", category="Surgery", benefit_category="Inpatient", requires_preauth=1)
	dent = make("Medical Service", service_code="T-DENT", service_name="Dental Cleaning", category="Dental", benefit_category="Dental")
	big = make("Medical Service", service_code="T-BIG", service_name="Big Procedure", category="Surgery", benefit_category="Outpatient")
	excl = make("Medical Service", service_code="T-EXCL", service_name="Cosmetic", category="Other", benefit_category="Outpatient")
	plan = make("Health Plan", plan_name="TPA Test Plan", tpa_client=client.name, insurer=client.name, funding_model="Insurance Company Funded",
		from_date=f"{TODAY.year}-01-01", to_date=f"{TODAY.year}-12-31", network=net.name, status="Active",
		benefits=[{"benefit_category": "Outpatient", "covered": 1, "copay_percent": 10},
			{"benefit_category": "Laboratory and Radiology", "covered": 1, "annual_limit": 100000},
			{"benefit_category": "Inpatient", "covered": 1},
			{"benefit_category": "Dental", "covered": 1, "waiting_days": 30}],
		exclusions=[{"exclusion_type": "Service", "service": excl.name}])
	tariff = make("Provider Tariff", tariff_name="TPA Test Tariff", provider=provider.name, valid_from=f"{TODAY.year}-01-01", discount_percent=10,
		items=[{"item_type": "Service", "service": svc.name, "price": 1000000}, {"item_type": "Service", "service": lab.name, "price": 80000},
			{"item_type": "Service", "service": surg.name, "price": 5000000}, {"item_type": "Service", "service": dent.name, "price": 50000},
			{"item_type": "Service", "service": big.name, "price": 10000000}, {"item_type": "Service", "service": excl.name, "price": 20000}])
	tariff.activate()
	check(frappe.db.get_value("Provider Tariff", tariff.name, "status") == "Active", "tariff activated")
	locked = frappe.get_doc("Provider Tariff", tariff.name)
	locked.discount_percent = 50
	raises(locked.save, "cannot be changed", "an active tariff is locked")

	# members and cards
	m = make("Plan Member", member_name="Test Member", plan=plan.name, national_id="NID-1", gender="Male", date_of_birth="1990-01-01",
		start_date=f"{TODAY.year}-01-01")
	check(m.card_no and m.status == "Pending", "member gets a card number and starts pending")
	m.activate()
	m.reload()
	check(m.status == "Active", "member activated")
	check(frappe.db.exists("Medical Card", {"member": m.name, "status": "Active"}), "card issued on activation")
	card = frappe.db.get_value("Medical Card", {"member": m.name, "status": "Active"})
	html = frappe.get_print("Medical Card", card, "Medical Card")
	check("data:image/png;base64" in html and m.card_no in html and "Test Member" in html, "the printed card shows the name, number and QR code")
	from a1erp_tpa.tpa_management.cards import sign, verify

	check(verify(m.card_no, sign(m.card_no))["valid"] and not verify(m.card_no, "bad")["valid"], "the QR code verifies an active card only with a good signature")
	from a1erp_tpa.tpa_management.doctype.medical_card.medical_card import issue_cards

	m3 = make("Plan Member", member_name="Group Member", plan=plan.name, national_id="NID-G1", start_date=f"{TODAY.year}-01-01")
	frappe.db.set_value("Plan Member", m3.name, "status", "Active")
	issued = issue_cards(plan.name)
	check(len(issued) == 1 and not issue_cards(plan.name), "group issuance creates cards only for members without one")
	frappe.db.set_value("Plan Member", m3.name, "status", "Terminated")
	d = frappe.get_doc({"doctype": "TPA Document", "title": "Provider contract", "document_type": "Provider Contract", "file": "/files/x.pdf",
		"reference_doctype": "Medical Provider", "reference_name": provider.name})
	d.insert()
	check(any(p.role == "TPA Claims Officer" for p in frappe.get_meta("TPA Document").permissions), "TPA roles can use the document register")
	raises(lambda: make("Plan Member", member_name="Dup", plan=plan.name, national_id="NID-1"), "already registered", "duplicate national id in the plan")
	m2 = make("Plan Member", member_name="New Member", plan=plan.name, national_id="NID-2", start_date=nowdate())
	m2.activate()

	# eligibility
	e = check_eligibility(m.name, provider.name, nowdate(), "Outpatient", svc.name)
	check(e.ok and e.copay_percent == 10, "eligible member, copay 10%")
	e = check_eligibility(m.name, outsider.name, nowdate(), "Outpatient", svc.name)
	check(not e.ok and "outside the network" in " ".join(str(x) for x in e.reasons).lower(), "provider outside the network refused")
	e = check_eligibility(m.name, provider.name, nowdate(), "Optical", None)
	check(not e.ok, "uncovered benefit refused")
	e = check_eligibility(m.name, provider.name, nowdate(), "Outpatient", excl.name)
	check(not e.ok, "excluded service refused")
	e = check_eligibility(m2.name, provider.name, nowdate(), "Dental", dent.name)
	check(not e.ok and "waiting" in " ".join(str(x) for x in e.reasons).lower(), "waiting period enforced")
	e = check_eligibility(m.name, provider.name, nowdate(), "Dental", dent.name)
	check(e.ok, "waiting period over for the older member")
	e = check_eligibility(m.name, provider.name, add_days(nowdate(), 400), "Outpatient", svc.name)
	check(not e.ok, "date outside the plan period refused")
	m2.suspend("Test")
	e = check_eligibility(m2.name, provider.name, nowdate(), "Outpatient", svc.name)
	check(not e.ok, "suspended member refused")
	m2.reload().reinstate()
	check(frappe.db.get_value("Plan Member", m2.name, "status") == "Active", "member reinstated")
	check(len(frappe.get_doc("Plan Member", m2.name).status_log) >= 3, "status history recorded")

	# the RFP example: 1,000,000 - 10% discount = 900,000; 10% copay = 90,000; payable 810,000
	c1 = claim(m.name, provider.name, [{"service": svc.name, "unit_price": 1000000}], "INV-1")
	check(c1.claimed_amount == 1000000 and c1.contractual_discount == 100000, "claim: discount 100,000")
	check(c1.copay_amount == 90000 and c1.payer_amount == 810000, f"claim: copay 90,000 and payer 810,000 (got {c1.copay_amount}/{c1.payer_amount})")
	check(c1.member_share == 90000, "claim: member share 90,000")
	c1.submit()
	c1.reload()
	check(c1.status == "Received", "claim received after submission")
	raises(lambda: claim(m.name, provider.name, [{"service": svc.name, "unit_price": 1000000}], "INV-1").submit(), "already submitted", "duplicate invoice refused")

	# a billed price above the tariff is cut to the tariff
	c2 = claim(m.name, provider.name, [{"service": svc.name, "unit_price": 1500000}], "INV-2", add_days(nowdate(), -10))
	check(c2.payer_amount == 810000 and c2.items[0].tariff_price == 1000000, "billed price above tariff is capped")

	# status control
	st = frappe.get_doc("TPA Settings")
	st.set("transitions", [{"from_status": "Received", "to_status": "Under Review"}])
	st.save()
	frappe.clear_document_cache("TPA Settings", "TPA Settings")
	raises(lambda: frappe.get_doc("Medical Claim", c1.name).set_status("Approved"), "cannot move", "workflow blocks a disallowed change")
	st.reload()
	st.set("transitions", [])
	st.save()
	frappe.clear_document_cache("TPA Settings", "TPA Settings")
	raises(lambda: frappe.get_doc("Medical Claim", c1.name).set_status("Paid"), "settlement", "paid status only through settlement")
	raises(lambda: frappe.get_doc("Medical Claim", c1.name).set_status("Rejected"), "rejection reason", "rejection needs a reason")

	# approval posts a journal entry: Dr customer, Cr supplier
	frappe.get_doc("Medical Claim", c1.name).set_status("Approved")
	c1.reload()
	check(c1.status == "Approved" and c1.journal_entry, "claim approved with a journal entry")
	je = frappe.get_doc("Journal Entry", c1.journal_entry)
	check(abs(flt(je.total_debit) - 810000) < 0.01 and abs(flt(je.total_credit) - 810000) < 0.01, "journal entry balanced at 810,000")
	check(any(r.party_type == "Customer" and flt(r.debit_in_account_currency) == 810000 for r in je.accounts), "debit on the insurer customer")
	check(any(r.party_type == "Supplier" and flt(r.credit_in_account_currency) == 810000 for r in je.accounts), "credit on the provider supplier")

	# annual benefit limit: laboratory limit 100,000
	l1 = claim(m.name, provider.name, [{"service": lab.name, "unit_price": 80000}], "INV-L1")
	l1.submit()
	frappe.get_doc("Medical Claim", l1.name).set_status("Approved")
	l2 = claim(m.name, provider.name, [{"service": lab.name, "unit_price": 80000}], "INV-L2")
	check(l2.over_limit_amount > 0 and abs(l2.payer_amount - 28000) < 0.01, f"second lab claim reduced to the remaining limit (got {l2.payer_amount})")
	l2.submit()
	raises(lambda: frappe.get_doc("Medical Claim", l2.name).set_status("Approved"), "partially approved", "limit overflow needs partial approval")
	frappe.get_doc("Medical Claim", l2.name).set_status("Partially Approved")
	l2.reload()
	check(l2.status == "Partially Approved" and l2.payer_amount > 0, "partial approval within limit")
	check(flt(l1.payer_amount) + flt(l2.payer_amount) <= 100000.01, "lab usage never exceeds the annual limit")

	# pre-authorization
	n0 = claim(m.name, provider.name, [{"service": surg.name, "unit_price": 5000000}], "INV-S0")
	check(n0.payer_amount == 0 and n0.items[0].status == "Rejected", "surgery without pre-authorization is rejected")
	pa = make("Pre-Authorization", member=m.name, provider=provider.name, auth_type="Surgery", items=[{"item_type": "Service", "service": surg.name, "quantity": 1}])
	check(pa.requested_amount == 5000000 and pa.payer_share == 4500000, f"pre-auth estimate 4,500,000 (got {pa.payer_share})")
	pa.submit_request()
	pa.reload()
	check(pa.status == "Under Review", "pre-auth under review")
	raises(lambda: frappe.get_doc("Pre-Authorization", pa.name).decide("Reject"), "rejection reason", "pre-auth rejection needs a reason")
	frappe.get_doc("Pre-Authorization", pa.name).decide("Approve", "ok")
	pa.reload()
	check(pa.status == "Approved" and pa.approved_amount == 4500000 and pa.valid_until, "pre-auth approved with validity")
	n1 = claim(m.name, provider.name, [{"service": surg.name, "unit_price": 5000000}], "INV-S1", pre_auth=pa.name)
	check(n1.payer_amount == 4500000 and n1.items[0].status != "Rejected", "surgery with pre-authorization is payable")
	n1.submit()
	frappe.get_doc("Medical Claim", n1.name).set_status("Approved")

	# nothing payable
	n0.submit()
	raises(lambda: frappe.get_doc("Medical Claim", n0.name).set_status("Approved"), "nothing is payable", "no approval without a payable amount")
	frappe.get_doc("Medical Claim", n0.name).set_status("Rejected", reason=make("Claim Rejection Reason", reason_code="T-R1", reason_en="Test", category="Coverage").name)
	check(frappe.db.get_value("Medical Claim", n0.name, "status") == "Rejected", "claim rejected")

	# fraud, waste and abuse
	make("FWA Rule", rule_name="T-Dup", rule_type="Duplicate Claim", severity="High", action="Hold for Review", window_days=7)
	d = claim(m.name, provider.name, [{"service": svc.name, "unit_price": 1000000}], "INV-DUP")
	d.submit()
	d.reload()
	check(d.fwa_flag == 1 and d.status == "Under Review", "duplicate service flagged and held for review")
	check(frappe.db.exists("FWA Alert", {"claim": d.name}), "fraud alert created")

	# provider settlement and payment
	s = frappe.new_doc("Provider Settlement")
	s.update({"provider": provider.name, "company": company, "period_from": add_days(nowdate(), -30), "period_to": nowdate(), "currency": "IQD"})
	s.fetch_claims()
	expected = flt(frappe.db.sql("select sum(payer_amount) from `tabMedical Claim` where provider=%s and status in ('Approved','Partially Approved') and docstatus=1", provider.name)[0][0])
	check(len(s.claims) == 4 and abs(flt(s.gross_payable) - expected) < 0.01, f"settlement loads the four approved claims (got {len(s.claims)})")
	s.append("adjustments", {"adjustment_type": "Penalty", "amount": 10000, "reason": "late"})
	s.insert()
	check(abs(flt(s.net_payable) - (expected - 10000)) < 0.01, "adjustment reduces the net payable")
	s.submit()
	check(frappe.db.get_value("Medical Claim", c1.name, "status") == "Ready for Payment", "claims ready for payment after the settlement")
	raises(lambda: frappe.get_doc("Medical Claim", c1.name).cancel(), "settlement", "claim in a settlement cannot be cancelled")
	pe = frappe.get_doc("Provider Settlement", s.name).make_payment()
	check(pe and frappe.db.get_value("Payment Entry", pe, "docstatus") == 1, "payment entry submitted")
	check(abs(flt(frappe.db.get_value("Payment Entry", pe, "paid_amount")) - (expected - 10000)) < 0.01, "payment equals the net payable")
	check(frappe.db.get_value("Medical Claim", c1.name, "status") == "Paid", "claims paid")
	raises(lambda: frappe.get_doc("Provider Settlement", s.name).make_payment(), "not yet paid", "a settlement cannot be paid twice")

	# self-funded plan and health fund
	fund = make("Health Fund", fund_name="TPA Test Fund", tpa_client=client.name, liability_account=acc["fund"])
	sf = make("Health Plan", plan_name="TPA Self Funded", tpa_client=client.name, funding_model="Self-Funded", fund=fund.name, status="Active",
		from_date=f"{TODAY.year}-01-01", to_date=f"{TODAY.year}-12-31", network=net.name, benefits=[{"benefit_category": "Outpatient", "covered": 1, "copay_percent": 10}])
	fm = make("Plan Member", member_name="Fund Member", plan=sf.name, national_id="NID-3", start_date=f"{TODAY.year}-01-01")
	fm.activate()
	make("Fund Contribution", fund=fund.name, amount=5000000, bank_account=acc["bank"], posting_date=nowdate()).submit()
	f = frappe.get_doc("Health Fund", fund.name).refresh()
	check(f["current_balance"] == 5000000 and f["available_balance"] == 5000000, "fund balance after the contribution")
	f1 = claim(fm.name, provider.name, [{"service": svc.name, "unit_price": 1000000}], "INV-F1")
	f1.submit()
	frappe.get_doc("Medical Claim", f1.name).set_status("Approved")
	f = frappe.get_doc("Health Fund", fund.name).refresh()
	check(f["current_balance"] == 5000000 - 810000, f"fund charged with the claim (got {f['current_balance']})")
	f2 = claim(fm.name, provider.name, [{"service": big.name, "unit_price": 10000000}], "INV-F2")
	f2.submit()
	raises(lambda: frappe.get_doc("Medical Claim", f2.name).set_status("Approved"), "available balance", "a claim above the fund balance cannot be approved")

	# administration fee: 5% of the approved claims of the client
	fee = make("TPA Fee Invoice", client=client.name, company=company, period_from=f"{TODAY.year}-01-01", period_to=nowdate())
	base = flt(frappe.db.sql("select sum(c.payer_amount) from `tabMedical Claim` c join `tabHealth Plan` p on p.name=c.plan where p.tpa_client=%s and c.docstatus=1 and c.status in ('Approved','Partially Approved','Ready for Payment','Paid','Closed')", client.name)[0][0])
	check(abs(fee.base_amount - base) < 0.01 and abs(fee.fee_amount - base * 0.05) < 0.01, f"fee is 5% of the claims (got {fee.fee_amount})")
	fee.submit()
	check(frappe.db.get_value("TPA Fee Invoice", fee.name, "journal_entry"), "fee journal entry posted")

	# service desk
	t = make("Service Ticket", ticket_type="Complaint", subject="Late payment", priority="High", provider=provider.name)
	check(frappe.db.exists("Service Ticket", t.name), "ticket stored")
	report_checks(client.name, provider.name)
	from a1erp_tpa.checks_portal import portal_checks

	portal_checks(client, provider, m, net)


REPORTS = ["medical_utilization_analysis", "pmpm_cost_analysis", "tpa_claims_register", "claim_rejection_analysis", "provider_performance", "provider_payables_aging", "health_fund_position",
	"plan_utilization", "preauthorization_turnaround", "service_desk_sla", "top_claimants"]


def report_checks(client, provider):
	f = {"from_date": f"{TODAY.year}-01-01", "to_date": nowdate(), "as_on_date": nowdate()}
	results = {}
	for r in REPORTS:
		fn = frappe.get_attr(f"a1erp_tpa.tpa_management.report.{r}.{r}.execute")
		try:
			res = fn(dict(f, group_by="Diagnosis" if r == "medical_utilization_analysis" else "Client"))
			results[r] = res
			check(len(res[0]) >= 4 and isinstance(res[1], list), f"report {r} runs and returns columns")
		except Exception as e:  # noqa: BLE001
			check(False, f"report {r} runs ({str(e)[:150]})")
	reg = results.get("tpa_claims_register")
	check(reg and len(reg[1]) >= 6 and any(abs(flt(x["payer_amount"]) - 810000) < 0.01 for x in reg[1]), "register lists the 810,000 claim")
	perf = results.get("provider_performance")
	check(perf and perf[1] and perf[1][0].provider == provider and perf[1][0].claims > 0, "provider performance counts the claims")
	aging = results.get("provider_payables_aging")
	check(aging is not None and all(abs(sum(r[k] for k in ("d30", "d60", "d90", "d181")) - r.total) < 0.01 for r in aging[1]), "aging buckets add up to the total")
	fund = results.get("health_fund_position")
	check(fund and any(abs(flt(x["balance"]) - 4190000) < 0.01 for x in fund[1]), "fund position shows the balance after the claim")
	util = results.get("medical_utilization_analysis")
	check(util and util[1] and sum(x.payable for x in util[1]) > 0, "utilization analysis totals the payable amounts")
	pm = results.get("pmpm_cost_analysis")
	check(pm and pm[1] and pm[1][0]["member_months"] > 0 and pm[1][0]["pmpm"] > 0, "PMPM is computed from member months")
	check(frappe.db.exists("Dashboard", "TPA Executive") and frappe.db.count("Number Card", {"name": ("like", "TPA - %")}) >= 11
		and frappe.db.count("Dashboard Chart", {"name": ("like", "TPA - %")}) >= 11, "TPA dashboards, cards and charts are installed")


def claim(member, provider, items, invoice_no, service_date=None, **kw):
	return make("Medical Claim", member=member, provider=provider, invoice_no=invoice_no, invoice_date=nowdate(), service_date=service_date or nowdate(),
		items=[{"item_type": "Service", "quantity": 1, **i} for i in items], **kw)
