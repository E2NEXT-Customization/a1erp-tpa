# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import shutil
import subprocess

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_years, cint, getdate, nowdate


class TPADocument(Document):
	def validate(self):
		years = cint(self.retention_years) or cint(frappe.get_cached_doc("TPA Settings").document_retention_years) or 10
		base = getdate(self.creation) if self.creation else getdate(nowdate())
		self.retention_until = add_years(base, years)
		if self.is_new():
			prev = frappe.db.get_value("TPA Document", {
				"reference_doctype": self.reference_doctype or ("is", "not set"), "reference_name": self.reference_name or ("is", "not set"),
				"document_type": self.document_type, "title": self.title, "is_latest": 1}, ["name", "version"], as_dict=True)
			if prev:
				self.version, self.supersedes, self.is_latest = cint(prev.version) + 1, prev.name, 1

	def after_insert(self):
		if self.supersedes:
			frappe.db.set_value("TPA Document", self.supersedes, "is_latest", 0, update_modified=False)

	def onload(self):
		if self.is_confidential and not self.is_new():
			log_access(self.doctype, self.name, "View")

	def on_trash(self):
		if frappe.session.user == "Administrator":
			return
		if not (self.archived and getdate(self.retention_until) < getdate(nowdate())) or "System Manager" not in frappe.get_roles():
			frappe.throw(_("Documents are kept for their retention period and cannot be deleted before it ends."))

	@frappe.whitelist()
	def extract_text(self):
		"""Read the text of the attached PDF or image so that it can be searched (needs pdftotext or pytesseract)."""
		self.check_permission("write")
		if not self.file:
			frappe.throw(_("Attach a file first."))
		path = frappe.get_doc("File", {"file_url": self.file}).get_full_path()
		text = ""
		if path.lower().endswith(".pdf") and shutil.which("pdftotext"):
			text = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=120).stdout
		elif path.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
			try:
				import pytesseract
				from PIL import Image

				text = pytesseract.image_to_string(Image.open(path), lang="ara+eng")
			except ImportError:
				frappe.throw(_("OCR needs the pytesseract package and the Tesseract engine on the server."))
		else:
			frappe.throw(_("Text extraction needs pdftotext for PDF files or Tesseract for images on the server."))
		self.db_set("extracted_text", text[:500000])
		return len(text)


def log_access(doctype, name, kind):
	try:
		frappe.get_doc({"doctype": "Access Log", "user": frappe.session.user, "export_from": doctype, "reference_document": name,
			"file_type": kind, "method": "onload"}).insert(ignore_permissions=True)
	except Exception:  # noqa: BLE001
		frappe.log_error(title="Access log failed")


def archive_expired():
	"""Flag documents whose retention period has ended as archived (nothing is ever deleted automatically)."""
	for name in frappe.get_all("TPA Document", filters={"archived": 0, "retention_until": ("<", nowdate())}, pluck="name"):
		frappe.db.set_value("TPA Document", name, {"archived": 1, "archived_on": nowdate()}, update_modified=False)