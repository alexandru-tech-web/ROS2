#!/usr/bin/env python3
"""test_vision_core.py — verificari pentru viziune, pe imagini SINTETICE.
Determinist, fara Gazebo: desenam dreptunghiuri colorate cu numpy + cv2."""
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vision_core import (detect_blobs, pixel_to_bearing, ground_range,
                         project_to_world)

N = 0
def check(c, m):
    global N; assert c, m; N += 1; print(f"  [ok] {m}")

W, H = 640, 480


def frame():
    return np.zeros((H, W, 3), np.uint8)   # fundal negru (ignorat: S=V=0)


# o singura pata rosie centrata
img = frame()
cv2.rectangle(img, (300, 220), (340, 260), (0, 0, 255), -1)   # BGR rosu
dets = detect_blobs(img)
check(len(dets) == 1 and dets[0]["color"] == "red", "detecteaza o pata rosie")
check(abs(dets[0]["cx"] - 320) < 1.5 and abs(dets[0]["cy"] - 240) < 1.5,
      "centroid corect (~320,240)")

# verde (mare) + albastru (mic) -> doua detectii, sortate dupa arie
img = frame()
cv2.rectangle(img, (100, 100), (180, 180), (0, 255, 0), -1)   # verde 80x80
cv2.rectangle(img, (400, 300), (440, 340), (255, 0, 0), -1)   # albastru 40x40
dets = detect_blobs(img)
check(len(dets) == 2, "doua culori -> doua detectii")
check(dets[0]["color"] == "green" and dets[1]["color"] == "blue",
      "sortare descrescatoare dupa arie (verde > albastru)")

# pata sub pragul de arie e filtrata
img = frame()
cv2.rectangle(img, (320, 240), (325, 245), (0, 0, 255), -1)   # 5x5 = 25 px
check(len(detect_blobs(img, min_area=80)) == 0, "pata mai mica decat min_area filtrata")

# bearing: centrul -> 0, semnul corect
check(abs(pixel_to_bearing(W / 2, W, 1.0)) < 1e-12, "bearing 0 la centru")
check(pixel_to_bearing(0, W, 1.0) > 0 and pixel_to_bearing(W, W, 1.0) < 0,
      "bearing: stanga pozitiv, dreapta negativ")

# range pe sol: scade cand randul coboara spre baza imaginii
r_sus = ground_range(300, H, 0.8, 0.5, 0.3)
r_jos = ground_range(400, H, 0.8, 0.5, 0.3)
check(r_sus is not None and r_jos is not None and r_jos < r_sus,
      "ground_range scade pe masura ce cy coboara")
check(ground_range(0, H, 0.8, 0.5, 0.3) is None, "deasupra orizontului -> None")

# proiectie monoculara cu geometrie cunoscuta: cam_h=1, pitch=45deg, cy=centru
cam = {"width": W, "height": H, "hfov": 1.0, "vfov": 0.8,
       "cam_h": 1.0, "pitch": math.pi / 4}
wx, wy = project_to_world({"cx": W / 2, "cy": H / 2}, (0.0, 0.0, 0.0), cam)
check(abs(wx - 1.0) < 1e-6 and abs(wy) < 1e-6,
      "proiectie: range=1 m drept in fata -> (1,0)")

# refinarea cu lidar are prioritate fata de estimarea monoculara
wx, wy = project_to_world({"cx": W / 2, "cy": H / 2}, (0.0, 0.0, 0.0), cam,
                          lidar_range=5.0)
check(abs(wx - 5.0) < 1e-9 and abs(wy) < 1e-9,
      "lidar_range suprascrie estimarea monoculara -> (5,0)")

print(f"\nTOATE TESTELE VISION AU TRECUT: {N} verificari.")
