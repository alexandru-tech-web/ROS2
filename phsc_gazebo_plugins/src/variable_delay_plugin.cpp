// variable_delay_plugin.cpp
// Plugin Gazebo Harmonic pentru injectare delay variabil in semnalele de control.
//
// Comunica prin ROS 2:
//   Subscrie: /robot_cmd (geometry_msgs::msg::Twist)
//   Publica:  /robot_cmd_delayed (geometry_msgs::msg::Twist)
//
// Parametri SDF:
//   <base_delay>    - latenta de baza [s] (default: 0.05)
//   <amplitude>     - amplitudine variatie [s] (default: 0.02)
//   <frequency>     - frecventa variatie [Hz] (default: 0.5)
//   <noise_std>     - deviatie standard zgomot [s] (default: 0.005)
//   <profile>       - "constant", "sine", "burst" (default: "sine")
//
// Autor: PhD Research - Predictive Haptic Shared Control

#include <gz/sim/System.hh>
#include <gz/sim/Model.hh>
#include <gz/plugin/Register.hh>
#include <sdf/Element.hh>
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <memory>
#include <queue>
#include <random>
#include <string>
#include <vector>

namespace phsc
{

// Timpii sunt in SECUNDE DE TIMP SIMULAT (_info.simTime), nu ceas de perete.
struct DelayedCommand
{
  geometry_msgs::msg::Twist msg;
  double release_time;   // sim time la care mesajul trebuie livrat
  double recv_time;      // sim time la care a fost primit
  double delay;
};

// Coada e ordonata dupa momentul de LIVRARE, nu dupa cel de sosire.
// Cu delay variabil, un mesaj primit mai tarziu poate avea deadline mai
// devreme; o coada FIFO cu 'break' l-ar tine blocat in spatele altuia
// (head-of-line blocking) si ar transforma distributia ceruta de intarzieri
// in anvelopa ei running-max.
struct ByReleaseTime
{
  bool operator()(const DelayedCommand &a, const DelayedCommand &b) const
  {
    return a.release_time > b.release_time;   // min-heap
  }
};

class VariableDelayPlugin : public gz::sim::System,
                            public gz::sim::ISystemPreUpdate,
                            public gz::sim::ISystemConfigure
{
public:
  VariableDelayPlugin() : gen_(42), dist_(0.0, 1.0) {}

  void Configure(const gz::sim::Entity &_entity,
                 const std::shared_ptr<const sdf::Element> &_sdf,
                 gz::sim::EntityComponentManager &_ecm,
                 gz::sim::EventManager &_eventMgr) override
  {
    (void)_entity;
    (void)_ecm;
    (void)_eventMgr;

    // Initializare ROS 2
    if (!rclcpp::ok()) {
      rclcpp::init(0, nullptr);
    }
    ros_node_ = std::make_shared<rclcpp::Node>("variable_delay_plugin");

    // Citire parametri SDF
    if (_sdf->HasElement("base_delay")) {
      base_delay_ = _sdf->Get<double>("base_delay");
    }
    if (_sdf->HasElement("amplitude")) {
      amplitude_ = _sdf->Get<double>("amplitude");
    }
    if (_sdf->HasElement("frequency")) {
      frequency_ = _sdf->Get<double>("frequency");
    }
    if (_sdf->HasElement("noise_std")) {
      noise_std_ = _sdf->Get<double>("noise_std");
      dist_ = std::normal_distribution<double>(0.0, noise_std_);
    }
    if (_sdf->HasElement("profile")) {
      profile_ = _sdf->Get<std::string>("profile");
    }

    RCLCPP_INFO(ros_node_->get_logger(),
      "VariableDelayPlugin: base=%.3fs, amp=%.3fs, freq=%.2fHz, profile=%s",
      base_delay_, amplitude_, frequency_, profile_.c_str());

    // Subscriptor si publicator
    sub_cmd_ = ros_node_->create_subscription<geometry_msgs::msg::Twist>(
      "/robot_cmd", 10,
      [this](const geometry_msgs::msg::Twist::ConstSharedPtr msg) {
        // Stampilam pe ceasul SIMULARII (actualizat in PreUpdate), nu pe cel
        // de perete: altfel intarzierea injectata ar fi delay_nominal * RTF
        // si experimentul nu ar fi reproductibil pe alta masina.
        DelayedCommand dc;
        dc.msg = *msg;
        dc.recv_time = sim_now_;
        dc.delay = compute_delay(sim_now_);
        dc.release_time = sim_now_ + dc.delay;
        cmd_queue_.push(dc);

        if (cmd_queue_.size() > queue_max_) {
          cmd_queue_.pop();
          ++dropped_;
          RCLCPP_WARN_THROTTLE(ros_node_->get_logger(), *ros_node_->get_clock(),
            5000, "Coada de delay plina (%zu); %lu mesaje aruncate.",
            queue_max_, dropped_);
        }
      });

    pub_delayed_ = ros_node_->create_publisher<geometry_msgs::msg::Twist>(
      "/robot_cmd_delayed", 10);
  }

  void PreUpdate(const gz::sim::UpdateInfo &_info,
                 gz::sim::EntityComponentManager &_ecm) override
  {
    (void)_ecm;

    // Ceasul de referinta al plugin-ului = timpul SIMULAT.
    sim_now_ = std::chrono::duration<double>(_info.simTime).count();

    rclcpp::spin_some(ros_node_);

    // Coada e min-heap dupa release_time, deci 'top()' e mereu mesajul cu
    // cel mai apropiat deadline. Golim TOT ce a expirat, in ordinea corecta
    // de livrare -- fara head-of-line blocking.
    while (!cmd_queue_.empty() && cmd_queue_.top().release_time <= sim_now_) {
      pub_delayed_->publish(cmd_queue_.top().msg);
      cmd_queue_.pop();
    }
  }

private:
  double compute_delay(double t)
  {
    double delay = base_delay_;

    if (profile_ == "sine") {
      delay += amplitude_ * std::sin(2.0 * M_PI * frequency_ * t);
    } else if (profile_ == "burst") {
      // Perioada burst-ului vine acum din <frequency> (Hz), cum promite
      // delay_profiles.yaml ('frequency: 0.2' = un burst la ~5 s). Inainte
      // era hardcodata 5.0 s si <frequency> era ignorat pentru acest profil.
      double burst_period = (frequency_ > 1e-6) ? (1.0 / frequency_) : 5.0;
      double burst_duration = std::min(1.0, 0.2 * burst_period);
      double phase = std::fmod(t, burst_period);
      if (phase < burst_duration) {
        delay += amplitude_ * 2.0;
      }
    }

    // Zgomot gaussian
    delay += dist_(gen_);

    // Clamp la valori pozitive
    return std::max(0.001, delay);
  }

  std::shared_ptr<rclcpp::Node> ros_node_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_cmd_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr pub_delayed_;
  std::priority_queue<DelayedCommand,
                      std::vector<DelayedCommand>,
                      ByReleaseTime> cmd_queue_;

  double sim_now_ = 0.0;        // timp simulat curent [s]
  std::size_t queue_max_ = 1000;
  unsigned long dropped_ = 0;

  // Parametri delay
  double base_delay_ = 0.05;
  double amplitude_ = 0.02;
  double frequency_ = 0.5;
  double noise_std_ = 0.005;
  std::string profile_ = "sine";

  // Generator random
  std::mt19937 gen_;
  std::normal_distribution<double> dist_;
};

} // namespace phsc

GZ_ADD_PLUGIN(phsc::VariableDelayPlugin,
              gz::sim::System,
              phsc::VariableDelayPlugin::ISystemConfigure,
              phsc::VariableDelayPlugin::ISystemPreUpdate)
