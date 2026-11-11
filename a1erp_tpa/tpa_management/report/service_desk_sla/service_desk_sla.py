# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime

from a1erp_tpa.tpa_management.report_utils import col, pct


def execute(filters=None):
	f = frappe._dict(filters or {})
	columns = [col("Type", "ticket_type", "Data", None, 110), col("Priority", "priority", "Data", None, 100), col("Tickets", "total", "Int", None, 80),
		col("Open", "open", "Int", None, 80), col("Resolved", "resolved", "Int", None, 90), col("Overdue", "overdue", "Int", None, 80),
		col("Within Service Level (%)", "within", "Percent", None, 140), col("Average Resolution Hours", "hours", "Float", None, 150),
		col("Satisfaction (1-5)", "satisfaction", "Float", None, 120)]
	data = frappe.db.sql("""select ticket_type, priority, count(*) as total,
		coalesce(sum(status in ('Open','In Progress','Escalated')), 0) as open, coalesce(sum(status in ('Resolved','Closed')), 0) as resolved,
		coalesce(sum(status in ('Open','In Progress','Escalated') and resolution_due < %(now)s), 0) as overdue,
		coalesce(sum(status in ('Resolved','Closed') and resolved_on <= resolution_due), 0) as in_time,
		coalesce(avg(case when resolved_on is not null then timestampdiff(minute, creation, resolved_on) / 60 end), 0) as hours,
		coalesce(avg(nullif(cast(satisfaction as unsigned), 0)), 0) as satisfaction
		from `tabService Ticket` where date(creation) between %(a)s and %(b)s group by ticket_type, priority order by ticket_type, priority""",
		{"now": now_datetime(), "a": f.from_date or "2000-01-01", "b": f.to_date or "2999-12-31"}, as_dict=True)
	for d in data:
		d.within = pct(d.in_time, d.resolved)
		d.hours, d.satisfaction = round(d.hours, 1), round(d.satisfaction, 1)
	return columns, data