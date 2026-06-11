#!/usr/bin/env python3
"""vision_core.py — nucleul PUR de viziune (OpenCV clasic, fara ROS, fara Gazebo).

Recunoastere de obiecte prin CULOARE (segmentare HSV + contururi) si proiectia
unui obiect detectat din PIXEL in COORDONATE LUMII (model pinhole + ipoteza
sol-plat), cu refinare optionala din lidar. Totul determinist si testabil pe
imagini SINTETICE (numpy + cv2.rectangle), deci validabil headless.

De ce HSV clasic si nu deep learning: e determinist, offline, fara descarcari
de modele, si se aseaza pe filosofia repo-ului ("nucleu pur + teste"). Tintele
din lumea Gazebo sunt cuburi colorate -> aceeasi paleta COLORS e si configul
culorilor din generatorul lumii si benzile de detectie de aici.

Math proiectie (vezi project_to_world / ground_range):
  f_px = (W/2) / tan(hfov/2)         # focala in pixeli (orizontal)
  bearing = atan2(W/2 - cx, f_px)    # + = stanga, - = dreapta
  f_py = (H/2) / tan(vfov/2)
  elev = atan2(cy - H/2, f_py)       # + in jos (randuri sub centru)
  depression = pitch + elev          # cat de jos bate raza fata de orizontala
  range = cam_h / tan(depression)    # valid DOAR daca depression > 0
  (wx, wy) = (x + range*cos(th+bearing), y + range*sin(th+bearing))

Moduri de esec (documentate, de aceea ground_range poate intoarce None):
  - singularitate la ORIZONT: depression -> 0 => range -> infinit;
  - ipoteza SOL-PLAT e falsa pe teren accidentat (heightmap) => eroare de
    range creste cu panta; de aici refinarea optionala cu lidar (range real la
    bearing-ul detectiei);
  - sensibilitate la pitch/inaltimea camerei (eroare mare departe de rover).
"""
import math

import cv2
import numpy as np

# Paleta de culori = config comun (generator de lume + detector). HSV OpenCV:
# H in [0,180], S,V in [0,255]. Rosul e la capetele cercului de nuanta, deci
# are DOUA benzi.
COLORS = {
    "red":   [((0, 120, 70), (10, 255, 255)),
              ((170, 120, 70), (180, 255, 255))],
    "green": [((40, 80, 60), (85, 255, 255))],
    "blue":  [((95, 120, 70), (130, 255, 255))],
    "yellow": [((20, 120, 90), (35, 255, 255))],
}


def detect_blobs(bgr, colors=COLORS, min_area=80):
    """Detecteaza pete colorate intr-o imagine BGR.

    Returneaza o lista de {"cx","cy","area","color"}, sortata descrescator
    dupa arie (cea mai mare detectie = candidatul-tinta).
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    out = []
    for color, ranges in colors.items():
        mask = None
        for lo, hi in ranges:
            m = cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
            mask = m if mask is None else cv2.bitwise_or(mask, m)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            mom = cv2.moments(c)
            if mom["m00"] == 0:
                continue
            out.append({"cx": mom["m10"] / mom["m00"],
                        "cy": mom["m01"] / mom["m00"],
                        "area": float(area), "color": color})
    out.sort(key=lambda d: d["area"], reverse=True)
    return out


def pixel_to_bearing(cx, width, hfov):
    """Unghiul orizontal (rad) al unei coloane cx fata de axa optica.

    + = stanga (cx < centru), - = dreapta. Pur trigonometric (pinhole).
    """
    f_px = (width / 2.0) / math.tan(hfov / 2.0)
    return math.atan2(width / 2.0 - cx, f_px)


def ground_range(cy, height, vfov, cam_h, pitch):
    """Distanta pe sol (m) pana la punctul de pe randul cy, ipoteza sol-plat.

    Intoarce None daca raza bate la sau peste orizont (depression <= 0) —
    acolo range-ul ar fi infinit/negativ si estimarea nu are sens.
    """
    f_py = (height / 2.0) / math.tan(vfov / 2.0)
    elev = math.atan2(cy - height / 2.0, f_py)   # + in jos
    depression = pitch + elev
    if depression <= 1e-3:
        return None
    return cam_h / math.tan(depression)


def project_to_world(det, rover_pose, cam, lidar_range=None):
    """Proiecteaza o detectie in coordonatele lumii (wx, wy) sau None.

    det        : {"cx","cy",...} din detect_blobs
    rover_pose : (x, y, th) al roverului in lume
    cam        : {"width","height","hfov","vfov","cam_h","pitch"}
    lidar_range: daca e dat, foloseste range-ul REAL (refinare lidar) in locul
                 estimarii monoculare sol-plat.
    """
    x, y, th = rover_pose
    bearing = pixel_to_bearing(det["cx"], cam["width"], cam["hfov"])
    if lidar_range is not None:
        rng = lidar_range
    else:
        rng = ground_range(det["cy"], cam["height"], cam["vfov"],
                           cam["cam_h"], cam["pitch"])
    if rng is None:
        return None
    wb = th + bearing
    return x + rng * math.cos(wb), y + rng * math.sin(wb)
