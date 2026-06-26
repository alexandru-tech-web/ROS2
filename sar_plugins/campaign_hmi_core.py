#!/usr/bin/env python3
"""campaign_hmi_core.py -- nucleu pur (fara ROS, fara Tk) pentru PANOUL de campanie:
construieste/valideaza matricea de campanie, formateaza comanda de lansare, agrega /sar/status.
Frontend-ul (campaign_panel.py) doar deseneaza; toata logica + testele sunt aici."""
import json


def build_matrix(rmws, conditions, reps):
    """Lista de rulari {rmw, condition, rep} pentru matricea RMW x conditie x repetitii."""
    out = []
    for rmw in rmws:
        for c in conditions:
            for rep in range(1, reps + 1):
                out.append({"rmw": rmw, "condition": c, "rep": rep})
    return out


def validate_matrix(rmws, conditions, reps, known_conditions, known_rmws=("cyclonedds", "zenoh")):
    """Intoarce lista de erori (goala = matrice valida)."""
    errs = []
    if not rmws:
        errs.append("niciun RMW selectat")
    for r in rmws:
        if r not in known_rmws:
            errs.append("RMW necunoscut: %s" % r)
    if not conditions:
        errs.append("nicio conditie selectata")
    for c in conditions:
        if c not in known_conditions:
            errs.append("conditie necunoscuta: %s" % c)
    if reps < 1:
        errs.append("reps trebuie >= 1")
    return errs


def launch_command(mode, iface, rmws, conditions, reps, layers=("transport",),
                   script="run_campaign.py"):
    """Comanda de lansare a campaniei (string, fara a o executa)."""
    return ("python3 %s --mode %s --iface %s --rmws %s --conditions %s --reps %d --layers %s"
            % (script, mode, iface, ",".join(rmws), ",".join(conditions), reps, " ".join(layers)))


def aggregate_status(status_jsons):
    """Din ultimele mesaje /sar/status (JSON string sau dict), intoarce KPI-urile curente."""
    latest = None
    for s in status_jsons:
        try:
            latest = json.loads(s) if isinstance(s, str) else s
        except (ValueError, TypeError):
            continue
    if not latest:
        return {"coverage": 0.0, "victims": 0, "e2e_telemetry_ms": 0.0, "drones_linked": 0}
    return {"coverage": float(latest.get("coverage", 0.0)),
            "victims": int(latest.get("victims_found", latest.get("victims", 0))),
            "e2e_telemetry_ms": float(latest.get("e2e_telemetry_ms", 0.0)),
            "drones_linked": int(latest.get("drones_linked", 0))}


def _selftest():
    mat = build_matrix(["cyclonedds", "zenoh"], ["ideal", "loss_30"], 3)
    assert len(mat) == 2 * 2 * 3
    assert mat[0] == {"rmw": "cyclonedds", "condition": "ideal", "rep": 1}

    known = {"ideal", "loss_30", "gilbert_30"}
    assert validate_matrix(["cyclonedds"], ["ideal"], 5, known) == []
    errs = validate_matrix([], ["necunoscut"], 0, known)
    assert any("niciun RMW" in e for e in errs)
    assert any("necunoscuta" in e for e in errs)
    assert any("reps" in e for e in errs)

    cmd = launch_command("sil", "lo", ["cyclonedds"], ["ideal", "loss_30"], 5)
    assert "--mode sil" in cmd and "--rmws cyclonedds" in cmd and "--reps 5" in cmd

    agg = aggregate_status([
        '{"coverage":0.5,"victims_found":2,"e2e_telemetry_ms":30,"drones_linked":3}',
        '{"coverage":0.9,"victims_found":5,"e2e_telemetry_ms":45,"drones_linked":4}'])
    assert agg["coverage"] == 0.9 and agg["victims"] == 5 and agg["drones_linked"] == 4
    assert aggregate_status([])["coverage"] == 0.0
    print("TOATE VERIFICARILE campaign_hmi_core AU TRECUT")


if __name__ == "__main__":
    _selftest()
