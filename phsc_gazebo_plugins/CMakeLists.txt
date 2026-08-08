cmake_minimum_required(VERSION 3.8)
project(phsc_gazebo_plugins)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(gz-sim8 REQUIRED)
find_package(gz-plugin2 REQUIRED)

# Plugin library
add_library(variable_delay_plugin SHARED src/variable_delay_plugin.cpp)
target_link_libraries(variable_delay_plugin
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
)
ament_target_dependencies(variable_delay_plugin
  rclcpp
  geometry_msgs
)

install(TARGETS variable_delay_plugin
  LIBRARY DESTINATION lib/${PROJECT_NAME}
)

# Fara acest hook, Gazebo NU gaseste plugin-ul: cauta doar in
# GZ_SIM_SYSTEM_PLUGIN_PATH, iar lib/${PROJECT_NAME} din workspace nu e acolo.
# Hook-ul face ca 'source install/setup.bash' sa adauge calea automat.
ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

ament_package()
