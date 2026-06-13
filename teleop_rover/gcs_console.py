#!/usr/bin/env python3
"""gcs_console.py - PUPITRU GCS cu harta (ROS 2, zero-build).

Operatorul (GCS) da CLICK pe harta si trimite coordonata-tinta roverului
(geometry_msgs/PoseStamped pe /teleop/goal). Pe harta se vad: conturul terenului,
punctele de interes (tintele colorate), roverul (sageata, din /teleop/pose) si
tinta curenta (X galben). Roverul porneste OPRIT (goto_node in mod gcs) si se
misca doar dupa ce GCS da o tinta - exact modelul SAR: GCS decide unde, comanda
trece prin legatura degradata pana la robot.

IMPORTANT - acelasi RMW ca roiul:
    export RMW_IMPLEMENTATION=rmw_zenoh_cpp     # daca launch-ul e cu rmw:=zenoh
    # (routerul Zenoh trebuie sa fie pornit - launch-ul perception il porneste)
    python3 gcs_console.py
sau, daca lumea e pe Cyclone:
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    python3 gcs_console.py

Parametri (--ros-args -p nume:=val):
    goal_topic   (/teleop/goal)   unde publica tinta
    pose_topic   (/teleop/pose)   de unde citeste pozitia roverului
    frame        (map)            frame-ul din header-ul tintei
    terrain_half (20.0)           jumatate din latura terenului [m]
"""
import json
import math
import os
import sys
import threading
import time

# --- nucleu pur: maparea harta <-> lume (testabil fara ROS/Tk) ---

def world_to_canvas(x, y, w, h, half):
    """Lume [-half,half]^2 -> pixel pe panza w x h (y in jos pe ecran)."""
    cx = (x + half) / (2.0 * half) * w
    cy = h - (y + half) / (2.0 * half) * h
    return cx, cy


def canvas_to_world(px, py, w, h, half):
    """Pixel pe panza -> lume [-half,half]^2."""
    x = px / w * (2.0 * half) - half
    y = (h - py) / h * (2.0 * half) - half
    return x, y


def _selftest():
    W = H = 600
    half = 20.0
    for (x, y) in [(0, 0), (8, 3), (-6, 5), (5, -7), (half, -half), (-half, half)]:
        px, py = world_to_canvas(x, y, W, H, half)
        rx, ry = canvas_to_world(px, py, W, H, half)
        assert abs(rx - x) < 1e-6 and abs(ry - y) < 1e-6, (x, y, rx, ry)
    # coltul lume (-half,-half) -> stanga-jos pe panza (0, H)
    px, py = world_to_canvas(-half, -half, W, H, half)
    assert abs(px - 0) < 1e-6 and abs(py - H) < 1e-6, (px, py)
    # centrul lumii -> centrul panzei
    px, py = world_to_canvas(0, 0, W, H, half)
    assert abs(px - W / 2) < 1e-6 and abs(py - H / 2) < 1e-6
    print("[ok] _selftest mapare harta<->lume: round-trip + colturi corecte")


# punctele de interes cunoscute de GCS (aceleasi ca OBJECTS din gen_rough_world.py)
POI = [
    ("rosie", 8.0, 3.0, "#d22020"),
    ("verde", -6.0, 5.0, "#28b432"),
    ("albastra", 5.0, -7.0, "#3050e0"),
]


def main():
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    from geometry_msgs.msg import PoseStamped
    import tkinter as tk
    from tkinter import ttk

    class GcsConsole(Node):
        def __init__(self):
            super().__init__("gcs_console")
            p = self.declare_parameter
            p("goal_topic", "/teleop/goal")
            p("pose_topic", "/teleop/pose")
            p("frame", "map")
            p("terrain_half", 20.0)
            g = lambda k: self.get_parameter(k).value
            self.frame = str(g("frame"))
            self.half = float(g("terrain_half"))
            self.rover = None        # (x, y, th)
            self.rover_t = 0.0
            self.goal = None         # (x, y)
            self.goal_pub = self.create_publisher(PoseStamped, str(g("goal_topic")), 10)
            self.create_subscription(String, str(g("pose_topic")), self.on_pose, 30)
            self.get_logger().info(
                f"pupitru GCS pornit; tinta -> {g('goal_topic')}, "
                f"pozitie <- {g('pose_topic')} (frame={self.frame})")

        def on_pose(self, msg):
            try:
                d = json.loads(msg.data)
                self.rover = (float(d["x"]), float(d["y"]), float(d.get("th", 0.0)))
                self.rover_t = time.time()
            except Exception:
                pass

        def send_goal(self, x, y):
            m = PoseStamped()
            m.header.frame_id = self.frame
            m.header.stamp = self.get_clock().now().to_msg()
            m.pose.position.x = float(x)
            m.pose.position.y = float(y)
            m.pose.orientation.w = 1.0
            self.goal_pub.publish(m)
            self.goal = (float(x), float(y))
            self.get_logger().info(f"GCS -> tinta ({x:.1f}, {y:.1f})")

    rclpy.init()
    node = GcsConsole()
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    W = H = 600
    half = node.half
    root = tk.Tk()
    root.title("Pupitru GCS - click pe harta = tinta roverului")
    cv = tk.Canvas(root, width=W, height=H, bg="#0e120c", highlightthickness=0)
    cv.pack(padx=8, pady=(8, 4))
    info = tk.StringVar(value="click pe harta ca sa trimiti roverul acolo")
    bar = ttk.Frame(root); bar.pack(fill="x", padx=8, pady=(0, 8))
    ttk.Label(bar, textvariable=info).pack(side="left")
    ttk.Button(bar, text="STOP (opreste roverul aici)",
               command=lambda: (node.rover and node.send_goal(node.rover[0], node.rover[1]))
               ).pack(side="right")

    def draw_static():
        cv.delete("static")
        # grila la fiecare 5 m
        step = 5.0
        n = int(half // step)
        for k in range(-n, n + 1):
            x0, y0 = world_to_canvas(k * step, -half, W, H, half)
            x1, y1 = world_to_canvas(k * step, half, W, H, half)
            cv.create_line(x0, y0, x1, y1, fill="#1d2a18", tags="static")
            x0, y0 = world_to_canvas(-half, k * step, W, H, half)
            x1, y1 = world_to_canvas(half, k * step, W, H, half)
            cv.create_line(x0, y0, x1, y1, fill="#1d2a18", tags="static")
        # contur teren
        cv.create_rectangle(0, 0, W - 1, H - 1, outline="#3a5a2a", width=2, tags="static")
        # punctele de interes (tintele)
        for name, x, y, col in POI:
            px, py = world_to_canvas(x, y, W, H, half)
            r = 9
            cv.create_oval(px - r, py - r, px + r, py + r, fill=col, outline="#ffffff", tags="static")
            cv.create_text(px, py - 16, text=name, fill="#cfe0c4", font=("TkDefaultFont", 8), tags="static")

    def redraw():
        cv.delete("dyn")
        # roverul
        if node.rover is not None:
            x, y, th = node.rover
            px, py = world_to_canvas(x, y, W, H, half)
            L = 14
            tipx = px + L * math.cos(th)
            tipy = py - L * math.sin(th)
            lx = px + 0.7 * L * math.cos(th + 2.5)
            ly = py - 0.7 * L * math.sin(th + 2.5)
            rx = px + 0.7 * L * math.cos(th - 2.5)
            ry = py - 0.7 * L * math.sin(th - 2.5)
            cv.create_polygon(tipx, tipy, lx, ly, rx, ry, fill="#46b4ff",
                              outline="#ffffff", tags="dyn")
            fresh = (time.time() - node.rover_t) < 1.5
            info.set(f"rover: ({x:.1f}, {y:.1f})  th={math.degrees(th):.0f} deg"
                     f"{'' if fresh else '  [feedback vechi]'}"
                     + (f"   tinta: ({node.goal[0]:.1f}, {node.goal[1]:.1f})" if node.goal else "   tinta: -"))
        else:
            info.set("astept pozitia roverului pe /teleop/pose ... (RMW corect? router pornit?)")
        # tinta curenta
        if node.goal is not None:
            gx, gy = node.goal
            px, py = world_to_canvas(gx, gy, W, H, half)
            s = 10
            cv.create_line(px - s, py - s, px + s, py + s, fill="#ffd21a", width=3, tags="dyn")
            cv.create_line(px - s, py + s, px + s, py - s, fill="#ffd21a", width=3, tags="dyn")
            cv.create_oval(px - 13, py - 13, px + 13, py + 13, outline="#ffd21a", width=2, tags="dyn")
        root.after(100, redraw)

    def on_click(ev):
        x, y = canvas_to_world(ev.x, ev.y, W, H, half)
        node.send_goal(x, y)

    cv.bind("<Button-1>", on_click)
    draw_static()
    redraw()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
