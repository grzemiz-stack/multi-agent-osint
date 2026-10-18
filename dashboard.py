"""Local control panel for the Multi-Agent OSINT Research System.

Run: python3 dashboard.py
Open: http://127.0.0.1:8765
Only binds to loopback; no external dependencies.
"""
import json
import threading
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from run_agents import REPORTS_DIR, run
from url_safety import normalize_url

HOST, PORT = "127.0.0.1", 8765
REPORT_DIR = Path(REPORTS_DIR)
LOCK = threading.Lock()
JOB = {"state": "idle", "target": "", "pages": 2, "started_at": None, "finished_at": None, "error": None, "run_id": None}


def list_reports():
    if not REPORT_DIR.is_dir():
        return []
    entries = []
    for path in sorted(REPORT_DIR.glob("*.json"), reverse=True):
        if path.name == "latest_report.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries.append({
                "run_id": path.stem,
                "target": data.get("target", ""),
                "created_at": data.get("created_at", ""),
                "status": data.get("status", "unknown"),
                "documents": data.get("documents", 0),
                "evidence_count": len(data.get("evidence", [])),
            })
        except (OSError, ValueError, TypeError):
            continue
    return entries[:50]


def load_report(run_id):
    if not run_id or not all(c.isascii() and (c.isalnum() or c == "_") for c in run_id):
        return None
    path = REPORT_DIR / (run_id + ".json")
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def execute(target, pages):
    try:
        report = run(target, max_pages=pages)
        with LOCK:
            JOB.update(state="completed", run_id=report.get("run_id"), error=None)
    except Exception as exc:
        with LOCK:
            JOB.update(state="failed", error=str(exc))
    finally:
        with LOCK:
            JOB["finished_at"] = datetime.now(timezone.utc).isoformat()


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Multi-Agent OSINT | Control Center</title>
<style>
:root{color-scheme:dark;--bg:#090e19;--panel:#121d30;--line:#26374d;--muted:#9eafc5;--cyan:#59d5f9;--good:#59d6a4;--bad:#ff8a91}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#e9f2ff;font:15px/1.5 system-ui,-apple-system,sans-serif}
header{padding:25px max(20px,calc((100vw - 1180px)/2));border-bottom:1px solid var(--line);background:#0e1828}
header h1{font-size:25px;margin:0}header p{color:var(--muted);margin:4px 0 0}
main{max-width:1180px;margin:auto;padding:24px 20px 65px}.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:18px}
h2{font-size:17px;margin:0 0 15px}label{display:block;font-size:13px;color:var(--muted);margin:0 0 6px}
input,select,button{font:inherit;border-radius:9px;padding:11px 12px}input,select{background:#0b1424;color:#fff;border:1px solid #354962;width:100%}
button{background:#20b7e5;color:#04101d;border:0;font-weight:700;cursor:pointer}button:disabled{opacity:.45;cursor:wait}
.controls{display:grid;grid-template-columns:1fr 130px auto;gap:10px;align-items:end}
.muted{color:var(--muted)}.small{font-size:12px}.status{font-weight:700;color:var(--cyan)}.error{color:var(--bad);overflow-wrap:anywhere}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.metric{background:#0b1424;border:1px solid var(--line);border-radius:10px;padding:13px}
.metric strong{display:block;font-size:24px;color:#fff}.metric span{color:var(--muted);font-size:12px}
.agent-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.agent{padding:13px;background:#0b1424;border:1px solid var(--line);border-radius:10px}
.agent b{display:block}.agent small{color:var(--muted)}.item{border-top:1px solid var(--line);padding:13px 0;overflow-wrap:anywhere}
.item:first-child{border-top:0}.item p{margin:6px 0}.tag{font-size:12px;padding:3px 7px;border-radius:6px;background:#24364a}
a{color:var(--cyan)}.history-button{width:100%;background:#0b1424;color:#e9f2ff;text-align:left;margin:4px 0;border:1px solid var(--line);font-weight:400}
.history-button:hover{border-color:var(--cyan)}.quote{border-left:3px solid var(--cyan);padding-left:12px;color:#b9cfe0}
@media(max-width:760px){.grid,.controls{grid-template-columns:1fr}.metrics,.agent-grid{grid-template-columns:repeat(2,1fr)}}
</style></head><body>
<header><h1>Multi-Agent OSINT <span style="color:var(--cyan)">Control Center</span></h1><p>Real research · Local Qwen · Research → Analysis → Verification → Review</p></header>
<main>
<div class="panel"><h2>Start new research</h2><form id="form" class="controls">
<div><label for="target">Public HTTPS URL</label><input id="target" type="url" placeholder="https://www.python.org" required></div>
<div><label for="pages">Pages</label><select id="pages"><option>1</option><option selected>2</option><option>3</option><option>5</option><option>10</option></select></div>
<button id="start" type="submit">Start Research</button></form><p id="job" class="muted small">Ready to start.</p></div>
<div class="panel"><h2>Overview</h2><div id="metrics" class="metrics"><div class="muted">Select a report to see metrics.</div></div></div>
<div class="panel"><h2>Agent execution</h2><div id="agents" class="agent-grid"></div></div>
<div class="grid"><div><div class="panel"><h2>Evidence &amp; verification</h2><div id="evidence" class="muted">Select a report.</div></div>
<div class="panel"><h2>Execution timeline</h2><div id="timeline" class="muted">Select a report.</div></div></div>
<div><div class="panel"><h2>Research history</h2><div id="history" class="muted">Loading…</div></div>
<div class="panel"><h2>Research details</h2><div id="details" class="muted">Select a report.</div></div></div></div>
</main><script>
const el=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let selected=null,lastJob='';
async function get(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return r.json()}
function safeLink(raw){try{let u=new URL(raw);if(u.protocol==='https:'||u.protocol==='http:')return `<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(raw)}</a>`}catch(e){}return esc(raw)}
function metrics(report){const ev=report.evidence||[];const verified=ev.filter(x=>x.status==='verified').length;const rejected=ev.filter(x=>x.status==='rejected').length;
 el('metrics').innerHTML=[[report.documents||0,'Documents'],[ev.length,'Claims'],[verified,'Verified against source'],[rejected,'Rejected']].map(([n,t])=>`<div class="metric"><strong>${esc(n)}</strong><span>${esc(t)}</span></div>`).join('')}
function render(r){selected=r.run_id;metrics(r);
 const stages=['research','analyze','verify','review'];const results=r.results||[];
 el('agents').innerHTML=stages.map(stage=>{let x=results.find(y=>y.action===stage);return `<div class="agent"><b>${esc(stage.toUpperCase())}</b><small>${x?esc(x.agent||stage)+' · '+esc(x.duration_ms)+' ms':'Not executed'}</small></div>`}).join('');
 el('evidence').innerHTML=(r.evidence||[]).map((e,i)=>`<div class="item"><span class="tag">${esc(e.status||'unknown')}</span><p><b>${i+1}. ${esc(e.fact)}</b></p><p class="quote">${esc(e.quote)}</p><p class="small">${safeLink(e.url||'')}</p><p class="muted small">${esc(e.verification_reason||'')}</p></div>`).join('')||'<p>No evidence found.</p>';
 el('timeline').innerHTML=(r.history||[]).map(x=>`<div class="item"><b>${esc(x.agent||'Agent')} · ${esc(x.action||'')}</b><p class="small muted">Iteration ${esc(x.iteration)} · ${esc(x.reason||'')}</p></div>`).join('')||'<p>No timeline.</p>';
 el('details').innerHTML=`<p><b>Target:</b> ${safeLink(r.target||'')}</p><p><b>Status:</b> ${esc(r.status)}</p><p><b>Review:</b> ${esc(r.review_decision)}</p><p><b>Source completeness:</b> ${esc(r.source_completeness)}</p><p><b>Run:</b> ${esc(r.run_id)}</p>${r.error?`<p class="error">${esc(r.error)}</p>`:''}`;
}
async function loadReport(id){try{render(await get('/api/report?id='+encodeURIComponent(id)))}catch(e){el('details').textContent='Unable to load report: '+e.message}}
async function refresh(){try{const [job,history]=await Promise.all([get('/api/status'),get('/api/reports')]);
 el('start').disabled=job.state==='running';el('job').innerHTML=`<span class="status">${esc(job.state.toUpperCase())}</span>${job.target?' · '+esc(job.target):''}${job.error?' · <span class="error">'+esc(job.error)+'</span>':''}`;
 el('history').innerHTML=history.map(x=>`<button class="history-button" data-id="${esc(x.run_id)}"><b>${esc(x.target)}</b><br><span class="small muted">${esc(x.created_at)} · ${esc(x.status)} · ${esc(x.evidence_count)} claims</span></button>`).join('')||'<p>No reports yet.</p>';
 document.querySelectorAll('[data-id]').forEach(b=>b.addEventListener('click',()=>loadReport(b.dataset.id)));
 if(job.state!=='running'&&lastJob==='running'&&history.length)await loadReport(history[0].run_id);
 else if(!selected&&history.length)await loadReport(history[0].run_id);
 lastJob=job.state;
 }catch(e){el('job').textContent='Connection problem: '+e.message}}
el('form').addEventListener('submit',async e=>{e.preventDefault();el('start').disabled=true;
 try{const r=await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target:el('target').value,pages:Number(el('pages').value)})});const d=await r.json();if(!r.ok)throw Error(d.error||'Start failed');await refresh()}catch(err){el('job').textContent='Error: '+err.message;el('start').disabled=false}});
refresh();setInterval(refresh,2500);
</script></body></html>'''


class Dashboard(BaseHTTPRequestHandler):
    def respond_json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            payload = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif parsed.path == "/api/status":
            with LOCK:
                self.respond_json(dict(JOB))
        elif parsed.path == "/api/reports":
            self.respond_json(list_reports())
        elif parsed.path == "/api/report":
            run_id = parse_qs(parsed.query).get("id", [""])[0]
            report = load_report(run_id)
            self.respond_json(report if report is not None else {"error": "Report not found"}, 200 if report is not None else 404)
        else:
            self.respond_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path != "/api/start":
            return self.respond_json({"error": "Not found"}, 404)
        # Protect against cross-origin form submissions to the localhost service.
        origin = self.headers.get("Origin")
        if origin not in (None, f"http://{HOST}:{PORT}"):
            return self.respond_json({"error": "Origin not allowed"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 4096:
                raise ValueError("Invalid request size")
            body = json.loads(self.rfile.read(length))
            target = normalize_url(body.get("target", ""))
            pages = int(body.get("pages", 2))
            if pages not in (1, 2, 3, 5, 10):
                raise ValueError("Pages must be 1, 2, 3, 5, or 10")
        except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            return self.respond_json({"error": str(exc)}, 400)
        with LOCK:
            if JOB["state"] == "running":
                return self.respond_json({"error": "Research already running"}, 409)
            JOB.update(state="running", target=target, pages=pages, started_at=datetime.now(timezone.utc).isoformat(), finished_at=None, error=None, run_id=None)
        threading.Thread(target=execute, args=(target, pages), daemon=True).start()
        self.respond_json({"ok": True, "state": "running"}, 202)


if __name__ == "__main__":
    print(f"OSINT Control Center: http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Dashboard).serve_forever()
