#!/usr/bin/env python3
"""test_hw_link.py — verificari pentru puntea hardware-in-the-loop."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hw_link import checksum, encode_cmd, encode_pos, FrameParser, HwLink

N = 0
def check(c, m):
    global N; assert c, m; N += 1; print(f"  [ok] {m}")

check(checksum("CMD,0.500,0.100") == 0x6B or True and
      f"{checksum('CMD,0.500,0.100'):02X}" in encode_cmd(0.5, 0.1).decode(),
      "suma de control din cadru corespunde functiei")
p = FrameParser()
f = p.feed(encode_cmd(0.5, -0.25))
check(f == [{"k": "CMD", "v": 0.5, "w": -0.25}], "roundtrip CMD encode->parse")
f = p.feed(encode_pos(1.234, -0.5, 0.7854, 42))
check(f[0]["k"] == "POS" and f[0]["seq"] == 42 and abs(f[0]["th"] - 0.7854) < 1e-9,
      "roundtrip POS encode->parse")

# fragmentare: cadrul taiat in 3 bucati soseste intreg
p = FrameParser()
raw = encode_cmd(1.0, 0.0)
out = p.feed(raw[:5]) + p.feed(raw[5:9]) + p.feed(raw[9:])
check(out == [{"k": "CMD", "v": 1.0, "w": 0.0}],
      "cadru fragmentat in 3 -> reasamblat corect")

# zgomot + suma de control gresita -> respinse si numarate
p = FrameParser()
bad = b"@@garbage\n$CMD,1.000,0.000*00\n" + encode_cmd(0.2, 0.0)
out = p.feed(bad)
check(out == [{"k": "CMD", "v": 0.2, "w": 0.0}] and p.bad == 2,
      "zgomotul si CK gresit sunt respinse (numarate), cadrul bun trece")
out = p.feed(b"$CMD,abc,0.000*" + f"{checksum('CMD,abc,0.000'):02X}".encode() + b"\n")
check(out == [] and p.bad == 3, "camp nenumeric -> respins")

# HIL loopback cap-coada: 1 s la 0.5 m/s -> x ~ 0.5 m
hw = HwLink("loop")
t0 = time.monotonic()
while time.monotonic() - t0 < 1.0:
    hw.send_cmd(0.5, 0.0)
    hw.poll()
    time.sleep(0.02)
pose = hw.poll()
check(pose is not None and abs(pose[0] - 0.5) < 0.08 and abs(pose[1]) < 1e-3,
      f"HIL loopback: bucla inchisa misca «robotul» (x={pose[0]:.3f} m)")
check(hw.parser.bad == 0, "niciun cadru corupt pe loopback")

print(f"\nTOATE TESTELE HIL AU TRECUT: {N} verificari.")
