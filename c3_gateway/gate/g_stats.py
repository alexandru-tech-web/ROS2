"""g_stats.py <eticheta> -- rezuma iesirea lui g_timing.sh (stdin: 't0 recv tinit msgN')."""
import statistics as st
import sys

tot, desc, idx, ratate = [], [], [], 0
for linie in sys.stdin:
    c = linie.split()
    if not c:
        continue
    if c[0] == "NIMIC":
        ratate += 1
        continue
    t0, recv, tinit, texec = (float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    tot.append(recv - t0)
    desc.append(recv - texec)
    idx.append(c[4] if len(c) > 4 else "?")

print("  %s: N=%d ratate=%d" % (sys.argv[1], len(tot), ratate))
if tot:
    print("    total de la spawn [s]: %s | MEDIANA %.3f"
          % (" ".join("%.3f" % x for x in tot), st.median(tot)))
    print("    transport (import rclpy -> primul mesaj) [s]: %s | MEDIANA %.3f"
          % (" ".join("%.3f" % x for x in desc), st.median(desc)))
    print("    primul mesaj primit:  %s" % " ".join(idx))
