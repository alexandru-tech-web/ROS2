#!/usr/bin/env python3
"""coverage.py — CoverageGrid: urmarirea acoperirii zonei de cautare.

Grila booleana peste aria misiunii; fiecare drona "vopseste" un disc cu raza
senzorului in jurul pozitiei ei. Metricile rezultate sunt cele care lipseau
din etajul de misiune: procentul acoperit in timp, timpul-pana-la-X%,
si exportul CSV in acelasi stil ca jurnalele existente (~/sar_data).
"""
import math

import numpy as np


class CoverageGrid:
    def __init__(self, xmin, xmax, ymin, ymax, cell=1.0):
        assert xmax > xmin and ymax > ymin and cell > 0
        self.xmin, self.xmax = float(xmin), float(xmax)
        self.ymin, self.ymax = float(ymin), float(ymax)
        self.cell = float(cell)
        self.nx = max(1, int(math.ceil((self.xmax - self.xmin) / self.cell)))
        self.ny = max(1, int(math.ceil((self.ymax - self.ymin) / self.cell)))
        self.grid = np.zeros((self.ny, self.nx), dtype=bool)
        self._milestones = {}          # pct atins -> t

    # ---- indexare ----
    def _ij(self, x, y):
        i = int((y - self.ymin) / self.cell)
        j = int((x - self.xmin) / self.cell)
        return i, j

    def in_bounds(self, x, y):
        return self.xmin <= x < self.xmax and self.ymin <= y < self.ymax

    # ---- marcare ----
    def mark_disc(self, x, y, r, t=None):
        """Marcheaza acoperit discul de raza r centrat in (x, y).
        Functioneaza si daca centrul e partial in afara ariei."""
        if r <= 0:
            return
        i0, j0 = self._ij(x, y)
        rc = int(math.ceil(r / self.cell)) + 1
        ilo, ihi = max(i0 - rc, 0), min(i0 + rc + 1, self.ny)
        jlo, jhi = max(j0 - rc, 0), min(j0 + rc + 1, self.nx)
        if ilo >= ihi or jlo >= jhi:
            return
        ii, jj = np.mgrid[ilo:ihi, jlo:jhi]
        # centrul celulei
        cx = self.xmin + (jj + 0.5) * self.cell
        cy = self.ymin + (ii + 0.5) * self.cell
        mask = (cx - x) ** 2 + (cy - y) ** 2 <= r * r
        self.grid[ilo:ihi, jlo:jhi] |= mask
        if t is not None:
            self._update_milestones(t)

    def mark_path(self, xy_list, r, t=None):
        for (x, y) in xy_list:
            self.mark_disc(x, y, r)
        if t is not None:
            self._update_milestones(t)

    # ---- metrici ----
    def percent(self):
        return 100.0 * float(self.grid.sum()) / self.grid.size

    def _update_milestones(self, t):
        p = self.percent()
        for goal in (25, 50, 75, 90, 95, 99):
            if p >= goal and goal not in self._milestones:
                self._milestones[goal] = float(t)

    def time_to(self, pct_goal):
        """Timpul la care s-a atins pct_goal% (None daca inca nu)."""
        return self._milestones.get(int(pct_goal))

    def milestones(self):
        return dict(self._milestones)

    # ---- export ----
    CSV_HEADER = "t_s,pct,cells_covered,cells_total\n"

    def csv_row(self, t):
        return (f"{t:.2f},{self.percent():.3f},"
                f"{int(self.grid.sum())},{self.grid.size}\n")

    def summary(self, t=None):
        s = {"pct": round(self.percent(), 2),
             "cells": int(self.grid.sum()), "total": int(self.grid.size),
             "milestones": self.milestones()}
        if t is not None:
            s["t"] = round(float(t), 2)
        return s
