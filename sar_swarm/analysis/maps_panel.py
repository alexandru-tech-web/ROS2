#!/usr/bin/env python3
"""maps_panel.py -- compune hartile SAR a 3 scenarii intr-un singur panel,
ca sa arate "retea buna -> retea proasta -> victime ratate" intr-o imagine.
Folosire: python3 maps_panel.py <dir_cu_harti> [scenariu1 scenariu2 scenariu3]
Implicit: baseline loss_70 mesh_relay. Iese: <dir>/fig_maps_panel.png
"""
import sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
SCN = sys.argv[2:] if len(sys.argv) > 2 else ["baseline", "loss_70", "mesh_relay"]
SUBTITLES = {"baseline": "retea buna", "loss_70": "pierdere severa (70%)",
             "mesh_relay": "fara relay mesh"}

imgs = []
for s in SCN:
    p = os.path.join(ROOT, f"{s}_map.png")
    if os.path.exists(p):
        imgs.append((s, p))
    else:
        print(f"[!] lipseste {p} -- sarit")

if not imgs:
    sys.exit("[!] nicio harta gasita (asteptam <scenariu>_map.png in " + ROOT + ")")

n = len(imgs)
fig, axes = plt.subplots(1, n, figsize=(6 * n, 6))
if n == 1:
    axes = [axes]
labels = "abcdefgh"
for ax, (s, p), lab in zip(axes, imgs, labels):
    ax.imshow(mpimg.imread(p))
    ax.axis("off")
    sub = SUBTITLES.get(s, "")
    ax.set_title(f"({lab}) {s}" + (f"\n{sub}" if sub else ""), fontsize=12)

fig.suptitle("Misiune SAR sub degradare crescatoare a comunicatiei",
             fontsize=14, y=1.02)
plt.tight_layout()
out = os.path.join(ROOT, "fig_maps_panel.png")
plt.savefig(out, dpi=130, bbox_inches="tight")
print(f"[ok] {out}  ({n} harti: {', '.join(s for s,_ in imgs)})")
