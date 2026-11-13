"""Exercise the real browser scripts with a small deterministic DOM and clock."""

# The embedded JavaScript is executed as-is by Node.
# ruff: noqa: E501

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

PROBE = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert/strict');
class Element {
  constructor() { this.children=[]; this.dataset={}; this.style={}; this.textContent=''; this.className=''; this.value=''; }
  set textContent(value) { this._text=String(value); }
  get textContent() { return this._text; }
  append(child) { child.parent=this; this.children.push(child); }
  replaceChildren(...children) { this.children=[]; for (const child of children) this.append(child); }
  remove() { this.parent.children=this.parent.children.filter(child=>child!==this); }
}
function environment(path) {
  const html=fs.readFileSync(path,'utf8'); const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const dom={health:new Element(),rows:new Element(),login:new Element(),token:new Element()};
  const hooks={}; const queue=[]; let clock=0;
  const context={document:{querySelector:s=>dom[s.slice(1)],createElement:()=>new Element(),
      addEventListener:(name,fn)=>{hooks[name]=fn;}},
    fetch:async()=>{const value=queue.shift(); if(value instanceof Error)throw value;
      return {ok:value.status===200,status:value.status,json:async()=>value.body};},
    AbortSignal:{timeout:()=>({})},performance:{now:()=>clock},setTimeout:()=>0,
    console,Map,Set,Number,String,Error};
  vm.createContext(context);vm.runInContext(script,context);
  vm.runInContext("token='test-token';generation=1",context);
  return {dom,hooks,queue,context,setClock:v=>{clock=v;},
    async poll(body,status=200){queue.push({status,body});await context.poll(1);},
    async fail(){queue.push(new Error('offline'));await context.poll(1);}};
}
const live=(id,age,delay)=>({format_version:'flink-live-state-v1',run_id:'run',collection_ok:true,
  vehicles:[{vehicle_id:'v1',event_id:id,source_timestamp:'2026-01-01T00:00:00Z',
    payload:{voltage_v:12,current_a:0,remaining_fraction:0},live_age_seconds:age,admission_to_live_ms:delay}]});
const links=(status,ok=true,epoch='epoch-1')=>({format_version:'live-link-state-v1',
  receiver_epoch:epoch,monitor_ok:ok,timeout_seconds:3,
  vehicles:[{vehicle_id:'v1',status,age_seconds:0.2}]});
async function main() {
  const page=environment(process.argv[1]);
  await page.poll(live('a',null,null));
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Replayed or unknown');
  await page.poll(live('b',0.1,100));
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Fresh');
  assert.equal(page.dom.rows.children[0].children[3].textContent,'0');
  await page.poll(live('b',3.0,100));
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Stale');
  await page.poll(live('c',0.2,2500));
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Updates resumed · delayed');
  assert.equal(page.dom.rows.children[0].children[6].textContent,'Slow · 2500 ms');
  page.setClock(4000);await page.poll(live('c',0.5,2500));
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Delayed');
  await page.fail();
  assert.match(page.dom.health.textContent,/unavailable/);
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Unknown');
  await page.poll(live('c',4,null));
  assert.match(page.dom.health.textContent,/reconnected/);
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Stale');
  assert.equal(page.dom.rows.children[0].children[6].textContent,'Unknown');
  await page.poll(live('d',0.1,null));
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Updates resumed');
  page.hooks.visibilitychange();
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Unknown');
  await page.poll(null,401);assert.match(page.dom.health.textContent,/token rejected/);
  await page.poll({...live('d',0.1,100),vehicles:[]});
  assert.match(page.dom.health.textContent,/unavailable/);
  const invalid=live('d',0.1,100);delete invalid.vehicles[0].event_id;
  await page.poll(invalid);
  assert.equal(page.dom.rows.children[0].children[1].textContent,'Waiting for data');
  await page.poll({...live('d',0.1,100),vehicles:[invalid.vehicles[0],invalid.vehicles[0]]});
  assert.match(page.dom.health.textContent,/unavailable/);

  const watch=environment(process.argv[2]);
  await watch.poll(links('connected'));assert.equal(watch.dom.rows.children[0].children[1].textContent,'Connected');
  await watch.poll(links('lost'));assert.equal(watch.dom.rows.children[0].children[1].textContent,'Connection lost');
  await watch.poll(links('connected'));assert.equal(watch.dom.rows.children[0].children[1].textContent,'Reconnected');
  watch.setClock(4000);await watch.poll(links('connected'));assert.equal(watch.dom.rows.children[0].children[1].textContent,'Connected');
  await watch.poll(links('lost'));await watch.poll(links('unknown',false));
  assert.equal(watch.dom.rows.children[0].children[1].textContent,'Unknown');
  await watch.poll(links('connected'));assert.equal(watch.dom.rows.children[0].children[1].textContent,'Connected');
  await watch.poll(links('lost'));await watch.poll(links('connected',true,'epoch-2'));
  assert.equal(watch.dom.rows.children[0].children[1].textContent,'Connected');
  await watch.fail();assert.equal(watch.dom.rows.children[0].children[1].textContent,'Unknown');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
"""


@pytest.mark.skipif(
    NODE is None, reason="Node.js is needed to exercise browser scripts"
)
def test_live_pages_report_freshness_outage_and_recovery() -> None:
    result = subprocess.run(
        [
            str(NODE),
            "-e",
            PROBE,
            str(ROOT / "runtime/continuous/live.html"),
            str(ROOT / "runtime/continuous/link_watch.html"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
