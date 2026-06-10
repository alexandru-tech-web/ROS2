#!/usr/bin/env python3
"""fault_panel.py — BANCUL DE DEFECTE CUSTOM (deschis din ecranul cu date).

Control fin, per-legatura, peste reteaua misiunii: pentru fiecare dintre
cele 10 legaturi (gcs-d1..d4 si intre drone) poti seta LIVE latenta [ms],
jitter-ul [ms], pierderea [0..1] si taierea completa (JOS), plus un rand
"TOATE legaturile" pentru setari globale. Trimite comenzi JSON pe
/sar/operator (action=set_link / set_all), aplicate de fault_injector si
respectate de toate nodurile la receptie (gating + intarziere + drop).
"""
import tkinter as tk
from tkinter import ttk

from world_config import DRONES

NODES = ["gcs"] + sorted(DRONES)
LINKS = ["-".join(sorted((a, b)))
         for i, a in enumerate(NODES) for b in NODES[i + 1:]]
_open = {"win": None}


def _row_vals(ms_e, jit_e, loss_e):
    def f(entry, default):
        try:
            return float(entry.get())
        except ValueError:
            return default
    return f(ms_e, 40.0), f(jit_e, 0.0), max(0.0, min(1.0, f(loss_e, 0.0)))


def open_panel(parent, send):
    """Deschide (sau aduce in fata) bancul de defecte. send = publisher JSON."""
    if _open["win"] is not None and _open["win"].winfo_exists():
        _open["win"].lift()
        return
    win = tk.Toplevel(parent)
    _open["win"] = win
    win.title("Banc de defecte — control per-legatura")
    frm = ttk.Frame(win, padding=10)
    frm.pack(fill="both", expand=True)

    for c, h in enumerate(("legatura", "JOS", "latenta [ms]", "jitter [ms]",
                           "pierdere [0..1]", "")):
        ttk.Label(frm, text=h, font=("TkDefaultFont", 9, "bold")
                  ).grid(row=0, column=c, padx=4, pady=(0, 6))

    # ----- randul global -----
    ttk.Label(frm, text="TOATE legaturile",
              font=("TkDefaultFont", 9, "bold")).grid(row=1, column=0,
                                                      sticky="w")
    g_down = tk.BooleanVar(value=False)
    ttk.Checkbutton(frm, variable=g_down).grid(row=1, column=1)
    g_ms, g_jit, g_loss = (ttk.Entry(frm, width=8) for _ in range(3))
    for c, (e, v) in enumerate(((g_ms, "40"), (g_jit, "0"), (g_loss, "0")),
                               start=2):
        e.insert(0, v)
        e.grid(row=1, column=c, padx=4)

    def apply_all():
        ms, jit, loss = _row_vals(g_ms, g_jit, g_loss)
        send({"type": "fault", "action": "set_all", "ms": ms, "jit": jit,
              "loss": loss, "down": bool(g_down.get())})
    ttk.Button(frm, text="Aplica tuturor", command=apply_all
               ).grid(row=1, column=5, padx=4)
    ttk.Separator(frm, orient="horizontal").grid(row=2, column=0,
                                                 columnspan=6, sticky="we",
                                                 pady=6)

    # ----- randurile per-legatura -----
    for i, link in enumerate(LINKS, start=3):
        ttk.Label(frm, text=link).grid(row=i, column=0, sticky="w")
        v_down = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, variable=v_down).grid(row=i, column=1)
        e_ms, e_jit, e_loss = (ttk.Entry(frm, width=8) for _ in range(3))
        for c, (e, v) in enumerate(((e_ms, "40"), (e_jit, "0"),
                                    (e_loss, "0")), start=2):
            e.insert(0, v)
            e.grid(row=i, column=c, padx=4)

        def apply_one(link=link, d=v_down, a=e_ms, b=e_jit, c_=e_loss):
            ms, jit, loss = _row_vals(a, b, c_)
            send({"type": "fault", "action": "set_link", "link": link,
                  "ms": ms, "jit": jit, "loss": loss,
                  "down": bool(d.get())})
        ttk.Button(frm, text="Aplica", command=apply_one
                   ).grid(row=i, column=5, padx=4)

    foot = ttk.Frame(frm)
    foot.grid(row=3 + len(LINKS), column=0, columnspan=6, sticky="we",
              pady=(10, 0))

    def heal():
        send({"type": "fault", "action": "set_all", "ms": 40.0, "jit": 0.0,
              "loss": 0.0, "down": False})
    ttk.Button(foot, text="Vindeca tot (40 ms / 0 / 0, toate SUS)",
               command=heal).pack(side="left")
    ttk.Label(foot, foreground="#888", wraplength=420, justify="left",
              text="  Valorile se aplica la apasarea Aplica (panoul nu "
                   "oglindeste starea curenta). Efectul e vizibil in "
                   "RTT/pierdere pe ecranul cu date si in "
                   "~/sar_data/op_commands.csv pentru comenzile tale."
              ).pack(side="left", padx=8)
