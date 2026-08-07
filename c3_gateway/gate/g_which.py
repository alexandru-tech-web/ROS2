"""g_which.py <eticheta> -- raporteaza ce RMW a primit EFECTIV procesul: variabila de
mediu vazuta si identificatorul returnat de rclpy (care e adevarul, nu variabila)."""
import os
import sys

import rclpy

et = sys.argv[1] if len(sys.argv) > 1 else "?"
rclpy.init()
n = rclpy.create_node("g_which_%s" % et.replace("-", "_"))
print("SCOPE %-8s env=%-22s efectiv=%s"
      % (et, os.environ.get("RMW_IMPLEMENTATION", "(nesetat)"),
         rclpy.get_rmw_implementation_identifier()), flush=True)
n.destroy_node()
rclpy.shutdown()
