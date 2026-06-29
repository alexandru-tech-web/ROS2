# teleop_rover

Demonstrator de aplicatie pentru teza (teleoperare in timp real peste retele
degradate): un rover terestru condus prin retea (operator-model sau pupitru GCS)
sub degradare controlata, ca al treilea demonstrator (control in bucla inchisa)
alaturi de comparatia RMW din C1. Respecta metodologia repo-ului: nucleu pur cu
teste -> nod ROS subtire (JSON pe std_msgs/String) -> SIL.

NOTA (arhiva/demo): pachetul e un director de scripturi standalone. NU are
package.xml / setup.py, deci NU se construieste cu colcon si NU expune
entry_points pentru 'ros2 run'. Scripturile se ruleaza direct cu 'python3', iar
launch-urile cu 'ros2 launch ./launch/<fisier>'. Vezi DOCUMENTATIE_teleop_rover.md
si README.md vechi (continut acum suprascris) pentru detaliile de campanie.

## Fisiere (cheie)

Nuclee pure (fara ROS, testabile):
- rover_core.py -- nucleul teleoperarii rover diferential: cinematica, traseul-slalom, eroarea de urmarire, pilotul-model si stratul de siguranta.
- nav_core.py -- rover cu 4 roti skid-steer + controler go-to-goal (goto_command).
- avoidance_core.py -- evitare de obstacole (potential-fields + VFH) din scanuri lidar.
- vision_core.py -- viziune HSV (detect_blobs) + proiectie pixel->lume (pinhole, sol-plat).
- hw_link.py -- punte hardware-in-the-loop, protocol serial stil NMEA cu XOR (loopback sau port real).
- netem_core.py -- model de degradare a retelei (latenta, jitter, pierdere, cadere, store-and-forward); scenarii din YAML.

Noduri ROS subtiri:
- robot_node.py -- roverul teleoperat; primeste /teleop/cmd prin link degradat, SafetyGate, publica /teleop/pose, jurnal robot_log.csv.
- operator_node.py -- operatorul la distanta (mode pilot sau manual Tk), publica /teleop/cmd la 20 Hz.
- goto_node.py -- navigator go-to-goal drop-in (sursa waypoint | object | gcs); publica /teleop/cmd + marker.
- link_node.py -- publica starea legaturii pe /teleop/linkstate (5 Hz), reglabila live pe /teleop/operator.
- detector_node.py -- recunoastere obiecte din camera, publica tinta pe /teleop/target.
- gcs_console.py -- pupitru GCS cu harta: click -> tinta pe /teleop/goal (PoseStamped).
- fake_camera_pub.py -- flux camera sintetic pe /camera/image/compressed, pentru test fara Gazebo.

SIL si analiza:
- sil_teleop.py -- teleoperare in bucla inchisa fara ROS prin canalul degradat (argparse: --lat --jit --loss --seed --trace --amax --wacc --plot).
- sweep_teleop.py -- experimentul de teza: sweep latenta x pierdere, regimuri ideal/realistic; scrie results/sweep.csv si figuri.
- analyze_campaign.py -- agrega o campanie RMW (argparse: --camp si --goal obligatorii, plus --arrive --xcol --ycol --tcol); scrie summary.csv si figuri.
- analyze_perception.py -- metrici go-to-goal sub perceptie (argparse: --run --goal --goal-class --arrive_r --out).
- plot_trace.py -- figura unei rulari reale din robot_log.csv ('python3 plot_trace.py ~/teleop_data/robot_log.csv').
- gen_rover_world.py / gen_rough_world.py -- genereaza lumile Gazebo (worlds/*.sdf).
- test_rover_core.py / test_nav_core.py / test_vision_core.py / test_hw_link.py -- teste ale nucleelor (rulate cu 'python3').

## Sintaxe de rulare

Nuclee/SIL/teste (offline, fara ROS):
    python3 test_rover_core.py        # idem test_nav_core / test_vision_core / test_hw_link
    python3 sil_teleop.py --lat 200 --jit 40 --loss 0.1 --plot
    python3 sweep_teleop.py
    python3 analyze_campaign.py --camp results/campaign_XXXX --goal 8 3

Noduri ROS (standalone, cu parametri prin --ros-args):
    python3 robot_node.py --ros-args -p use_gazebo:=false
    python3 fake_camera_pub.py --ros-args -p color:=red -p cx:=170
    python3 gcs_console.py            # sau: python3 gcs_console.py --selftest

Launch (din radacina pachetului):
    ros2 launch ./launch/teleop.launch.py lat:=200 jit:=40 loss:=0.1 mode:=pilot
    ros2 launch ./launch/teleop_gazebo.launch.py lat:=500 jit:=100 mode:=manual
    ros2 launch ./launch/teleop_perception.launch.py rmw:=cyclone goal_source:=object

## Parametri si topicuri (noduri ROS)

Mesajele de aplicatie sunt JSON pe std_msgs/String. Topicuri (din cod):
- robot_node: sub /teleop/cmd, /teleop/linkstate; pub /teleop/pose; in Gazebo pub /model/rover/cmd_vel (Twist), sub /model/rover/odometry (Odometry).
- operator_node: pub /teleop/cmd; sub /teleop/pose, /teleop/linkstate.
- goto_node: pub /teleop/cmd, /teleop/goal_marker (Marker); sub /teleop/pose, /teleop/linkstate; optional /scan, /teleop/target, goal_topic (PoseStamped).
- link_node: pub /teleop/linkstate; sub /teleop/operator.
- detector_node: pub target_topic (/teleop/target); sub image_topic, pose_topic, optional scan_topic.
- gcs_console: pub goal_topic (/teleop/goal, PoseStamped); sub pose_topic (/teleop/pose).
- fake_camera_pub: pub topic (/camera/image/compressed, CompressedImage).

Parametri reali (declare_parameter):
- robot_node: use_gazebo, use_world_pose, model_name, world_name, pose_min_dist, safety_lidar, scan_topic, d_crit, use_hardware, port.
- goto_node: goal_source, goal_x, goal_y, target_class, arrive_r, goal_topic, frame, use_avoidance, scan_topic.
- detector_node: image_topic, pose_topic, target_topic, scan_topic, target_class, min_area, hfov, vfov, cam_h, pitch, width, height.
- link_node: lat_ms, jit_ms, loss, down.
- gcs_console: goal_topic, pose_topic, frame, terrain_half.
- fake_camera_pub: topic, color, width, height, cx, cy, size, rate.
- operator_node: mode.
