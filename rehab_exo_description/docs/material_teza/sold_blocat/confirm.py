import sys, time
sys.path.insert(0,"/home/ubuntu/ros2_ws/src/rehab_exo_description/scripts")
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import exercise_core as ec
J=list(ec.JOINT_NAMES)
class P(Node):
    def __init__(s):
        super().__init__("conf"); s.q={}
        s.create_subscription(JointState,"/joint_states",s.cb,20)
        s.cmd=s.create_publisher(String,"/exercise_cmd",10)
        s.t=s.create_publisher(JointTrajectory,"/leg_trajectory_controller/joint_trajectory",10)
    def cb(s,m):
        for n,p in zip(m.name,m.position): s.q[n]=p
def gira(n,t):
    t0=time.time()
    while time.time()-t0<t: rclpy.spin_once(n,timeout_sec=0.03)
rclpy.init(); n=P(); gira(n,8)
print("  stare la sosire: sold=%+.4f genunchi=%+.4f"
      % (n.q.get("left_hip_joint",9), n.q.get("left_knee_joint",9)))
print("  A. hip_hold prin player, cu genunchiul cum e (intins)")
n.cmd.publish(String(data="hip_hold")); gira(n,7)
print("     sold=%+.4f genunchi=%+.4f" % (n.q.get("left_hip_joint",9), n.q.get("left_knee_joint",9)))
print("  ... indoi genunchiul la 90, FARA sa ating soldul")
m=JointTrajectory(); m.joint_names=J
pt=JointTrajectoryPoint(); pt.positions=[0.0 if "hip" in j else (1.5708 if "knee" in j else 0.0) for j in J]
pt.time_from_start=Duration(sec=4); m.points=[pt]
for _ in range(3): n.t.publish(m); rclpy.spin_once(n,timeout_sec=0.1)
gira(n,8)
print("     sold=%+.4f genunchi=%+.4f" % (n.q.get("left_hip_joint",9), n.q.get("left_knee_joint",9)))
print("  B. hip_hold prin player, ACUM cu genunchiul indoit")
n.cmd.publish(String(data="hip_hold")); gira(n,7)
h=n.q.get("left_hip_joint",9)
print("     sold=%+.4f genunchi=%+.4f  -> %s" % (h, n.q.get("left_knee_joint",9),
      "SE MISCA (mecanism confirmat)" if abs(h)>0.2 else "tot blocat"))
