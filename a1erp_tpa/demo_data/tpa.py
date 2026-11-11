"""Demo data for the health TPA: clients, network, providers, codes, plans, members, then the year's medical activity."""

import frappe
from datetime import timedelta

from frappe.utils import add_days, add_months, cint, flt, getdate

from a1erp_tpa.demo_data import catalog as C
from a1erp_tpa.demo_data.builder import as_of

PASSWORD = "Demo@2026"
NETWORKS = [("الشبكة الذهبية", "Gold"), ("الشبكة الفضية", "Silver"), ("الشبكة الاقتصادية", "Economy")]
TPA_STAFF = [("tpa_mgr", ["TPA Manager"], "Male"), ("tpa_co1", ["TPA Claims Officer"], "Female"), ("tpa_co2", ["TPA Claims Officer"], "Male"),
	("tpa_fin", ["TPA Finance"], "Male"), ("tpa_cs1", ["TPA Customer Service"], "Female"), ("tpa_cs2", ["TPA Customer Service"], "Female")]
REVIEWERS = [("Internal Medicine", "Male"), ("General Surgery", "Male"), ("Obstetrics & Gynecology", "Female"), ("Orthopedics", "Male"),
	("Cardiology", "Male"), ("Pediatrics", "Female")]
# benefit rows: category, annual limit (class A base), co-payment %, waiting days, requires pre-authorization, sessions
BENEFITS = [("Inpatient", 10_000_000, 10, 0, 1, 0), ("Outpatient", 2_000_000, 10, 0, 0, 0), ("Pharmacy", 1_000_000, 15, 0, 0, 0),
	("Laboratory and Radiology", 1_500_000, 10, 0, 0, 0), ("Dental", 500_000, 20, 90, 0, 0), ("Maternity", 3_000_000, 10, 270, 1, 0),
	("Emergency", 0, 0, 0, 0, 0), ("Optical", 300_000, 20, 0, 0, 0), ("Physiotherapy", 600_000, 20, 0, 0, 12), ("Chronic", 3_000_000, 10, 0, 0, 0)]


# ------------------------------------------------------------------- helpers
def make_user(ctx, roles, gender, key, user_type="System User"):
	ar, en, g, first = ctx.person(gender)
	email = f"{en.split()[0].lower()}.{en.split()[-1].lower().replace('al-', '')}.{key}@{'example.com'}"
	if frappe.db.exists("User", email):
		return email
	parts = ar.split()
	u = frappe.get_doc({"doctype": "User", "email": email, "first_name": parts[0], "last_name": " ".join(parts[1:]), "send_welcome_email": 0,
		"user_type": user_type, "language": "ar", "mobile_no": ctx.mobile(), "gender": g, "new_password": PASSWORD})
	u.flags.ignore_permissions = True
	u.flags.no_welcome_mail = True
	u.insert()
	ctx.track("User", u.name)
	if roles:
		u.add_roles(*roles)
	return u.name


def supplier(ctx, name, group):
	if frappe.db.exists("Supplier", name):
		return name
	doc = ctx.insert({"doctype": "Supplier", "supplier_name": name, "supplier_group": group if frappe.db.exists("Supplier Group", group) else
		frappe.db.get_value("Supplier Group", {"is_group": 0}), "country": "Iraq"})
	return doc.name


# ------------------------------------------------------------------- masters
def masters(ctx):
	st = ctx.store
	year = ctx.today.year
	ctx.log("Health: staff, clients, network and providers")
	st.tpa_users = {}
	for key, roles, gender in TPA_STAFF:
		st.tpa_users[key] = ctx.attempt("tpa user", lambda key=key, roles=roles, gender=gender: make_user(ctx, roles, gender, key))
	st.reviewers = []
	for spec, gender in REVIEWERS:
		def rev(spec=spec, gender=gender):
			u = make_user(ctx, ["TPA Medical Reviewer"], gender, "dr" + str(len(st.reviewers) + 1))
			if not frappe.db.exists("Medical Reviewer", u):
				ctx.insert({"doctype": "Medical Reviewer", "user": u, "active": 1, "max_open_items": 40, "specialities": [{"speciality": spec}]})
			st.reviewers.append(u)
		ctx.attempt("reviewer", rev)

	# clients
	st.clients = []
	for ar, en, kind, basis, rate, gov in C.TPA_CLIENTS:
		def cl(ar=ar, en=en, kind=kind, basis=basis, rate=rate, gov=gov):
			if frappe.db.exists("TPA Client", ar):
				st.clients.append(frappe._dict(name=ar, en=en, kind=kind))
				return
			cust = ar if frappe.db.exists("Customer", ar) else ctx.insert({"doctype": "Customer", "customer_name": ar, "customer_type": "Company",
				"customer_group": "Commercial", "territory": "Iraq" if frappe.db.exists("Territory", "Iraq") else None, "customer_details": en}).name
			ctx.insert({"doctype": "TPA Client", "client_name": ar, "client_name_ar": ar, "client_type": kind, "customer": cust, "status": "Active",
				"contract_from": f"{year}-01-01", "contract_to": f"{year}-12-31", "currency": "IQD", "fee_basis": basis, "fee_rate": rate,
				"fee_minimum": 5_000_000 if basis == "Percent of Claims" else 0, "billing_frequency": "Monthly", "contact_person": ctx.person()[0],
				"mobile_no": ctx.mobile(), "email_id": f"hr@{en.split()[0].lower().replace('-', '')}.example.com", "governorate": gov, "address": ctx.address(gov)[1]})
			st.clients.append(frappe._dict(name=ar, en=en, kind=kind))
		ctx.attempt("client " + en, cl)
	if st.clients:
		ctx.attempt("client portal", lambda: client_portal(ctx, st.clients[0].name))

	# networks
	st.networks = {}
	for ar, key in NETWORKS:
		if not frappe.db.exists("Provider Network", ar):
			ctx.attempt("network", lambda ar=ar, key=key: ctx.insert({"doctype": "Provider Network", "network_name": ar,
				"description": {"Gold": "أفضل المستشفيات والمراكز من الدرجة A", "Silver": "مستشفيات ومراكز الدرجتين A و B", "Economy": "مراكز أساسية وصيدليات"}[key]}))
		st.networks[key] = ar
	ctx.progress("Health: clients and networks", 0.06)

	# medical codes, services and drugs
	for code, en, ar, spec, chronic in C.ICD10:
		if not frappe.db.exists("Medical Code", f"ICD-10-{code}"):
			ctx.attempt("icd", lambda code=code, en=en, ar=ar, spec=spec, chronic=chronic: ctx.insert({"doctype": "Medical Code", "code_type": "ICD-10", "code": code,
				"description_en": en, "description_ar": ar, "specialty": spec, "is_chronic": chronic, "chapter": code[0]}))
	for code, en, ar, cat, ben, price, pre, spec in C.SERVICES:
		if not frappe.db.exists("Medical Service", code):
			ctx.attempt("service", lambda code=code, en=en, ar=ar, cat=cat, ben=ben, price=price, pre=pre, spec=spec: ctx.insert({"doctype": "Medical Service",
				"service_code": code, "service_name": en, "service_name_ar": ar, "category": cat, "benefit_category": ben, "default_price": price,
				"requires_preauth": pre, "specialty": spec, "is_surgical": 1 if cat == "Surgery" else 0, "is_admission": 1 if cat == "Inpatient Stay" else 0}))
	for code, trade, generic, form, price, chronic, pre, covered, qty in C.DRUGS:
		if not frappe.db.exists("Drug", code):
			ctx.attempt("drug", lambda code=code, trade=trade, generic=generic, form=form, price=price, chronic=chronic, pre=pre, covered=covered, qty=qty: ctx.insert({
				"doctype": "Drug", "drug_code": code, "trade_name": trade, "generic_name": generic, "dosage_form": form.split(" ")[0],
				"strength": " ".join(form.split(" ")[1:]), "price": price, "chronic_drug": chronic, "requires_preauth": pre, "covered": covered,
				"max_quantity": qty, "max_days_supply": 30 if chronic else 10, "min_days_between_fills": 25 if chronic else 0}))
	ctx.progress("Health: codes, services, drugs", 0.12)

	# providers
	st.providers = []
	for ar, en, kind, specs, gov, grade in C.PROVIDERS[: ctx.p.providers]:
		ctx.attempt("provider " + en, lambda ar=ar, en=en, kind=kind, specs=specs, gov=gov, grade=grade: st.providers.append(make_provider(ctx, ar, en, kind, specs, gov, grade)))
	ctx.attempt("provider portal", lambda: provider_portal(ctx))
	ctx.attempt("tariffs", lambda: tariffs(ctx))
	ctx.progress("Health: providers and tariffs", 0.2)

	# fund and plans
	ctx.attempt("plans", lambda: plans(ctx))
	ctx.progress("Health: plans", 0.24)


def client_portal(ctx, client):
	email = "client.portal@example.com"
	if not frappe.db.exists("User", email):
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "بوابة", "last_name": "شركة التأمين", "user_type": "Website User",
			"send_welcome_email": 0, "new_password": PASSWORD, "language": "ar"})
		u.flags.ignore_permissions = True
		u.insert()
		ctx.track("User", u.name)
	doc = frappe.get_doc("TPA Client", client)
	if not any(r.user == email for r in doc.portal_users):
		doc.append("portal_users", {"user": email, "active": 1, "note": "قسم الموارد البشرية"})
		doc.save(ignore_permissions=True)
	ctx.highlight("بوابة شركة التأمين: client.portal@example.com / Demo@2026", "TPA Client", client, "/tpa")


def make_provider(ctx, ar, en, kind, specs, gov, grade):
	if frappe.db.exists("Medical Provider", ar):
		return frappe._dict(name=ar, kind=kind, gov=gov, grade=grade, specs=specs,
			nets={r.network for r in frappe.get_all("Provider Network Row", filters={"parent": ar}, fields=["network"])})
	ancillary = kind in ("Pharmacy", "Laboratory", "Radiology Center", "Dental Center", "Physiotherapy Center", "Other Specialty")
	nets = [ctx.store.networks["Gold"]] if grade == "A" or ancillary else []
	if grade in ("A", "B") or ancillary:
		nets.append(ctx.store.networks["Silver"])
	nets.append(ctx.store.networks["Economy"])
	_g, address = ctx.address(gov)
	expired = ctx.chance(0.05)
	doc = ctx.insert({"doctype": "Medical Provider", "provider_name": ar, "provider_name_ar": ar, "provider_type": kind, "status": "Active",
		"accreditation_level": grade, "license_no": f"MOH/{gov[:3].upper()}/{ctx.rng.randint(2010, 2024)}/{ctx.rng.randint(100, 9999)}",
		"license_expiry": add_days(ctx.today, -ctx.rng.randint(5, 40)) if expired else add_days(ctx.today, ctx.rng.randint(90, 900)),
		"contract_from": f"{ctx.today.year}-01-01", "contract_to": f"{ctx.today.year}-12-31", "default_discount_percent": ctx.pick([5, 7.5, 10, 12]),
		"governorate": gov, "city": address.split("، ")[1], "address": address, "phone": ctx.mobile(), "email_id": f"accounts@{en.split()[0].lower().replace('-', '').replace('.', '')}{ctx.rng.randint(1, 99)}.example.com",
		"latitude": round(_coords(gov)[0] + ctx.rng.uniform(-0.05, 0.05), 6), "longitude": round(_coords(gov)[1] + ctx.rng.uniform(-0.05, 0.05), 6),
		"bank_name": ctx.pick(["مصرف الرشيد", "مصرف الرافدين", "المصرف التجاري العراقي", "مصرف بغداد"]), "iban": ctx.iban(),
		"networks": [{"network": n} for n in nets if n], "specialities": [{"speciality": s} for s in specs],
		"contacts": [{"contact_name": ctx.person()[0], "mobile_no": ctx.mobile(), "portal_role": "Admin"}]})
	doc.create_supplier()
	sup = frappe.db.get_value("Medical Provider", doc.name, "supplier")
	ctx.track("Supplier", sup)
	return frappe._dict(name=doc.name, kind=kind, gov=gov, grade=grade, specs=specs, expired=expired, nets=set(n for n in nets if n))


def provider_portal(ctx):
	targets = [p for p in ctx.store.providers if p.kind in ("Hospital", "Pharmacy") and not p.get("expired")][:2]
	for p in targets:
		email = "hospital.portal@example.com" if p.kind == "Hospital" else "pharmacy.portal@example.com"
		if frappe.db.exists("User", email):
			continue
		u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "بوابة", "last_name": p.name, "user_type": "Website User",
			"send_welcome_email": 0, "new_password": PASSWORD, "language": "ar"})
		u.flags.ignore_permissions = True
		u.insert()
		ctx.track("User", u.name)
		doc = frappe.get_doc("Medical Provider", p.name)
		doc.append("contacts", {"contact_name": "مكتب التأمين", "user": email, "portal_role": "Staff", "mobile_no": ctx.mobile()})
		doc.save(ignore_permissions=True)
		ctx.highlight(f"بوابة مقدم الخدمة ({p.name}): {email} / Demo@2026", "Medical Provider", p.name, "/tpa", limit=2)


def _coords(gov):
	return {"Baghdad": (33.3152, 44.3661), "Basra": (30.5085, 47.7804), "Erbil": (36.1911, 44.0092), "Nineveh": (36.3400, 43.1300),
		"Najaf": (32.0259, 44.3462), "Karbala": (32.6160, 44.0249), "Sulaymaniyah": (35.5613, 45.4300), "Kirkuk": (35.4681, 44.3922),
		"Babil": (32.4637, 44.4196), "Dhi Qar": (31.0580, 46.2573), "Duhok": (36.8670, 42.9500)}.get(gov, (33.3, 44.4))


def tariffs(ctx):
	year = ctx.today.year
	items_all = [("Service", s[0], s[5]) for s in C.SERVICES] + [("Drug", d[0], d[4]) for d in C.DRUGS]
	for key in ("Gold", "Silver", "Economy"):
		net = ctx.store.networks[key]
		factor = {"Gold": 1.0, "Silver": 0.92, "Economy": 0.85}[key]
		for y in (year - 1, year):
			name = f"تعرفة {net} {y}"
			if frappe.db.exists("Provider Tariff", {"tariff_name": name}):
				continue
			t = ctx.insert({"doctype": "Provider Tariff", "tariff_name": name, "network": net, "valid_from": f"{y}-01-01", "currency": "IQD",
				"discount_percent": {"Gold": 5, "Silver": 8, "Economy": 12}[key],
				"items": [{"item_type": kind, "service" if kind == "Service" else "drug": code, "price": int(price * factor * (0.94 if y < year else 1) // 500 * 500)}
					for kind, code, price in items_all if frappe.db.exists("Medical Service" if kind == "Service" else "Drug", code)]})
			t.activate()
	for p in [p for p in ctx.store.providers if p.kind == "Hospital"][:4]:
		name = f"تعرفة خاصة - {p.name} {year}"
		if frappe.db.exists("Provider Tariff", {"tariff_name": name}):
			continue
		svc = [s for s in C.SERVICES if s[3] in ("Surgery", "Inpatient Stay", "Maternity")]
		t = ctx.insert({"doctype": "Provider Tariff", "tariff_name": name, "provider": p.name, "valid_from": f"{year}-01-01", "currency": "IQD",
			"discount_percent": 10, "items": [{"item_type": "Service", "service": s[0], "price": int(s[5] * ctx.rng.uniform(0.88, 1.05) // 5000 * 5000)} for s in svc],
			"rebates": [{"from_amount": 0, "to_amount": 50_000_000, "rebate_percent": 0}, {"from_amount": 50_000_000, "to_amount": 0, "rebate_percent": 2}]})
		t.activate()


def plans(ctx):
	st = ctx.store
	year = ctx.today.year
	st.plans = []
	settings = frappe.get_cached_doc("TPA Settings")
	clients = {c.en: c.name for c in st.clients}
	oil = clients.get("Al-Ufuq Petroleum Services")
	fund = None
	if oil:
		fund = "صندوق الأفق الصحي" if frappe.db.exists("Health Fund", "صندوق الأفق الصحي") else ctx.insert({"doctype": "Health Fund",
			"fund_name": "صندوق الأفق الصحي", "tpa_client": oil, "status": "Active", "currency": "IQD", "liability_account": settings.fund_liability_account,
			"low_balance_percent": 15}).name
		st.fund = fund

	designs = [  # client, plan name, network, scale, model, classes
		("Sanabel Al-Khair Insurance Co.", "برنامج سنابل الذهبي للشركات", "Gold", 1.5, "Insurance Company Funded", ["A", "B", "C"]),
		("Rafidain Bridge Insurance Co.", "برنامج جسر الرافدين القياسي", "Silver", 1.0, "Insurance Company Funded", ["A", "B"]),
		("Al-Waha Commercial Bank", "التأمين الصحي لموظفي مصرف الواحة", "Gold", 1.3, "Insurance Company Funded", ["A", "B", "C"]),
		("Ur Mobile Telecom Co.", "برنامج أور للرعاية الصحية", "Silver", 1.1, "Insurance Company Funded", ["A", "B"]),
		("Sumer Private University College", "برنامج كلية سومر للهيئة التدريسية", "Silver", 0.9, "Multiple Funding Sources", ["A", "B"]),
		("Al-Ufuq Petroleum Services", "البرنامج الذاتي لشركة نفط الأفق", "Gold", 1.4, "Self-Funded", ["A", "B", "C"]),
	]
	for client_en, plan_name, net, scale, model, classes in designs:
		client = clients.get(client_en)
		if not client:
			continue
		def one(client=client, plan_name=plan_name, net=net, scale=scale, model=model, classes=classes, client_en=client_en):
			existing = frappe.db.get_value("Health Plan", {"plan_name": plan_name})
			if existing:
				st.plans.append(frappe._dict(name=existing, client=client, classes=classes, en=client_en, network=st.networks[net]))
				return
			cls = [{"class_name": c, "annual_limit": int(25_000_000 * scale * (1 - 0.25 * i)), "family_limit": int(60_000_000 * scale * (1 - 0.25 * i)),
				"description": {"A": "الإدارة العليا", "B": "الموظفون", "C": "العمال والفنيون"}[c]} for i, c in enumerate(classes)]
			benefits = []
			for cat, limit, copay, wait, pre, sessions in BENEFITS:
				benefits.append({"benefit_category": cat, "covered": 1, "annual_limit": int(limit * scale) if limit else 0, "copay_percent": copay,
					"waiting_days": wait, "requires_preauth": pre, "preauth_threshold": 500_000 if cat == "Inpatient" else 0, "sessions_limit": sessions,
					"oon_covered": 1 if cat == "Emergency" else 0, "oon_copay_percent": 30 if cat == "Emergency" else 0,
					"gender": "Female" if cat == "Maternity" else "", "min_age": 18 if cat == "Maternity" else 0})
			if "C" in classes:
				benefits.append({"class_name": "C", "benefit_category": "Dental", "covered": 0})
				benefits.append({"class_name": "C", "benefit_category": "Optical", "covered": 0})
			data = {"doctype": "Health Plan", "plan_name": plan_name, "plan_name_ar": plan_name, "tpa_client": client, "status": "Active",
				"funding_model": model, "from_date": f"{year}-01-01", "to_date": f"{year}-12-31", "currency": "IQD", "network": st.networks[net],
				"outside_network_covered": 0, "annual_limit": int(20_000_000 * scale), "family_limit": int(60_000_000 * scale), "limit_mode": "Individual",
				"member_copay_percent": 10, "deductible": 0, "chronic_covered": 1, "maternity_covered": 1, "emergency_covered": 1, "pharmacy_covered": 1,
				"pre_existing_covered": 1 if scale > 1.2 else 0, "classes": cls, "benefits": benefits,
				"exclusions": [{"exclusion_type": "Service", "service": "COS-BTX", "note": "الإجراءات التجميلية"},
					{"exclusion_type": "Keyword", "keyword": "Cosmetic", "note": "كل ما هو تجميلي"},
					{"exclusion_type": "Drug", "drug": "DR-0042", "note": "أدوية حب الشباب التجميلية"}],
				"terms": "<p>تسري شروط العقد الموقع بين الطرفين. التغطية داخل جمهورية العراق، والطوارئ خارج الشبكة بنسبة تحمل 30%.</p>"}
			if model == "Self-Funded":
				data["fund"] = fund
			if model == "Multiple Funding Sources":
				insurer = clients.get("Sanabel Al-Khair Insurance Co.")
				data["funding_sources"] = [{"source": client, "share_percent": 40}, {"source": insurer, "share_percent": 60}]
				data["insurer"] = insurer
			doc = ctx.insert(data)
			st.plans.append(frappe._dict(name=doc.name, client=client, classes=classes, en=client_en, network=st.networks[net]))
		ctx.attempt("plan " + plan_name, one)
	for tname, net in (("قالب البرنامج الذهبي", "Gold"), ("قالب البرنامج الاقتصادي", "Economy")):
		if not frappe.db.exists("Health Plan", {"plan_name": tname}):
			ctx.attempt("template", lambda tname=tname, net=net: ctx.insert({"doctype": "Health Plan", "plan_name": tname, "is_template": 1, "status": "Draft",
				"funding_model": "Insurance Company Funded", "network": st.networks[net], "annual_limit": 20_000_000 if net == "Gold" else 8_000_000,
				"member_copay_percent": 10 if net == "Gold" else 20, "classes": [{"class_name": "A", "annual_limit": 20_000_000}],
				"benefits": [{"benefit_category": cat, "covered": 1, "annual_limit": limit, "copay_percent": copay, "waiting_days": wait, "requires_preauth": pre}
					for cat, limit, copay, wait, pre, _s in BENEFITS]}))


# ------------------------------------------------------------------- members
def members(ctx):
	st = ctx.store
	year = ctx.today.year
	st.members = []
	if not st.plans:
		return
	weights = {"Sanabel Al-Khair Insurance Co.": 30, "Rafidain Bridge Insurance Co.": 18, "Al-Waha Commercial Bank": 15, "Ur Mobile Telecom Co.": 17,
		"Sumer Private University College": 8, "Al-Ufuq Petroleum Services": 12}
	plan_pick = [(p, weights.get(p.en, 10)) for p in st.plans]
	target = ctx.p.members
	made = 0
	fam_no = 0
	ctx.log(f"Health: enrolling about {target} members in families")
	while made < target:
		plan = ctx.weighted(plan_pick)
		fam_no += 1
		def family(plan=plan):
			created = []
			kurdish = ctx.chance(0.1)
			family_name = ctx.pick(C.KURDISH_FAMILIES if kurdish else C.FAMILIES)
			gender = "Male" if ctx.chance(0.72) else "Female"
			ar, en, g, _f = ctx.person(gender, kurdish, family_name)
			age = ctx.rng.randint(24, 59)
			joined = f"{year}-01-01" if ctx.chance(0.88) else str(add_days(f"{year}-01-01", ctx.rng.randint(30, max(31, (ctx.today - getdate(f'{year}-01-01')).days - 20))))
			cls = ctx.weighted([(c, w) for c, w in zip(plan.classes, [15, 55, 30][: len(plan.classes)])])
			gov = ctx.governorate()
			principal = ctx.insert({"doctype": "Plan Member", "member_name": en, "member_name_ar": ar, "plan": plan.name, "class_name": cls,
				"relationship": "Principal", "national_id": ctx.national_id(), "gender": g, "date_of_birth": birth(ctx, age), "mobile_no": ctx.mobile(),
				"email_id": ctx.email(en), "language": "ar" if not kurdish else "en", "employer": C.EMPLOYERS.get(plan.en, plan.client),
				"employee_no": f"EMP-{ctx.rng.randint(1000, 99999)}", "start_date": joined})
			created.append(principal)
			if g == "Male" and age > 26 and ctx.chance(0.75):
				sar, sen, _sg, _sf = ctx.person("Female", kurdish, ctx.pick(C.FAMILIES))
				created.append(ctx.insert({"doctype": "Plan Member", "member_name": sen, "member_name_ar": sar, "plan": plan.name, "class_name": cls,
					"relationship": "Spouse", "principal": principal.name, "national_id": ctx.national_id(), "gender": "Female",
					"date_of_birth": birth(ctx, max(20, age - ctx.rng.randint(2, 9))), "mobile_no": ctx.mobile(), "start_date": joined}))
				father_first = en.split()[0]
				father_ar = ar.split()[0]
				for k in range(ctx.weighted([(0, 15), (1, 25), (2, 30), (3, 20), (4, 10)])):
					cg = ctx.pick(["Male", "Female"])
					first = ctx.pick(C.MALE if cg == "Male" else C.FEMALE)
					child_age = ctx.rng.randint(0, min(22, age - 22))
					created.append(ctx.insert({"doctype": "Plan Member", "member_name": f"{first[1]} {father_first} {family_name[1]}",
						"member_name_ar": f"{first[0]} {father_ar} {family_name[0]}", "plan": plan.name, "class_name": cls,
						"relationship": "Son" if cg == "Male" else "Daughter", "principal": principal.name, "national_id": ctx.national_id(), "gender": cg,
						"date_of_birth": birth(ctx, child_age), "start_date": joined}))
			for m in created:
				m.gov = gov
			return created
		fam = ctx.attempt("family", family)
		if not fam:
			if fam_no > target * 2:
				break
			continue
		made += len(fam)
		pending = ctx.chance(0.04)
		for m in fam:
			if pending:
				continue
			def act(m=m):
				with as_of(ctx.stamp(m.start_date)):
					m.reload()
					m.activate()
				card = frappe.db.get_value("Medical Card", {"member": m.name, "status": "Active"})
				ctx.track("Medical Card", card)
			ctx.attempt("activate", act)
		st.members.extend(frappe._dict(name=m.name, plan=m.plan, gender=m.gender, dob=getdate(m.date_of_birth), start=getdate(m.start_date),
			principal=m.principal or m.name, rel=m.relationship, pending=pending, ar=m.member_name_ar, gov=getattr(m, "gov", "Baghdad")) for m in fam)
		if fam_no % 15 == 0:
			ctx.progress(f"Health: members {made}/{target}", 0.24 + 0.16 * made / target)
	# a few status changes and lost cards
	active = [m for m in st.members if not m.pending]
	for m in ctx.rng.sample(active, min(len(active) // 60 + 1, len(active))):
		ctx.attempt("suspend", lambda m=m: frappe.get_doc("Plan Member", m.name).suspend("إيقاف مؤقت بطلب جهة العمل لحين تسوية الوضع الوظيفي"))
		m.pending = True
	for m in ctx.rng.sample([x for x in active if not x.pending], min(15, len(active))):
		def lost(m=m):
			card = frappe.db.get_value("Medical Card", {"member": m.name, "status": "Active"})
			if card:
				new = frappe.get_doc("Medical Card", card).replace("فقدان البطاقة وتقديم إقرار بذلك", lost=1)
				ctx.track("Medical Card", new)
		ctx.attempt("lost card", lost)
	# portal members
	for k, m in enumerate([m for m in active if m.rel == "Principal"][:2]):
		def portal(m=m, k=k):
			email = f"member{k + 1}.portal@example.com"
			if not frappe.db.exists("User", email):
				u = frappe.get_doc({"doctype": "User", "email": email, "first_name": m.ar.split()[0], "last_name": " ".join(m.ar.split()[1:]),
					"user_type": "Website User", "send_welcome_email": 0, "new_password": PASSWORD, "language": "ar"})
				u.flags.ignore_permissions = True
				u.insert()
				ctx.track("User", u.name)
			frappe.db.set_value("Plan Member", m.name, "user", email)
			ctx.highlight(f"بوابة العضو ({m.ar}): {email} / Demo@2026", "Plan Member", m.name, "/tpa", limit=2)
		ctx.attempt("member portal", portal)
	ctx.attempt("fund contributions", lambda: contributions(ctx))
	ctx.log(f"members: {len(st.members)}")
	ctx.progress("Health: members", 0.4)


def contributions(ctx):
	"""Monthly funding of the self-funded scheme: about 11,000 IQD per member per month (a little above the expected cost), three months in advance at the start."""
	st = ctx.store
	fund = st.get("fund")
	plan = next((p for p in st.plans if p.en == "Al-Ufuq Petroleum Services"), None)
	if not fund or not plan:
		return
	size = len([m for m in st.members if m.plan == plan.name]) or 20
	monthly = int(size * 11_000 // 10_000 * 10_000) or 250_000
	bank = frappe.get_cached_value("Company", ctx.company, "default_bank_account") or frappe.db.get_value("Account", {"account_type": "Bank", "is_group": 0})
	year = ctx.today.year
	for m in range(1, ctx.today.month + 1):
		d = f"{year}-{m:02d}-05"
		if getdate(d) > ctx.today:
			break
		ctx.attempt("contribution", lambda d=d, m=m: ctx.insert({"doctype": "Fund Contribution", "fund": fund, "posting_date": d,
			"amount": monthly * (3 if m == 1 else 1), "bank_account": bank, "reference": f"تحويل مصرفي رقم {ctx.rng.randint(100000, 999999)}"}, submit=True))
	ctx.highlight("الصندوق الصحي ذاتي التمويل", "Health Fund", fund, "المساهمات الشهرية والمطالبات المحملة والرصيد المتاح")


def birth(ctx, age):
	return add_days(ctx.today, -(age * 365 + ctx.rng.randint(0, 364)))


# ------------------------------------------------------------------- activity
SERVICE_BY_CODE = {s[0]: s for s in C.SERVICES}
DIAG_BY_SPEC = {}
for _c in C.ICD10:
	DIAG_BY_SPEC.setdefault(_c[3], []).append(f"ICD-10-{_c[0]}")


def diag(ctx, spec=None, chronic=None):
	pool = [f"ICD-10-{c[0]}" for c in C.ICD10 if (not spec or c[3] == spec) and (chronic is None or c[4] == chronic)]
	return ctx.pick(pool or [f"ICD-10-{C.ICD10[0][0]}"])


def age_of(m, on):
	return (getdate(on) - m.dob).days // 365


def activity(ctx):
	st = ctx.store
	year = ctx.today.year
	active = [m for m in st.members if not m.pending]
	if not active or not st.providers:
		return
	ok_providers = [p for p in st.providers if not p.get("expired")]
	by_kind = {}
	for p in ok_providers:
		by_kind.setdefault(p.kind, []).append(p)
	hospitals = by_kind.get("Hospital") or ok_providers
	st.preauths = []
	reasons = {r.category: r.name for r in frappe.get_all("Claim Rejection Reason", fields=["name", "category"])}

	# pre-authorizations
	ctx.log(f"Health: {ctx.p.preauths} pre-authorizations")
	types = [("Standard", 30), ("Surgery", 20), ("Admission", 13), ("Advanced Diagnostics", 12), ("Special Drug", 6), ("Continuous Treatment", 5),
		("Emergency", 6), ("Admission Extension", 4), ("Out-of-Network", 4)]
	for i in range(ctx.p.preauths):
		ctx.attempt("pre-auth", lambda: preauth(ctx, active, hospitals, ctx.weighted(types), reasons))
		if i % 10 == 0:
			ctx.progress(f"Health: pre-authorizations {i + 1}/{ctx.p.preauths}", 0.4 + 0.1 * (i + 1) / ctx.p.preauths)

	# claims
	n = ctx.p.med_claims
	ctx.log(f"Health: {n} medical claims")
	kinds = [("Outpatient", 40), ("Pharmacy", 25), ("Laboratory and Radiology", 15), ("Inpatient", 8), ("Dental", 5), ("Emergency", 4), ("Optical", 2), ("Maternity", 1)]
	start = getdate(f"{year}-01-01")
	span = (ctx.today - start).days
	st.invoice_seq = 1000
	for i in range(n):
		# more claims in winter and in recent months
		day = int(span * (ctx.rng.random() ** 0.8))
		service_day = add_days(start, min(day, span - 1))
		kind = ctx.weighted(kinds)
		ctx.attempt("medical claim", lambda: medical_claim(ctx, active, by_kind, hospitals, kind, service_day, reasons))
		if i % 25 == 0:
			ctx.progress(f"Health: medical claims {i + 1}/{n}", 0.5 + 0.32 * (i + 1) / n)

	ctx.attempt("expire authorizations", lambda: expire_unused(ctx))
	ctx.attempt("settlements", lambda: settlements(ctx))
	ctx.progress("Health: settlements", 0.88)
	ctx.attempt("fee invoices", lambda: fee_invoices(ctx))
	ctx.attempt("fraud follow-up", lambda: fraud(ctx, active))
	ctx.attempt("medical cases", lambda: cases(ctx, active))
	ctx.attempt("service tickets", lambda: tickets(ctx, active))
	ctx.attempt("tpa documents", lambda: tpa_documents(ctx))
	frappe.db.commit()
	ctx.progress("Health: service desk", 0.98)


def network_of(ctx, member):
	plan = next((p for p in ctx.store.plans if p.name == member.plan), None)
	return plan.network if plan else None


def choose(ctx, member, pool):
	"""Members use providers of their own network; now and then they go elsewhere (and the engine refuses)."""
	net = network_of(ctx, member)
	inside = [p for p in pool if net in (p.get("nets") or set())]
	if inside and not ctx.chance(0.03):
		return ctx.pick(inside)
	return ctx.pick(pool)


def eligible_member(ctx, active, on, female_adult=False):
	for _i in range(30):
		m = ctx.pick(active)
		if getdate(m.start) > getdate(on):
			continue
		if female_adult and (m.gender != "Female" or not 18 <= age_of(m, on) <= 45 or (getdate(on) - getdate(m.start)).days < 280):
			continue
		return m
	return None


def preauth(ctx, active, hospitals, kind, reasons):
	st = ctx.store
	when = ctx.days_ago(1, max(2, (ctx.today - getdate(f"{ctx.today.year}-01-01")).days - 5))
	m = eligible_member(ctx, active, when)
	if not m:
		return
	prov = choose(ctx, m, hospitals)
	surg = [s for s in C.SERVICES if s[3] == "Surgery" and s[6]]
	if kind in ("Surgery", "Emergency"):
		s = ctx.pick(surg)
		items = [{"item_type": "Service", "service": s[0], "quantity": 1}, {"item_type": "Service", "service": "IP-WARD", "quantity": ctx.rng.randint(1, 4)}]
		dx = diag(ctx, s[7] or None)
	elif kind in ("Admission", "Admission Extension"):
		items = [{"item_type": "Service", "service": ctx.pick(["IP-WARD", "IP-PRV"]), "quantity": ctx.rng.randint(2, 7)},
			{"item_type": "Service", "service": "LAB-CBC", "quantity": 2}]
		dx = diag(ctx, "Internal Medicine")
	elif kind == "Advanced Diagnostics":
		items = [{"item_type": "Service", "service": ctx.pick(["RAD-CTB", "RAD-CTA", "RAD-MRS", "RAD-MRK"]), "quantity": 1}]
		dx = diag(ctx, ctx.pick(["Neurology", "Orthopedics"]))
	elif kind == "Special Drug":
		items = [{"item_type": "Drug", "drug": ctx.pick(["DR-0039", "DR-0040", "DR-0012", "DR-0051"]), "quantity": 1}]
		dx = diag(ctx, chronic=1)
	elif kind == "Continuous Treatment":
		items = [{"item_type": "Service", "service": ctx.pick(["PHY-SES", "TRT-DIA"]), "quantity": 8}]
		dx = diag(ctx, ctx.pick(["Orthopedics", "Internal Medicine"]))
	else:
		items = [{"item_type": "Service", "service": ctx.pick(["PRC-END", "PRC-COL", "RAD-MRS"]), "quantity": 1}]
		dx = diag(ctx)
	parent = None
	if kind == "Admission Extension":
		cands = [p for p in st.preauths if p.member == m.name]
		if not cands:
			kind = "Admission"
		else:
			parent = cands[0].name
	data = {"doctype": "Pre-Authorization", "member": m.name, "provider": prov.name, "auth_type": kind, "request_date": when, "diagnosis": dx,
		"priority": "Emergency" if kind == "Emergency" else ctx.pick(["Routine", "Routine", "Urgent"]), "items": items,
		"medical_notes": "<p>التقرير الطبي مرفق. الحالة تستدعي الإجراء المطلوب وفق تقييم الطبيب المعالج.</p>",
		"admission_date": when if kind in ("Admission", "Surgery", "Admission Extension") else None, "expected_days": ctx.rng.randint(1, 5) if "Admission" in kind else None,
		"parent_auth": parent, "sessions_authorized": 8 if kind == "Continuous Treatment" else None}
	with as_of(ctx.stamp(when)):
		pa = ctx.insert(data, backdate=ctx.stamp(when))
		pa.submit_request()
	st.preauths.append(frappe._dict(name=pa.name, member=m.name, provider=prov.name, when=getdate(when)))
	age = (ctx.today - getdate(when)).days
	outcome = ctx.weighted([("Approve", 62), ("Reject", 15), ("Info", 8), ("Open", 15)] if age > 7 else [("Approve", 35), ("Open", 50), ("Info", 10), ("Reject", 5)])
	if outcome == "Open":
		return
	decided = min(ctx.stamp(add_days(when, ctx.rng.choice([0, 0, 1, 1, 2, 3]))), ctx.stamp(ctx.today, 7, 9))
	with as_of(decided):
		pa.reload()
		pa.start_review()
		pa.reload()
		if outcome == "Approve":
			try:
				pa.decide("Approve", notes="موافقة وفق التقرير الطبي والتعرفة المتعاقد عليها")
			except frappe.ValidationError:
				pa.reload()
				pa.decide("Reject", notes="الخدمة غير مستحقة وفق شروط البرنامج", reason=reasons.get("Eligibility") or reasons.get("Coverage"))
		elif outcome == "Reject":
			pa.decide("Reject", notes="الإجراء غير ضروري طبياً في هذه المرحلة", reason=reasons.get("Medical Necessity") or reasons.get("Coverage"))
		else:
			pa.decide("Request Information", info="يرجى تزويدنا بتقرير الأشعة وتقرير الطبيب الاستشاري")
	frappe.db.set_value("Pre-Authorization", pa.name, "decision_on", decided, update_modified=False)


def medical_claim(ctx, active, by_kind, hospitals, kind, service_day, reasons):
	st = ctx.store
	m = eligible_member(ctx, active, service_day, female_adult=(kind == "Maternity"))
	if not m:
		return
	pre = None
	if kind == "Outpatient":
		prov = choose(ctx, m, (by_kind.get("Clinic / Medical Center") or []) + (by_kind.get("Doctor") or []) + hospitals)
		items = [{"service": ctx.pick(["CON-SP", "CON-GP", "CON-CN", "CON-FU"])}] + [{"service": ctx.pick(["LAB-CBC", "LAB-FBS", "LAB-CRP", "LAB-UA"])}
			for _ in range(ctx.weighted([(0, 50), (1, 30), (2, 20)]))]
		dx = diag(ctx, ctx.pick(prov.specs) if prov.specs else None)
	elif kind == "Pharmacy":
		prov = choose(ctx, m, by_kind.get("Pharmacy") or hospitals)
		chronic = ctx.chance(0.35)
		pool = [d for d in C.DRUGS if d[5] == (1 if chronic else 0) and not d[6] and d[7]]
		items = [{"item_type": "Drug", "drug": d[0], "quantity": ctx.rng.randint(1, min(2, d[8]))} for d in ctx.rng.sample(pool, ctx.rng.randint(1, 4))]
		if ctx.chance(0.03):
			items.append({"item_type": "Drug", "drug": "DR-0042", "quantity": 1})
		dx = diag(ctx, chronic=1 if chronic else 0)
	elif kind == "Laboratory and Radiology":
		prov = choose(ctx, m, (by_kind.get("Laboratory") or []) + (by_kind.get("Radiology Center") or []) or hospitals)
		pool = [s for s in C.SERVICES if s[3] in (("Laboratory",) if prov.kind == "Laboratory" else ("Radiology",)) and not s[6] and s[4] != "Maternity"] or [s for s in C.SERVICES if s[3] == "Laboratory"]
		items = [{"service": s[0]} for s in ctx.rng.sample(pool, min(len(pool), ctx.rng.randint(1, 5)))]
		dx = diag(ctx)
	elif kind == "Dental":
		prov = choose(ctx, m, by_kind.get("Dental Center") or hospitals)
		items = [{"service": ctx.pick(["DEN-FIL", "DEN-SCL", "DEN-EXT", "DEN-RCT", "DEN-CRN"])}, {"service": "CON-SP"}]
		dx = diag(ctx, "Dentistry")
	elif kind == "Optical":
		prov = choose(ctx, m, by_kind.get("Other Specialty") or hospitals)
		items = [{"service": "OPT-EXM"}, {"service": "OPT-GLS"}]
		dx = diag(ctx, "Ophthalmology")
	elif kind == "Emergency":
		prov = choose(ctx, m, hospitals)
		items = [{"service": "CON-ER"}] + [{"service": ctx.pick(["ER-NEB", "ER-IVF", "ER-SUT", "ER-CST", "RAD-XL"])} for _ in range(ctx.rng.randint(1, 3))]
		dx = diag(ctx, ctx.pick(["Orthopedics", "Internal Medicine", "Pediatrics"]))
	elif kind == "Maternity":
		prov = choose(ctx, m, [h for h in hospitals if "Obstetrics & Gynecology" in (h.specs or [])] or hospitals)
		cs = ctx.chance(0.45)
		items = [{"service": "MAT-CS" if cs else "MAT-NVD"}, {"service": "IP-WARD", "quantity": 3 if cs else 1}, {"service": "LAB-CBC"}]
		dx = "ICD-10-O82" if cs else "ICD-10-O80"
		pre = quick_preauth(ctx, m.name, prov.name, items, service_day, dx, "Admission")
	else:  # inpatient
		cands = [p for p in st.preauths if 0 <= (getdate(service_day) - p.when).days <= 20 and not p.get("used")
			and frappe.db.get_value("Pre-Authorization", p.name, "status") in ("Approved", "Partially Approved")]
		if cands and ctx.chance(0.8):
			pa = ctx.pick(cands)
			pa.used = True
			m = frappe._dict(name=pa.member)
			prov = frappe._dict(name=pa.provider)
			items = [{"item_type": r.item_type, "service": r.service, "drug": r.drug, "quantity": r.approved_quantity or r.quantity}
				for r in frappe.get_all("Pre-Auth Item", filters={"parent": pa.name, "status": ("!=", "Rejected")}, fields=["item_type", "service", "drug", "quantity", "approved_quantity"])]
			dx = frappe.db.get_value("Pre-Authorization", pa.name, "diagnosis")
			pre = pa.name
			service_day = max(getdate(service_day), pa.when)
		else:
			prov = choose(ctx, m, hospitals)
			items = [{"service": "IP-WARD", "quantity": ctx.rng.randint(1, 3)}, {"service": "LAB-CBC"}, {"service": "CON-CN"}]
			dx = diag(ctx, "Internal Medicine")
			if ctx.chance(0.7):
				pre = quick_preauth(ctx, m.name, prov.name, items, service_day, dx, "Admission")
	if getdate(service_day) > ctx.today:
		service_day = ctx.today
	rows = []
	for it in items:
		row = {"item_type": it.get("item_type") or "Service", "quantity": it.get("quantity") or 1}
		if row["item_type"] == "Drug":
			row["drug"] = it["drug"]
		else:
			row["service"] = it["service"]
		rows.append(row)
	inflate = ctx.chance(0.04)
	st.invoice_seq += 1
	received = min(getdate(add_days(service_day, ctx.rng.randint(1, 12))), ctx.today)
	data = {"doctype": "Medical Claim", "claim_type": kind if kind != "Maternity" else "Maternity", "member": m.name, "provider": prov.name,
		"invoice_no": f"INV-{getdate(service_day).year}-{st.invoice_seq:06d}", "invoice_date": service_day, "service_date": service_day, "diagnosis": dx,
		"items": rows, "source": ctx.weighted([("Provider Portal", 55), ("Manual", 35), ("API", 10)]), "pre_auth": pre if isinstance(pre, str) else None}
	if kind in ("Inpatient", "Maternity"):
		data.update(claim_type="Inpatient" if kind == "Inpatient" else "Maternity", admission_date=service_day,
			discharge_date=add_days(service_day, max(1, sum(r["quantity"] for r in rows if r.get("service") in ("IP-WARD", "IP-PRV", "IP-ICU")))))
		if getdate(data["discharge_date"]) > ctx.today:
			data["discharge_date"] = ctx.today
	with as_of(ctx.stamp(received)):
		doc = frappe.get_doc(data)
		doc.flags.ignore_permissions = True
		doc.insert()
		if inflate:
			for r in doc.items:
				r.unit_price = flt(r.unit_price) * ctx.rng.uniform(1.15, 1.45)
			doc.save()
		ctx.track("Medical Claim", doc.name)
		doc.submit()
	ctx.backdate("Medical Claim", doc.name, ctx.stamp(received))
	doc.reload()
	if doc.fwa_flag and len(st.get("flagged", [])) < 2:
		st.setdefault("flagged", []).append(doc.name)
		ctx.highlight("مطالبة أوقفتها قواعد الاحتيال للمراجعة", "Medical Claim", doc.name, f"درجة الخطورة {doc.fwa_score}")
	# duplicate submissions (a classic fraud pattern) for a small share
	if ctx.chance(0.012) and kind in ("Outpatient", "Laboratory and Radiology"):
		dup = dict(data, invoice_no=f"INV-{getdate(service_day).year}-{st.invoice_seq + 500000:06d}", service_date=add_days(service_day, 1) if getdate(add_days(service_day, 1)) <= ctx.today else service_day)
		with as_of(ctx.stamp(received)):
			d2 = ctx.insert(dup, submit=True, backdate=ctx.stamp(received))
	age = (ctx.today - received).days
	outcome = ctx.weighted([("approve", 78), ("reject", 9), ("info", 4), ("open", 9)] if age > 20 else
		([("approve", 50), ("reject", 6), ("info", 8), ("open", 36)] if age > 5 else [("approve", 10), ("open", 85), ("info", 5)]))
	severe = doc.fwa_flag and frappe.db.exists("FWA Alert", {"claim": doc.name, "severity": "High"})
	if severe and ctx.chance(0.6):
		outcome = ctx.pick(["reject", "reject", "open"])
	if outcome == "open":
		if ctx.chance(0.5) and doc.status == "Received":
			with as_of(ctx.stamp(received)):
				doc.set_status(ctx.pick(["Under Review", "Medical Review"]))
		return
	decided = min(ctx.stamp(add_days(received, ctx.rng.randint(1, 9))), ctx.stamp(ctx.today, 7, 9))
	with as_of(decided):
		doc.reload()
		if outcome == "reject" or flt(doc.payer_amount) <= 0:
			cat = "Fraud" if severe else ("Coverage" if flt(doc.payer_amount) <= 0 else ctx.pick(["Documentation", "Medical Necessity", "Pricing"]))
			doc.set_status("Rejected", notes="قرار لجنة المطالبات", reason=reasons.get(cat) or reasons.get("Other"))
		elif outcome == "info":
			doc.set_status("Pending Information", info="يرجى إرفاق الوصفة الطبية الأصلية ونتائج التحاليل")
		else:
			partial = any(i.status == "Rejected" for i in doc.items) or flt(doc.over_limit_amount) > 0.005
			doc.set_status("Partially Approved" if partial else "Approved", notes="مطابقة للتعرفة والمنافع")


def expire_unused(ctx):
	"""Approved authorizations past their validity that no claim used become Expired (the used ones stay Approved)."""
	used = {r[0] for r in frappe.db.sql("select distinct pre_auth from `tabMedical Claim` where pre_auth is not null")}
	for name in frappe.get_all("Pre-Authorization", filters={"status": ("in", ["Approved", "Partially Approved"]), "valid_until": ("<", ctx.today)}, pluck="name"):
		if name not in used:
			frappe.db.set_value("Pre-Authorization", name, "status", "Expired", update_modified=False)


def quick_preauth(ctx, member, provider, items, service_day, dx, kind):
	"""An approved pre-authorization issued shortly before the admission (what a hospital does in practice)."""
	when = max(getdate(add_days(service_day, -ctx.rng.randint(1, 3))), getdate(f"{ctx.today.year}-01-01"))
	rows = [{"item_type": "Service", "service": i["service"], "quantity": i.get("quantity") or 1} for i in items if i.get("service")]
	with as_of(ctx.stamp(when)):
		pa = ctx.insert({"doctype": "Pre-Authorization", "member": member, "provider": provider, "auth_type": kind, "request_date": when, "diagnosis": dx,
			"priority": "Urgent", "items": rows, "admission_date": service_day, "expected_days": 2,
			"medical_notes": "<p>طلب موافقة للتنويم وفق تقرير الطبيب المعالج.</p>"}, backdate=ctx.stamp(when))
		pa.submit_request()
		pa.reload()
		pa.start_review()
		pa.reload()
		pa.decide("Approve", notes="موافقة على التنويم")
	ctx.store.preauths.append(frappe._dict(name=pa.name, member=member, provider=provider, when=getdate(when), used=True))
	return pa.name if frappe.db.get_value("Pre-Authorization", pa.name, "status") in ("Approved", "Partially Approved") else None


def settlements(ctx):
	st = ctx.store
	year = ctx.today.year
	top = frappe.db.sql("""select provider, count(*) n from `tabMedical Claim` where docstatus = 1 and status in ('Approved', 'Partially Approved')
		and name in (select ref_name from `tabTPA Demo Record` where run = %s and ref_doctype = 'Medical Claim') group by provider order by n desc limit 4""",
		ctx.run.name, as_dict=True)
	for t in top:
		for month in range(1, ctx.today.month):
			start = getdate(f"{year}-{month:02d}-01")
			end = add_days(add_months(start, 1), -1)
			def one(t=t, start=start, end=end, month=month):
				when = add_days(end, 6)
				with as_of(ctx.stamp(when)):
					s = frappe.new_doc("Provider Settlement")
					s.update({"provider": t.provider, "company": ctx.company, "posting_date": when, "period_from": start, "period_to": end, "currency": "IQD"})
					s.fetch_claims()
					if not s.claims:
						return
					if ctx.chance(0.25) and flt(s.gross_payable) > 2_000_000:
						s.append("adjustments", {"adjustment_type": "Penalty", "amount": ctx.amount(25_000, 150_000, 5_000), "reason": "غرامة تأخير تسليم الفواتير الورقية"})
					s.flags.ignore_permissions = True
					s.insert()
					ctx.track("Provider Settlement", s.name)
					s.submit()
				if month < ctx.today.month - 1 or ctx.chance(0.4):
					paid_on = min(getdate(add_days(when, ctx.rng.randint(5, 15))), ctx.today)
					with as_of(ctx.stamp(paid_on)):
						pe = frappe.get_doc("Provider Settlement", s.name).make_payment()
					ctx.track("Payment Entry", pe)
				elif not st.get("unpaid_settlement"):
					st.unpaid_settlement = s.name
					ctx.highlight("تسوية معتمدة بانتظار الدفع", "Provider Settlement", s.name, "اضغط Make Payment لإصدار قيد الدفع")
			ctx.attempt("settlement", one)


def fee_invoices(ctx):
	year = ctx.today.year
	for c in [c for c in ctx.store.clients if c.kind != "Corporate Client" or c.en == "Al-Waha Commercial Bank"][:3]:
		for month in range(max(1, ctx.today.month - 3), ctx.today.month):
			start = getdate(f"{year}-{month:02d}-01")
			end = add_days(add_months(start, 1), -1)
			fund = ctx.store.get("fund") if c.kind == "Self-Funded Scheme" else None
			ctx.attempt("fee", lambda c=c, start=start, end=end, fund=fund: ctx.insert({"doctype": "TPA Fee Invoice", "client": c.name, "company": ctx.company,
				"period_from": start, "period_to": end, "posting_date": add_days(end, 3), "charge_to": "Health Fund" if fund else "Client", "fund": fund}, submit=True))


def fraud(ctx, active):
	st = ctx.store
	inv = st.tpa_users.get("tpa_mgr")
	for m in ctx.rng.sample(active, min(2, len(active))):
		ctx.attempt("watch member", lambda m=m: ctx.insert({"doctype": "FWA Watchlist", "entity_type": "Member", "member": m.name, "active": 1,
			"from_date": ctx.days_ago(30, 90), "reason": "تكرار مراجعات الطوارئ وطلب أدوية بكميات كبيرة"}))
	prov = [p for p in st.providers if p.kind == "Pharmacy"][:1]
	for p in prov:
		ctx.attempt("watch provider", lambda p=p: ctx.insert({"doctype": "FWA Watchlist", "entity_type": "Provider", "provider": p.name, "active": 1,
			"from_date": ctx.days_ago(20, 60), "reason": "فواتير أدوية مزمنة بأسعار تتجاوز التعرفة"}))
	alerts = frappe.get_all("FWA Alert", filters={"status": "Open", "claim": ("in", [r[0] for r in frappe.db.sql(
		"select ref_name from `tabTPA Demo Record` where run=%s and ref_doctype='Medical Claim'", ctx.run.name)] or [""])}, pluck="name")
	for k, a in enumerate(alerts[:12]):
		status = ["Under Investigation", "Confirmed", "False Positive", "Closed"][k % 4]
		outcome = {"Under Investigation": "", "Confirmed": "ثبت تكرار الفوترة لنفس الخدمة وتم خصم المبلغ من التسوية التالية",
			"False Positive": "تبين أن الخدمة الثانية تمت بأمر طبي مستقل", "Closed": "أُغلقت بعد تنبيه مقدم الخدمة"}[status]
		ctx.attempt("alert", lambda a=a, status=status, outcome=outcome: frappe.db.set_value("FWA Alert", a, {"status": status, "investigator": inv, "outcome": outcome}))


def cases(ctx, active):
	mgr = ctx.store.tpa_users.get("tpa_co1")
	chronic = frappe.db.sql("""select distinct c.member, c.diagnosis from `tabMedical Claim` c join `tabMedical Code` mc on mc.name = c.diagnosis
		where mc.is_chronic = 1 and c.docstatus = 1 and c.name in (select ref_name from `tabTPA Demo Record` where run=%s and ref_doctype='Medical Claim') limit 12""",
		ctx.run.name, as_dict=True)
	for r in chronic:
		if frappe.db.exists("Medical Case", {"member": r.member, "status": ("!=", "Closed")}):
			continue
		ctx.attempt("case", lambda r=r: ctx.insert({"doctype": "Medical Case", "member": r.member, "diagnosis": r.diagnosis, "case_type": "Chronic",
			"status": ctx.pick(["Open", "Monitoring"]), "case_manager": mgr, "opened_on": ctx.days_ago(30, 200),
			"follow_ups": [{"follow_up_date": ctx.days_ago(1, 25), "notes": "اتصال هاتفي للتأكد من الالتزام بالعلاج وموعد التحاليل الدورية", "next_follow_up": ctx.days_ago(-30, -10)}],
			"notes": "برنامج إدارة الأمراض المزمنة"}))


def tickets(ctx, active):
	st = ctx.store
	cs = [u for k, u in st.tpa_users.items() if k.startswith("tpa_cs") and u] or [None]
	claims = [r[0] for r in frappe.db.sql("select ref_name from `tabTPA Demo Record` where run=%s and ref_doctype='Medical Claim' limit 300", ctx.run.name)]
	for i in range(ctx.p.tickets):
		def one():
			kind = ctx.weighted([("Inquiry", 55), ("Complaint", 40), ("Suggestion", 5)])
			subject = ctx.pick({"Inquiry": C.SUBJECTS_INQUIRY, "Complaint": C.SUBJECTS_COMPLAINT, "Suggestion": C.SUBJECTS_SUGGESTION}[kind])
			when = ctx.stamp(ctx.days_ago(0, 150), 8, 20)
			m = ctx.pick(active)
			data = {"doctype": "Service Ticket", "ticket_type": kind, "channel": ctx.weighted([("Phone", 50), ("WhatsApp", 20), ("Portal", 15), ("Email", 10), ("Walk-in", 5)]),
				"priority": ctx.weighted([("Medium", 50), ("High", 25), ("Low", 15), ("Urgent", 10)]), "subject": subject, "member": m.name,
				"assigned_to": ctx.pick(cs), "description": f"<p>{subject}. اتصل المؤمن عليه {m.ar} وطلب المساعدة.</p>",
				"call_start": when, "call_duration_sec": ctx.rng.randint(60, 900), "call_reference": f"REC-{ctx.rng.randint(100000, 999999)}"}
			if kind == "Complaint" and claims and ctx.chance(0.5):
				c = ctx.pick(claims)
				data.update(claim=c, provider=frappe.db.get_value("Medical Claim", c, "provider"))
			with as_of(when):
				t = ctx.insert(data, backdate=when)
			age_h = (ctx.today - when.date()).days * 24
			if age_h > 48 and ctx.chance(0.8):
				resolved = when + timedelta(hours=ctx.rng.randint(2, 70))
				frappe.db.set_value("Service Ticket", t.name, {"status": ctx.pick(["Resolved", "Closed"]), "resolution": ctx.pick([
					"تم توضيح الرصيد المتبقي للمؤمن عليه", "تم التنسيق مع المستشفى وإلغاء المبلغ الإضافي", "أُعيدت دراسة المطالبة وتم اعتمادها جزئياً",
					"صدرت بطاقة بدل ضائع وأُرسلت إلى جهة العمل"]), "resolved_on": resolved, "first_response_on": when + timedelta(minutes=ctx.rng.randint(5, 240)),
					"satisfaction": ctx.weighted([("5", 35), ("4", 35), ("3", 18), ("2", 8), ("1", 4)])}, update_modified=False)
		ctx.attempt("ticket", one)


def tpa_documents(ctx):
	from a1erp_tpa.demo_data.builder import simple_pdf as get_pdf

	for c in ctx.store.clients[:3]:
		def one(c=c):
			html = ["Health Services Administration Agreement", f"Between Al-Taawidh TPA and {c.en}", f"Contract year {ctx.today.year}", "Demo document"]
			f = frappe.get_doc({"doctype": "File", "file_name": f"contract-{frappe.scrub(c.en)}.pdf", "content": get_pdf(html), "is_private": 1,
				"attached_to_doctype": "TPA Client", "attached_to_name": c.name})
			f.flags.ignore_permissions = True
			f.insert()
			ctx.track("File", f.name)
			ctx.insert({"doctype": "TPA Document", "title": f"عقد إدارة الخدمات - {c.name}", "document_type": "Client Contract", "file": f.file_url,
				"reference_doctype": "TPA Client", "reference_name": c.name, "retention_years": 10, "is_confidential": 1})
		ctx.attempt("tpa document", one)
