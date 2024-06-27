from core.simulator_entities import *
import random
import numpy as np

def nodes_in_range(node_a, power, nodes):
    r_2 = (power / 2)**2
    return [node_b for node_b in nodes
            if ((node_b.coordinate.x - node_a.coordinate.x)**2 + (node_b.coordinate.y - node_a.coordinate.y)**2) <= r_2]


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


def compute_packet_generation_times(mean_production_interval):
    """
    Use a Poisson process to determine when packets are generated inside a node.
    This function will return an array with the timestamps at which a packet
    will be generated by the node.
    """
    # Create as many random generation intervals as there is (on average) time for in the simulation
    inter_arrival_time_samples = \
        np.random.exponential(mean_production_interval,
                              size=int((Config.max_sim_time/Config.mean_packet_production_interval)/Config.generation_one_on_n))

    inter_arrival_times = (np.ceil(inter_arrival_time_samples
                                   / Config.simulation_interval) * Config.simulation_interval).astype(int)

    for i, inter_arrival_time in enumerate(inter_arrival_times):
        if i == 0:
            continue
        inter_arrival_times[i] = inter_arrival_times[i] + inter_arrival_times[i-1]

    return inter_arrival_times.tolist()

def test( power):
    r_2 = (power / 2)**2
    coord_a = Coordinate(417.33309, 739.79125)
    coords = [Coordinate(549.41241, 805.83848), Coordinate(296.71755, 478.22763)]
    return [coord for coord in coords if ((coord.x - coord_a.x)**2 + (coord.y - coord_a.y)**2) <= r_2]


if __name__ == '__main__':
    print(test(200))

    print(compute_packet_generation_times(Config.mean_packet_production_interval))
    print(point_bounce(Coordinate(100, 1000)))

    # print(point_bounce(Coordinate(-100, 0)))
    # print(point_bounce(Coordinate(-50, -50)))
    # print(point_bounce(Coordinate(200, 2000)))

    # node_1 = Node(Coordinate(0, 0), 10)
    # nodes_1 = [Node(Coordinate(0, 0), 20), Node(Coordinate(50, 50), 20, ), Node(Coordinate(201, 0), 20, ), Node(Coordinate(141.42, 141.42), 20, )]
    #
    # for node in nodes_in_range(node_1, 200, nodes_1):
    #     print(node.coordinate.x, node.coordinate.y)

