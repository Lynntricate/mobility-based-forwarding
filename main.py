from graphics.display import *
from core.node_factory import *
import random

start_c = Coordinate(740, 360)
nodes_0 = [
    Node(start_c, waypoints=generate_waypoint_array(start_c, 5, 0.1, 1))
]




if __name__ == "__main__":
    ui = Simulator(nodes_0)

    atexit.register(ui.exit_handler)

