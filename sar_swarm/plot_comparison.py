#!/usr/bin/env python3
"""Figura de comparatie intre scenarii (din rezultatele SIL masurate)."""
import csv, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

S = json.load(open("results/all_summaries.json"))
names = [s["scenario"] for s in S]
short = {"baseline":"referinta","loss_30":"pierdere 30%","loss_70":"pierdere 70%",
         "gcs_delay_spike":"varf latenta 2s","partition_2v2":"partitie 2v2",
         "drone_isolation":"izolare d2"}
cols = ["#2E8B57","#2E73CC","#1f4e79","#d8702e","#9b59b6","#c0392b"]

fig, ax = plt.subplots(2, 2, figsize=(13, 9))

# (a) acoperirea in timp
for s, c in zip(S, cols):
    n = s["scenario"]
    ts, cov = [], []
    with open(f"results/{n}_metrics.csv") as f:
        for row in csv.DictReader(f):
            ts.append(float(row["t_s"])); cov.append(100*float(row["coverage"]))
    ax[0,0].plot(ts, cov, color=c, lw=2, label=short[n])
ax[0,0].set_title("Acoperirea zonei in timp"); ax[0,0].set_xlabel("timp [s]")
ax[0,0].set_ylabel("acoperire [%]"); ax[0,0].grid(alpha=0.3)
ax[0,0].legend(fontsize=8); ax[0,0].axhline(95, ls=":", c="#888")

# (b) timp misiune + victime
x = range(len(S))
ax[0,1].bar(x, [s["mission_time_s"] for s in S], color=cols)
for i, s in enumerate(S):
    ax[0,1].text(i, s["mission_time_s"]+2,
                 f"{s['victims_found']}/{s['victims_total']}\nvictime",
                 ha="center", fontsize=8)
ax[0,1].set_xticks(list(x)); ax[0,1].set_xticklabels([short[n] for n in names],
                                                     rotation=20, fontsize=8)
ax[0,1].set_title("Timp de misiune (plafon 150 s) + victime gasite")
ax[0,1].set_ylabel("timp [s]"); ax[0,1].grid(axis="y", alpha=0.3)

# (c) pierdere configurata vs masurata + RTT p95
conf = [0, 30, 70, 2, 5, 5]
meas = [100*s["loss_measured_gcs"] for s in S]
ax[1,0].bar([i-0.2 for i in x], conf, width=0.4, label="configurat", color="#999")
ax[1,0].bar([i+0.2 for i in x], meas, width=0.4, label="masurat (modul inregistrare)",
            color="#2E73CC")
ax2 = ax[1,0].twinx()
ax2.plot(list(x), [s["rtt_p95_ms"] for s in S], "o--", color="#c0392b",
         label="RTT p95 [ms]")
ax2.set_yscale("log"); ax2.set_ylabel("RTT p95 [ms] (log)", color="#c0392b")
ax[1,0].set_xticks(list(x)); ax[1,0].set_xticklabels([short[n] for n in names],
                                                     rotation=20, fontsize=8)
ax[1,0].set_title("Pierdere de pachete: configurat vs masurat; RTT p95")
ax[1,0].set_ylabel("pierdere [%]"); ax[1,0].legend(fontsize=8, loc="upper left")
ax[1,0].grid(axis="y", alpha=0.3)

# (d) timp deconectat + recuperare + coeziune
ax[1,1].bar([i-0.2 for i in x], [s["disconnected_total_s"] for s in S],
            width=0.4, color="#d8702e", label="timp deconectat total [s]")
ax[1,1].bar([i+0.2 for i in x], [100*s["cohesion_mean"] for s in S],
            width=0.4, color="#2E8B57", label="coeziune medie [%]")
for i, s in enumerate(S):
    if s["recovery_time_mean_s"] > 0:
        ax[1,1].text(i-0.2, s["disconnected_total_s"]+1,
                     f"recup.\n{s['recovery_time_mean_s']}s", ha="center", fontsize=7)
ax[1,1].set_xticks(list(x)); ax[1,1].set_xticklabels([short[n] for n in names],
                                                     rotation=20, fontsize=8)
ax[1,1].set_title("Deconectare, recuperare si coeziunea roiului")
ax[1,1].legend(fontsize=8); ax[1,1].grid(axis="y", alpha=0.3)

fig.suptitle("Misiune SAR multi-drona sub degradare de retea -- metrici MASURATE in SIL "
             "(4 drone, 60x60 m, ruine+fum, 5 victime; store-and-forward activ)",
             fontsize=12, fontweight="bold")
fig.tight_layout(rect=[0,0,1,0.96])
fig.savefig("results/comparatie_scenarii.png", dpi=140)
print("[ok] results/comparatie_scenarii.png")
