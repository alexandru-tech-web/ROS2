import sys, time
sys.path.insert(0,"/home/ubuntu/ros2_ws/src/rehab_exo_description/scripts")
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import exercise_core as ec
J=list(ec.JOINT_NAMES)
class P(Node):
    def __init__(s):
        super().__init__("minim"); s.q={}
        s.create_subscription(JointState,"/joint_states",s.cb,20)
        s.t=s.create_publisher(JointTrajectory,"/leg_trajectory_controller/joint_trajectory",10)
    def cb(s,m):
        for n,p in zip(m.name,m.position): s.q[n]=p
def gira(n,t):
    t0=time.time()
    while time.time()-t0<t: rclpy.spin_once(n,timeout_sec=0.03)
def du(n, hip, knee, sec=4):
    m=JointTrajectory(); m.joint_names=J
    pt=JointTrajectoryPoint()
    pt.positions=[hip if "hip" in j else (knee if "knee" in j else 0.0) for j in J]
    pt.time_from_start=Duration(sec=sec); m.points=[pt]
    for _ in range(3): n.t.publish(m); rclpy.spin_once(n,timeout_sec=0.1)
    gira(n, sec+4)
    return n.q.get("left_hip_joint",9), n.q.get("left_knee_joint",9)
rclpy.init(); n=P(); gira(n,8)
print("  REPRO MINIM: aceeasi tinta de sold, singura variabila e GENUNCHIUL")
print("  %-34s %10s %10s %s" % ("configuratie","sold","genunchi","verdict"))
h,k = du(n, 0.0, 0.0); print("  %-34s %+10.4f %+10.4f" % ("0. asezare: tot zero", h, k))
h,k = du(n, 1.3464, 0.0)
print("  %-34s %+10.4f %+10.4f %s" % ("A. genunchi INTINS (0), sold 1.3464", h, k,
      "BLOCAT" if abs(h)<0.05 else "se misca"))
h,k = du(n, 0.0, 1.5708); print("  %-34s %+10.4f %+10.4f" % ("   revin, indoi genunchiul", h, k))
h,k = du(n, 1.3464, 1.5708)
print("  %-34s %+10.4f %+10.4f %s" % ("B. genunchi INDOIT (90), sold 1.3464", h, k,
      "BLOCAT" if abs(h)<0.05 else "SE MISCA"))
