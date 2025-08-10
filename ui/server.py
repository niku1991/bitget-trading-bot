import threading
import time
import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from io import BytesIO
import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
from main import BitgetTradingBot

load_dotenv()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Bitget Bot</title>
<style>
  :root { --bg:#0b0e11; --card:#12161c; --text:#eaecef; --muted:#9aa4af; --acc:#2a5bd7; --danger:#d72a3a; --ok:#1faa59; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue"; background:var(--bg); color:var(--text); }
  header { padding:16px 20px; border-bottom:1px solid #1f2937; display:flex; align-items:center; justify-content:space-between; }
  header h1 { margin:0; font-size:18px; letter-spacing:0.5px; }
  header .pill { font-size:12px; color:var(--muted); border:1px solid #334155; padding:4px 8px; border-radius:999px; }
  main { max-width:1000px; margin:24px auto; padding:0 16px; display:grid; grid-template-columns: 1fr 1fr; gap:16px; }
  .card { background:var(--card); border:1px solid #1f2937; border-radius:12px; padding:16px; }
  .card h2 { margin:0 0 12px; font-size:16px; }
  .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .btn { background:#1f2937; color:var(--text); border:1px solid #334155; padding:10px 12px; border-radius:8px; text-decoration:none; display:inline-block; cursor:pointer; }
  .btn.primary { background:var(--acc); border-color:var(--acc); }
  .btn.danger { background:var(--danger); border-color:var(--danger); }
  .btn.ok { background:var(--ok); border-color:var(--ok); }
  .inp { background:#0b0e11; color:var(--text); border:1px solid #334155; padding:10px 12px; border-radius:8px; }
  .kv { display:grid; grid-template-columns: 160px 1fr; gap:8px; margin-bottom:6px; }
  .muted { color:var(--muted); font-size:12px; }
  .grid-1 { grid-column: span 2; }
  pre { background:#0b0e11; border:1px solid #1f2937; border-radius:8px; padding:12px; max-height:260px; overflow:auto; }
  form { margin:0; }
</style>
</head>
<body>
  <header>
    <h1>Bitget Trading Bot</h1>
    <div class="pill">Status: {status}</div>
  </header>
  <main>
    <div class="card">
      <h2>Quick Actions</h2>
      <div class="row" style="margin-bottom:12px;">
        <form method="post" action="/action"><input type="hidden" name="cmd" value="auto_connect" />
          <button class="btn">Auto-Connect</button>
        </form>
        <form method="post" action="/action"><input type="hidden" name="cmd" value="summary" />
          <button class="btn">Summary</button>
        </form>
        <form method="post" action="/action"><input type="hidden" name="cmd" value="cancel_all" />
          <button class="btn danger">Cancel All</button>
        </form>
      </div>
      <form method="post" action="/action">
        <div class="row" style="margin-bottom:8px;">
          <input class="inp" type="number" name="min_ai_score" step="0.01" min="0" max="1" value="{min_ai_score}" placeholder="Min AI Score" />
          <input class="inp" type="number" name="risk_per_trade" step="0.01" min="0" value="{risk_per_trade}" placeholder="Risk per trade (USD)" />
        </div>
        <div class="row">
          <input type="hidden" name="cmd" value="start_dry" />
          <button class="btn ok">Start Dry-Run</button>
          <button class="btn primary" formaction="/action?live=1">Start Live</button>
          <button class="btn danger" formaction="/action?stop=1">Stop</button>
        </div>
      </form>
      <div class="muted" style="margin-top:8px;">{flash}</div>
    </div>

    <div class="card">
      <h2>Portfolio</h2>
      <div class="kv"><div>Balance</div><div>{balance} USDT</div></div>
      <div class="kv"><div>Active Positions</div><div>{positions_count}</div></div>
      <div class="kv"><div>Pending Orders</div><div>{orders_count}</div></div>
    </div>

    <div class="card grid-1">
      <h2>Recent Events</h2>
      <pre>{events}</pre>
      <div class="muted">Showing latest {events_count} events</div>
    </div>
  </main>
</body>
</html>
"""

class BotService:
    def __init__(self):
        self._thread = None
        self._bot = None
        self._lock = threading.Lock()
        self.last_flash = ""
        self.db_path = os.path.join(PROJECT_ROOT, "trades.db")

    def status(self) -> str:
        if self._thread and self._thread.is_alive():
            return "Running"
        return "Stopped"

    def _run_bot(self, live: bool, min_ai_score: float, risk_per_trade: float):
        try:
            self._bot = BitgetTradingBot(debug=False, dry_run=(not live), min_ai_score=min_ai_score)
            if risk_per_trade is not None:
                self._bot.risk_per_trade = float(risk_per_trade)
            self._bot.start()
        except Exception as e:
            self.last_flash = f"Bot error: {e}"

    def start(self, live: bool, min_ai_score: float, risk_per_trade: float):
        with self._lock:
            if self._thread and self._thread.is_alive():
                self.last_flash = "Bot already running"
                return
            self._thread = threading.Thread(target=self._run_bot, args=(live, min_ai_score, risk_per_trade), daemon=True)
            self._thread.start()
            self.last_flash = "Bot started"

    def stop(self):
        with self._lock:
            if self._bot:
                try:
                    self._bot.stop()
                    self.last_flash = "Bot stopped"
                except Exception as e:
                    self.last_flash = f"Stop failed: {e}"
            self._bot = None
            self._thread = None

    def ensure_client(self):
        # Return an active client, or create a temporary one
        if self._bot:
            return self._bot.client
        temp = BitgetTradingBot(debug=False, dry_run=True, min_ai_score=0.0)
        ok = temp.verify_connectivity()
        if not ok:
            raise RuntimeError("Connectivity failed")
        if not temp.test_authentication():
            raise RuntimeError("Authentication failed")
        return temp.client

    def summary(self):
        try:
            client = self.ensure_client()
            bal = client.get_account_balance()
            pos = client.get_positions()
            orders = client.get_pending_orders()
            pc = len([p for p in pos.get('data', []) if float(p.get('total', 0)) > 0])
            oc = len(orders.get('data', []) or [])
            return bal, pc, oc
        except Exception as e:
            self.last_flash = f"Summary error: {e}"
            return 0.0, 0, 0

    def cancel_all(self):
        try:
            client = self.ensure_client()
            if self._bot and self._bot.dry_run:
                pending = client.get_pending_orders()
                n = len(pending.get('data', []) or [])
                self.last_flash = f"Dry-run: would cancel {n} orders"
                return
            res = client.cancel_all_pending_orders()
            self.last_flash = f"Canceled {len(res)} orders"
        except Exception as e:
            self.last_flash = f"Cancel error: {e}"

    def auto_connect(self):
        try:
            temp = BitgetTradingBot(debug=False, dry_run=True, min_ai_score=0.0)
            if not temp.verify_connectivity():
                self.last_flash = "Connectivity failed"
                return False
            if not temp.test_authentication():
                self.last_flash = "Authentication failed"
                return False
            self.last_flash = "Auto-connect successful"
            return True
        except Exception as e:
            self.last_flash = f"Auto-connect error: {e}"
            return False

    def recent_events(self, limit: int = 50) -> str:
        try:
            if not os.path.exists(self.db_path):
                return "No events yet. Start the bot to collect events."
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT ts, type, symbol, entry_price, current_price, size, unrealized_pnl FROM trade_events ORDER BY id DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            conn.close()
            lines = []
            for r in rows:
                ts, etype, sym, ep, cp, sz, pnl = r
                lines.append(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))} | {etype} | {sym or ''} | entry={ep or ''} | current={cp or ''} | size={sz or ''} | upnl={pnl or ''}")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to load events: {e}"

service = BotService()

class Handler(BaseHTTPRequestHandler):
    def _render(self, flash_override: str = ""):
        bal, pc, oc = service.summary()
        events = service.recent_events(limit=50)
        html = HTML_TEMPLATE.format(
            status=service.status(),
            min_ai_score="0.60",
            risk_per_trade=f"{getattr(service._bot, 'risk_per_trade', 6.0):.2f}" if service._bot else "6.00",
            flash=flash_override or service.last_flash,
            balance=f"{bal:.2f}",
            positions_count=pc,
            orders_count=oc,
            events=events,
            events_count=str(len(events.splitlines())) if events else "0"
        )
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_GET(self):
        if self.path.startswith('/'):  # Single page
            self._render()
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)
        params = parse_qs(data.decode('utf-8'))
        query = parse_qs(urlparse(self.path).query)
        cmd = (params.get('cmd', [''])[0])
        min_ai = float(params.get('min_ai_score', ['0.6'])[0])
        rpt = params.get('risk_per_trade', [''])
        rpt_val = float(rpt[0]) if rpt and rpt[0] != '' else None
        flash = ""

        try:
            if cmd == 'auto_connect':
                ok = service.auto_connect()
                flash = service.last_flash
            elif cmd == 'summary':
                # summary is shown on refresh
                flash = "Summary refreshed"
            elif cmd == 'cancel_all':
                service.cancel_all()
                flash = service.last_flash
            elif cmd == 'start_dry':
                live = ('live' in query and query['live'][0] == '1')
                service.start(live=live, min_ai_score=min_ai, risk_per_trade=rpt_val)
                flash = service.last_flash
            elif 'stop' in query:
                service.stop()
                flash = service.last_flash
            else:
                flash = "Unknown action"
        except Exception as e:
            flash = f"Error: {e}"

        # Render page
        self._render(flash_override=flash)


def run(host: str = '0.0.0.0', port: int = 8000):
    httpd = HTTPServer((host, port), Handler)
    print(f"UI server running on http://{host}:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Bitget Bot UI Server')
    parser.add_argument('--host', default=os.getenv('UI_HOST', '0.0.0.0'), help='Host to bind')
    parser.add_argument('--port', type=int, default=int(os.getenv('UI_PORT', '8000')), help='Port to bind')
    args = parser.parse_args()
    run(args.host, args.port)