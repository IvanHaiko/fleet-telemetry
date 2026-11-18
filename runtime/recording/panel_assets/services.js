"use strict";
const node = id => document.getElementById(id);
const serviceLabels = {kafka:"Kafka",jobmanager:"Flink",archive:"SeaweedFS / S3",serving:"ClickHouse",grafana:"Grafana"};
let dashboardKey = "";
let sessionReady = false;
let dashboardURL = "";

function showPage(grafana) {
  node("overview").hidden = grafana;
  node("dashboard").hidden = !grafana;
  node("console-page").setAttribute("aria-pressed",String(!grafana));
  node("dashboard-page").setAttribute("aria-pressed",String(grafana));
  if (grafana && sessionReady && !node("dashboard-frame").hasAttribute("src")) {
    node("dashboard-frame").src = dashboardURL;
    node("dashboard-frame").hidden = false;
  }
}
function navigate(grafana) {
  history.replaceState(null,"",grafana ? "#grafana" : location.pathname);
  showPage(grafana);
}
node("console-page").onclick = () => navigate(false);
node("dashboard-page").onclick = () => navigate(true);
node("grafana").onclick = e => { e.preventDefault(); navigate(true); };
showPage(location.hash === "#grafana");
node("retry-login").onclick = () => { dashboardKey = ""; refresh(); };

async function signIn(key,run) {
  try {
    const response = await fetch("/api/grafana-session",{
      method:"POST", headers:{"Content-Type":"application/json","X-Panel-Token":token},
      body:JSON.stringify({run})
    });
    if (!response.ok) throw Error((await response.json()).error || "Sign-in unavailable.");
    if (key !== dashboardKey) return;
    sessionReady = true;
    node("dashboard-status").textContent = "Viewer session · " + run;
    if (!node("dashboard").hidden) showPage(true);
  } catch (error) {
    if (key !== dashboardKey) return;
    node("dashboard-status").textContent = error.message;
    node("retry-login").hidden = false;
  }
}

function updateServices(s) {
  const health = s.health || {};
  const age = health.at ? Math.max(0,Math.floor(Date.now()/1000-health.at)) : null;
  const stale = age !== null && age > 30;
  node("health-age").textContent = health.error || (age === null ? "Checking…" : "Checked " + age + "s ago");
  for (const [id,label] of Object.entries(serviceLabels)) {
    let item = node("svc-"+id);
    if (!item) {
      item = document.createElement("div"); item.id = "svc-"+id;
      for (const tag of ["strong","b","small"]) item.append(document.createElement(tag));
      node("health-grid").append(item);
    }
    const report = health.services?.[id];
    const state = stale ? "Unknown" : report?.state || "Unknown";
    item.dataset.state = state;
    item.children[0].textContent = label;
    item.children[1].textContent = state;
    item.children[2].textContent = stale ? "Sample expired" : report?.detail || "No current probe";
  }
  const available = ["Running","Completed","Viewing"].includes(s.phase) && !["view","close","stop"].includes(s.task);
  const url = s.view || "http://127.0.0.1:13003/d/fleet-live";
  const key = available ? s.run+" "+url : "";
  if (key === dashboardKey && key) return;
  if (key !== dashboardKey) {
    sessionReady = false;
    const frame = node("dashboard-frame");
    frame.removeAttribute("src"); frame.hidden = true;
  }
  dashboardKey = key;
  node("retry-login").hidden = true;
  if (!key) {
    node("dashboard-status").textContent = "Start a fleet session or load a historical view to open Grafana.";
    return;
  }
  dashboardURL = url+"?kiosk&hideLogo=true&theme=dark";
  node("dashboard-status").textContent = "Signing in to Grafana…";
  signIn(key,s.run);
}
