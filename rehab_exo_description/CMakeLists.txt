cmake_minimum_required(VERSION 3.8)
project(rehab_exo_description)

find_package(ament_cmake REQUIRED)

# Pachet de descriere: instaleaza resursele (urdf, launch, config, rviz)
# in share/, ca sa fie gasite cu get_package_share_directory / FindPackageShare.
install(
  DIRECTORY urdf launch config rviz worlds
  DESTINATION share/${PROJECT_NAME}
)

# URDF-ul e ARTEFACT GENERAT, nu sursa. Se produce din xacro la build si se instaleaza
# alaturi de el. Fisierul din arborele sursa NU se mai editeaza manual niciodata:
# pana la F1a existau trei surse de adevar (urdf, xacro vechi, patch_urdf_extensions.py),
# doi roboti diferiti si un README care il documenta pe cel gresit.
find_program(XACRO_EXE xacro REQUIRED)
set(URDF_GEN "${CMAKE_CURRENT_BINARY_DIR}/rehab_exo.urdf")
add_custom_command(
  OUTPUT "${URDF_GEN}"
  COMMAND "${XACRO_EXE}" "${CMAKE_CURRENT_SOURCE_DIR}/urdf/rehab_exo.urdf.xacro"
          "controllers:=${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME}/config/controllers.yaml"
          -o "${URDF_GEN}"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/urdf/rehab_exo.urdf.xacro"
  COMMENT "Generare rehab_exo.urdf din xacro (sursa canonica unica)")
add_custom_target(urdf_generat ALL DEPENDS "${URDF_GEN}")
install(FILES "${URDF_GEN}" DESTINATION share/${PROJECT_NAME}/urdf)
# Scripturile de control, instalate ca executabile (ros2 run / launch Node).
# exercise_core.py merge alaturi, ca importul local sa functioneze.
install(
  PROGRAMS
    scripts/exercise_controller.py
    scripts/exercise_core.py
    scripts/sensor_recorder.py
    scripts/operator_panel.py
    scripts/telemetry_display.py
    scripts/plot_recording.py
    scripts/safety_supervisor.py
    scripts/operator_heartbeat.py
    scripts/patient_model.py
    scripts/session_report.py
    scripts/rmw_guard.py
    scripts/spec_derivate.py
  DESTINATION lib/${PROJECT_NAME}
)
# rmw_guard.py se instaleaza SI in launch/, ca modul: launch/rmw_common.py importa de
# acolo tabela de aliasuri si functia de verdict, ca sa nu existe doua copii ale lor.
install(
  FILES scripts/rmw_guard.py
  DESTINATION share/${PROJECT_NAME}/launch
)

if(BUILD_TESTING)
  # Selftestul DESCRIERII: genereaza URDF-ul din sursa canonica si il interogheaza
  # (topologie, limite, simetrie stanga-dreapta, flaguri cu control negativ).
  find_package(ament_cmake_test REQUIRED)
  # GENERATE_RESULT_FOR_RETURN_CODE_ZERO: testul e un script obisnuit, nu pytest -- nu scrie el
  # xunit-ul, deci il genereaza wrapper-ul din codul de iesire.
  # Echivalenta conventiei (M1): schimbarea de zero nu a schimbat robotul.
  # Nucleul pur al valorilor derivate din documentatie.
  ament_add_test(test_spec_derivate
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/spec_derivate.py" "--selftest"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_spec_derivate.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_spec_derivate.xunit.xml"
    TIMEOUT 60)
  ament_add_test(test_conventie
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_conventie.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_conventie.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_conventie.xunit.xml"
    TIMEOUT 180)
  # Traiectoriile convertite: genunchi/glezna identice fizic, sold re-derivat pe fractie.
  ament_add_test(test_traiectorii
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_traiectorii.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_traiectorii.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_traiectorii.xunit.xml"
    TIMEOUT 120)
  ament_add_test(test_descriere
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_descriere.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_descriere.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_descriere.xunit.xml"
    TIMEOUT 120)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
