app_name = "a1erp_tpa"
app_title = "A1ERP Health TPA"
app_publisher = "A1ERP"
app_description = "Health insurance third party administration (TPA) for ERPNext (Iraqi market): members, cards, provider networks, pre-authorization, claims, settlements, funds and fraud control"
app_email = "m0ham3d113@gmail.com"
app_license = "mit"
required_apps = ["erpnext"]

add_to_apps_screen = [
	{
		"name": "a1erp_tpa",
		"logo": "/assets/a1erp_tpa/images/tpa.svg",
		"title": "Health TPA",
		"route": "/app/tpa-management",
	}
]

app_include_js = ["/assets/a1erp_tpa/js/tpa_forms.js"]

fixtures = [
	{"dt": "Custom HTML Block", "filters": [["name", "like", "WS-tpa-%"]]},
]

before_install = "a1erp_tpa.setup.install.before_install"
after_install = "a1erp_tpa.setup.install.after_install"
after_migrate = "a1erp_tpa.setup.install.after_migrate"

doc_events = {
	"Journal Entry": {"before_cancel": "a1erp_tpa.tpa_management.accounting.prevent_direct_cancel"},
}

jinja = {"methods": ["a1erp_tpa.tpa_management.cards.card_qr"]}

doctype_list_js = {"Medical Card": "public/js/medical_card_list.js"}

scheduler_events = {
	"daily": [
		"a1erp_tpa.tpa_management.doctype.plan_member.plan_member.expire_members",
		"a1erp_tpa.tpa_management.doctype.plan_member.plan_member.remind_expiring",
		"a1erp_tpa.tpa_management.doctype.health_plan.health_plan.expire_plans",
		"a1erp_tpa.tpa_management.doctype.provider_tariff.provider_tariff.expire_tariffs",
		"a1erp_tpa.tpa_management.doctype.pre_authorization.pre_authorization.expire_authorizations",
		"a1erp_tpa.tpa_management.doctype.health_fund.health_fund.check_low_balances",
		"a1erp_tpa.tpa_management.doctype.service_ticket.service_ticket.escalate_overdue",
		"a1erp_tpa.tpa_management.doctype.tpa_document.tpa_document.archive_expired",
	],
	"hourly": [
		"a1erp_tpa.tpa_management.notifications.process_queue",
	],
}
