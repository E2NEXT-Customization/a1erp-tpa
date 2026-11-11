# Copyright (c) 2026, A1ERP and contributors
# For license information, please see license.txt

import frappe

from a1erp_tpa.tpa_management.report_utils import chart, claim_where, col, pct

# dimension -> (select expression, joins, label of the first column)
DIMENSIONS = {
	"Diagnosis": ("coalesce(c.diagnosis, '-')", "", "Diagnosis"),
	"Speciality": ("coalesce(mc.specialty, '-')", "left join `tabMedical Code` mc on mc.name = c.diagnosis", "Speciality"),
	"Benefit": ("coalesce(i.benefit_category, '-')", "join `tabClaim Item` i on i.parent = c.name", "Benefit"),
	"Service": ("coalesce(i.service, i.drug, '-')", "join `tabClaim Item` i on i.parent = c.name", "Service"),
	"Provider Type": ("p.provider_type", "", "Provider Type"),
	"Claim Type": ("c.claim_type", "", "Claim Type"),
	"Governorate": ("coalesce(p.governorate, '-')", "", "Governorate"),
}


def execute(filters=None):
	f = frappe._dict(filters or {})
	where, args = claim_where(f)
	dim = f.group_by if f.group_by in DIMENSIONS else "Diagnosis"
	expr, join, label = DIMENSIONS[dim]
	if f.governorate:
		where += " and p.governorate = %(governorate)s"
		args["governorate"] = f.governorate
	item_level = "i." in expr
	amount = "i.payer_amount" if item_level else "c.payer_amount"
	claimed = "i.line_total" if item_level else "c.claimed_amount"
	good = "c.status in ('Approved','Partially Approved','Ready for Payment','Paid','Closed')"
	columns = [col(label, "key", "Data", None, 240), col("Claims", "claims", "Int", None, 90), col("Members", "members", "Int", None, 90),
		col("Admissions", "admissions", "Int", None, 100), col("Claimed Amount", "claimed", "Currency", None, 140), col("Payable to the Provider", "payable", "Currency", None, 140),
		col("Average Claim", "average", "Currency", None, 120), col("Share of Cost (%)", "share", "Percent", None, 110)]
	data = frappe.db.sql(f"""select {expr} as `key`, count(distinct c.name) as claims, count(distinct c.member) as members,
		count(distinct case when c.claim_type = 'Inpatient' then c.name end) as admissions, coalesce(sum({claimed}), 0) as claimed,
		coalesce(sum(case when {good} then {amount} else 0 end), 0) as payable
		from `tabMedical Claim` c join `tabMedical Provider` p on p.name = c.provider {join} where {where} group by {expr} order by payable desc limit 200""", args, as_dict=True)
	total = sum(d.payable for d in data)
	for d in data:
		d.average = d.payable / d.claims if d.claims else 0
		d.share = pct(d.payable, total)
	top = data[:10]
	return columns, data, None, chart([d.key for d in top], [d.payable for d in top], "Payable") if data else None