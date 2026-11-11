"""Default configuration of the TPA module: roles, accounts, settings, fraud rules, rejection reasons and notification templates.

Everything is created only when missing, so a re-run never overwrites what the user edited."""

import frappe

TPA_ROLES = ("TPA Manager", "TPA Claims Officer", "TPA Medical Reviewer", "TPA Finance", "TPA Customer Service")

# claim workflow: (from, to, role that may make the change; managers always may)
TRANSITIONS = [
	("Received", "Under Review", None), ("Received", "Medical Review", None), ("Received", "Pending Information", None),
	("Received", "Rejected", "TPA Claims Officer"), ("Received", "Approved", "TPA Claims Officer"), ("Received", "Partially Approved", "TPA Claims Officer"),
	("Under Review", "Medical Review", None), ("Under Review", "Financial Review", None), ("Under Review", "Pending Information", None),
	("Under Review", "Rejected", "TPA Claims Officer"), ("Under Review", "Approved", "TPA Claims Officer"), ("Under Review", "Partially Approved", "TPA Claims Officer"),
	("Medical Review", "Financial Review", "TPA Medical Reviewer"), ("Medical Review", "Pending Information", "TPA Medical Reviewer"),
	("Medical Review", "Rejected", "TPA Medical Reviewer"), ("Medical Review", "Approved", "TPA Medical Reviewer"),
	("Medical Review", "Partially Approved", "TPA Medical Reviewer"),
	("Financial Review", "Pending Information", "TPA Finance"), ("Financial Review", "Rejected", "TPA Finance"),
	("Financial Review", "Approved", "TPA Finance"), ("Financial Review", "Partially Approved", "TPA Finance"),
	("Pending Information", "Under Review", None), ("Pending Information", "Medical Review", None), ("Pending Information", "Rejected", "TPA Claims Officer"),
	("Rejected", "Under Review", "TPA Manager"),
]
# (document, up to amount, role, level); 0 = no ceiling
APPROVAL_LEVELS = [
	("Pre-Authorization", 5_000_000, "TPA Claims Officer", 1), ("Pre-Authorization", 25_000_000, "TPA Medical Reviewer", 2), ("Pre-Authorization", 0, "TPA Manager", 3),
	("Medical Claim", 10_000_000, "TPA Claims Officer", 1), ("Medical Claim", 50_000_000, "TPA Medical Reviewer", 2), ("Medical Claim", 0, "TPA Manager", 3),
	("Provider Settlement", 100_000_000, "TPA Finance", 1), ("Provider Settlement", 0, "TPA Manager", 2),
]
SLA = [("Urgent", 1, 24), ("High", 4, 48), ("Medium", 8, 72), ("Low", 24, 120)]

FWA_RULES = [
	("Duplicate claim for the same service", "Duplicate Claim", "High", "Hold for Review", {"window_days": 7}),
	("Many claims in a short period", "High Frequency", "Medium", "Flag Only", {"window_days": 30, "threshold_count": 6}),
	("Several services not covered", "Coverage Mismatch", "Low", "Flag Only", {"threshold_count": 2}),
	("Billed price above the tariff", "Price Above Tariff", "Medium", "Flag Only", {"threshold_percent": 0}),
	("Sudden rise in a provider's claims", "Provider Cost Spike", "Medium", "Flag Only", {"window_days": 30, "threshold_percent": 50, "threshold_count": 20}),
	("Drug dispensed again too early", "Drug Pattern", "Medium", "Flag Only", {"window_days": 0}),
	("High cost claim", "High Cost Case", "Medium", "Flag Only", {"threshold_amount": 10_000_000}),
	("Unusually long stay", "Long Stay", "Low", "Flag Only", {"threshold_count": 14}),
]
# code, English, Arabic, category
REASONS = [
	("COV-01", "Service not covered by the plan", "الخدمة غير مغطاة بموجب الخطة", "Coverage"),
	("COV-02", "Benefit limit exhausted", "استُنفد حد المنفعة", "Coverage"),
	("COV-03", "Excluded condition or treatment", "حالة أو علاج مستثنى", "Coverage"),
	("ELG-01", "Membership not active on the date of service", "العضوية غير فعالة بتاريخ الخدمة", "Eligibility"),
	("ELG-02", "Waiting period not completed", "لم تنتهِ فترة الانتظار", "Eligibility"),
	("ELG-03", "Provider outside the network", "مقدم الخدمة خارج الشبكة", "Eligibility"),
	("MED-01", "Not medically necessary", "غير ضروري طبياً", "Medical Necessity"),
	("PRC-01", "Price above the agreed tariff", "السعر أعلى من التعرفة المتفق عليها", "Pricing"),
	("DOC-01", "Required documents are missing", "المستندات المطلوبة ناقصة", "Documentation"),
	("DUP-01", "Duplicate claim", "مطالبة مكررة", "Duplicate"),
	("FRD-01", "Suspected fraud", "اشتباه في احتيال", "Fraud"),
	("OTH-01", "Other reason", "سبب آخر", "Other"),
]

# event: (English subject, English message, Arabic subject, Arabic message); every message is plain text and editable
TEXTS = {
	"Member Activated": (
		"Your health cover is active", "Dear {{ customer_name }}, your health cover is now active. Membership number: {{ doc.card_no }}. Present your card at the provider.",
		"تفعيل التغطية الصحية", "السيد/ة {{ customer_name }} المحترم/ة، تم تفعيل تغطيتكم الصحية. رقم العضوية: {{ doc.card_no }}. يرجى إبراز البطاقة لدى مقدم الخدمة."),
	"Card Issued": (
		"Your medical card was issued", "Dear {{ customer_name }}, your medical card {{ doc.card_no }} was issued and is valid until {{ doc.valid_until }}.",
		"إصدار البطاقة الطبية", "السيد/ة {{ customer_name }} المحترم/ة، تم إصدار بطاقتكم الطبية رقم {{ doc.card_no }} وهي سارية حتى {{ doc.valid_until }}."),
	"Coverage Expiring": (
		"Your health cover is about to end", "Dear {{ customer_name }}, your health cover ends on {{ doc.end_date }}. Please contact your employer or insurer to renew.",
		"قرب انتهاء التغطية الصحية", "السيد/ة {{ customer_name }} المحترم/ة، تنتهي تغطيتكم الصحية بتاريخ {{ doc.end_date }}. يرجى مراجعة جهة العمل أو شركة التأمين للتجديد."),
	"Pre-Auth Requested": (
		"Pre-authorization {{ doc.name }} received", "Dear {{ customer_name }}, the pre-authorization request {{ doc.name }} was received and is under review.",
		"استلام طلب الموافقة المسبقة {{ doc.name }}", "السيد/ة {{ customer_name }} المحترم/ة، تم استلام طلب الموافقة المسبقة رقم {{ doc.name }} وهو قيد المراجعة."),
	"Pre-Authorization Decision": (
		"Pre-authorization {{ doc.name }}: {{ doc.status }}", "Dear {{ customer_name }}, the decision on pre-authorization {{ doc.name }} is: {{ doc.status }}. Approved amount: {{ doc.approved_amount }}.",
		"قرار الموافقة المسبقة {{ doc.name }}", "السيد/ة {{ customer_name }} المحترم/ة، قرار الموافقة المسبقة رقم {{ doc.name }}: {{ doc.status }}. المبلغ المعتمد: {{ doc.approved_amount }}."),
	"Claim Status Update": (
		"Claim {{ doc.name }}: {{ doc.status }}", "Dear {{ customer_name }}, your claim {{ doc.name }} is now: {{ doc.status }}.",
		"تحديث حالة المطالبة {{ doc.name }}", "السيد/ة {{ customer_name }} المحترم/ة، أصبحت حالة مطالبتكم رقم {{ doc.name }}: {{ doc.status }}."),
}

ACCOUNTS = [
	("fund_liability_account", "TPA Health Funds", "Liability", ["Current Liabilities", "Liabilities"], ""),
	("admin_fee_income_account", "TPA Administration Fee Income", "Income", ["Direct Income", "Income"], ""),
	("adjustments_account", "TPA Settlement Adjustments", "Income", ["Indirect Income", "Direct Income", "Income"], ""),
]


def _find_parent(company, root_type, preferred):
	for name in preferred:
		acc = frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_name": name, "root_type": root_type})
		if acc:
			return acc
	return frappe.db.get_value("Account", {"company": company, "is_group": 1, "root_type": root_type, "parent_account": ("is", "not set")}, "name")


def _ensure(company, account_name, parent, is_group, account_type="", currency=None):
	existing = frappe.db.get_value("Account", {"company": company, "account_name": account_name})
	if existing:
		return existing, False
	doc = frappe.get_doc({"doctype": "Account", "account_name": account_name, "parent_account": parent, "company": company,
		"is_group": is_group, "account_type": account_type, "account_currency": currency})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name, True


def ensure_tpa_defaults():
	ensure_roles()
	ensure_settings()
	ensure_fwa_rules()
	ensure_reasons()
	ensure_templates()


def ensure_roles():
	for role in TPA_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def ensure_settings():
	s = frappe.get_doc("TPA Settings")
	company = s.company or frappe.db.get_value("Company", {}, "name")
	s.company = company
	if company:
		currency = frappe.get_cached_value("Company", company, "default_currency")
		for field, name, root, preferred, kind in ACCOUNTS:
			if s.get(field):
				continue
			parent = _find_parent(company, root, preferred)
			if parent:
				s.set(field, _ensure(company, name, parent, 0, kind, currency)[0])
	if not s.transitions:
		for a, b, role in TRANSITIONS:
			s.append("transitions", {"from_status": a, "to_status": b, "allowed_role": role})
	if not s.approval_levels:
		for doc, amount, role, level in APPROVAL_LEVELS:
			s.append("approval_levels", {"document_type": doc, "max_amount": amount, "role": role, "level": level})
	if not s.sla_rules:
		for priority, first, resolve in SLA:
			s.append("sla_rules", {"priority": priority, "response_hours": first, "resolution_hours": resolve})
	s.flags.ignore_permissions = True
	s.save()
	frappe.clear_document_cache("TPA Settings", "TPA Settings")


def ensure_fwa_rules():
	for name, kind, severity, action, params in FWA_RULES:
		if not frappe.db.exists("FWA Rule", {"rule_type": kind}):
			frappe.get_doc({"doctype": "FWA Rule", "rule_name": name, "rule_type": kind, "severity": severity, "action": action, "enabled": 1, **params}
				).insert(ignore_permissions=True)


def ensure_reasons():
	for code, en, ar, category in REASONS:
		if not frappe.db.exists("Claim Rejection Reason", code):
			frappe.get_doc({"doctype": "Claim Rejection Reason", "reason_code": code, "reason_en": en, "reason_ar": ar, "category": category}).insert(ignore_permissions=True)


def ensure_templates():
	for event, (sub_en, msg_en, sub_ar, msg_ar) in TEXTS.items():
		for lang, sub, msg in (("en", sub_en, msg_en), ("ar", sub_ar, msg_ar)):
			for channel in ("Email", "SMS"):
				if frappe.db.exists("TPA Notification Template", {"event": event, "channel": channel, "language": lang, "recipients": "Member"}):
					continue
				frappe.get_doc({"doctype": "TPA Notification Template", "event": event, "channel": channel, "language": lang, "recipients": "Member",
					"subject": sub, "message": msg, "enabled": 1}).insert(ignore_permissions=True)