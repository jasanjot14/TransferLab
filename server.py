"""Local API and UI. Run alongside ingest.py to read stored predictions."""
import json
import os
import sqlite3
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from analysis import Prediction, assess, next_arrival

ROOT = Path(__file__).parent / "dist"
DB = os.environ.get("TRANSFERLAB_DB", "transferlab.db")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/transfer":
            return super().do_GET()
        params = parse_qs(parsed.query)
        stop, first, second = (params.get(k, [""])[0] for k in ("stop", "from", "to"))
        try:
            walk = int(params.get("walk", ["3"])[0])
            if not (stop and first and second) or not 0 <= walk <= 30:
                raise ValueError("Specify stop, from, to, and walk in 0..30")
            now = int(time.time())
            with sqlite3.connect(DB) as conn:
                rows = conn.execute("SELECT route,trip,stop,arrival,observed FROM predictions "
                                    "WHERE stop=? AND route IN (?,?) ORDER BY observed DESC LIMIT 2000",
                                    (stop, first, second)).fetchall()
            latest = {}
            for route, trip, stop_id, arrival, observed in rows:
                latest.setdefault((route, trip, stop_id), Prediction(route, trip, stop_id, arrival, observed))
            a = next_arrival(latest.values(), first, stop, now)
            b = next_arrival(latest.values(), second, stop, now)
            data = {"assessment": assess(a, b, walk, now), "from": vars(a) if a else None,
                    "to": vars(b) if b else None, "mode": "live", "generated_at": now}
            self.respond(200, data)
        except ValueError as exc:
            self.respond(400, {"error": str(exc)})
        except sqlite3.Error as exc:
            self.respond(503, {"error": f"Prediction store unavailable: {exc}"})

    def respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
