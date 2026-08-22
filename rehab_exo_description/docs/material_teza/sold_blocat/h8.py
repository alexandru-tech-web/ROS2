import sys, time
sys.path.insert(0,"/home/ubuntu/ros2_ws/src/rehab_exo_description/scripts")
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration as DMsg
from rclpy.duration import Duration
from std_msgs.msg import String
from sensor_msgs.msg import JointState
import exercise_core as ec
J=list(ec.JOINT_NAMES)
class P(Node):
    def __init__(s):
        super().__init__("h8"); s.got=None; s.q={}
        s.create_subscription(JointTrajectory,"/leg_trajectory_controller/joint_trajectory",
                              lambda m: setattr(s,"got",m), 10)
        s.create_subscription(JointState,"/joint_states",s.cb,20)
        s.cmd=s.create_publisher(String,"/exercise_cmd",10)
    def cb(s,m):
        for n,p in zip(m.name,m.position): s.q[n]=p
def gira(n,t):
    t0=time.time()
    while time.time()-t0<t: rclpy.spin_once(n,timeout_sec=0.02)
rclpy.init(); n=P(); gira(n,8)
n.cmd.publish(String(data="hip_hold")); gira(n,4)
A = n.got
if A is None: print("  n-am prins mesajul playerului"); raise SystemExit(1)

# replica construita EXACT ca in send_trajectory
prog = ec.build("hip_hold", 3, q_init=dict(n.q) if n.q else dict(ec.POSTURA_INITIALA))
pl = ec.Player(prog)
B=JointTrajectory(); B.joint_names=list(ec.JOINT_NAMES)
t=0.0
while t <= pl.p.total_time + 1e-9:
    q,_=pl.sample(t)
    pt=JointTrajectoryPoint(); pt.positions=[q[j] for j in ec.JOINT_NAMES]
    pt.time_from_start=Duration(seconds=t/1.0).to_msg()
    B.points.append(pt); t += 0.1

print("  header A: sec=%d nsec=%d frame='%s'" % (A.header.stamp.sec, A.header.stamp.nanosec, A.header.frame_id))
print("  header B: sec=%d nsec=%d frame='%s'" % (B.header.stamp.sec, B.header.stamp.nanosec, B.header.frame_id))
print("  joint_names identice: %s" % (list(A.joint_names)==list(B.joint_names)))
print("  nr puncte: A=%d B=%d" % (len(A.points), len(B.points)))
import exercise_core as _ec
NUM=list(_ec.JOINT_NAMES)
maxd={j:0.0 for j in NUM}; worst=(0.0,None)
tdif=0
for k,(a,b) in enumerate(zip(A.points,B.points)):
    for i,j in enumerate(NUM):
        d=abs(a.positions[i]-b.positions[i]); maxd[j]=max(maxd[j],d)
        if d>worst[0]: worst=(d,(k,j,a.positions[i],b.positions[i]))
    if (a.time_from_start.sec,a.time_from_start.nanosec)!=(b.time_from_start.sec,b.time_from_start.nanosec):
        tdif+=1
print("  diferenta MAXIMA de pozitie, pe articulatie:")
for j in NUM: print("    %-20s %.6e" % (j, maxd[j]))
if worst[1]:
    k,j,va,vb = worst[1]
    print("  cea mai mare: pct %d, %s: player=%.6f replica=%.6f (delta %.6e)" % (k,j,va,vb,worst[0]))
print("  puncte cu timp diferit: %d" % tdif)
print("  A: velocities pe pct0=%d, accelerations=%d, effort=%d" %
      (len(A.points[0].velocities), len(A.points[0].accelerations), len(A.points[0].effort)))
print("  B: velocities pe pct0=%d, accelerations=%d, effort=%d" %
      (len(B.points[0].velocities), len(B.points[0].accelerations), len(B.points[0].effort)))
import rclpy.serialization as ser
sa, sb = ser.serialize_message(A), ser.serialize_message(B)
print("  serializat: A=%d octeti B=%d octeti IDENTICE=%s" % (len(sa), len(sb), sa==sb))
