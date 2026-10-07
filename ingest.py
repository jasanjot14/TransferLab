"""Poll a configurable GTFS-Realtime TripUpdates endpoint into SQLite.

Requires `pip install -r requirements.txt`. Use the transit operator's feed URL,
following its published terms. This module deliberately does not assume an
undocumented TTC endpoint or imply that predictions are actual arrival times.
"""
import argparse
import os
import sqlite3
import time
from urllib.request import Request, urlopen

from google.transit import gtfs_realtime_pb2


SCHEMA = """CREATE TABLE IF NOT EXISTS predictions (
  route TEXT NOT NULL, trip TEXT NOT NULL, stop TEXT NOT NULL,
  arrival INTEGER NOT NULL, observed INTEGER NOT NULL,
  PRIMARY KEY(trip, stop, observed)
); CREATE INDEX IF NOT EXISTS ix_predictions_stop_route_time
ON predictions(stop, route, observed);"""


def parse_trip_updates(payload, observed):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(payload)
    if not feed.IsInitialized():
        raise ValueError("Incomplete GTFS-Realtime message")
    result = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        update = entity.trip_update
        route, trip = update.trip.route_id, update.trip.trip_id
        if not route or not trip:
            continue
        for stop in update.stop_time_update:
            event = stop.arrival if stop.HasField("arrival") else stop.departure
            if stop.stop_id and event.HasField("time"):
                result.append((route, trip, stop.stop_id, int(event.time), observed))
    return result


def store_payload(conn, payload, observed=None):
    observed = int(time.time()) if observed is None else int(observed)
    rows = parse_trip_updates(payload, observed)
    with conn:
        conn.executemany("INSERT OR REPLACE INTO predictions VALUES (?,?,?,?,?)", rows)
    return len(rows)


def poll(conn, url, interval=30):
    if interval < 10:
        raise ValueError("Polling interval must be at least 10 seconds")
    while True:
        try:
            request = Request(url, headers={"User-Agent": "TransferLab/0.1"})
            with urlopen(request, timeout=15) as response:
                count = store_payload(conn, response.read())
            print(f"Stored {count} predictions", flush=True)
        except Exception as exc:
            print(f"Feed unavailable: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Store GTFS-Realtime trip updates")
    parser.add_argument("--db", default="transferlab.db")
    parser.add_argument("--url", default=os.environ.get("GTFS_RT_TRIP_UPDATES_URL"))
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()
    if not args.url or not args.url.startswith("https://"):
        parser.error("Provide an HTTPS TripUpdates feed URL with --url or GTFS_RT_TRIP_UPDATES_URL")
    connection = sqlite3.connect(args.db)
    connection.executescript(SCHEMA)
    poll(connection, args.url, args.interval)
