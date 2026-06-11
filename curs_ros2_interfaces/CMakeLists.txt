cmake_minimum_required(VERSION 3.8)
project(curs_ros2_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Genereaza codul (Python + C++) pentru fiecare interfata custom a cursului.
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Temperatura.msg"
  "srv/AjustareTemperatura.srv"
  "action/Incalzire.action"
)

ament_export_dependencies(rosidl_default_runtime)

ament_package()
