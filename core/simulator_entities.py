import math
import uuid
import time

from core.config import Config
from core.types import PacketType


class Node:
    def __init__(self, coordinate, velocity, waypoints=None):
        if waypoints is None:
            waypoints = []

        self.waypointer = 0
        # self.vector = Vector(velocity, 0)
        if len(waypoints) > 0:
            self.vector = Vector(velocity, math.atan2(waypoints[self.waypointer].y - coordinate.y, waypoints[self.waypointer].x - coordinate.x))

        self.coordinate = coordinate
        self.waypoints = waypoints
        self.queue = []
        self.id = uuid.uuid4()

        # Radio
        self.nodes_in_range = []
        self.node_estimations = {}  # { dst_id:  payload: MobilityPayload }

        # Display properties
        self.display_show_waypoints = False
        self.display_objects = []

        self.time = 0
        self.finished = False

    def update_pos(self):
        if math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]) \
                < 1:
            if self.waypointer >= len(self.waypoints) - 1:
                self.finished = True
                return
            self.waypointer += 1

            self.update_vector(self.vector.velocity)  # Update velocity here

        elif math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]) \
                <= self.vector.velocity:
            self.coordinate.move(
                Vector(math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]),
                       self.vector.heading))
            return

        self.coordinate.move(self.vector)

    def update_time(self, sim_time):
        # ToDo global variable
        self.time = sim_time

    def update_vector(self, velocity):
        self.vector = Vector(velocity, math.atan2(self.waypoints[self.waypointer].y - self.coordinate.y, self.waypoints[self.waypointer].x - self.coordinate.x))

    def update_traffic_table(self, traffic_data, c_time):
        for node_id in traffic_data.keys():
            self.node_estimations[node_id] = [traffic_data[node_id][0], traffic_data[node_id][1], c_time]

    def transmit(self, packet, relay=None):
        if relay is None:
            # Broadcast
            for node in self.nodes_in_range:
                node.receive(packet)
        else:
            relay.receive(packet)

    def receive(self, packet):
        if packet.p_type == PacketType.TRAFFIC_UPDATE:
            self.update_traffic_table(packet.payload, packet.c_time)
        elif packet.p_type == PacketType.DATA:
            if packet.dst == self.id:
                # ToDo Process success
                print('Packet received at destination succesfully!')
            elif packet.dst in self.node_estimations.keys():
                # Packet
                # Todo
                pass
            else:
                # No position estimate for destination -> forward randomly
                # Todo
                pass

    def estimate_position(self, target_id):
        self.node_estimations[target_id]


class Packet:
    def __init__(self, p_type, src, dst, c_time, hop_count, payload=None):
        self.p_type = p_type
        self.src = src
        self.dst = dst
        self.c_time = c_time
        self.hop_count = hop_count
        self.payload = payload


class Coordinate:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.distance = None

    def __eq__(self, other):
        if not isinstance(other, Coordinate):
            return NotImplemented
        return (self.x == other.x and
                self.y == other.y and
                self.distance == other.distance)

    def __str__(self):
        return f"C: ({self.x}, {self.y})"

    def move(self, vector):
        self.x = round(self.x + vector.velocity * math.cos(vector.heading), Config.granularity)  # Determine new x
        self.y = round(self.y + vector.velocity * math.sin(vector.heading), Config.granularity)  # Determine new y


class Vector:
    def __init__(self, velocity, heading):
        self.velocity = velocity
        self.heading = heading

    def __str__(self):
        return f"V: {self.velocity}, {self.heading}"


class MobilityPayload:
    def __init__(self, coordinate, vector, timestamp):
        self.coordinate = coordinate
        self.vector = vector
        self.timestamp = timestamp
