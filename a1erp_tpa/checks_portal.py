"""Checks of the TPA portals (provider, client, member). Called from checks after the data of that suite has been created."""

import frappe

from a1erp_tpa.checks import check, make_user, raises


def portal_checks(client, provider, member, net):
	from a1erp_tpa.tpa_management import portal

	for email in ("tpa_prov@example.com", "tpa_cli@example.com", "tpa_mem@example.com", "tpa_none@example.com"):
		make_user(email, [], user_type="Website User")
	other = frappe.get_doc({"doctype": "Medical Provider", "provider_name": "TPA Other Provider", "provider_type": "Clinic / Medical Center",
		"supplier": "TPA Test Hospital", "networks": [{"network": net.name}]}).insert()
	pdoc = frappe.get_doc("Medical Provider", provider.name)
	pdoc.append("contacts", {"contact_name": "Desk", "user": "tpa_prov@example.com", "portal_role": "Staff"})
	pdoc.save()
	cdoc = frappe.get_doc("TPA Client", client.name)
	cdoc.append("portal_users", {"user": "tpa_cli@example.com", "active": 1})
	cdoc.save()
	frappe.db.set_value("Plan Member", member.name, "user", "tpa_mem@example.com")

	frappe.set_user("tpa_none@example.com")
	raises(portal.bootstrap, "not linked", "a user without a link has no portal")

	frappe.set_user("tpa_prov@example.com")
	b = portal.bootstrap()
	check(b["kind"] == "provider" and "new_claim" in b["tabs"] and b["tr"], "provider bootstrap")
	e = portal.eligibility(card_no=member.card_no, category="Outpatient")
	check(e["ok"] and e["copay_percent"] == 10, "provider eligibility check")
	raises(lambda: portal.eligibility(card_no="NO-SUCH"), "no member", "unknown card refused")
	r = portal.submit_claim({"card_no": member.card_no, "invoice_no": "PORTAL-1", "claim_type": "Outpatient", "items": [{"code": "T-CONS", "quantity": 1}]})
	check(r["payer_amount"] > 0 and r["status"] in ("Received", "Under Review"), "provider submits a claim through the portal")
	check(frappe.db.get_value("Medical Claim", r["name"], "source") == "Provider Portal", "claim source is the provider portal")
	raises(lambda: portal.submit_claim({"card_no": member.card_no, "invoice_no": "PORTAL-2", "provider": other.name, "items": [{"code": "T-CONS"}]}),
		"outside your scope", "a provider cannot file claims for another provider")
	raises(lambda: portal.submit_claim({"card_no": member.card_no, "invoice_no": "PORTAL-3", "items": [{"code": "NOPE"}]}), "was not found", "an unknown code is refused")
	pa = portal.request_preauth({"card_no": member.card_no, "auth_type": "Surgery", "items": [{"code": "T-SURG", "quantity": 1}]})
	check(pa["status"] == "Under Review", "provider requests a pre-authorization")
	own = portal.list_claims()
	check(own and all(x.provider == provider.name for x in own), "provider sees only its own claims")
	check(len(portal.list_settlements()) >= 1, "provider sees its settlements")
	check(portal.claim_detail(r["name"])["items"], "provider reads a claim detail")
	raises(portal.list_members, "not available", "a provider cannot list members")
	check(portal.dashboard()["claims"] >= 1, "provider dashboard")

	frappe.set_user("tpa_cli@example.com")
	check(portal.bootstrap()["kind"] == "client", "client bootstrap")
	check(len(portal.list_members()) >= 2 and portal.dashboard()["members"] >= 2, "client sees the members of its plans")
	check(len(portal.list_claims()) >= 1, "client sees the claims of its plans")
	check(isinstance(portal.list_funds(), list), "client funds")
	raises(lambda: portal.eligibility(card_no=member.card_no), "not available", "a client cannot use provider functions")

	frappe.set_user("tpa_mem@example.com")
	check(portal.bootstrap()["kind"] == "member", "member bootstrap")
	cards = portal.my_cards()
	check(cards and cards[0]["qr"] and cards[0]["card_no"] == member.card_no, "member card with a QR code")
	cov = portal.my_coverage()
	check(cov["benefits"] and cov["plan_year"], "member coverage")
	claims = portal.list_claims()
	check(claims and all("settlement" not in x for x in claims), "member sees own claims without settlement data")
	check(len(portal.find_providers()) >= 1, "member finds providers in the network")
	tk = portal.open_ticket("Question", "Hello")
	check(frappe.db.exists("Service Ticket", tk["name"]), "member opens a ticket")
	foreign = frappe.db.get_value("Medical Claim", {"member": ("!=", member.name), "docstatus": 1})
	if foreign:
		raises(lambda: portal.claim_detail(foreign), "not permitted", "a member cannot read another member claim")
	frappe.set_user("Administrator")
