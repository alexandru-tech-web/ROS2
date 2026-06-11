#!/usr/bin/env python3
"""node_utils.py — utilitare comune pentru nodurile ROS2 din sar_plugins.
QoS in conventia proiectului (RELIABLE pentru comenzi, BEST_EFFORT pentru
telemetrie) + parsarea flexibila a pozelor JSON, ca nodurile sa accepte
mai multe forme de telemetrie fara modificari in codul existent."""
import json

from rclpy.qos import (QoSProfile, ReliabilityPolicy, HistoryPolicy,
                       DurabilityPolicy)


def qos_reliable(depth=10):
    return QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                      history=HistoryPolicy.KEEP_LAST, depth=depth)


def qos_best_effort(depth=10):
    return QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                      history=HistoryPolicy.KEEP_LAST, depth=depth)


def qos_latched(depth=1):
    """TRANSIENT_LOCAL — abonatii tarzii primesc ultimul mesaj (latched)."""
    return QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                      durability=DurabilityPolicy.TRANSIENT_LOCAL,
                      history=HistoryPolicy.KEEP_LAST, depth=depth)


def now_s(node):
    return node.get_clock().now().nanoseconds * 1e-9


def parse_poses(text, default_id="rover"):
    """Accepta mai multe forme de telemetrie JSON si intoarce
    dict id -> (x, y, z):
      {"id": "d1", "x": 1, "y": 2}                      — o singura drona
      {"x": 1, "y": 2}                                  — fara id => default
      {"poses": [{"id":..., "x":..., "y":...}, ...]}    — lista
      {"d1": {"x":..., "y":...}, "d2": {...}}           — dict de id-uri
    Campurile lipsa z se considera 0. Intoarce {} daca nu se poate parsa."""
    try:
        d = json.loads(text)
    except (ValueError, TypeError):
        return {}
    out = {}

    def add(did, rec):
        try:
            out[str(did)] = (float(rec["x"]), float(rec["y"]),
                             float(rec.get("z", 0.0)))
        except (KeyError, TypeError, ValueError):
            pass

    if isinstance(d, dict):
        if "poses" in d and isinstance(d["poses"], list):
            for rec in d["poses"]:
                if isinstance(rec, dict):
                    add(rec.get("id", default_id), rec)
        elif "x" in d and "y" in d:
            add(d.get("id", default_id), d)
        else:
            for k, v in d.items():
                if isinstance(v, dict) and "x" in v and "y" in v:
                    add(k, v)
    elif isinstance(d, list):
        for rec in d:
            if isinstance(rec, dict) and "x" in rec and "y" in rec:
                add(rec.get("id", default_id), rec)
    return out
