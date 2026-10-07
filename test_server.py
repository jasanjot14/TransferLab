import json
import sqlite3
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

import server


class TransferAPITests(unittest.TestCase):
    def test_stale_predictions_are_not_discarded_by_query(self):
        now = int(time.time())
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "predictions.db"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE predictions (route TEXT, trip TEXT, stop TEXT, arrival INTEGER, observed INTEGER)")
                conn.executemany("INSERT INTO predictions VALUES (?,?,?,?,?)", [
                    ("A", "a1", "S", now + 50, now - 200),
                    ("B", "b1", "S", now + 420, now - 200),
                ])
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                with patch.object(server, "DB", str(db)):
                    url = f"http://127.0.0.1:{httpd.server_address[1]}/api/transfer?stop=S&from=A&to=B&walk=3"
                    with urlopen(url) as response:
                        data = json.load(response)
                self.assertEqual(data["assessment"]["status"], "stale")
                self.assertIsNone(data["assessment"]["gap_minutes"])
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
