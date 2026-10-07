"""Transfer forecasts. All timestamps are Unix seconds in UTC."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Prediction:
    route: str
    trip: str
    stop: str
    arrival: int
    observed: int


def next_arrival(rows, route, stop, now):
    candidates = [r for r in rows if r.route == route and r.stop == stop and r.arrival >= now - 30]
    return min(candidates, key=lambda r: r.arrival, default=None)


def assess(first, second, walk_minutes=3, now=None):
    if walk_minutes < 0:
        raise ValueError("Walking time must be nonnegative")
    if first is None or second is None:
        return {"status": "unknown", "reason": "Missing arrival prediction", "gap_minutes": None}
    age = max(now - first.observed, now - second.observed) if now is not None else 0
    if age > 90 or age < -10:
        return {"status": "stale", "reason": "Prediction is more than 90 seconds old", "gap_minutes": None}
    gap = round((second.arrival - first.arrival) / 60, 1)
    status = "missed" if gap < walk_minutes else "tight" if gap < walk_minutes + 2 else "comfortable"
    return {"status": status, "gap_minutes": gap,
            "reason": f"{gap:g} minute predicted gap; {walk_minutes:g} minutes needed to walk",
            "age_seconds": age}


def forecast_history(snapshot_pairs, walk_minutes=3):
    """Fraction of sampled forecasts with enough time. Not actual transfer success."""
    gaps = [round((b.arrival - a.arrival) / 60, 1) for a, b in snapshot_pairs
            if abs(a.observed - b.observed) <= 60]
    if not gaps:
        return {"samples": 0, "forecast_share": None, "median_gap": None}
    ordered = sorted(gaps)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return {"samples": len(gaps), "forecast_share": round(sum(g >= walk_minutes for g in gaps) / len(gaps), 3),
            "median_gap": median}
