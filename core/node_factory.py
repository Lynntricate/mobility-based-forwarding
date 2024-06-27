import random
from core.simulator_entities import Node, Coordinate
from core.config import Config
import math

"""
Node Factory

This file contains generator functions for nodes, including their waypoint arrays, 
and the Node objects themselves
"""


def generate_waypoint_array(start, length, h_factor, v_factor):
    if length < 0:
        Exception('Length cannot be smaller than 0')
    if length == 0:
        return []

    waypoints = [start]
    w_h = random.uniform(0, 2*math.pi)  # Random heading (rad)
    w_d = random.uniform(Config.min_node_d, Config.max_node_d)  # Random velocity

    while len(waypoints) < length:
        w_h = w_h + h_factor * random.uniform(-math.pi, math.pi)

        w_x = round(waypoints[-1].x + w_d * math.cos(w_h), Config.granularity)  # Determine waypoint x
        w_y = round(waypoints[-1].y + w_d * math.sin(w_h), Config.granularity)  # Determine waypoint y

        if w_x < 0 or w_x > Config.width or w_y < 0 or w_y > Config.height:
            # Point outside of area, readjust heading and try again
            continue

        waypoints.append(Coordinate(w_x, w_y))  # Add waypoint to array

        w_h = w_h + (h_factor * random.uniform(-math.pi, math.pi))

        w_d = min(max(w_d + v_factor * random.uniform(-0.5 * Config.node_dd, 0.5 * Config.node_dd), Config.min_node_d), Config.max_node_d)

    return waypoints


def generate_coordinate_array(length, max_x, max_y, min_x=0, min_y=0):
    return [(generate_coordinate(max_x, max_y, min_x, min_y)) for _ in range(length)]


def generate_coordinate(max_x, max_y, min_x=0, min_y=0):
    return Coordinate(random.randint(min_x, max_x), random.randint(min_y, max_y))


def generate_nodes(count, max_x, max_y, num_waypoints, h_factor, v_factor, min_x=0, min_y=0):
    return [
        Node(f"Node_{random.randint(0, 99999999)}", Coordinate(x, y), generate_waypoint_array(Coordinate(x,y), num_waypoints, h_factor, v_factor))
        for x, y in generate_coordinate_array(count, max_x, max_y, min_x, min_y)
    ]


if __name__ == "__main__":
    random.seed(8908342)

    # print(vars(point_bounce(Coordinate(-1281, 721))))
    # print(vars(point_bounce(Coordinate(-10, -20))))
    # gen = generate_waypoint_array(Coordinate(50, 50), 100)
    # for coord in gen:
    #     print(f"x: {coord.x}, y: {coord.y}" )
    # print(generate_coordinate_array(10, 500, 500))
    # print(generate_coordinate_array(10, 500, 500))
