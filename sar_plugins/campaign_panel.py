#!/usr/bin/env python3
"""campaign_panel.py -- PANOU de campanie unificat (Tkinter) peste nucleul PUR campaign_hmi_core.
Selectezi RMW x conditii x reps x mod (SIL/HIL) si construieste/valideaza comanda de lansare
(run_campaign.py). Toata logica + testele sunt in campaign_hmi_core; aici doar GUI subtire.
Ruleaza: python3 campaign_panel.py    (NU se poate verifica vizual headless -- de revizuit la rulare)."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import campaign_hmi_core as chc

# conditii cunoscute: din bench_core daca e accesibil, altfel o lista implicita rezonabila
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "c1_benchmark"))
    from bench_core import CONDITIONS
    KNOWN_CONDS = [c["name"] for c in CONDITIONS]
except Exception:
    KNOWN_CONDS = ["ideal", "loss_5", "loss_15", "loss_30", "gilbert_30", "lat200_l15"]

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    sys.exit("Lipseste Tkinter: sudo apt install -y python3-tk")


def build_ui():
    root = tk.Tk()
    root.title("Panou campanie C1 (SIL/HIL)")

    rmw_vars = {r: tk.BooleanVar(value=(r == "cyclonedds")) for r in ("cyclonedds", "zenoh")}
    frm_rmw = ttk.LabelFrame(root, text="RMW")
    frm_rmw.pack(fill="x", padx=6, pady=4)
    for r, v in rmw_vars.items():
        ttk.Checkbutton(frm_rmw, text=r, variable=v).pack(side="left", padx=4)

    cond_vars = {c: tk.BooleanVar(value=(c in ("ideal", "loss_30", "gilbert_30"))) for c in KNOWN_CONDS}
    frm_c = ttk.LabelFrame(root, text="Conditii")
    frm_c.pack(fill="x", padx=6, pady=4)
    for i, (c, v) in enumerate(cond_vars.items()):
        ttk.Checkbutton(frm_c, text=c, variable=v).grid(row=i // 3, column=i % 3, sticky="w")

    frm_o = ttk.LabelFrame(root, text="Optiuni")
    frm_o.pack(fill="x", padx=6, pady=4)
    mode = tk.StringVar(value="sil")
    iface = tk.StringVar(value="lo")
    reps = tk.IntVar(value=5)
    transport = tk.BooleanVar(value=True)
    mission = tk.BooleanVar(value=False)
    ttk.Label(frm_o, text="mod:").grid(row=0, column=0)
    ttk.Combobox(frm_o, textvariable=mode, values=["sil", "hil"], width=5).grid(row=0, column=1)
    ttk.Label(frm_o, text="iface:").grid(row=0, column=2)
    ttk.Entry(frm_o, textvariable=iface, width=8).grid(row=0, column=3)
    ttk.Label(frm_o, text="reps:").grid(row=0, column=4)
    ttk.Spinbox(frm_o, from_=1, to=20, textvariable=reps, width=4).grid(row=0, column=5)
    ttk.Checkbutton(frm_o, text="transport", variable=transport).grid(row=1, column=0, columnspan=2, sticky="w")
    ttk.Checkbutton(frm_o, text="mission", variable=mission).grid(row=1, column=2, columnspan=2, sticky="w")

    out = tk.Text(root, height=5, width=72)
    out.pack(fill="x", padx=6, pady=4)

    def build():
        rmws = [r for r, v in rmw_vars.items() if v.get()]
        conds = [c for c, v in cond_vars.items() if v.get()]
        layers = tuple(name for name, v in (("transport", transport), ("mission", mission))
                       if v.get()) or ("transport",)
        errs = chc.validate_matrix(rmws, conds, reps.get(), set(KNOWN_CONDS))
        out.delete("1.0", "end")
        if errs:
            out.insert("end", "ERORI:\n" + "\n".join(errs))
            return None
        n = len(chc.build_matrix(rmws, conds, reps.get()))
        cmd = chc.launch_command(mode.get(), iface.get(), rmws, conds, reps.get(), layers)
        out.insert("end", "matrice: %d rulari x %d straturi\n%s\n" % (n, len(layers), cmd))
        return cmd

    def run():
        cmd = build()
        if cmd:
            subprocess.Popen(cmd.split())

    bar = ttk.Frame(root)
    bar.pack(fill="x", padx=6, pady=4)
    ttk.Button(bar, text="Construieste comanda", command=build).pack(side="left", padx=4)
    ttk.Button(bar, text="RUN", command=run).pack(side="left", padx=4)
    return root


def main():
    build_ui().mainloop()


if __name__ == "__main__":
    main()
