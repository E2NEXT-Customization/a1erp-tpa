"""Medical card helpers: QR code and public verification."""

import hashlib
import hmac

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import getdate, nowdate


def sign(card_no):
	key = (frappe.local.conf.get("encryption_key") or frappe.local.site).encode()
	return hmac.new(key, card_no.encode(), hashlib.sha256).hexdigest()[:24]


def verify_url(card_no):
	try:
		base = frappe.utils.get_url()
	except AttributeError:  # no web request (console, scheduler)
		base = frappe.local.conf.host_name or "http://" + frappe.local.site
	return "{0}/api/method/a1erp_tpa.tpa_management.cards.verify?card_no={1}&sig={2}".format(base, card_no, sign(card_no))


def card_qr(card):
	"""PNG data URL of the QR code of a card (a jinja method used by the print format)."""
	from pyqrcode import create as qr

	return "data:image/png;base64," + qr(verify_url(frappe.db.get_value("Medical Card", card, "card_no"))).png_as_base64_str(scale=4)


@frappe.whitelist()
def qr_data(card):
	"""Same image for the mobile application; the caller needs read permission on the card."""
	frappe.get_doc("Medical Card", card).check_permission("read")
	return card_qr(card)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=60, seconds=60)
def verify(card_no, sig):
	"""Public check made when a card is scanned: is the membership active today?"""
	if not hmac.compare_digest(sig, sign(card_no)):
		return {"valid": False}
	m = frappe.db.get_value("Plan Member", {"card_no": card_no}, ["name", "member_name", "status", "start_date", "end_date", "plan"], as_dict=True)
	if not m:
		return {"valid": False}
	today = getdate(nowdate())
	ok = m.status == "Active" and (not m.start_date or getdate(m.start_date) <= today) and (not m.end_date or today <= getdate(m.end_date))
	return {"valid": bool(ok), "member": m.member_name, "card_no": card_no, "status": _(m.status), "valid_until": m.end_date}