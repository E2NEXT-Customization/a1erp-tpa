// Demo Data Console: generate realistic demo data in the background, follow it live, review it, and remove it in one step.

frappe.pages["tpa-demo-data"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("TPA Demo Data"), single_column: true });
	const API = "a1erp_tpa.demo_data.api.";
	const PROFILE_INFO = {
		"Quick Tour": { minutes: "3 - 6", text: __("A light set to tour every screen quickly.") },
		Standard: { minutes: "10 - 20", text: __("A convincing company for a management presentation.") },
		Full: { minutes: "35 - 70", text: __("The full volume of the specification: a busy year of business.") },
	};
	const esc = frappe.utils.escape_html;
	const fmt = (n) => Number(n || 0).toLocaleString();
	let state = { profile: "Standard", timer: null, data: null };

	$(`<style>
	.ddc{--card:var(--card-bg,#fff);--ink:var(--text-color,#1d1d1f);--mute:var(--text-muted,#6e6e73);--line:var(--border-color,#e5e5ea);--blue:#0071e3;--green:#248a3d;--amber:#b25000;--red:#d70015;
		font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Tahoma,sans-serif;color:var(--ink);max-width:1120px;margin:0 auto;padding:6px 2px 60px}
	.ddc .hero{padding:26px 4px 10px}.ddc .hero h1{font-size:34px;font-weight:700;letter-spacing:-.02em;margin:0}
	.ddc .hero p{color:var(--mute);font-size:16px;margin:8px 0 0;max-width:760px;line-height:1.7}
	.ddc .grid{display:grid;gap:14px}.ddc .g3{grid-template-columns:repeat(auto-fit,minmax(250px,1fr))}.ddc .g4{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
	.ddc .card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
	.ddc h3{font-size:18px;font-weight:650;margin:28px 4px 12px}
	.ddc .prof{cursor:pointer;transition:all .18s}.ddc .prof:hover{transform:translateY(-2px)}
	.ddc .prof.on{border-color:var(--blue);box-shadow:0 0 0 3px rgba(0,113,227,.18)}
	.ddc .prof b{font-size:19px}.ddc .prof small{display:block;color:var(--mute);margin:4px 0 12px;font-size:13px}
	.ddc .prof .nums{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;font-size:13px;color:var(--mute)}.ddc .prof .nums span b{color:var(--ink);font-size:14px}
	.ddc .row{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-top:16px}
	.ddc .chk{display:flex;gap:8px;align-items:center;font-size:15px;cursor:pointer}
	.ddc .btn-go{background:var(--blue);color:#fff;border:0;border-radius:980px;padding:11px 26px;font-size:15px;font-weight:600;cursor:pointer}
	.ddc .btn-go:disabled{opacity:.45;cursor:default}.ddc .btn-del{background:transparent;color:var(--red);border:1px solid rgba(215,0,21,.35);border-radius:980px;padding:9px 20px;font-weight:600;cursor:pointer}
	.ddc .bar{height:10px;border-radius:99px;background:rgba(120,120,128,.16);overflow:hidden;margin:14px 0 8px}.ddc .bar i{display:block;height:100%;background:linear-gradient(90deg,var(--blue),#5e5ce6);border-radius:99px;transition:width .6s}
	.ddc .status{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}.ddc .status .big{font-size:30px;font-weight:700;font-variant-numeric:tabular-nums}
	.ddc .pill{display:inline-block;padding:3px 11px;border-radius:980px;font-size:12px;font-weight:600;background:rgba(120,120,128,.16)}
	.ddc .pill.ok{background:rgba(36,138,61,.14);color:var(--green)}.ddc .pill.run{background:rgba(0,113,227,.12);color:var(--blue)}.ddc .pill.bad{background:rgba(215,0,21,.12);color:var(--red)}
	.ddc pre.log{background:#1d1d1f;color:#e5e5ea;border-radius:14px;padding:14px 16px;max-height:220px;overflow:auto;font-size:12px;line-height:1.6;direction:ltr;text-align:left;margin:12px 0 0;white-space:pre-wrap}
	.ddc table{width:100%;border-collapse:collapse;font-size:14px}.ddc th{color:var(--mute);font-weight:500;font-size:12px;text-align:start;padding:8px 10px;border-bottom:1px solid var(--line)}
	.ddc td{padding:9px 10px;border-bottom:1px solid var(--line)}.ddc td.n{font-variant-numeric:tabular-nums;text-align:end}.ddc tr:last-child td{border-bottom:0}
	.ddc .hl{display:flex;gap:14px;align-items:flex-start;padding:12px 4px;border-bottom:1px solid var(--line)}.ddc .hl:last-child{border:0}
	.ddc .hl .k{min-width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,var(--blue),#5e5ce6);color:#fff;display:grid;place-items:center;font-weight:700;font-size:13px}
	.ddc .hl a{font-weight:600}.ddc .hl small{display:block;color:var(--mute);margin-top:2px}
	.ddc .warn{border-radius:14px;padding:12px 16px;background:rgba(178,80,0,.09);color:var(--ink);font-size:14px;margin-top:12px}
	</style>`).appendTo(page.main);

	const $root = $('<div class="ddc"></div>').appendTo(page.main);
	$root.html(`<div class="hero"><h1>${__("TPA Demo Data")}</h1>
		<p>${__("Fill the system with realistic, fictional data: Iraqi names, employers, hospitals, pharmacies, plans, members and medical claims spread over the past months. Every record goes through the real business rules, so the accounts, reports and dashboards are consistent. Everything created here can be removed in one step.")}</p></div>
		<div id="ddc-status"></div>
		<h3>${__("1. Choose the size")}</h3><div class="grid g3" id="ddc-profiles"></div>
		<div class="row">
			<span style="flex:1"></span><button class="btn-go" id="ddc-go">${__("Generate demo data")}</button></div>
		<div id="ddc-walk"></div>
		<h3>${__("Records in the system")}</h3><div class="grid" id="ddc-counts"></div>
		<h3 style="color:var(--red)">${__("Remove the demo data")}</h3>
		<div class="card"><p style="margin:0 0 12px;color:var(--mute)">${__("Cancels and deletes every record created by this console, with its journal entries, and restores the settings it changed. Data you entered yourself is not touched.")}</p>
		<button class="btn-del" id="ddc-del">${__("Remove all demo data")}</button></div>`);

	function profiles(p) {
		$("#ddc-profiles").html(Object.keys(p).map((k) => {
			const v = p[k], info = PROFILE_INFO[k] || {};
			return `<div class="card prof ${state.profile === k ? "on" : ""}" data-p="${k}"><b>${__(k)}</b><small>${esc(info.text || "")} ${__("About {0} minutes.", [info.minutes || "?"])}</small>
				<div class="nums"><span>${__("Health members")}: <b>${fmt(v.members)}</b></span><span>${__("Medical claims")}: <b>${fmt(v.med_claims)}</b></span>
				<span>${__("Providers")}: <b>${fmt(v.providers)}</b></span>
				<span>${__("Pre-authorizations")}: <b>${fmt(v.preauths)}</b></span><span>${__("History (months)")}: <b>${fmt(v.months)}</b></span></div></div>`;
		}).join(""));
		$("#ddc-profiles .prof").on("click", function () { state.profile = $(this).data("p"); profiles(p); });
	}

	function statusCard(d) {
		const r = d.last;
		if (!r) { $("#ddc-status").html(""); return; }
		const running = ["Queued", "Running", "Cleaning"].includes(r.status);
		const cls = running ? "run" : (r.status === "Failed" ? "bad" : "ok");
		let warn = "";
		if (running && d.workers === 0) warn = `<div class="warn">${__("No background worker is running. Start the bench (bench start) so the job can run.")}</div>`;
		$("#ddc-status").html(`<div class="card"><div class="status"><div><span class="pill ${cls}">${__(r.status)}</span>
			<div style="margin-top:8px;font-weight:600">${esc(__(r.current_step || ""))}</div>
			<small style="color:var(--mute)">${r.name} · ${__(r.profile || "")} · ${__("Records Created")}: ${fmt(r.records)}${r.errors ? " · " + __("Skipped Records") + ": " + fmt(r.errors) : ""}</small></div>
			<div class="big">${Math.round(r.progress || 0)}%</div></div><div class="bar"><i style="width:${Math.min(100, r.progress || 0)}%"></i></div>
			${d.log ? `<pre class="log">${esc(d.log.split("\n").slice(-14).join("\n"))}</pre>` : ""}${warn}</div>`);
		$("#ddc-go, #ddc-del").prop("disabled", running);
	}

	function counts(d) {
		$("#ddc-counts").html(d.groups.map((g) => `<div class="card"><b style="font-size:16px">${esc(g.group)}</b><table style="margin-top:8px">
			<tr><th>${__("Document")}</th><th style="text-align:end">${__("Demo records")}</th><th style="text-align:end">${__("All records")}</th></tr>
			${g.rows.map((r) => `<tr><td><a href="/app/${r.route}">${esc(r.label)}</a></td><td class="n">${fmt(r.demo)}</td><td class="n">${fmt(r.total)}</td></tr>`).join("")}
			</table></div>`).join(""));
	}

	function walkthrough(d) {
		if (!d.highlights || !d.highlights.length) { $("#ddc-walk").html(""); return; }
		$("#ddc-walk").html(`<h3>${__("2. Suggested demo walkthrough")}</h3><div class="card">${d.highlights.map((h, i) => {
			const portal = h.note && h.note.startsWith("/");
			const link = portal ? h.note : `/app/${h.route}/${encodeURIComponent(h.name)}`;
			return `<div class="hl"><div class="k">${i + 1}</div><div><a href="${link}" ${portal ? 'target="_blank"' : ""}>${esc(h.title)}</a>
				<small>${esc(portal ? __("Open the portal in a private window") : (h.note || ""))} · ${esc(__(h.doctype))} ${esc(h.name)}</small></div></div>`;
		}).join("")}<div class="warn">${__("Staff accounts created by the console use the password Demo@2026. Change or disable them before any real use.")}</div></div>`);
	}

	function load() {
		frappe.call({ method: API + "overview" }).then((r) => {
			const d = r.message;
			state.data = d;
			profiles(d.profiles);
			statusCard(d);
			counts(d);
			walkthrough(d);
			const running = d.last && ["Queued", "Running", "Cleaning"].includes(d.last.status);
			clearTimeout(state.timer);
			if (running) state.timer = setTimeout(load, 2500);
		});
	}

	$root.on("click", "#ddc-go", () => {
		frappe.confirm(__("Generate the {0} demo data set now? It runs in the background; you can leave this page.", [__(state.profile)]), () => {
			frappe.call({ method: API + "start", args: { profile: state.profile } }).then(() => {
				frappe.show_alert({ message: __("Started"), indicator: "blue" });
				load();
			});
		});
	});
	$root.on("click", "#ddc-del", () => {
		frappe.prompt({ fieldname: "confirm", fieldtype: "Data", reqd: 1, label: __("Type DELETE to confirm") }, (v) => {
			if ((v.confirm || "").trim().toUpperCase() !== "DELETE") { frappe.msgprint(__("Nothing was removed.")); return; }
			frappe.call({ method: API + "clear" }).then(() => { frappe.show_alert({ message: __("Removal started"), indicator: "orange" }); load(); });
		}, __("Remove all demo data"), __("Remove"));
	});
	frappe.realtime.on("tpa_demo_progress", () => { clearTimeout(state.timer); state.timer = setTimeout(load, 400); });
	load();
};
