import json, math, sys, time
sys.path.insert(0,"/home/ubuntu/ros2_ws/src/rehab_exo_description/scripts")
import rclpy
from rclpy.node import Node
from control_msgs.msg import JointTrajectoryControllerState as CS
from sensor_msgs.msg import JointState
from std_msgs.msg import String
class S(Node):
    def __init__(s):
        super().__init__("sc"); s.q={}; s.ref={}
        s.create_subscription(JointState,"/joint_states",s._js,50)
        s.create_subscription(CS,"/leg_trajectory_controller/controller_state",s._cs,50)
        s.pub=s.create_publisher(String,"/exercise_cmd",10)
    def _js(s,m):
        for n,p in zip(m.name,m.position): s.q[n]=p
    def _cs(s,m):
        for n,p in zip(m.joint_names,m.reference.positions): s.ref[n]=p
rclpy.init(); n=S()
t0=time.time()
while time.time()-t0<8: rclpy.spin_once(n,timeout_sec=0.03)
inv=json.load(open("/tmp/inventar.json"))
print("  %-20s %10s %10s %10s" % ("exercitiu","err_sold","err_gen","err_glezna"))
print("  "+"-"*54)
for nume, art, npct, dur, reps in inv:
    n.pub.publish(String(data=nume))
    t0=time.time(); m={"hip":0.0,"knee":0.0,"ankle":0.0}
    # esantionare CONTINUA pe toata durata reala (reps=3 la controler)
    while time.time()-t0 < dur*1.6 + 5:
        rclpy.spin_once(n,timeout_sec=0.02)
        for a in ("hip","knee","ankle"):
            j="left_%s_joint"%a
            if j in n.ref and j in n.q:
                m[a]=max(m[a], abs(n.ref[j]-n.q[j]))
    print("  %-20s %10.4f %10.4f %10.4f" % (nume, m["hip"], m["knee"], m["ankle"]))
