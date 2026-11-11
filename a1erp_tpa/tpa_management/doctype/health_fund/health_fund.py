# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from a1erp_tpa.tpa_management.posting import refresh_fund


class HealthFund(Document):
	def onload(self):
		if not self.is_new():
			doc = refresh_fund(self.name)
			for k in ("total_contributions", "current_balance", "reserved_amount", "available_balance", "total_claims"):
				self.set(k, doc.get(k))

	@frappe.whitelist()
	def refresh(self):
		return refresh_fund(self.name).as_dict()


def check_low_balances():
	"""Alert the finance team when a fund runs below its threshold (once a day)."""
	for name in frappe.get_all("Health Fund", filters={"status": "Active"}, pluck="name"):
		f = refresh_fund(name)
		limit = flt(f.low_balance_amount) or flt(f.total_contributions) * flt(f.low_balance_percent) / 100
		if limit and flt(f.available_balance) < limit and str(f.last_alert_date) != nowdate():
			for u in frappe.get_all("Has Role", filters={"role": ("in", ["TPA Finance", "TPA Manager"]), "parenttype": "User"}, pluck="parent"):
				if u != "Administrator":
					frappe.get_doc({"doctype": "ToDo", "allocated_to": u, "reference_type": "Health Fund", "reference_name": name,
						"description": _("Fund {0}: the available balance {1} is below {2}").format(name, f.available_balance, flt(limit, 2))}).insert(ignore_permissions=True)
			f.db_set("last_alert_date", nowdate())