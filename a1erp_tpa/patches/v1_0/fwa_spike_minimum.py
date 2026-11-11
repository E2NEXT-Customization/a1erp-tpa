import frappe


def execute():
	"""The provider spike rule needs a minimum number of claims in the previous period (else small providers flag on every claim)."""
	for name in frappe.get_all("FWA Rule", filters={"rule_type": "Provider Cost Spike", "threshold_count": ("in", [0, None])}, pluck="name"):
		frappe.db.set_value("FWA Rule", name, "threshold_count", 20)