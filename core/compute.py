from core.simulator_entities import *


def nodes_in_range(node_a, power, nodes):
    r_2 = power**2
    return [node_b for node_b in nodes
            if ((node_b.coordinate.x - node_a.coordinate.x)**2 + (node_b.coordinate.y - node_a.coordinate.y)**2) <= r_2]


if __name__ == '__main__':
    node_1 = Node(Coordinate(0, 0), 10)
    nodes_1 = [Node(Coordinate(0, 0), 20), Node(Coordinate(50, 50), 20, ), Node(Coordinate(201, 0), 20, ), Node(Coordinate(141.42, 141.42), 20, )]

    for node in nodes_in_range(node_1, 200, nodes_1):
        print(node.coordinate.x, node.coordinate.y)

