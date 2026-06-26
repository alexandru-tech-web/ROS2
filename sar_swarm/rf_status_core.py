#!/usr/bin/env python3
"""rf_status_core.py -- nucleu pur (fara ROS/Tk) pentru bara de stare RF a dashboard-ului:
rezuma /sar/linkstate (loss, burst_len, interf_db) si /link_adaptive/state intr-un text + nivel
(ok/warn/crit) pe care HMI-ul il afiseaza colorat. Logica + testele aici; dashboard-ul doar afiseaza."""

LEVEL_COLOR = {"ok": "#2E8B57", "warn": "#d8a000", "crit": "#c0392b"}


def rf_status(ls):
    """Din /sar/linkstate dict -> {text, level, color}. Nivelul din loss + burst_len + interf_db
    (rafala lunga sau interferenta ridicata urca nivelul chiar la pierdere medie mica)."""
    loss = float(ls.get("loss", 0.0))
    burst = float(ls.get("burst_len", 1.0))
    interf = float(ls.get("interf_db", 0.0))
    if loss >= 0.20 or burst >= 6.0 or interf >= 10.0:
        level = "crit"
    elif loss >= 0.05 or burst >= 3.0 or interf >= 3.0:
        level = "warn"
    else:
        level = "ok"
    text = "RF: loss %.0f%%  rafala~%.1f  interf %.0fdB  [%s]" % (
        100 * loss, burst, interf, level.upper())
    return {"text": text, "level": level, "color": LEVEL_COLOR[level]}


def link_summary(la):
    """Din /link_adaptive/state dict -> text scurt (mod + metrici)."""
    if not la:
        return "link_adaptive: --"
    return ("link_adaptive: %s (rtt_p95=%.0fms, loss=%.0f%%, max_burst=%s)"
            % (la.get("mode", "?"), float(la.get("rtt_p95_ms", 0)),
               100 * float(la.get("loss", 0)), la.get("max_burst", "?")))


def _selftest():
    assert rf_status({"loss": 0.0, "burst_len": 1})["level"] == "ok"
    assert rf_status({"loss": 0.10})["level"] == "warn"
    assert rf_status({"loss": 0.30})["level"] == "crit"
    assert rf_status({"loss": 0.0, "burst_len": 8})["level"] == "crit"   # rafala lunga
    assert rf_status({"interf_db": 12})["level"] == "crit"
    assert "RF: loss" in rf_status({"loss": 0.1})["text"]
    assert rf_status({"loss": 0.0})["color"] == LEVEL_COLOR["ok"]

    assert link_summary({}) == "link_adaptive: --"
    s = link_summary({"mode": "CRITICAL", "rtt_p95_ms": 800, "loss": 0.3, "max_burst": 9})
    assert "CRITICAL" in s and "max_burst=9" in s
    print("TOATE VERIFICARILE rf_status_core AU TRECUT")


if __name__ == "__main__":
    _selftest()
