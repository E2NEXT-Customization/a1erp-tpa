"""Notifications of the TPA module: member alerts by email, SMS, WhatsApp and in-app, with a delivery log and retries."""

import json
from math import ceil

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime

TEMPLATE = "TPA Notification Template"
LOG = "TPA Notification Log"
PROVIDER = "TPA Notification Provider"


def settings():
	return frappe.get_cached_doc("TPA Settings")


# ------------------------------------------------------------------ recipients and rendering
def resolve_party(doc):
	member = doc if doc.doctype == "Plan Member" else frappe.get_doc("Plan Member", doc.member)
	return frappe._dict(name=member.member_name, mobile=member.mobile_no, email=member.email_id, language=member.language)


def pick_template(templates, channel, kind, language):
	default = settings().notification_default_language or "ar"
	pool = [t for t in templates if t.channel == channel and t.recipients == kind]
	for lang in (language, default, "en", "ar"):
		for t in pool:
			if t.language == lang:
				return t
	return pool[0] if pool else None


def segments_of(text):
	unicode = any(ord(c) > 127 for c in text or "")
	single, multi = (70, 67) if unicode else (160, 153)
	n = len(text or "")
	return 1 if n <= single else ceil(n / multi)


def render(text, context):
	return frappe.render_template(text or "", context)


def notify(event, doc, extra=None, send_at=None, dedupe=None):
	"""Create (and queue for sending) the notification logs of an event; returns the log names."""
	if not cint(settings().notifications_enabled):
		return []
	templates = frappe.get_all(TEMPLATE, filters={"event": event, "enabled": 1},
		fields=["name", "channel", "language", "recipients", "internal_role", "provider", "subject", "message", "attach_print"])
	if not templates:
		return []
	party = resolve_party(doc)
	ctx = {"doc": doc, "customer_name": party.name, "company": doc.get("company"), "policy": doc, **(extra or {})}
	logs = []
	if any(t.recipients == "Member" for t in templates):
		for channel, address in (("SMS", party.mobile), ("WhatsApp", party.mobile), ("Email", party.email)):
			t = pick_template(templates, channel, "Member", party.language)
			if t and address:
				logs.append(create_log(event, t, address, ctx, doc, send_at, dedupe))
	for t in templates:
		if t.recipients == "Internal Role" and t.internal_role:
			users = frappe.get_all("Has Role", filters={"role": t.internal_role, "parenttype": "User"}, pluck="parent")
			for u in set(users) - {"Administrator", "Guest"}:
				if t.channel == "In-App":
					logs.append(create_log(event, t, u, ctx, doc, send_at, dedupe))
				elif t.channel == "Email":
					email = frappe.db.get_value("User", u, "email")
					if email:
						logs.append(create_log(event, t, email, ctx, doc, send_at, dedupe))
	return [x for x in logs if x]


def create_log(event, t, recipient, ctx, doc, send_at, dedupe):
	key = "{0}|{1}|{2}|{3}".format(event, doc.name, recipient, dedupe or "") if dedupe else None
	if key and frappe.db.exists(LOG, {"dedupe_key": key}):
		return None
	message = render(t.message, ctx)
	provider = None
	if t.channel in ("SMS", "WhatsApp"):
		provider = t.provider or settings().get("default_sms_provider" if t.channel == "SMS" else "default_whatsapp_provider")
	segs = segments_of(message) if t.channel in ("SMS", "WhatsApp") else 0
	cost = flt(frappe.db.get_value(PROVIDER, provider, "cost_per_segment")) * segs if provider else 0
	log = frappe.get_doc({"doctype": LOG, "event": event, "channel": t.channel, "status": "Scheduled",
		"recipient": recipient, "language": t.language, "provider": provider, "reference_doctype": doc.doctype,
		"reference_name": doc.name, "scheduled_for": send_at or now_datetime(), "subject": render(t.subject, ctx) or _(event),
		"message": message, "segments": segs, "cost": cost, "dedupe_key": key, "template": t.name})
	log.insert(ignore_permissions=True)
	if not send_at:
		if frappe.flags.in_test:
			send_log(log.name)
		else:
			frappe.enqueue("a1erp_tpa.tpa_management.notifications.send_log", log_name=log.name, queue="short", enqueue_after_commit=True)
	return log.name


# ------------------------------------------------------------------ sending
def send_log(log_name):
	log = frappe.get_doc(LOG, log_name)
	if log.status in ("Sent", "Cancelled"):
		return
	log.attempts = cint(log.attempts) + 1
	try:
		{"Email": send_email, "SMS": send_text, "WhatsApp": send_text, "In-App": send_in_app}[log.channel](log)
		log.status, log.sent_on, log.error = "Sent", now_datetime(), None
	except Exception as e:  # noqa: BLE001
		log.status, log.error = "Failed", str(e)[:500]
	log.save(ignore_permissions=True)
	frappe.db.commit() if not frappe.flags.in_test else None


def send_email(log):
	template = frappe.get_doc(TEMPLATE, log.template) if log.get("template") else None
	attachments = None
	if template and template.attach_print and log.reference_doctype and log.reference_name:
		attachments = [frappe.attach_print(log.reference_doctype, log.reference_name, print_format=None)]
	frappe.sendmail(recipients=[log.recipient], subject=log.subject, message=log.message, reference_doctype=log.reference_doctype,
		reference_name=log.reference_name, attachments=attachments, now=bool(frappe.flags.in_test))


def send_in_app(log):
	frappe.get_doc({"doctype": "Notification Log", "for_user": log.recipient, "type": "Alert", "subject": log.subject,
		"email_content": log.message, "document_type": log.reference_doctype, "document_name": log.reference_name}
		).insert(ignore_permissions=True)


def send_text(log):
	if not log.provider:
		if log.channel == "SMS":
			from frappe.core.doctype.sms_settings.sms_settings import send_sms

			send_sms([log.recipient], log.message, success_msg=False)
			return
		raise frappe.ValidationError(_("No WhatsApp provider is configured."))
	http_send(frappe.get_doc(PROVIDER, log.provider), log.recipient, log.message)


def http_send(provider, recipient, message):
	import requests

	if not provider.enabled:
		raise frappe.ValidationError(_("Provider {0} is disabled.").format(provider.name))
	body = render(provider.body_template or '{"to": {{ recipient | tojson }}, "text": {{ message | tojson }}}',
		{"recipient": recipient, "message": message, "sender": provider.sender_id or ""})
	headers = json.loads(provider.extra_headers) if provider.extra_headers else {}
	params, auth = {}, None
	secret = provider.get_password("auth_secret", raise_exception=False)
	if provider.auth_type == "Bearer Token":
		headers["Authorization"] = "Bearer {0}".format(secret)
	elif provider.auth_type == "Basic":
		auth = (provider.auth_name, secret)
	elif provider.auth_type == "Header Key":
		headers[provider.auth_name] = secret
	elif provider.auth_type == "Query Parameter":
		params[provider.auth_name] = secret
	kwargs = {"headers": headers, "params": params, "auth": auth, "timeout": 15}
	payload = json.loads(body)
	if provider.http_method == "GET":
		kwargs["params"] = {**params, **payload}
	elif provider.content_type == "Form":
		kwargs["data"] = payload
	else:
		headers.setdefault("Content-Type", "application/json")
		kwargs["data"] = body.encode("utf-8")
	res = requests.request(provider.http_method, provider.endpoint_url, **kwargs)
	ok = {c.strip() for c in (provider.success_codes or "200,201,202").split(",")}
	if str(res.status_code) not in ok:
		raise frappe.ValidationError(_("Provider answered {0}: {1}").format(res.status_code, res.text[:200]))


# ------------------------------------------------------------------ scheduled job
def process_queue():
	"""Send scheduled notifications and retry failed ones."""
	for name in frappe.get_all(LOG, filters={"status": "Scheduled", "scheduled_for": ("<=", now_datetime())}, pluck="name"):
		send_log(name)
	limit = cint(settings().notification_max_attempts) or 3
	retry_before = frappe.utils.add_to_date(now_datetime(), hours=-1)
	for name in frappe.get_all(LOG, filters={"status": "Failed", "attempts": ("<", limit), "modified": ("<", retry_before)}, pluck="name"):
		send_log(name)
