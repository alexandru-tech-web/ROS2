"""Lumea apocaliptica — UNICA sursa de adevar pentru SIL, nodurile ROS,
dashboard si generarea lumii Gazebo (1 celula = 1 m)."""
WORLD = dict(
    w_cells=60, h_cells=60, cell=1.0,
    ruins=[(8, 8, 14, 20), (20, 30, 30, 36), (38, 10, 44, 24),
           (46, 40, 54, 48), (10, 44, 18, 52), (28, 50, 36, 56),
           (50, 4, 56, 10)],
    smoke=[(25, 15, 7), (44, 32, 6), (16, 38, 5)],
    victims=[(12, 25), (33, 41), (41, 7), (52, 52), (22, 54)],
)
ALT = 6.0
SENSE_R = 6.0
DRONES = {"d1": (3, 3), "d2": (3, 6), "d3": (6, 3), "d4": (6, 6)}
