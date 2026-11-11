"""Core of the demo data generator: run context, record registry, simulated dates and realistic value helpers."""

import importlib
import json
import random
import string
import traceback
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime, nowdate

from a1erp_tpa.demo_data import catalog as C

# size of each profile
PROFILES = {
	"Quick Tour": dict(providers=24, members=180, preauths=40, med_claims=260, tickets=25, months=8),
	"Standard": dict(providers=36, members=600, preauths=120, med_claims=1000, tickets=60, months=12),
	"Full": dict(providers=len(C.PROVIDERS), members=1500, preauths=300, med_claims=3000, tickets=120, months=18),
}
PREFIX_EMAIL = "example.com"

# modules whose nowdate / now_datetime are replaced while a record is created "in the past"
SIM_MODULES = [
	"a1erp_tpa.tpa_management.engine", "a1erp_tpa.tpa_management.posting",
	"a1erp_tpa.tpa_management.doctype.medical_claim.medical_claim", "a1erp_tpa.tpa_management.doctype.pre_authorization.pre_authorization",
	"a1erp_tpa.tpa_management.doctype.provider_settlement.provider_settlement", "a1erp_tpa.tpa_management.doctype.plan_member.plan_member",
	"a1erp_tpa.tpa_management.doctype.medical_card.medical_card", "a1erp_tpa.tpa_management.doctype.service_ticket.service_ticket",
	"a1erp_tpa.tpa_management.doctype.health_fund.health_fund", "a1erp_tpa.tpa_management.fwa",
]


class Ctx:
	"""State of one generation run."""

	def __init__(self, run):
		self.run = run
		self.p = frappe._dict(PROFILES.get(run.profile) or PROFILES["Standard"])
		self.rng = random.Random(cint(run.seed) or 2026)
		self.company = frappe.db.get_single_value("TPA Settings", "company") or frappe.db.get_value("Company", {}, "name")
		self.today = getdate(nowdate())
		self.seq = cint(frappe.db.sql("select max(seq) from `tabTPA Demo Record`")[0][0])
		self.errors = 0
		self.created = 0
		self.lines = []
		self.highlights = []
		self.backup = json.loads(run.backup or "{}")
		self.used_ids = set()
		self.used_names = set()
		self.store = frappe._dict()
		self._weights = None
		self._pending = 0
		self.phase = (0, 100)

	# ---------------------------------------------------------------- progress and logging
	def log(self, text, error=False):
		stamp = now_datetime().strftime("%H:%M:%S")
		self.lines.append(f"{stamp} {'ERROR ' if error else ''}{text}")
		self.lines = self.lines[-400:]

	def progress(self, step, fraction):
		lo, hi = self.phase
		pct = round(lo + (hi - lo) * max(0.0, min(1.0, fraction)), 1)
		frappe.db.set_value("TPA Demo Run", self.run.name, {"progress": pct, "current_step": step[:140], "records": self.created,
			"errors": self.errors, "log": "\n".join(self.lines)}, update_modified=False)
		frappe.db.commit()
		frappe.publish_realtime("tpa_demo_progress", {"run": self.run.name, "progress": pct, "step": step, "records": self.created,
			"errors": self.errors, "log": self.lines[-1] if self.lines else ""}, after_commit=False)

	def batch(self, n=20):
		self._pending += 1
		if self._pending >= n:
			frappe.db.commit()
			self._pending = 0

	# ---------------------------------------------------------------- registry
	def track(self, doctype, name):
		if not name:
			return
		self.seq += 1
		frappe.db.sql("""insert into `tabTPA Demo Record` (name, creation, modified, owner, modified_by, docstatus, idx, run, ref_doctype, ref_name, seq)
			values (%s, now(), now(), 'Administrator', 'Administrator', 0, 0, %s, %s, %s, %s)""", (frappe.generate_hash(length=12), self.run.name, doctype, name, self.seq))
		self.created += 1

	def insert(self, data, submit=False, backdate=None):
		doc = frappe.get_doc(data) if isinstance(data, dict) else data
		doc.flags.ignore_permissions = True
		doc.insert()
		self.track(doc.doctype, doc.name)
		if submit:
			doc.submit()
		if backdate:
			self.backdate(doc.doctype, doc.name, backdate)
		return doc

	def backdate(self, doctype, name, when):
		when = get_datetime(when) if not isinstance(when, datetime) else when
		frappe.db.sql(f"update `tab{doctype}` set creation=%s, modified=%s where name=%s", (when, when, name))

	def attempt(self, label, fn, *args, **kw):
		"""Run one record inside a savepoint: an error skips the record but keeps the run going."""
		sp = "dd_" + frappe.generate_hash(length=8)
		frappe.db.savepoint(sp)
		try:
			out = fn(*args, **kw)
			self.batch()
			return out
		except Exception as e:  # noqa: BLE001
			frappe.db.rollback(save_point=sp)
			self.errors += 1
			msg = str(e).replace("\n", " ")[:220] or e.__class__.__name__
			self.log(f"{label}: {msg}", error=True)
			if self.errors <= 3:
				frappe.log_error(title=f"Demo data: {label}", message=traceback.format_exc())
			return None

	def highlight(self, title, doctype, name, note="", limit=1):
		"""Keep the walkthrough short: at most `limit` examples of each kind (the kind is the title before any colon)."""
		if not name:
			return
		kind = title.split(":")[0].split("(")[0].strip()
		if sum(1 for h in self.highlights if h.get("kind") == kind) >= limit:
			return
		self.highlights.append({"title": title, "doctype": doctype, "name": name, "note": note, "kind": kind})

	# ---------------------------------------------------------------- random helpers
	def chance(self, p):
		return self.rng.random() < p

	def pick(self, seq):
		return self.rng.choice(seq)

	def weighted(self, pairs):
		total = sum(w for _v, w in pairs)
		r = self.rng.uniform(0, total)
		upto = 0
		for v, w in pairs:
			upto += w
			if r <= upto:
				return v
		return pairs[-1][0]

	def amount(self, lo, hi, step=1000):
		return int(self.rng.uniform(lo, hi) // step * step) or step

	def days_ago(self, lo, hi):
		return add_days(self.today, -self.rng.randint(lo, hi))

	def stamp(self, d, start_hour=8, end_hour=16):
		return datetime.combine(getdate(d), time(self.rng.randint(start_hour, end_hour), self.rng.randint(0, 59), self.rng.randint(0, 59)))

	def governorate(self):
		if not self._weights:
			self._weights = [(k, v[2]) for k, v in C.GOVERNORATES.items()]
		return self.weighted(self._weights)

	def address(self, gov=None):
		gov = gov or self.governorate()
		ar, districts, _w = C.GOVERNORATES[gov]
		return gov, f"{ar}، {self.pick(districts)}، محلة {self.rng.randint(101, 999)}، زقاق {self.rng.randint(1, 60)}، دار {self.rng.randint(1, 120)}"

	def mobile(self):
		return f"07{self.pick(['70', '71', '72', '73', '80', '81', '82', '50', '51'])}{self.rng.randint(1000000, 9999999)}"

	def national_id(self):
		while True:
			n = f"{self.pick(['19', '20'])}{self.rng.randint(10 ** 9, 10 ** 10 - 1)}"
			if n not in self.used_ids:
				self.used_ids.add(n)
				return n

	def person(self, gender=None, kurdish=None, family=None):
		"""Returns (arabic full name, latin full name, gender, first latin)."""
		gender = gender or self.pick(["Male", "Male", "Female"])
		kurdish = self.chance(0.12) if kurdish is None else kurdish
		if gender == "Male":
			first = self.pick(C.KURDISH_MALE if kurdish else C.MALE)
		else:
			first = self.pick(C.KURDISH_FEMALE if kurdish else C.FEMALE)
		father = self.pick(C.KURDISH_MALE + C.FATHERS[:10] if kurdish else C.FATHERS)
		grand = self.pick(C.FATHERS)
		fam = family or self.pick(C.KURDISH_FAMILIES if kurdish else C.FAMILIES)
		for _i in range(5):
			ar = f"{first[0]} {father[0]} {grand[0]} {fam[0]}"
			en = f"{first[1]} {father[1]} {grand[1]} {fam[1]}"
			if en not in self.used_names:
				break
			grand = self.pick(C.FATHERS)
		self.used_names.add(en)
		return ar, en, gender, first[1]

	def email(self, latin):
		base = "".join(ch for ch in latin.lower().replace(" ", ".") if ch.isalnum() or ch == ".")
		return f"{base[:28]}{self.rng.randint(1, 99)}@{PREFIX_EMAIL}"

	def company_name(self):
		for _i in range(50):
			stem, act, form = self.pick(C.COMPANY_STEMS), self.pick(C.COMPANY_ACTIVITIES), self.pick(C.COMPANY_FORMS)
			en = f"{stem[1]} {act[1]} {form[1]}"
			if en not in self.used_names:
				self.used_names.add(en)
				return f"{form[0]} {stem[0]} {act[0]}", en, act[2]
		raise frappe.ValidationError("No more company names")

	def vin(self, make):
		prefix = {"Toyota": "JTM", "Hyundai": "KMH", "Kia": "KNA", "Nissan": "JN1", "Chevrolet": "1GN", "GMC": "1GK", "Lexus": "JTJ",
			"Mercedes-Benz": "WDD", "BMW": "WBA", "Mitsubishi": "JMB", "Isuzu": "JAL", "Honda": "LAL"}.get(make, "LGW")
		chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
		return prefix + "".join(self.pick(chars) for _ in range(14))

	def plate(self):
		return f"{self.rng.randint(10000, 999999)} {self.pick(C.PLATE_LETTERS)}"

	def iban(self):
		return f"IQ{self.rng.randint(10, 98)}{''.join(self.pick(string.ascii_uppercase) for _ in range(4))}{self.rng.randint(10 ** 14, 10 ** 15 - 1)}"


@contextmanager
def as_of(when):
	"""Make the application believe the current date and time is `when` (only inside the listed modules)."""
	when = get_datetime(when) if not isinstance(when, datetime) else when
	d = when.date()
	fakes = {"nowdate": lambda: str(d), "today": lambda: str(d), "now_datetime": lambda: when, "now": lambda: str(when)}
	saved = []
	for path in SIM_MODULES:
		try:
			mod = importlib.import_module(path)
		except ImportError:
			continue
		for attr, fn in fakes.items():
			if hasattr(mod, attr):
				saved.append((mod, attr, getattr(mod, attr)))
				setattr(mod, attr, fn)
	try:
		yield when
	finally:
		for mod, attr, fn in saved:
			setattr(mod, attr, fn)


@contextmanager
def quiet():
	"""No e-mails, SMS or WhatsApp messages while demo data is created."""
	from a1erp_tpa.tpa_management import notifications

	saved = notifications.notify
	notifications.notify = lambda *a, **k: []
	frappe.flags.mute_emails = True
	try:
		yield
	finally:
		notifications.notify = saved
		frappe.flags.mute_emails = False


def ensure_fiscal_years(company, first_day):
	"""Journal entries need a fiscal year for every date used."""
	year = getdate(first_day).year
	for y in range(year, getdate(nowdate()).year + 2):
		start, end = f"{y}-01-01", f"{y}-12-31"
		existing = frappe.db.sql("select name from `tabFiscal Year` where year_start_date <= %s and year_end_date >= %s", (start, end))
		if existing:
			fy = frappe.get_doc("Fiscal Year", existing[0][0])
			if not any(c.company == company for c in fy.companies) and fy.companies:
				fy.append("companies", {"company": company})
				fy.save(ignore_permissions=True)
			continue
		frappe.get_doc({"doctype": "Fiscal Year", "year": str(y), "year_start_date": start, "year_end_date": end,
			"companies": [{"company": company}]}).insert(ignore_permissions=True)


def simple_pdf(lines):
	"""A small valid one-page PDF (Latin text) for attachments, without needing wkhtmltopdf."""
	if isinstance(lines, str):
		lines = [lines]
	text = ["BT", "/F1 18 Tf", "72 760 Td", f"({_pdf_escape(lines[0])}) Tj", "/F1 11 Tf"]
	for line in lines[1:]:
		text += ["0 -22 Td", f"({_pdf_escape(line)}) Tj"]
	text.append("ET")
	stream = "\n".join(text).encode("latin-1", "replace")
	objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
		b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
	out = b"%PDF-1.4\n"
	offsets = []
	for i, body in enumerate(objs, 1):
		offsets.append(len(out))
		out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
	xref = len(out)
	out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
	out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
	return out


def _pdf_escape(s):
	s = "".join(ch if ord(ch) < 128 else "?" for ch in str(s))
	return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")