#!/usr/bin/env python3
"""sar_launcher.py -- MENIUL DE MISIUNE (fara dependinta de ROS in proces).

Dintr-o fereastra alegi:
  - middleware-ul: CycloneDDS / Zenoh / FastDDS (cele indisponibile apar
    dezactivate, cu pachetul apt de instalat);
  - modul: SIL (fara ROS) / ROS pur / ROS + Gazebo;
  - scenariul de degradare (fisierele din scenarios/ + none.yaml = manual);
  - autostart, dashboard, regenerarea lumii Gazebo.

"Porneste" construieste comanda prin launcher_core.build_plan, seteaza
RMW_IMPLEMENTATION pentru TOATE nodurile, porneste automat routerul Zenoh
cand e cazul (rmw_zenohd) si ruleaza misiunea ca proces-copil, cu jurnalul
live in fereastra. "Opreste" inchide ordonat tot grupul de procese.

Rulare:  python3 sar_launcher.py        (necesita doar python3-tk)
"""
import os
import signal
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launcher_core import (RMW, APT, rmw_available, build_plan, ROUTER_CMD)

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    print("Lipseste Tkinter: sudo apt install -y python3-tk", file=sys.stderr)
    sys.exit(1)

PKG = os.path.dirname(os.path.abspath(__file__))


class Launcher:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.router = None
        root.title("SAR Swarm -- meniul de misiune")
        frm = ttk.Frame(root, padding=10)
        frm.pack(fill="both", expand=True)

        # ----- middleware -----
        ttk.Label(frm, text="Middleware (RMW):",
                  font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0,
                                                           sticky="w")
        self.rmw = tk.StringVar(value="CycloneDDS")
        r = 1
        for name in RMW:
            ok = rmw_available(name)
            rb = ttk.Radiobutton(frm, text=name, value=name,
                                 variable=self.rmw,
                                 state="normal" if ok else "disabled")
            rb.grid(row=r, column=0, sticky="w", padx=12)
            hint = "instalat" if ok else f"lipseste: sudo apt install {APT[name]}"
            ttk.Label(frm, foreground="#3a7" if ok else "#b55",
                      text=hint).grid(row=r, column=1, sticky="w")
            r += 1
        ttk.Label(frm, foreground="#888", wraplength=420, justify="left",
                  text="Zenoh: routerul rmw_zenohd este pornit automat de "
                       "meniu. SIL nu foloseste RMW (rulare pura Python)."
                  ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 6))
        r += 1

        # ----- mod + scenariu + optiuni -----
        ttk.Label(frm, text="Mod:", font=("TkDefaultFont", 10, "bold")
                  ).grid(row=r, column=0, sticky="w")
        self.mode = tk.StringVar(value="ros")
        for i, (lbl, val) in enumerate((("SIL (fara ROS)", "sil"),
                                        ("ROS pur", "ros"),
                                        ("ROS + Gazebo", "gazebo"))):
            ttk.Radiobutton(frm, text=lbl, value=val, variable=self.mode
                            ).grid(row=r + 1 + i, column=0, sticky="w", padx=12)
        scen_files = sorted(f for f in os.listdir(os.path.join(PKG, "scenarios"))
                            if f.endswith(".yaml")) + ["none.yaml"]
        ttk.Label(frm, text="Scenariu:", font=("TkDefaultFont", 10, "bold")
                  ).grid(row=r, column=1, sticky="w")
        self.scen = tk.StringVar(value="baseline.yaml")
        ttk.Combobox(frm, textvariable=self.scen, values=scen_files,
                     state="readonly", width=24
                     ).grid(row=r + 1, column=1, sticky="w")
        self.autostart = tk.BooleanVar(value=True)
        self.dash = tk.BooleanVar(value=True)
        self.regen = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="autostart (porneste singura)",
                        variable=self.autostart
                        ).grid(row=r + 2, column=1, sticky="w")
        ttk.Checkbutton(frm, text="ecranul cu date (dashboard)",
                        variable=self.dash).grid(row=r + 3, column=1, sticky="w")
        ttk.Checkbutton(frm, text="regenereaza lumea Gazebo",
                        variable=self.regen).grid(row=r + 4, column=1,
                                                  sticky="w")
        r += 5

        # ----- butoane + stare + jurnal -----
        bar = ttk.Frame(frm)
        bar.grid(row=r, column=0, columnspan=2, sticky="we", pady=8)
        self.btn_start = ttk.Button(bar, text="> Porneste misiunea",
                                    command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(bar, text="# Opreste", state="disabled",
                                   command=self.stop)
        self.btn_stop.pack(side="left", padx=6)
        self.status = tk.StringVar(value="pregatit")
        ttk.Label(bar, textvariable=self.status).pack(side="left", padx=10)
        self.log = tk.Text(frm, height=16, width=78, bg="#14141a",
                           fg="#cfcfcf", state="disabled")
        self.log.grid(row=r + 1, column=0, columnspan=2, sticky="nsew")
        frm.rowconfigure(r + 1, weight=1)
        frm.columnconfigure(1, weight=1)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------
    def _println(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line)
        if int(self.log.index("end-1c").split(".")[0]) > 600:
            self.log.delete("1.0", "2.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _reader(self, proc):
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode(errors="replace")
            self.root.after(0, self._println, line)
        self.root.after(0, self._on_exit)

    def start(self):
        cfg = dict(mode=self.mode.get(), rmw=self.rmw.get(),
                   scenario=self.scen.get(),
                   autostart=self.autostart.get(),
                   dashboard=self.dash.get(), regen_world=self.regen.get())
        try:
            plan = build_plan(cfg, PKG)
        except ValueError as e:
            self.status.set(f"eroare: {e}")
            return
        for pre in plan["pre"]:
            self._println(f"$ {' '.join(pre)}\n")
            subprocess.run(pre, cwd=PKG)
        env = {**os.environ, **plan["env"]}
        if plan["router"]:
            self._println("$ pornesc routerul Zenoh (rmw_zenohd)...\n")
            self.router = subprocess.Popen(
                ROUTER_CMD, env=env, cwd=PKG, preexec_fn=os.setsid,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._println(f"$ RMW_IMPLEMENTATION={plan['env'].get('RMW_IMPLEMENTATION','-')} "
                      f"{' '.join(plan['cmd'])}\n")
        self.proc = subprocess.Popen(
            plan["cmd"], env=env, cwd=PKG, preexec_fn=os.setsid,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        threading.Thread(target=self._reader, args=(self.proc,),
                         daemon=True).start()
        self.status.set(f"RULEAZA -- {cfg['mode']} / {cfg['rmw']} / {cfg['scenario']}")
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

    def _kill_group(self, proc, sig):
        if proc and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), sig)
            except ProcessLookupError:
                pass

    def stop(self):
        self.status.set("opresc...")
        self._kill_group(self.proc, signal.SIGINT)
        self.root.after(2500, lambda: (self._kill_group(self.proc,
                                                        signal.SIGTERM),
                                       self._kill_group(self.router,
                                                        signal.SIGTERM)))

    def _on_exit(self):
        self._kill_group(self.router, signal.SIGTERM)
        self.router = None
        self.status.set("oprit -- pregatit pentru urmatoarea rulare")
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    def on_close(self):
        self.stop()
        self.root.after(600, self.root.destroy)


def main():
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
