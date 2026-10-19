"""Courier simulation: deterministic route generator for live-map demo (no GPS hardware needed)."""
import math


def courier_route(order_id=1, steps=12):
    """Generate a smooth route from hub to doorstep around VIT Vellore demo coords."""
    hub = (12.9850, 79.1700)
    door = (12.9716, 79.1585)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        # ease-in-out + slight curve for visual interest
        e = t * t * (3 - 2 * t)
        lat = hub[0] + (door[0] - hub[0]) * e + math.sin(t * math.pi) * 0.0015
        lng = hub[1] + (door[1] - hub[1]) * e + math.sin(t * math.pi) * 0.0012
        pts.append({"lat": round(lat, 6), "lng": round(lng, 6), "step": i})
    return {
        "order_id": order_id,
        "hub": {"lat": hub[0], "lng": hub[1], "label": "Chennai Central Fulfillment Hub"},
        "doorstep": {"lat": door[0], "lng": door[1], "label": "Customer Doorstep (50m S2 geofence)"},
        "points": pts,
        "eta_minutes": [round((steps - p["step"]) * 1.5, 1) for p in pts],
    }
