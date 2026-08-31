import json, os, threading, time, collections, random, uuid, urllib.request, urllib.parse
from flask import Flask, request, jsonify, session, redirect, url_for
import logging
from functools import wraps
from instagrapi import Client

app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET_KEY", "SINISTERS-SX7-PANEL-SECRET")

PANEL_USERNAME = "SINISTERS"
PANEL_PASSWORD = "Ayan@2003"

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("panel_logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Login required"}), 401
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)
    return wrapped

LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>SINISTERS SX7</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100vh;display:grid;place-items:center;background:radial-gradient(900px 500px at 70% -10%,#003f3a44,transparent 60%),radial-gradient(700px 500px at 10% 20%,#004b5740,transparent 65%),#05090b;color:#eef2ff;font-family:Inter,system-ui,sans-serif}
.login{width:min(390px,92vw);padding:30px;border:1px solid #193238;border-radius:16px;background:linear-gradient(145deg,#0b1518,#090d18);box-shadow:0 25px 80px #0008}
.brand{text-align:center;margin-bottom:25px}
.brand-mark{width:50px;height:50px;margin:0 auto 12px;border-radius:14px;background:linear-gradient(135deg,#14b8a6,#22d3ee);display:grid;place-items:center;color:#fff;font:800 24px Inter;box-shadow:0 0 25px #14b8a655}
h1{font:700 21px 'Share Tech Mono';letter-spacing:2px;color:#99f6e4}
p{font-size:10px;color:#7f9aa3;margin-top:5px;letter-spacing:1px}
.field{margin-top:14px}
label{display:block;font-size:9px;color:#7f9aa3;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}
input{width:100%;padding:11px 12px;background:#080c15;border:1px solid #1a353b;color:#e2e8f0;border-radius:8px;outline:none;font:11px 'Share Tech Mono'}
input:focus{border-color:#0e7490;box-shadow:0 0 0 3px #0e74901a}
button{width:100%;margin-top:18px;padding:11px;border:1px solid #67e8f9;border-radius:8px;background:linear-gradient(135deg,#0f766e,#14b8a6);color:#fff;cursor:pointer;font:11px 'Share Tech Mono';letter-spacing:1px}
.error{margin-top:12px;text-align:center;color:#f87171;font-size:10px;min-height:14px}
</style>
</head>
<body>
<div class="login">
  <div class="brand">
    <div class="brand-mark">S</div>
    <h1>SINISTERS SX7</h1>
    <p>SECURE PANEL LOGIN</p>
  </div>
  <form method="POST" action="/login">
    <div class="field"><label>Username</label><input name="username" autocomplete="username" required autofocus></div>
    <div class="field"><label>Password</label><input type="password" name="password" autocomplete="current-password" required></div>
    <button type="submit">LOGIN</button>
    <div class="error">{{ error }}</div>
  </form>
</div>
</body>
</html>"""

DATA_FILE = "data_v2.json"
data_lock = threading.Lock()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f: return json.load(f)
    return {"accounts": {}}

def save_data(d):
    with open(DATA_FILE, "w") as f: json.dump(d, f, indent=2)

bot_threads = {}
bot_stop    = {}
bot_status  = {}
ig_clients  = {}
bot_logs    = {}

def log(acc_id, msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    if acc_id not in bot_logs:
        bot_logs[acc_id] = collections.deque(maxlen=300)
    bot_logs[acc_id].append(line)

import urllib.parse
import urllib.request

def decode_session(session_id):
    if not session_id: return session_id
    try: return urllib.parse.unquote(session_id)
    except Exception: return session_id

def persist_client_settings(acc_id, cl):
    """Persist the full instagrapi client settings for this account.

    This keeps device identifiers, cookies and authorization state together
    instead of relying only on the browser sessionid.
    """
    try:
        settings = cl.get_settings()
        if not settings:
            return
        with data_lock:
            d = load_data()
            if acc_id in d.get("accounts", {}):
                d["accounts"][acc_id]["session_settings"] = settings
                save_data(d)
    except Exception:
        pass

def get_client(acc_id, session_id, proxy=None, csrf_token=None):
    if acc_id in ig_clients:
        return ig_clients[acc_id]

                                                               
    if 'fetch_temp' in ig_clients:
        cl = ig_clients.pop('fetch_temp')
        ig_clients[acc_id] = cl
        persist_client_settings(acc_id, cl)
        return cl

                                                                           
                                                                             
                                          
    saved_settings = None
    try:
        with data_lock:
            d = load_data()
            saved_settings = d.get("accounts", {}).get(acc_id, {}).get("session_settings")
    except Exception:
        saved_settings = None

    if saved_settings:
        try:
            cl = Client()
            cl.set_settings(saved_settings)
            if proxy:
                cl.set_proxy(proxy)
                                                         
            cl.account_info()
            ig_clients[acc_id] = cl
            return cl
        except Exception:
                                                                             
                                                                      
            pass

    cl = Client()
    if proxy:
        cl.set_proxy(proxy)
    session_id = decode_session(session_id)
    cl.login_by_sessionid(session_id)
    ig_clients[acc_id] = cl
    persist_client_settings(acc_id, cl)
    return cl

def extract_thread_id(s):
    s = s.strip()
    if "instagram.com/direct/t/" in s:
        return s.rstrip("/").split("/")[-1]
    return s

def nc_rename(cl, thread_id, title):
    try:
        result = cl.direct_thread_update_title(thread_id, title)
        if result is not False:
            return True, None
    except Exception: pass
    try:
        cl.private_request(
            f"direct_v2/threads/{thread_id}/update_title/",
            data={"title": title, "_uuid": cl.uuid, "_uid": str(cl.user_id), "_csrftoken": cl.token}
        )
        return True, None
    except Exception: pass
    try:
        thread = cl.direct_thread(thread_id)
        r = thread.update_title(title)
        if r is not False:
            return True, None
    except Exception: pass
    try:
        cl.private_request(
            f"direct_v2/threads/{thread_id}/update_title/",
            data={"title": title, "_uuid": cl.uuid, "_uid": str(cl.user_id), "use_unified_inbox": "true"}
        )
        return True, None
    except Exception as e4:
        return False, str(e4)

def get_thread_title(cl, thread_id):
    try:
        thread = cl.direct_thread(int(thread_id))
        return (thread.thread_title or "").strip()
    except Exception:
        return None

def bot_worker(acc_id, acc, stop_event):
    session_id = acc["session_id"]
    proxy = acc.get("proxy", "").strip() or None
    csrf_token = acc.get("csrf_token", "").strip() or None
               
    raw_groups = [extract_thread_id(g) for g in acc.get("groups", "").split("\n") if g.strip()]
    groups = raw_groups[:5]
    titles = [t.strip() for t in acc.get("nc_titles", "").split(",") if t.strip()]
    messages = [m.strip() for m in acc.get("messages", "").split("---MSG---") if m.strip()]
    if not messages:
        single = acc.get("message", "").strip()
        if single: messages = [single]

            
    msg_delay_min  = float(acc.get("msg_delay_min", 2))
    msg_delay_max  = float(acc.get("msg_delay_max", 5))

                               
    cooldown_after_msgs = int(acc.get("cooldown_after", 0))                
    cooldown_dur        = float(acc.get("cooldown_dur", 5))           

                                             
    nc_every_msgs = int(acc.get("nc_every_msgs", 0))

    bot_logs[acc_id] = collections.deque(maxlen=300)
    bot_status[acc_id] = {
        "running": True, "sent": 0, "failed": 0,
        "nc_done": 0, "nc_failed": 0, "nc_skipped": 0,
        "gcs_done": 0, "total_gcs": len(groups),
        "last_action": "Logging in...", "started_at": time.time(),
        "cooldown": False, "cooldown_end": 0,
        "reauth_attempted": False
    }

    log(acc_id, "⚡ Starting bot...")
    log(acc_id, f"📋 GCs: {len(groups)} | Titles: {len(titles)} | Messages: {len(messages)}")
    log(acc_id, f"⏱ Msg delay: {msg_delay_min}-{msg_delay_max}s")
    if cooldown_after_msgs > 0:
        log(acc_id, f"😴 Cooldown: every {cooldown_after_msgs} messages → {cooldown_dur} min pause")

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(get_client, acc_id, session_id, proxy, csrf_token)
            cl = future.result(timeout=30)
        log(acc_id, f"✅ Logged in successfully{' (proxy)' if proxy else ''}")
        bot_status[acc_id]["last_action"] = "Logged in ✓"
    except concurrent.futures.TimeoutError:
        log(acc_id, "❌ Login timed out after 30s — check session ID")
        bot_status[acc_id]["running"] = False
        bot_status[acc_id]["last_action"] = "Login timed out"
        return
    except Exception as e:
        log(acc_id, f"❌ Login failed: {e}")
        bot_status[acc_id]["running"] = False
        bot_status[acc_id]["last_action"] = f"Login failed: {e}"
        return

    title_idx     = 0
    msg_idx       = 0
    msgs_since_cd = 0                                     
    msgs_since_nc = 0                               

    def do_nc_for_all():
        nonlocal title_idx
        if not titles: return
        t = titles[title_idx % len(titles)]
        for thread_id in groups:
            if stop_event.is_set(): break
            bot_status[acc_id]["last_action"] = f"Checking NC → {thread_id}"
            try:
                current_title = get_thread_title(cl, thread_id)
            except Exception:
                current_title = None
            if current_title is not None and current_title.strip() == t.strip():
                log(acc_id, f"⏭ NC skip (already '{t}') → {thread_id}")
                bot_status[acc_id]["nc_skipped"] += 1
            else:
                bot_status[acc_id]["last_action"] = f"NC → {t}"
                try:
                    ok, err = nc_rename(cl, int(thread_id), t)
                    if ok:
                        bot_status[acc_id]["nc_done"] += 1
                        persist_client_settings(acc_id, cl)
                        log(acc_id, f"✅ NC done [{t}] → {thread_id}")
                    else:
                        bot_status[acc_id]["nc_failed"] += 1
                        log(acc_id, f"❌ NC failed → {thread_id}: {err}")
                except Exception as e:
                    bot_status[acc_id]["nc_failed"] += 1
                    log(acc_id, f"❌ NC error → {thread_id}: {e}")
        title_idx += 1

                     
    log(acc_id, "✏️ Initial NC...")
    do_nc_for_all()

    while not stop_event.is_set():
        bot_status[acc_id]["gcs_done"] = 0

                             
        if titles and nc_every_msgs > 0 and msgs_since_nc >= nc_every_msgs:
            log(acc_id, f"✏️ NC after {nc_every_msgs} messages...")
            do_nc_for_all()
            msgs_since_nc = 0

        for thread_id in groups:
            if stop_event.is_set(): break

                          
            message = messages[msg_idx % len(messages)] if messages else ""
            bot_status[acc_id]["last_action"] = f"Sending → {thread_id}"
            try:
                cl.direct_send(message, thread_ids=[int(thread_id)])
                bot_status[acc_id]["sent"] += 1
                persist_client_settings(acc_id, cl)
                msgs_since_cd += 1
                msgs_since_nc += 1
                log(acc_id, f"✅ Sent → {thread_id}")
            except Exception as e:
                bot_status[acc_id]["failed"] += 1
                err_str = str(e)
                status_code = None
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        resp_json = e.response.json()
                        ig_msg = resp_json.get('message') or resp_json.get('error_title') or resp_json.get('feedback_message') or err_str
                        status_code = e.response.status_code
                        err_str = f"{ig_msg} (status {status_code})"
                    except Exception:
                        status_code = e.response.status_code
                        err_str = f"{status_code}: {e.response.text[:120]}"
                log(acc_id, f"❌ Send failed → {thread_id}: {err_str}")

                                                                          
                                                              
                if status_code == 403 or "user_has_logged_out" in err_str or "login_required" in err_str:
                    if bot_status[acc_id].get("reauth_attempted"):
                        log(acc_id, "🛑 Session is still invalid — stopping (no retry loop)")
                        bot_status[acc_id]["running"] = False
                        bot_status[acc_id]["last_action"] = "Session expired — re-auth required"
                        return
                    bot_status[acc_id]["reauth_attempted"] = True
                    log(acc_id, "🔄 Session expired — attempting one re-auth...")
                    bot_status[acc_id]["last_action"] = "Re-authenticating..."
                    try:
                        ig_clients.pop(acc_id, None)
                                                                               
                                                                              
                        with data_lock:
                            d = load_data()
                            if acc_id in d.get("accounts", {}):
                                d["accounts"][acc_id].pop("session_settings", None)
                                save_data(d)
                        cl = get_client(acc_id, session_id, proxy, csrf_token)
                        bot_status[acc_id]["reauth_attempted"] = False
                        log(acc_id, "✅ Re-auth successful — resuming")
                        bot_status[acc_id]["last_action"] = "Re-auth done ✓"
                    except Exception as re_err:
                        log(acc_id, f"❌ Re-auth failed: {re_err}")
                        bot_status[acc_id]["running"] = False
                        bot_status[acc_id]["last_action"] = "Session expired — re-auth required"
                        return
                else:
                                                                  
                    log(acc_id, "⏳ Error cooldown — 5 min pause...")
                    bot_status[acc_id]["last_action"] = "Error cooldown 5 min..."
                    bot_status[acc_id]["cooldown"] = True
                    for _ in range(300):
                        if stop_event.is_set(): break
                        time.sleep(1)
                    bot_status[acc_id]["cooldown"] = False
                    log(acc_id, "✅ Error cooldown done — resuming")

            msg_idx += 1
            bot_status[acc_id]["gcs_done"] += 1

            if stop_event.is_set(): break
            delay = random.uniform(msg_delay_min, msg_delay_max)
            log(acc_id, f"💤 Delay: {delay:.1f}s")
            time.sleep(delay)

        bot_status[acc_id]["last_action"] = "Loop complete ✓"
        if cooldown_after_msgs > 0 and msgs_since_cd >= cooldown_after_msgs:
            dur_secs = cooldown_dur * 60
            log(acc_id, f"😴 Cooldown after {cooldown_after_msgs} messages — {cooldown_dur} min pause...")
            bot_status[acc_id]["cooldown"] = True
            bot_status[acc_id]["cooldown_end"] = time.time() + dur_secs
            elapsed = 0
            while elapsed < dur_secs and not stop_event.is_set():
                time.sleep(1)
                elapsed += 1
            bot_status[acc_id]["cooldown"] = False
            bot_status[acc_id]["cooldown_end"] = 0
            msgs_since_cd = 0
            log(acc_id, "✅ Cooldown done — resuming...")

        bot_status[acc_id]["last_action"] = "Loop complete ✓"

    log(acc_id, "🛑 Bot stopped")
    bot_status[acc_id]["running"] = False
    bot_status[acc_id]["last_action"] = "Stopped"

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>SINISTERS SX7</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet"/>
<style>
:root{
 --bg:#05090b;--bg2:#081113;--card:#0b1518;--card2:#0d1a1d;--line:#193238;
 --purple:#14b8a6;--purple2:#06b6d4;--cyan:#22d3ee;--blue:#38bdf8;
 --green:#22c55e;--red:#ef4444;--amber:#f97316;--text:#eef2ff;--muted:#7f9aa3;
}
*{box-sizing:border-box;margin:0;padding:0}html{scroll-behavior:smooth}
body{min-height:100vh;background:radial-gradient(900px 500px at 70% -10%,#003f3a44,transparent 60%),radial-gradient(700px 500px at 10% 20%,#004b5740,transparent 65%),var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif}
button,input,textarea{font:inherit}.shell{display:flex;min-height:100vh}
.sidebar{width:190px;flex:none;position:fixed;left:0;top:0;bottom:0;padding:18px 12px;background:linear-gradient(180deg,#080b14f2,#090c15f8);border-right:1px solid var(--line);z-index:100;display:flex;flex-direction:column}
.brand{display:flex;align-items:center;gap:10px;padding:8px 10px 22px}.brand-mark{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,var(--purple),var(--cyan));display:grid;place-items:center;color:#fff;font-weight:800;box-shadow:0 0 25px #14b8a655}.brand-name{font:700 20px 'Share Tech Mono';letter-spacing:2px;color:#99f6e4}.brand-sub{font-size:8px;letter-spacing:3px;color:#94a3b8;margin-top:2px}
.nav{display:flex;flex-direction:column;gap:5px}.nav-item{display:flex;align-items:center;gap:10px;padding:10px 11px;border-radius:9px;color:#9aa5bd;font-size:12px;text-decoration:none;border:1px solid transparent}.nav-item:hover,.nav-item.active{color:#fff;background:linear-gradient(90deg,#14b8a61e,#22d3ee08);border-color:#0f766e44}.nav-icon{width:20px;text-align:center;color:#2dd4bf;font-size:15px}.side-bottom{margin-top:auto;border-top:1px solid var(--line);padding-top:14px}.side-owner{font-size:10px;color:#64748b;text-align:center;letter-spacing:2px}.side-owner strong{display:block;color:#67e8f9;font-size:15px;letter-spacing:1px;margin-bottom:3px}
.main{margin-left:190px;width:calc(100% - 190px);padding:20px 24px 34px;max-width:1500px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:18px}.top-title h1{font-size:22px;letter-spacing:.5px}.top-title p{font-size:11px;color:var(--muted);margin-top:3px}.top-actions{display:flex;gap:8px;align-items:center}.system-pill{padding:8px 12px;border:1px solid #04785766;background:#0a1a1222;border-radius:9px;color:#34d399;font:10px 'Share Tech Mono'}
.btn{border:1px solid var(--line);background:#0b1518;color:#dbe4ff;border-radius:7px;padding:8px 12px;cursor:pointer;font:600 10px 'Share Tech Mono';letter-spacing:1px;transition:.18s}.btn:hover{border-color:#0f766e;box-shadow:0 0 18px #14b8a622}.btn-add{background:linear-gradient(135deg,#0f766e,#14b8a6);border-color:#67e8f9;color:#fff}.btn-start{border-color:#047857;color:#34d399}.btn-stop{border-color:#991b1b;color:#f87171}.btn-logs{border-color:#155e75;color:#67e8f9}.btn-edit{border-color:#334155;color:#7dd3fc}.btn-del{border-color:#991b1b;color:#f87171}.btn-collapse{background:transparent;border:0;color:#64748b;cursor:pointer;padding:8px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}.stat-card{background:linear-gradient(145deg,#0d191c,#081113);border:1px solid var(--line);border-radius:11px;padding:14px 15px;display:flex;align-items:center;gap:12px;box-shadow:0 12px 35px #0004}.stat-icon{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:20px;background:#14b8a61c;color:#99f6e4;border:1px solid #14b8a644}.stat-card:nth-child(2) .stat-icon{background:#22c55e16;color:#34d399;border-color:#22c55e44}.stat-card:nth-child(3) .stat-icon{background:#22d3ee16;color:#67e8f9;border-color:#22d3ee44}.stat-card:nth-child(4) .stat-icon{background:#ef444416;color:#f87171;border-color:#ef444444}.stat-label{font-size:10px;color:#94a3b8;letter-spacing:1px;text-transform:uppercase}.stat-number{font:700 22px 'Share Tech Mono';margin-top:3px}.stat-sub{font-size:9px;color:#64748b;margin-top:2px}
.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:8px 0 10px}.panel-head h2{font-size:15px}.panel-head p{font-size:10px;color:var(--muted)}.panel-tools{display:flex;gap:8px}.search{width:250px;background:#090d18;border:1px solid var(--line);color:#e2e8f0;padding:9px 11px;border-radius:8px;outline:none;font-size:11px}.search:focus{border-color:#0e7490}
#accounts-wrap{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;align-items:start}.acc-card{background:linear-gradient(145deg,#0b1518,#090d18);border:1px solid #1a343a;border-radius:12px;overflow:hidden;min-width:0;box-shadow:0 15px 40px #0005;transition:.18s}.acc-card:hover{border-color:#0e7490;transform:translateY(-1px)}.acc-header{display:flex;align-items:center;gap:9px;padding:11px 12px;background:#0c111e;cursor:pointer}.status-dot{width:8px;height:8px;border-radius:50%;flex:none}.dot-on{background:var(--green);box-shadow:0 0 10px #22c55eaa}.dot-off{background:#64748b}.dot-cooldown{background:var(--amber);box-shadow:0 0 10px #f97316aa}.acc-name{font-weight:600;font-size:12px;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.acc-runtime{font:10px 'Share Tech Mono';color:#64748b}.acc-btns{display:flex;gap:5px;margin-left:auto}.acc-btns .btn{padding:6px 8px;font-size:9px}
.stats-row{display:grid;grid-template-columns:repeat(5,1fr);background:#090d16;border-top:1px solid var(--line)}.stat{padding:9px 4px;text-align:center;border-right:1px solid var(--line)}.stat:last-child{border-right:0}.stat-val{font:700 16px 'Share Tech Mono'}.stat-lbl{font-size:8px;color:#64748b;letter-spacing:.7px;margin-top:3px}.c-green{color:#34d399}.c-red{color:#f87171}.c-amber{color:#fb923c}.c-purple{color:#67e8f9}.c-blue{color:#67e8f9}
.gc-row{padding:9px 11px;border-top:1px solid var(--line);display:flex;gap:6px;flex-wrap:wrap;align-items:center}.gc-label,.info-key{font-size:8px;color:#64748b;letter-spacing:1px;text-transform:uppercase}.gc-pill{font:9px 'Share Tech Mono';color:#f0abfc;background:#06b6d412;border:1px solid #06b6d433;padding:4px 6px;border-radius:5px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.info-row{padding:9px 11px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:7px}.info-item{display:grid;grid-template-columns:70px 1fr;gap:6px;font-size:10px}.info-val{color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.last-action{padding:9px 11px;border-top:1px solid var(--line);font:10px 'Share Tech Mono';color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.last-action span{color:#cbd5e1}.log-panel{display:none;border-top:1px solid var(--line);background:#05070d}.log-panel.open{display:block}.log-header{display:flex;justify-content:space-between;padding:7px 10px;border-bottom:1px solid var(--line)}.log-title{font:9px 'Share Tech Mono';color:#64748b;letter-spacing:1px}.log-live{font-size:9px;color:#34d399}.log-box{height:180px;overflow:auto;padding:8px;font:9px/1.6 'Share Tech Mono';color:#78939a}.log-line.ok{color:#34d399}.log-line.err{color:#f87171}.log-line.warn{color:#fb923c}.log-line.info{color:#67e8f9}.log-line.round{color:#22d3ee}
.empty{grid-column:1/-1;text-align:center;padding:80px 20px;color:#64748b;border:1px dashed #18343a;border-radius:12px;background:#090d16}.empty-icon{font-size:36px;opacity:.5;margin-bottom:10px}.empty-text{font:12px 'Share Tech Mono';letter-spacing:2px}
.bottom-grid{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:12px;margin-top:18px}.mini-panel{background:linear-gradient(145deg,#0b1518,#090d18);border:1px solid var(--line);border-radius:11px;padding:14px}.mini-title{font-size:12px;font-weight:600;margin-bottom:12px}.mini-line{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #14282d;font-size:10px}.mini-line:last-child{border-bottom:0}.mini-key{color:#64748b}.mini-val{color:#cbd5e1}.quick{display:flex;gap:7px;flex-wrap:wrap}.quick .btn{flex:1;min-width:90px}

.modal-overlay{display:none;position:fixed;inset:0;background:#02040bdd;backdrop-filter:blur(9px);z-index:1000;align-items:center;justify-content:center}.modal-overlay.open{display:flex}.modal{background:#0b101c;border:1px solid #0e7490;border-radius:13px;padding:24px;width:680px;max-width:96vw;max-height:92vh;overflow-y:auto;box-shadow:0 30px 100px #000}.modal::-webkit-scrollbar{width:4px}.modal::-webkit-scrollbar-thumb{background:#155e75}.modal-title{font:18px 'Share Tech Mono';color:#99f6e4;letter-spacing:2px;margin-bottom:20px;border-bottom:1px solid var(--line);padding-bottom:12px}.form-section{margin-bottom:18px}.form-section-title{font-size:10px;color:var(--cyan);letter-spacing:1.7px;text-transform:uppercase;margin-bottom:9px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:11px}.form-group{display:flex;flex-direction:column;gap:5px}.form-group.full{grid-column:1/-1}label{font-size:9px;color:#7f9aa3;letter-spacing:1px;text-transform:uppercase}input,textarea,select{background:#080c15;border:1px solid #1a353b;color:#e2e8f0;padding:9px 10px;font:11px 'Share Tech Mono';outline:none;width:100%;border-radius:7px}input:focus,textarea:focus{border-color:#0e7490}textarea{resize:vertical;min-height:70px}.hint{font-size:9px;color:#64748b}.fetch-row{display:flex;gap:9px;align-items:flex-end}.btn-fetch{background:#111827;border:1px solid #0891b2;color:#67e8f9;padding:9px 12px;border-radius:7px;cursor:pointer;font:10px 'Share Tech Mono'}.gc-picker{margin-top:9px;display:none}.gc-picker-title{font-size:9px;color:#64748b;margin-bottom:7px;text-transform:uppercase}.gc-list{display:flex;flex-direction:column;gap:5px;max-height:190px;overflow:auto}.gc-item{display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid #1a353b;background:#090d16;border-radius:7px;cursor:pointer}.gc-item:hover,.gc-item.selected{border-color:#0e7490;background:#151027}.gc-item input[type=checkbox]{width:auto}.gc-item-name{font:10px 'Share Tech Mono';flex:1}.gc-item-id{font-size:8px;color:#64748b}.gc-count{font:9px 'Share Tech Mono';color:#fb923c;margin-top:5px}.msgs-wrap{display:flex;flex-direction:column;gap:7px}.msg-row{display:flex;gap:7px}.msg-row textarea{flex:1}.btn-icon{background:#0a0e18;border:1px solid #1a353b;color:#64748b;padding:8px 10px;border-radius:6px;cursor:pointer}.btn-add-msg{margin-top:7px;background:transparent;border:1px dashed #5b3ba3;color:#67e8f9;padding:7px 10px;border-radius:7px;cursor:pointer;font:10px 'Share Tech Mono'}.modal-footer{display:flex;justify-content:flex-end;gap:8px;border-top:1px solid var(--line);padding-top:15px}.btn-save{background:linear-gradient(135deg,#0f766e,#14b8a6);border:1px solid #67e8f9;color:#fff;padding:10px 24px;border-radius:7px;cursor:pointer;font:11px 'Share Tech Mono';letter-spacing:1px}.btn-cancel{background:transparent;border:1px solid #475569;color:#94a3b8;padding:10px 18px;border-radius:7px;cursor:pointer;font:10px 'Share Tech Mono'}
@media(max-width:1100px){#accounts-wrap{grid-template-columns:repeat(2,minmax(0,1fr))}.stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:760px){.sidebar{width:58px;padding:10px 7px}.brand{justify-content:center;padding:7px 0 18px}.brand-name,.brand-sub,.nav-label,.side-bottom{display:none}.brand-mark{width:36px;height:36px}.nav-item{justify-content:center;padding:10px 0}.nav-icon{width:auto}.main{margin-left:58px;width:calc(100% - 58px);padding:12px 10px 24px}.topbar{align-items:flex-start}.top-title h1{font-size:18px}.system-pill{display:none}.stats{grid-template-columns:repeat(2,1fr);gap:8px}.stat-card{padding:10px}.stat-icon{width:34px;height:34px}.stat-number{font-size:18px}.panel-head{align-items:stretch;flex-direction:column}.search{width:100%}.panel-tools{width:100%}.panel-tools .btn-add{flex:1}#accounts-wrap{grid-template-columns:1fr}.acc-btns{flex-wrap:wrap}.acc-btns .btn{padding:6px 7px}.bottom-grid{grid-template-columns:1fr}.form-grid{grid-template-columns:1fr}.form-group.full{grid-column:auto}.fetch-row{align-items:stretch;flex-direction:column}.modal{padding:16px}}

.tg-section{margin-top:18px}.tg-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:12px}.tg-card{min-height:150px}.tg-list{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.tg-bot{border:1px solid var(--line);background:linear-gradient(145deg,#0b1015,#080b10);border-radius:12px;padding:14px}.tg-bot-head{display:flex;align-items:center;gap:10px}.tg-dot{width:9px;height:9px;border-radius:50%;background:#64748b}.tg-dot.on{background:#22c55e;box-shadow:0 0 10px #22c55e99}.tg-name{font:14px 'Share Tech Mono';color:#99f6e4;flex:1}.tg-meta{font-size:10px;color:#64748b}.tg-actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.tg-users-list{margin-top:10px;color:#94a3b8;font:11px 'Share Tech Mono';line-height:1.8}.tg-token{color:#64748b;font:10px 'Share Tech Mono';margin-top:7px}.tg-empty{border:1px dashed #334155;padding:20px;border-radius:10px;text-align:center;color:#64748b}.tg-modal-note{font-size:10px;color:#64748b;margin-top:5px}@media(max-width:760px){.tg-grid,.tg-list{grid-template-columns:1fr}}

.tg-frame-wrap{width:100%;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#050505;box-shadow:0 18px 50px #0006}
.tg-frame{display:block;width:100%;height:860px;border:0;background:#050505}
@media(max-width:760px){.tg-frame{height:calc(100vh - 120px);min-height:720px}}

:root{--uma-bg:#070910;--uma-panel:#0c101a;--uma-panel-2:#101522;--uma-line:#202a3a;--uma-accent:#8b5cf6;--uma-accent-2:#22d3ee;--uma-text:#eef2ff;--uma-muted:#8d99ad}
html{background:var(--uma-bg)!important}
body{background:radial-gradient(900px 420px at 8% -5%,rgba(139,92,246,.13),transparent 55%),radial-gradient(700px 360px at 95% 0%,rgba(34,211,238,.08),transparent 52%),linear-gradient(180deg,#070910,#05070c)!important;color:var(--uma-text)!important}
.sidebar,.topbar,.panel,.stat-card,.acc-card,.tg-card,.tg-bot,.gc-picker,.form-section{background:linear-gradient(145deg,rgba(14,19,30,.98),rgba(8,11,18,.98))!important;border-color:rgba(139,92,246,.20)!important;box-shadow:0 12px 32px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.025)!important}
.topbar{backdrop-filter:blur(14px);border-bottom-color:rgba(139,92,246,.22)!important}
.stat-card,.acc-card,.tg-card,.tg-bot,.form-section{border-radius:16px!important}
.btn-add,.btn-save{background:linear-gradient(135deg,#6d28d9,#8b5cf6)!important;border-color:rgba(196,181,253,.35)!important;box-shadow:0 8px 22px rgba(124,58,237,.20)!important}
.btn-fetch,.btn-logs,.btn-edit{border-color:rgba(139,92,246,.38)!important;color:#c4b5fd!important;background:rgba(139,92,246,.045)!important}
input,textarea,select{background:#080c13!important;border-color:#253247!important;color:#eef2ff!important;border-radius:12px!important}
input::placeholder,textarea::placeholder{color:#66738a!important}
input:focus,textarea:focus,select:focus{border-color:#8b5cf6!important;box-shadow:0 0 0 3px rgba(139,92,246,.10),0 0 18px rgba(139,92,246,.07)!important}
button{transition:transform .16s ease,box-shadow .16s ease,background .16s ease}
button:active{transform:translateY(1px)}
.badge,.status,.pill{border-radius:999px!important}

</style>
</head>
<body>
<div class="shell">
<aside class="sidebar">
  <div class="brand"><div class="brand-mark">S</div><div><div class="brand-name">SINISTERS SX7</div><div class="brand-sub">PANEL</div></div></div>
  <nav class="nav">
    <a class="nav-item active" href="#dashboard"><span class="nav-icon">⌂</span><span class="nav-label">Dashboard</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">♙</span><span class="nav-label">Accounts</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">♧</span><span class="nav-label">Groups (GCs)</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">▤</span><span class="nav-label">Messages</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">✎</span><span class="nav-label">NC Titles</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">▣</span><span class="nav-label">Logs</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">◈</span><span class="nav-label">Sessions</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">⌁</span><span class="nav-label">Proxies</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">♙</span><span class="nav-label">Users</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">⚙</span><span class="nav-label">Settings</span></a>
    <a class="nav-item" href="#accounts"><span class="nav-icon">?</span><span class="nav-label">Help &amp; Docs</span></a>
  </nav>
  <div class="side-bottom"><div class="side-owner"><strong>SINISTERS SX7</strong>PANEL • v2.0</div></div>
</aside>
<main class="main" id="dashboard">
  <div class="topbar"><div class="top-title"><h1>SINISTERS</h1><p>SX7 PANEL</p></div><div class="top-actions"><div class="system-pill">● SYSTEM ONLINE</div><button class="btn" onclick="loadAccounts()">↻ REFRESH</button></div></div>
  <section class="stats">
    <div class="stat-card"><div class="stat-icon">♙</div><div><div class="stat-label">Accounts</div><div class="stat-number" id="h-accounts">0</div><div class="stat-sub">Configured</div></div></div>
    <div class="stat-card"><div class="stat-icon">▶</div><div><div class="stat-label">Running</div><div class="stat-number" id="h-running">0</div><div class="stat-sub">Active bots</div></div></div>
    <div class="stat-card"><div class="stat-icon">➤</div><div><div class="stat-label">Total Sent</div><div class="stat-number" id="h-sent">0</div><div class="stat-sub">Current runtime</div></div></div>
    <div class="stat-card"><div class="stat-icon">◷</div><div><div class="stat-label">Panel</div><div class="stat-number">LIVE</div><div class="stat-sub">Auto refresh</div></div></div>
  </section>
  <section id="accounts">
    <div class="panel-head"><div><h2>Accounts</h2><p>Manage existing accounts without changing their commands or API routes.</p></div><div class="panel-tools"><input id="accountSearch" class="search" placeholder="Search account..." oninput="filterCards(this.value)"/><button class="btn btn-add" onclick="openAddModal()">＋ ADD ACCOUNT</button></div></div>
    <div id="accounts-wrap"></div>
  </section>
  <section class="bottom-grid">
    <div class="mini-panel"><div class="mini-title">⚙ GLOBAL SETTINGS</div><div class="mini-line"><span class="mini-key">Session mode</span><span class="mini-val">Saved settings</span></div><div class="mini-line"><span class="mini-key">Port</span><span class="mini-val">0.0.0.0 : PORT</span></div><div class="mini-line"><span class="mini-key">Refresh</span><span class="mini-val">2 sec</span></div><div class="quick"><button class="btn btn-add" onclick="openAddModal()">＋ ADD ACCOUNT</button><button class="btn" onclick="loadAccounts()">↻ REFRESH</button></div></div>
    <div class="mini-panel"><div class="mini-title">▤ MESSAGES</div><div class="mini-line"><span class="mini-key">Source</span><span class="mini-val">Per-account</span></div><div class="mini-line"><span class="mini-key">Rotation</span><span class="mini-val">Round robin</span></div><div class="mini-line"><span class="mini-key">Delay</span><span class="mini-val">Per account</span></div></div>
    <div class="mini-panel"><div class="mini-title">✎ NC TITLES</div><div class="mini-line"><span class="mini-key">Source</span><span class="mini-val">Per-account</span></div><div class="mini-line"><span class="mini-key">Rotation</span><span class="mini-val">Configured titles</span></div><div class="mini-line"><span class="mini-key">Max GCs</span><span class="mini-val">5</span></div></div>
  </section>
</main>
</div>

<div class="modal-overlay" id="modal">
<div class="modal">
  <div class="modal-title" id="modal-title">Add Account</div>

  
  <div class="form-section">
    <div class="form-section-title">Account</div>
    <div class="form-grid">
      <div class="form-group"><label>Name</label><input type="text" id="f-name" placeholder="Account label"/></div>
      <div class="form-group"><label>Session ID</label><input type="text" id="f-sid" placeholder="sessionid cookie" autocomplete="off"/></div>
      <div class="form-group"><label>CSRF Token <span style="opacity:.5;font-weight:400">(optional)</span></label><input type="text" id="f-csrf" placeholder="csrftoken cookie" autocomplete="off"/></div>
      <div class="form-group full"><label>Proxy <span style="opacity:.5;font-weight:400">(optional)</span></label><input type="text" id="f-proxy" placeholder="http://user:pass@ip:port"/></div>
    </div>
  </div>

  
  <div class="form-section">
    <div class="form-section-title">Group Chats (Max 5)</div>
    <div class="fetch-row">
      <div class="form-group" style="flex:1">
        <label>Session ID for Fetch</label>
      </div>
      <button class="btn-fetch" onclick="fetchGroups()">⚡ FETCH GCs</button>
    </div>
    <div id="fetch-status"></div>
    <div class="gc-picker" id="gc-picker">
      <div class="gc-picker-title">Select up to 5 GCs</div>
      <div class="gc-list" id="gc-list"></div>
      <div class="gc-count" id="gc-count">0 / 5 selected</div>
    </div>
    
    <textarea id="f-groups" style="display:none"></textarea>
  </div>

  
  <div class="form-section">
    <div class="form-section-title">NC Titles</div>
    <div class="form-grid">
      <div class="form-group full">
        <label>Titles (comma separated)</label>
        <input type="text" id="f-titles" placeholder="Title1, Title2, Title3"/>
        <div class="hint">NC will rotate through these titles every round</div>
      </div>
    </div>
  </div>

  
  <div class="form-section">
    <div class="form-section-title">Messages (Round Robin)</div>
    <div class="msgs-wrap" id="msgs-wrap"></div>
    <button class="btn-add-msg" onclick="addMsgField()">+ ADD MESSAGE</button>
  </div>

  
  <div class="form-section">
    <div class="form-section-title">Delays</div>
    <div class="form-grid">
      <div class="form-group">
        <label>Min Delay Between Messages (s)</label>
        <input type="number" id="f-msg-min" value="2" min="0" step="0.5"/>
      </div>
      <div class="form-group">
        <label>Max Delay Between Messages (s)</label>
        <input type="number" id="f-msg-max" value="5" min="0" step="0.5"/>
      </div>
      <div class="form-group">
        <label>NC After N Messages</label>
        <input type="number" id="f-nc-every-msgs" value="0" min="0"/>
        <div class="hint">0 = only at start</div>
      </div>
      <div class="form-group">
        <label>Cooldown After N Messages</label>
        <input type="number" id="f-cooldown-after" value="0" min="0"/>
        <div class="hint">0 = disabled</div>
      </div>
      <div class="form-group">
        <label>Cooldown Duration (minutes)</label>
        <input type="number" id="f-cooldown-dur" value="5" min="1"/>
      </div>
    </div>
  </div>

  <div class="modal-footer">
    <button class="btn-cancel" onclick="closeModal()">CANCEL</button>
    <button class="btn-save" onclick="saveAccount()">SAVE</button>
  </div>
</div>
</div>

<script>
let accounts = {};
let editingId = null;
let fetchedGroups = [];
let selectedGCs = []; // [{id, name}]

async function fetchGroups() {
  const sid = document.getElementById('f-sid').value.trim();
  if (!sid) { alert('Enter Session ID first'); return; }
  const proxy = document.getElementById('f-proxy').value.trim();
  const statusEl = document.getElementById('fetch-status');
  statusEl.textContent = '⚡ Fetching...';
  statusEl.style.color = '#f97316';
  try {
    const r = await fetch('/api/fetch-groups', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({session_id: sid, acc_id: editingId || 'fetch_temp', proxy: proxy})
    });
    const d = await r.json();
    if (d.groups && d.groups.length > 0) {
      fetchedGroups = d.groups;
      statusEl.textContent = `✅ ${d.groups.length} GCs found`;
      statusEl.style.color = '#00cc44';
      renderGCPicker();
    } else {
      statusEl.textContent = '⚠️ No GCs found';
      statusEl.style.color = '#f97316';
    }
  } catch(e) {
    statusEl.textContent = `❌ Error: ${e.message}`;
    statusEl.style.color = '#ef4444';
  }
}

function renderGCPicker() {
  const picker = document.getElementById('gc-picker');
  const list = document.getElementById('gc-list');
  picker.style.display = 'block';
  list.innerHTML = '';
  fetchedGroups.forEach(g => {
    const isSelected = selectedGCs.some(s => s.id === g.id);
    const item = document.createElement('div');
    item.className = 'gc-item' + (isSelected ? ' selected' : '');
    item.innerHTML = `
      <input type="checkbox" ${isSelected ? 'checked' : ''} data-id="${g.id}" data-name="${g.name}"/>
      <span class="gc-item-name">${g.name}</span>
      <span class="gc-item-id">${g.id}</span>
    `;
    const cb = item.querySelector('input');
    cb.addEventListener('change', () => toggleGC(g.id, g.name, cb, item));
    list.appendChild(item);
  });
  updateGCCount();
}

function toggleGC(id, name, cb, item) {
  if (cb.checked) {
    if (selectedGCs.length >= 5) {
      cb.checked = false;
      alert('Max 5 GCs allowed');
      return;
    }
    selectedGCs.push({id, name});
    item.classList.add('selected');
  } else {
    selectedGCs = selectedGCs.filter(s => s.id !== id);
    item.classList.remove('selected');
  }
  updateGCCount();
  syncGroupsField();
}

function updateGCCount() {
  document.getElementById('gc-count').textContent = `${selectedGCs.length} / 5 selected`;
}

function syncGroupsField() {
  document.getElementById('f-groups').value = selectedGCs.map(s => s.id).join('\n');
}

function addMsgField(val = '') {
  const wrap = document.getElementById('msgs-wrap');
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `
    <textarea placeholder="Message text..." rows="3">${val}</textarea>
    <button class="btn-icon" onclick="this.parentElement.remove()">✕</button>
  `;
  wrap.appendChild(row);
}

function getMsgs() {
  return [...document.querySelectorAll('#msgs-wrap textarea')]
    .map(t => t.value.trim()).filter(Boolean);
}

function setMsgs(raw) {
  document.getElementById('msgs-wrap').innerHTML = '';
  const parts = raw.split('---MSG---').map(s => s.trim()).filter(Boolean);
  if (parts.length === 0) { addMsgField(); return; }
  parts.forEach(p => addMsgField(p));
}

function openAddModal() {
  editingId = null;
  fetchedGroups = [];
  selectedGCs = [];
  document.getElementById('modal-title').textContent = 'Add Account';
  document.getElementById('f-name').value = '';
  document.getElementById('f-sid').value = '';
  document.getElementById('f-csrf').value = '';
  document.getElementById('f-proxy').value = '';
  document.getElementById('f-titles').value = '';
  document.getElementById('f-msg-min').value = '2';
  document.getElementById('f-msg-max').value = '5';
  document.getElementById('f-nc-every-msgs').value = '0';
  document.getElementById('f-cooldown-after').value = '0';
  document.getElementById('f-cooldown-dur').value = '5';
  document.getElementById('f-groups').value = '';
  document.getElementById('gc-picker').style.display = 'none';
  document.getElementById('gc-list').innerHTML = '';
  document.getElementById('gc-count').textContent = '0 / 5 selected';
  document.getElementById('fetch-status').textContent = '';
  setMsgs('');
  document.getElementById('modal').classList.add('open');
}

function openEditModal(id) {
  editingId = id;
  fetchedGroups = [];
  const acc = accounts[id];

  selectedGCs = [];
  const savedGroups = acc.groups ? acc.groups.split('\n').filter(Boolean) : [];
  const savedNames  = acc.group_names ? acc.group_names.split('\n').filter(Boolean) : [];
  savedGroups.forEach((gid, i) => {
    selectedGCs.push({id: gid.trim(), name: savedNames[i] || gid.trim()});
  });

  document.getElementById('modal-title').textContent = 'Edit Account';
  document.getElementById('f-name').value = acc.name || '';
  document.getElementById('f-sid').value = acc.session_id || '';
  document.getElementById('f-csrf').value = acc.csrf_token || '';
  document.getElementById('f-proxy').value = acc.proxy || '';
  document.getElementById('f-titles').value = acc.nc_titles || '';
  document.getElementById('f-msg-min').value = acc.msg_delay_min || '2';
  document.getElementById('f-msg-max').value = acc.msg_delay_max || '5';
  document.getElementById('f-nc-every-msgs').value = acc.nc_every_msgs || '0';
  document.getElementById('f-cooldown-after').value = acc.cooldown_after || '0';
  document.getElementById('f-cooldown-dur').value = acc.cooldown_dur || '5';
  document.getElementById('f-groups').value = savedGroups.join('\n');
  document.getElementById('fetch-status').textContent = '';

  if (selectedGCs.length > 0) {
    fetchedGroups = selectedGCs.map(s => ({id: s.id, name: s.name}));
    renderGCPicker();
  } else {
    document.getElementById('gc-picker').style.display = 'none';
  }

  setMsgs(acc.messages || acc.message || '');
  document.getElementById('modal').classList.add('open');
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
  editingId = null;
}

async function saveAccount() {
  const msgs = getMsgs();
  if (!msgs.length) { alert('Add at least one message'); return; }

  const body = {
    name:            document.getElementById('f-name').value.trim(),
    session_id:      document.getElementById('f-sid').value.trim(),
    csrf_token:      document.getElementById('f-csrf').value.trim(),
    proxy:           document.getElementById('f-proxy').value.trim(),
    groups:          selectedGCs.map(s => s.id).join('\n'),
    group_names:     selectedGCs.map(s => s.name).join('\n'),
    nc_titles:       document.getElementById('f-titles').value.trim(),
    messages:        msgs.join('---MSG---'),
    msg_delay_min:   document.getElementById('f-msg-min').value,
    msg_delay_max:   document.getElementById('f-msg-max').value,
    nc_every_msgs:   document.getElementById('f-nc-every-msgs').value,
    cooldown_after:  document.getElementById('f-cooldown-after').value,
    cooldown_dur:    document.getElementById('f-cooldown-dur').value,
  };

  if (!body.name) { alert('Enter account name'); return; }
  if (editingId && !body.session_id) delete body.session_id;

  const url    = editingId ? `/api/accounts/${editingId}` : '/api/accounts';
  const method = editingId ? 'PUT' : 'POST';
  const r = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const d = await r.json();
  if (d.success) { closeModal(); loadAccounts(); }
  else alert(d.error || 'Save failed');
}

async function startBot(id) {
  const r = await fetch(`/api/accounts/${id}/start`, {method:'POST'});
  const d = await r.json();
  if (!d.success) alert(d.error || 'Start failed');
}

async function stopBot(id) {
  await fetch(`/api/accounts/${id}/stop`, {method:'POST'});
}

async function deleteAcc(id) {
  if (!confirm('Delete this account?')) return;
  await fetch(`/api/accounts/${id}`, {method:'DELETE'});
  loadAccounts();
}

function toggleLogs(id) {
  const el = document.getElementById(`log-panel-${id}`);
  if (el) el.classList.toggle('open');
}

function toggleCollapse(id) {
  const el = document.getElementById(`body-${id}`);
  if (el) el.style.display = el.style.display === 'none' ? '' : 'none';
}

function filterCards(q) { const cards=[...document.querySelectorAll('#accounts-wrap .acc-card')]; q=(q||'').toLowerCase(); cards.forEach(c=>c.style.display=c.innerText.toLowerCase().includes(q)?'':'none'); }

function fmtTime(secs) {
  if (!secs || secs < 0) return '--:--:--';
  const h = Math.floor(secs/3600);
  const m = Math.floor((secs%3600)/60);
  const s = Math.floor(secs%60);
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function renderAccounts(data) {
  const wrap = document.getElementById('accounts-wrap');
  const ids = Object.keys(data);

  if (ids.length === 0) {
    wrap.innerHTML = `<div class="empty"><div class="empty-icon">☠</div><div class="empty-text">No accounts — add one to begin</div></div>`;
    return;
  }

  let totalRunning = 0, totalSent = 0;
  ids.forEach(id => {
    const st = data[id].status || {};
    if (st.running) totalRunning++;
    totalSent += st.sent || 0;
  });
  document.getElementById('h-accounts').textContent = ids.length;
  document.getElementById('h-running').textContent  = totalRunning;
  document.getElementById('h-sent').textContent     = totalSent;

  ids.forEach(id => {
    const acc = data[id];
    const st  = acc.status || {};
    const isRunning = st.running;
    const isCooldown = st.cooldown;
    const runtime = st.runtime_secs ? fmtTime(st.runtime_secs) : '--:--:--';
    const cooldownStr = st.cooldown && st.cooldown_remaining > 0
      ? ` 😴 ${fmtTime(st.cooldown_remaining)}`
      : (isCooldown ? ' 😴 COOLDOWN' : '');

    const dotCls = isCooldown ? 'dot-cooldown' : (isRunning ? 'dot-on' : 'dot-off');
    const gcNames = acc.group_names ? acc.group_names.split('\n').filter(Boolean) : [];

    let existing = document.getElementById(`card-${id}`);
    if (!existing) {
      existing = document.createElement('div');
      existing.className = 'acc-card';
      existing.id = `card-${id}`;
      wrap.appendChild(existing);
    }

    const existingLogPanel = document.getElementById(`log-panel-${id}`);
    const logOpen = existingLogPanel ? existingLogPanel.classList.contains('open') : false;

    existing.innerHTML = `
      <div class="acc-header">
        <div class="status-dot ${dotCls}"></div>
        <div class="acc-name">${acc.name || id}${cooldownStr ? `<span style="color:var(--amber);font-size:11px;margin-left:10px">${cooldownStr}</span>` : ''}</div>
        <div class="acc-runtime">${runtime}</div>
        <div class="acc-btns">
          ${isRunning
            ? `<button class="btn btn-stop" onclick="stopBot('${id}')">■ STOP</button>`
            : `<button class="btn btn-start" onclick="startBot('${id}')">▶ START</button>`}
          <button class="btn btn-logs" onclick="toggleLogs('${id}')">LOGS</button>
          <button class="btn btn-edit" onclick="openEditModal('${id}')">EDIT</button>
          <button class="btn btn-del" onclick="deleteAcc('${id}')">✕</button>
          <button class="btn-collapse" onclick="toggleCollapse('${id}')">▲</button>
        </div>
      </div>
      <div id="body-${id}">
        <div class="stats-row">
          <div class="stat"><div class="stat-val c-green">${st.sent||0}</div><div class="stat-lbl">Sent</div></div>
          <div class="stat"><div class="stat-val c-red">${st.failed||0}</div><div class="stat-lbl">Failed</div></div>
          <div class="stat"><div class="stat-val c-purple">${st.nc_done||0}</div><div class="stat-lbl">NC Done</div></div>
          <div class="stat"><div class="stat-val c-red">${st.nc_failed||0}</div><div class="stat-lbl">NC Fail</div></div>
          
          <div class="stat"><div class="stat-val c-amber">${st.gcs_done||0}<span style="color:var(--muted);font-size:12px"> / ${st.total_gcs||0}</span></div><div class="stat-lbl">GCs</div></div>
        </div>
        ${gcNames.length ? `
        <div class="gc-row">
          <span class="gc-label">GCs</span>
          ${gcNames.map(n=>`<span class="gc-pill">${n}</span>`).join('')}
        </div>` : ''}
        <div class="info-row">
          <div class="info-item"><span class="info-key">Delay</span><span class="info-val">${acc.msg_delay_min||2}s – ${acc.msg_delay_max||5}s</span></div>
          ${acc.cooldown_after > 0 ? `<div class="info-item"><span class="info-key">Cooldown</span><span class="info-val">After ${acc.cooldown_after} msgs → ${acc.cooldown_dur} min pause</span></div>` : ''}
          ${acc.nc_titles ? `<div class="info-item"><span class="info-key">NC</span><span class="info-val">${acc.nc_titles.split(',').length} titles</span></div>` : ''}
        </div>
        <div class="last-action">▸ <span>${st.last_action||'Idle'}</span></div>
        <div class="log-panel ${logOpen ? 'open' : ''}" id="log-panel-${id}">
          <div class="log-header">
            <span class="log-title">📟 CONSOLE LOG</span>
            <span class="log-live">● LIVE</span>
          </div>
          <div class="log-box" id="log-box-${id}"></div>
        </div>
      </div>
    `;
  });

  wrap.querySelectorAll('.acc-card').forEach(el => {
    if (!data[el.id.replace('card-','')]) el.remove();
  });
}

function colorLog(line) {
  if (line.includes('✅') || line.includes('✓')) return 'ok';
  if (line.includes('❌') || line.includes('failed') || line.includes('Failed')) return 'err';
  if (line.includes('⚠️')) return 'warn';
  if (line.includes('🔄') || line.includes('Round')) return 'round';
  if (line.includes('💤') || line.includes('⏭') || line.includes('😴')) return 'info';
  return '';
}

async function loadAccounts() {
  const r = await fetch('/api/accounts');
  accounts = await r.json();
  renderAccounts(accounts);
}

async function pollLogs() {
  const openPanels = document.querySelectorAll('.log-panel.open');
  for (const panel of openPanels) {
    const id = panel.id.replace('log-panel-','');
    try {
      const r = await fetch(`/api/accounts/${id}/logs`);
      const d = await r.json();
      const box = document.getElementById(`log-box-${id}`);
      if (box && d.logs) {
        const currentCount = box.querySelectorAll('.log-line').length;
        if (currentCount === 0) {

          box.innerHTML = d.logs.map(l => `<div class="log-line ${colorLog(l)}">${l}</div>`).join('');
          box.scrollTop = box.scrollHeight;
        } else if (d.logs.length > currentCount) {

          const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
          const newLines = d.logs.slice(currentCount);
          newLines.forEach(l => {
            const div = document.createElement('div');
            div.className = `log-line ${colorLog(l)}`;
            div.textContent = l;
            box.appendChild(div);
          });
          if (atBottom) box.scrollTop = box.scrollHeight;
        } else if (d.logs.length < currentCount) {

          box.innerHTML = d.logs.map(l => `<div class="log-line ${colorLog(l)}">${l}</div>`).join('');
          box.scrollTop = box.scrollHeight;
        }
      }
    } catch(e) {}
  }
}

async function pollStatus() {
  try {
    const r = await fetch('/api/status');
    const st = await r.json();
    Object.keys(st).forEach(id => {
      if (accounts[id]) accounts[id].status = st[id];
    });
    renderAccounts(accounts);
  } catch(e) {}
}

loadAccounts();
setInterval(pollStatus, 2000);
setInterval(pollLogs, 1500);

document.getElementById('modal').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});
</script>
</body>
</html>"""

                                                              

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if session.get("panel_logged_in"):
        return redirect(url_for("combined_index"))
    error = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if username == PANEL_USERNAME and password == PANEL_PASSWORD:
            session["panel_logged_in"] = True
            return redirect(url_for("combined_index"))
        error = "Invalid username or password"
    return LOGIN_HTML.replace("{{ error }}", error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/")
@login_required
def combined_index():
    return HTML

@app.route("/instagram")
@login_required
def instagram_panel():
    return HTML

@app.route("/api/accounts")
@login_required
def get_accounts():
    with data_lock:
        d = load_data()
    result = {}
    for acc_id, acc in d.get("accounts", {}).items():
        st = bot_status.get(acc_id, {"running": False})
        result[acc_id] = {
            "name":           acc.get("name", ""),
            "session_id":     acc.get("session_id", ""),
            "csrf_token":     acc.get("csrf_token", ""),
            "proxy":          acc.get("proxy", ""),
            "groups":         acc.get("groups", ""),
            "group_names":    acc.get("group_names", ""),
            "nc_titles":      acc.get("nc_titles", ""),
            "messages":       acc.get("messages", ""),
            "msg_delay_min":  acc.get("msg_delay_min", 2),
            "msg_delay_max":  acc.get("msg_delay_max", 5),
            "nc_every_msgs":  acc.get("nc_every_msgs", 0),
            "cooldown_after": acc.get("cooldown_after", 0),
            "cooldown_dur":   acc.get("cooldown_dur", 5),
            "status": st
        }
    return jsonify(result)

@app.route("/api/accounts", methods=["POST"])
@login_required
def add_account():
    body = request.json
    session_id = (body.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"success": False, "error": "Session ID required"}), 400

    acc_id = str(int(time.time() * 1000))
    entry = {
        "name":           body.get("name", ""),
        "session_id":     session_id,
        "csrf_token":     body.get("csrf_token", ""),
        "proxy":          body.get("proxy", ""),
        "groups":         body.get("groups", ""),
        "group_names":    body.get("group_names", ""),
        "nc_titles":      body.get("nc_titles", ""),
        "messages":       body.get("messages", ""),
        "msg_delay_min":  body.get("msg_delay_min", 2),
        "msg_delay_max":  body.get("msg_delay_max", 5),
        "nc_every_msgs":  body.get("nc_every_msgs", 0),
        "cooldown_after": body.get("cooldown_after", 0),
        "cooldown_dur":   body.get("cooldown_dur", 5),
    }
                                                                           
                                                                   
    try:
        temp_cl = ig_clients.get("fetch_temp")
        if temp_cl:
            entry["session_settings"] = temp_cl.get_settings()
    except Exception:
        pass
    with data_lock:
        d = load_data()
        d["accounts"][acc_id] = entry
        save_data(d)
    return jsonify({"success": True, "id": acc_id})

@app.route("/api/accounts/<acc_id>", methods=["PUT"])
@login_required
def update_account(acc_id):
    body = request.json
    with data_lock:
        d = load_data()
        if acc_id not in d["accounts"]:
            return jsonify({"success": False, "error": "Not found"}), 404
        acc = d["accounts"][acc_id]
        for k in ["name", "proxy", "csrf_token", "groups", "group_names", "nc_titles",
                  "messages", "msg_delay_min", "msg_delay_max", "nc_every_msgs", "cooldown_after", "cooldown_dur"]:
            if k in body: acc[k] = body[k]
        if body.get("session_id"):
            acc["session_id"] = body["session_id"]
                                                                     
                                                                       
            acc.pop("session_settings", None)
            ig_clients.pop(acc_id, None)
        save_data(d)
    return jsonify({"success": True})

@app.route("/api/accounts/<acc_id>", methods=["DELETE"])
@login_required
def delete_account(acc_id):
    if acc_id in bot_stop: bot_stop[acc_id].set()
    ig_clients.pop(acc_id, None)
    with data_lock:
        d = load_data()
        d["accounts"].pop(acc_id, None)
        save_data(d)
    return jsonify({"success": True})

@app.route("/api/accounts/<acc_id>/start", methods=["POST"])
@login_required
def start_bot(acc_id):
    with data_lock:
        d = load_data()
        acc = d["accounts"].get(acc_id)
    if not acc: return jsonify({"success": False, "error": "Not found"}), 404
                                                
    if acc_id in bot_threads and bot_threads[acc_id].is_alive():
        if acc_id in bot_stop: bot_stop[acc_id].set()
        bot_threads[acc_id].join(timeout=5)
        if bot_threads[acc_id].is_alive():
            return jsonify({"success": False, "error": "Bot did not stop in time, please wait a moment"})
    stop_event = threading.Event()
    bot_stop[acc_id] = stop_event
    t = threading.Thread(target=bot_worker, args=(acc_id, acc, stop_event), daemon=True)
    bot_threads[acc_id] = t
    t.start()
    return jsonify({"success": True})

@app.route("/api/accounts/<acc_id>/stop", methods=["POST"])
@login_required
def stop_bot(acc_id):
    if acc_id in bot_stop: bot_stop[acc_id].set()
    if acc_id in bot_status:
        bot_status[acc_id]["running"] = False
        bot_status[acc_id]["last_action"] = "Stopped"
    return jsonify({"success": True})

@app.route("/api/accounts/<acc_id>/logs")
@login_required
def get_logs(acc_id):
    logs = list(bot_logs.get(acc_id, []))
    return jsonify({"logs": logs})

@app.route("/api/status")
@login_required
def all_status():
    result = {}
    for acc_id, st in bot_status.items():
        s = dict(st)
        if s.get("started_at") and s.get("running"):
            s["runtime_secs"] = int(time.time() - s["started_at"])
        else:
            s["runtime_secs"] = 0
        if s.get("cooldown") and s.get("cooldown_end", 0) > 0:
            s["cooldown_remaining"] = max(0, int(s["cooldown_end"] - time.time()))
        else:
            s["cooldown_remaining"] = 0
        result[acc_id] = s
    return jsonify(result)

@app.route("/api/fetch-groups", methods=["POST"])
@login_required
def fetch_groups():
    body = request.json
    session_id = (body.get("session_id") or "").strip()
    acc_id = (body.get("acc_id") or "fetch_temp").strip()
    if not session_id:
        return jsonify({"success": False, "error": "Session ID required"}), 400
    try:
                                                                
        proxy = (body.get("proxy") or "").strip() or None
        if acc_id in ig_clients:
            cl = ig_clients[acc_id]
        elif acc_id != "fetch_temp":
            cl = get_client(acc_id, session_id, proxy)
        else:
            cl = Client()
            if proxy:
                cl.set_proxy(proxy)
            cl.login_by_sessionid(decode_session(session_id))
            ig_clients[acc_id] = cl
        threads = cl.direct_threads(amount=50)
        groups = []
        for t in threads:
            if t.is_group:
                groups.append({"id": str(t.id), "name": t.thread_title or str(t.id)})
        try:
            if acc_id in ig_clients:
                persist_client_settings(acc_id, ig_clients[acc_id])
        except Exception:
            pass
        return jsonify({"success": True, "groups": groups})
    except Exception as e:
        ig_clients.pop(acc_id, None)                    
        return jsonify({"success": False, "error": str(e)}), 400

                                           
SELF_URL = (os.getenv("SELF_URL") or os.getenv("PUBLIC_URL") or "").strip()
SELF_PING_INTERVAL = int(os.getenv("SELF_PING_INTERVAL", "300"))

def self_ping_worker():
    while True:
        try:
            if SELF_URL:
                req = urllib.request.Request(
                    SELF_URL,
                    headers={"User-Agent": "SelfPing/1.0"},
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp.read(1)
        except Exception:
            pass
        time.sleep(max(30, SELF_PING_INTERVAL))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    if SELF_URL:
        threading.Thread(target=self_ping_worker, daemon=True).start()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=port, debug=False)
