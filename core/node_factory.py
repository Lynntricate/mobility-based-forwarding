import random
from core.simulator_entities import Node, Coordinate
from core.config import Config
import math

"""
Node Factory

This file contains generator functions for nodes, including their waypoint arrays, 
and the Node objects themselves
"""


def point_bounce(coordinate):
    if coordinate.x < 0:
        coordinate.x = -coordinate.x
    coordinate.x %= 2 * Config.width
    if coordinate.x > Config.width:
        coordinate.x = 2 * Config.width - coordinate.x

    if coordinate.y < 0:
        coordinate.y = -coordinate.y
    coordinate.y %= 2 * Config.height
    if coordinate.y > Config.height:
        coordinate.y = 2 * Config.height - coordinate.y

    return coordinate


def generate_waypoint_array(start, length, h_factor, v_factor):
    if length < 0:
        Exception('Length cannot be smaller than 0')
    if length == 0:
        return []

    waypoints = [start]
    w_h = random.uniform(0, 2*math.pi)  # Random heading (rad)
    w_v = random.uniform(Config.min_node_v, Config.max_node_v)  # Random velocity

    for i in range(length):
        w_x = round(waypoints[-1].x + w_v * math.cos(w_h), Config.granularity)  # Determine waypoint x
        w_y = round(waypoints[-1].y + w_v * math.sin(w_h), Config.granularity)  # Determine waypoint y

        waypoints.append(point_bounce(Coordinate(w_x, w_y)))  # Add waypoint to array
        bruh = h_factor * random.uniform(-math.pi, math.pi)
        w_h = w_h + bruh

        w_v = min(max(w_v + v_factor * random.uniform(-0.5 * Config.node_v_d, 0.5 * Config.node_v_d), Config.min_node_v), Config.max_node_v)

    # w_heading = math.atan2(dx, dy)

    return waypoints


def generate_coordinate_array(length, max_x, max_y, min_x=0, min_y=0):
    return [(generate_coordinate(max_x, max_y, min_x, min_y)) for _ in range(length)]


def generate_coordinate(max_x, max_y, min_x=0, min_y=0):
    return Coordinate(random.randint(min_x, max_x), random.randint(min_y, max_y))


def generate_nodes(count, max_x, max_y, num_waypoints, h_factor, v_factor, min_x=0, min_y=0):
    return [
        Node(Coordinate(x,y), generate_waypoint_array(Coordinate(x,y), num_waypoints, h_factor, v_factor))
        for x, y in generate_coordinate_array(count, max_x, max_y, min_x, min_y)
    ]


if __name__ == "__main__":
    random.seed(8908342)
    print(vars(point_bounce(Coordinate(-1281, 721))))
    print(vars(point_bounce(Coordinate(-10, -20))))
    # gen = generate_waypoint_array(Coordinate(50, 50), 100)
    # for coord in gen:
    #     print(f"x: {coord.x}, y: {coord.y}" )
    # print(generate_coordinate_array(10, 500, 500))
    # print(generate_coordinate_array(10, 500, 500))
