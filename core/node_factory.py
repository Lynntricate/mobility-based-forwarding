import random
from core.simulator_entities import Node, Coordinate
from core.config import Config
import math

"""
Node Factory

This file contains generator functions for nodes, including their waypoint arrays, 
and the Node objects themselves
"""


def generate_waypoint_array(start, length, p_factor=1, s_factor=1, seed=None):
    # Generate first waypoint to determine initial direction
    w_x = start.x + (s_factor * random.randint(start.x, Config.width - start.x))
    w_y = start.x + (s_factor * random.randint(start.y, Config.height - start.y))

    w_last = Coordinate(w_x, w_y)
    waypoints = [w_last]

    for i in range(length - 1):
        dx = start.x - w_last.x
        dy = start.y - w_last.y
        w_angle = math.atan2(dx, dy)
        angle_delta = p_factor * random.uniform(0, 2*math.pi)

        w_x = start.x + (s_factor * random.randint(start.x))
    return waypoints


def generate_coordinate_array(length, max_x, max_y, min_x=0, min_y=0, seed=None):
    return [(generate_coordinate(max_x, max_y, min_x, min_y, seed=seed)) for _ in range(length)]


def generate_coordinate(max_x, max_y, min_x=0, min_y=0, seed=None):
    random.seed(seed)
    return random.randint(min_x, max_x), random.randint(min_y, max_y)


def generate_nodes(count, max_x, max_y, min_x=0, min_y=0, seed=None):
    return [
        Node(x, y, generate_waypoint_array()) for x, y in
        generate_coordinate_array(count, max_x, max_y, min_x, min_y, seed=seed)
    ]


if __name__ == "__main__":
    print(generate_waypoint_array(Coordinate(0, 0), 1, 1, 1 ))
    print(generate_coordinate_array(10, 500, 500, seed=8908342))
    print(generate_coordinate_array(10, 500, 500, seed=8908341))