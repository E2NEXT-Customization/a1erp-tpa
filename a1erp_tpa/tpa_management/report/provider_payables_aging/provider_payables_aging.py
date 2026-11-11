# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import date_diff, flt, getdate, nowdate

from a1erp_tpa.tpa_management.report_utils import col

BUCKETS = [("d30", "1-30 Days", 30), ("d60", "31-60 Days", 60), ("d90", "61-90 Days", 90), ("d181", "Over 90 Days", None)]


def execute(filters=None):
	f = frappe._dict(filters or {})
	as_on = getdate(f.as_on_date or nowdate())
	columns = [col("Provider", "provider", "Link", "Medical Provider", 200)] + [col(label, key, "Currency", None, 120) for key, label, _l in BUCKETS] + [
		col("Total Outstanding", "total", "Currency", None, 140)]
	cond = "c.docstatus = 1 and c.status in ('Approved','Partially Approved','Ready for Payment')"
	args = {}
	if f.provider:
		cond += " and c.provider = %(provider)s"
		args["provider"] = f.provider
	rows = frappe.db.sql(f"select c.provider, c.payer_amount, date(coalesce(c.decided_on, c.service_date)) as since from `tabMedical Claim` c where {cond}", args, as_dict=True)
	out = {}
	for r in rows:
		d = out.setdefault(r.provider, frappe._dict(provider=r.provider, d30=0, d60=0, d90=0, d181=0, total=0))
		age = date_diff(as_on, r.since)
		key = next((k for k, _lbl, lim in BUCKETS if lim is None or age <= lim), "d181")
		d[key] += flt(r.payer_amount)
		d.total += flt(r.payer_amount)
	return columns, sorted(out.values(), key=lambda x: -x.total)