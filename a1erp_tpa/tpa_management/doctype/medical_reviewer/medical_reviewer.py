# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MedicalReviewer(Document):
	def validate(self):
		self.refresh_open()

	def refresh_open(self):
		n = frappe.db.count("Medical Claim", {"medical_reviewer": self.user, "docstatus": 1, "status": ("in", ["Under Review", "Medical Review", "Pending Information"])})
		n += frappe.db.count("Pre-Authorization", {"assigned_reviewer": self.user, "status": ("in", ["Submitted", "Under Review", "Medical Review", "Pending Information"])})
		self.open_items = n


def assign(speciality=None):
	"""Active reviewer with the lowest load for the speciality (a general reviewer when nobody matches)."""
	best = None
	for r in frappe.get_all("Medical Reviewer", filters={"active": 1}, pluck="name"):
		doc = frappe.get_doc("Medical Reviewer", r)
		doc.refresh_open()
		if doc.open_items >= (doc.max_open_items or 30):
			continue
		match = speciality and speciality in [s.speciality for s in doc.specialities]
		general = not doc.specialities
		if not (match or general):
			continue
		key = (0 if match else 1, doc.open_items)
		if best is None or key < best[0]:
			best = (key, doc.user)
	return best[1] if best else None