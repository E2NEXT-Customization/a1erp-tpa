import frappe
from frappe import _

no_cache = 1

KEYS = {
	"title": "Health Insurance Portal", "welcome": "Welcome", "none": "No records.", "error": "Error", "saved": "Saved", "send": "Send", "search": "Search",
	"dashboard": "Dashboard", "eligibility": "Check Eligibility", "new_claim": "Submit a Claim", "claims": "Claims", "new_preauth": "Request Pre-Authorization",
	"preauths": "Pre-Authorizations", "settlements": "Settlements", "members": "Members", "funds": "Funds", "card": "My Card", "coverage": "My Coverage",
	"providers": "Find a Provider", "help": "Help and Complaints", "status": "Status", "date": "Date", "claim": "Claim", "member": "Member", "provider": "Provider",
	"plan": "Plan", "type": "Type", "amount": "Amount", "card_no": "Card No.", "national_id": "National ID", "category": "Benefit", "service_date": "Date of Service",
	"invoice_no": "Invoice No.", "invoice_date": "Invoice Date", "claim_type": "Claim Type", "diagnosis": "Diagnosis", "pre_auth": "Pre-Authorization",
	"items": "Services and Drugs", "add_item": "Add a line", "code": "Code", "quantity": "Quantity", "price": "Price", "service": "Service", "drug": "Drug",
	"claimed": "Claimed Amount", "discount": "Contractual Discount", "member_share": "Member Share", "payable": "Payable to the Provider", "paid": "Paid",
	"in_progress": "In Progress", "rejected": "Rejected", "open_preauths": "Open Pre-Authorizations", "active_members": "Active Members", "check": "Check",
	"eligible": "Eligible", "not_eligible": "Not Eligible", "reasons": "Reasons", "copay": "Co-payment (%)", "needs_preauth": "Requires pre-authorization",
	"remaining": "Remaining", "limit": "Annual Limit", "used": "Used", "valid_until": "Valid Until", "class_name": "Class", "network": "In the network",
	"yes": "Yes", "no": "No", "posting_date": "Posting Date", "period": "Period", "gross": "Claims Payable", "adjustments": "Adjustments", "net": "Net Payable",
	"payment": "Payment", "contributions": "Contributions", "balance": "Balance", "reserved": "Reserved", "available": "Available Balance", "fund": "Fund",
	"status_filter": "All statuses", "details": "Details", "close": "Close", "info_needed": "Information requested", "reason": "Reason", "line_total": "Billed Amount",
	"payer": "Payable", "note": "Note", "name": "Name", "relationship": "Relationship", "governorate": "Governorate", "city": "City", "phone": "Phone",
	"address": "Address", "subject": "Subject", "description": "Description", "ticket_type": "Ticket Type", "inquiry": "Inquiry", "complaint": "Complaint",
	"suggestion": "Suggestion", "ticket_ok": "Your request was received. Reference", "claim_ok": "The claim was received", "preauth_ok": "The request was received",
	"scan_hint": "Show this code to the provider to confirm your membership.", "overall": "Overall Limit", "waiting": "Waiting Period (Days)",
	"sign_out": "Sign out", "approved": "Approved Amount", "auth_type": "Authorization Type", "notes": "Medical Notes", "priority": "Priority", "expected_days": "Expected Days",
	"hint_eligibility": "Enter the card number or the national ID of the member.", "hint_claim": "Enter the invoice data and the billed services. Prices are checked against your tariff.",
	"claimed_total": "Claimed", "branch": "Provider",
}


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/tpa"
		raise frappe.Redirect
	context.title = _("Health Insurance Portal")
	context.T = {k: _(v) for k, v in KEYS.items()}
	context.rtl = frappe.local.lang == "ar"