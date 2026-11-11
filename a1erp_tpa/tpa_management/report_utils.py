"""Shared helpers of the TPA script reports."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

COUNTED = ("Approved", "Partially Approved", "Ready for Payment", "Paid", "Closed")


def col(label, fieldname, fieldtype="Data", options=None, width=120):
	c = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
	if options:
		c["options"] = options
	return c


def claim_where(f, alias="c"):
	"""WHERE clause and arguments for the common claim filters (dates on the date of service)."""
	f = frappe._dict(f or {})
	args = {"from_date": f.from_date or "2000-01-01", "to_date": f.to_date or nowdate()}
	cond = [f"{alias}.docstatus = 1", f"{alias}.service_date between %(from_date)s and %(to_date)s"]
	for k in ("tpa_client", "provider", "plan", "status"):
		if f.get(k):
			cond.append(f"{alias}.{k} = %({k})s")
			args[k] = f.get(k)
	return " and ".join(cond), args


def pct(a, b):
	return flt(a) / flt(b) * 100 if flt(b) else 0.0


def chart(labels, values, title, kind="bar"):
	return {"data": {"labels": labels, "datasets": [{"name": title, "values": values}]}, "type": kind}