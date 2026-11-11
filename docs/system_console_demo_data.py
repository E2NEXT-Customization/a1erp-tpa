# =====================================================================================================
#  A1ERP Health TPA - realistic demo data from the System Console
#  كود توليد بيانات العرض الواقعية للإدارة الطبية (TPA) من System Console
#
#  Where:  /app/system-console  ->  Type: Python  ->  paste ONE block  ->  tick "Commit"  ->  Execute
#  أين:    افتح /app/system-console  واختر Python  والصق مقطعاً واحداً  وفعّل Commit  ثم Execute
#
#  Needs on that system: the a1erp_tpa app at its latest version (bench migrate done),
#  server scripts enabled (bench set-config -g server_script_enabled 1) and a running background worker.
# =====================================================================================================


# ---------------------------------------------------------------- 1) GENERATE  /  إنشاء البيانات
SIZE = "Standard"   # "Quick Tour" (about 800 records)  |  "Standard" (about 2,500)  |  "Full" (about 6,500)
SEED = 11           # any number; another number gives other names, amounts and dates

run = frappe.call("a1erp_tpa.demo_data.api.start", profile=SIZE, seed=SEED)
print("Started:", run)
print("It runs in the background (Standard takes about 10 minutes). Paste block 2 to follow it.")


# ---------------------------------------------------------------- 2) PROGRESS  /  متابعة التقدم
d = frappe.call("a1erp_tpa.demo_data.api.overview")
r = d["last"]
if not r:
	print("No demo data run yet.")
else:
	print(r["name"], "|", r["status"], "|", str(r["progress"]) + "%", "|", r["current_step"], "| records:", r["records"], "| skipped:", r["errors"])
	print("Background workers:", d["workers"])
	print("\n".join((d["log"] or "").split("\n")[-12:]))
	if d["highlights"]:
		print("\nSuggested demo walkthrough:")
		for h in d["highlights"]:
			print("-", h["title"], "->", "/app/" + h["route"] + "/" + h["name"])


# ---------------------------------------------------------------- 3) REMOVE  /  حذف بيانات العرض
# Removes only what the generator created (with its journal entries) and restores the settings it changed.
CONFIRM = ""        # write DELETE between the quotes to confirm
if CONFIRM == "DELETE":
	print("Removal started:", frappe.call("a1erp_tpa.demo_data.api.clear"))
else:
	print("Nothing removed. Set CONFIRM = \"DELETE\" to remove the demo data.")
