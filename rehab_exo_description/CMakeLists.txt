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
# Cotele geometrice se GENEREAZA din scripts/geometrie_core.py, singura lor sursa.
# Niciun numar de geometrie nu se scrie de mana in xacro: pana pe 22 aug 2026 toate
# erau inventate si nemarcate, iar rezultatul se vedea in simulare (piciorul trecea
# prin placa). Acum fiecare cota are o clasa de provenienta, verificata in selftest.
set(COTE_GEN "${CMAKE_CURRENT_SOURCE_DIR}/urdf/cote_derivate.xacro")
add_custom_command(
  OUTPUT "${COTE_GEN}"
  COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/geometrie_core.py"
          "--xacro" "${COTE_GEN}"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/scripts/geometrie_core.py"
  COMMENT "Generare urdf/cote_derivate.xacro din geometrie_core.py")

find_program(XACRO_EXE xacro REQUIRED)
set(URDF_GEN "${CMAKE_CURRENT_BINARY_DIR}/rehab_exo.urdf")
add_custom_command(
  OUTPUT "${URDF_GEN}"
  COMMAND "${XACRO_EXE}" "${CMAKE_CURRENT_SOURCE_DIR}/urdf/rehab_exo.urdf.xacro"
          "controllers:=${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME}/config/controllers.yaml"
          -o "${URDF_GEN}"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/urdf/rehab_exo.urdf.xacro" "${COTE_GEN}"
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
    scripts/transmisie_core.py
    scripts/homing_node.py
    scripts/senzori_core.py
    scripts/senzori_node.py
    scripts/monitor_senzori.py
    scripts/supervizor_electric.py
    scripts/demo_cu_gui.sh
    scripts/supervizor_core.py
    scripts/geometrie_core.py
    scripts/monitor_core.py
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
  ament_add_test(test_senzori
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/senzori_core.py" "--selftest"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_senzori.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_senzori.xunit.xml"
    TIMEOUT 60)
  ament_add_test(test_transmisie
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/transmisie_core.py" "--selftest"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_transmisie.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_transmisie.xunit.xml"
    TIMEOUT 60)
  ament_add_test(test_rmw_mutant
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_rmw_mutant.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_rmw_mutant.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_rmw_mutant.xunit.xml"
    TIMEOUT 300)

  ament_add_test(test_postura
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_postura.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_postura.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_postura.xunit.xml"
    TIMEOUT 300)

  ament_add_test(test_podea
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_podea.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_podea.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_podea.xunit.xml"
    TIMEOUT 300)

  ament_add_test(test_gardian_conventie
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_gardian_conventie.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_gardian_conventie.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_gardian_conventie.xunit.xml"
    TIMEOUT 120)

  ament_add_test(test_geometrie
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/geometrie_core.py" "--selftest"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_geometrie.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_geometrie.xunit.xml"
    TIMEOUT 60)

  ament_add_test(test_supervizor_core
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/supervizor_core.py" "--selftest"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_supervizor_core.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_supervizor_core.xunit.xml"
    TIMEOUT 60)

  ament_add_test(test_supervizor
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_supervizor.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_supervizor.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_supervizor.xunit.xml"
    TIMEOUT 120)

  ament_add_test(test_monitor
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/monitor_core.py" "--selftest"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_monitor.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_monitor.xunit.xml"
    TIMEOUT 60)

  ament_add_test(test_rmw_scope
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
    COMMAND "/usr/bin/python3" "${CMAKE_CURRENT_SOURCE_DIR}/test/test_rmw_scope.py"
    OUTPUT_FILE "${CMAKE_BINARY_DIR}/test_rmw_scope.log"
    RESULT_FILE "${CMAKE_BINARY_DIR}/test_rmw_scope.xunit.xml"
    TIMEOUT 60)

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
