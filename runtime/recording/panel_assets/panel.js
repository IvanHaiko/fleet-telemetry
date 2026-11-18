"use strict";
const el = id => document.getElementById(id);
const token = document.querySelector('meta[name="panel-token"]').content;
const fmt = value => value == null ? "—" : value.toLocaleString();
let pending = false;
let last = {};
let clientError = "";
function button(title, action, id, enabled) {
  const b = document.createElement("button");
  b.textContent = title; b.dataset.action = action; b.dataset.id = id; b.disabled = !enabled;
  return b;
}
function row(values) {
  const tr = document.createElement("tr");
  for (const value of values) {
    const td = tr.insertCell();
    for (const part of Array.isArray(value) ? value : [value]) td.append(part ?? "—");
  }
  return tr;
}
// Keep focused controls and rows in place across identical status samples.
function table(id, rows, empty) {
  if (!rows.length) {
    const tr = row([empty]); tr.cells[0].colSpan = 5; tr.cells[0].className = "empty"; rows.push(tr);
  }
  const body = el(id);
  rows.forEach((tr,i) => {
    const old = body.children[i];
    if (!old) body.append(tr);
    else if (!old.isEqualNode(tr)) old.replaceWith(tr);
  });
  while (body.children.length > rows.length) body.lastChild.remove();
}
function render(s) {
  last = s;
  updateServices(s);
  const free = !pending && !s.task;
  const active = s.phase === "Running";
  const allowed = {start:["Idle","Stopped"], complete:["Running"], verify:["Completed"], stop:["Starting","Running","Completed"],close:["Viewing"]};
  document.querySelector('[data-action="close"]').hidden = s.phase !== "Viewing";
  document.querySelectorAll(".actions button").forEach(b => b.disabled = !free || !allowed[b.dataset.action].includes(s.phase));
  document.querySelector('[data-action="browse"]').disabled = !free;
  el("run").textContent = s.run;
  el("phase").textContent = s.phase;
  el("grafana").href = s.view || "http://127.0.0.1:13003/d/fleet-live";
  el("grafana").textContent = s.view ? "Historical dashboard ↗" : "Fleet dashboard ↗";
  el("grafana").hidden = !(active || s.phase === "Completed" || s.view);
  const event = s.event ? " · " + s.event.replaceAll("_"," ") : "";
  el("feedback").textContent = clientError || (s.task ? s.task + " in progress…" + event : s.message) || "";
  el("feedback").className = clientError || s.message.includes("failed") ? "error" : "";
  for (const k of ["ack","archived","visible"]) el(k).textContent = fmt(s.stream[k]);
  const age = s.stream.t_ms == null ? null : Math.max(0, Math.round((Date.now()-s.stream.t_ms)/1000));
  el("sample").textContent = age == null ? "No sample yet" : "Last sample " + age + "s ago" + (s.stream.error ? " · " + s.stream.error : "");
  const vehicles = s.fleet.vehicles || [];
  table("vehicles", vehicles.map(v => {
    const key = Object.keys(s.members).find(k => s.members[k] === v.vehicle);
    const name = s.sources.find(source => source.id === key)?.name;
    return row([name || v.vehicle, v.player || "Unknown",fmt(v.sent)+" / "+fmt(v.total),v.heartbeat_age_ms == null ? "—" : (v.heartbeat_age_ms/1000).toFixed(1)+" s",
      [button("Pause","pause",key,free && active && key && v.player==="running"),button("Resume","resume",key,free && active && key && v.player==="paused"),button("End","remove",key,free && active && key && ["running","paused"].includes(v.player))]]);
  }), s.fleet.error || (active ? "Waiting for published vehicle data." : "Start a session and add a recording."));
  table("sources",s.sources.map(source => {
    const info = source.info;
    const title = document.createElement("strong");
    title.textContent = /^F\d+$/.test(source.id) ? source.id + " · " + source.name : source.name;
    const tags = info && [info.position_topic && "GPS", info.available?.battery && "Battery", info.available?.armed && "Arming state"].filter(Boolean).join(" · ");
    return row([title,info ? fmt(info.duration_s)+" s" : "—",tags || "—",[button("Inspect","inspect",source.id,free),button("Add to session","add",source.id,free && active && !(source.id in s.members))]]);
  }),"Choose a local .ulg file to begin.");
  table("history",s.history.map(h => row([h.run,h.source,h.date,h.verified || "No report",button("Load view","view",h.run,free && h.project && ["Idle","Stopped"].includes(s.phase))])),"No stored runs.");
}
async function refresh() {
  try {
    const r = await fetch("/api/state"); if (!r.ok) throw Error("Console unavailable.");
    render(await r.json());
  } catch { updateServices({health:{error:"Panel disconnected"},phase:"Unknown"}); el("feedback").textContent = "Console disconnected. Reopen the launcher to reconnect."; }
}
document.addEventListener("click",async e => {
  const b = e.target.closest("button[data-action]"); if (!b || b.disabled || pending) return;
  if (["stop","complete","remove"].includes(b.dataset.action) && !confirm(b.textContent+" for the selected session or vehicle?")) return;
  pending = true; clientError = ""; render(last);
  try {
    const r = await fetch("/api/action",{method:"POST",headers:{"Content-Type":"application/json","X-Panel-Token":token},body:JSON.stringify({action:b.dataset.action,id:b.dataset.id || ""})});
    if (!r.ok) throw Error((await r.json()).error || "Action failed.");
  } catch (err) { clientError = err.message; }
  finally { pending = false; await refresh(); }
});
(async function poll(){ await refresh(); setTimeout(poll,2500); })();
