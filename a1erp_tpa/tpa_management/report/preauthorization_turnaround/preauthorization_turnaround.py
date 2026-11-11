# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe

from a1erp_tpa.tpa_management.report_utils import col, pct


def execute(filters=None):
	f = frappe._dict(filters or {})
	columns = [col("Medical Reviewer", "reviewer", "Link", "User", 200), col("Requests", "requests", "Int", None, 90), col("Approved", "approved", "Int", None, 90),
		col("Rejected", "rejected", "Int", None, 90), col("Pending", "pending", "Int", None, 90), col("Approval Rate (%)", "rate", "Percent", None, 120),
		col("Average Hours to Decide", "hours", "Float", None, 130)]
	data = frappe.db.sql("""select coalesce(assigned_reviewer, '') as reviewer, count(*) as requests,
		coalesce(sum(status in ('Approved','Partially Approved','Expired')), 0) as approved, coalesce(sum(status = 'Rejected'), 0) as rejected,
		coalesce(sum(status in ('Submitted','Under Review','Medical Review','Pending Information')), 0) as pending,
		coalesce(avg(case when decision_on is not null then timestampdiff(minute, creation, decision_on) / 60 end), 0) as hours
		from `tabPre-Authorization` where status != 'Draft' and request_date between %(a)s and %(b)s group by assigned_reviewer order by requests desc""",
		{"a": f.from_date or "2000-01-01", "b": f.to_date or "2999-12-31"}, as_dict=True)
	for d in data:
		d.rate = pct(d.approved, d.approved + d.rejected)
		d.hours = round(d.hours, 1)
	return columns, data