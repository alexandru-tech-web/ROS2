cmake_minimum_required(VERSION 3.8)
project(rehab_exo_description)

find_package(ament_cmake REQUIRED)

# Pachet de descriere: instaleaza resursele (urdf, launch, config, rviz)
# in share/, ca sa fie gasite cu get_package_share_directory / FindPackageShare.
install(
  DIRECTORY urdf launch config rviz
  DESTINATION share/${PROJECT_NAME}
)

# Scripturile de control, instalate ca executabile (ros2 run / launch Node).
# exercise_core.py merge alaturi, ca importul local sa functioneze.
install(
  PROGRAMS
    scripts/exercise_controller.py
    scripts/exercise_core.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
