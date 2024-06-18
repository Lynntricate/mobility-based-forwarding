import functools
import math
import uuid
import time

from core.config import Config
from core.types import PacketType
import copy
from core.compute import point_bounce

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

    def move(self, vector, duration=Config.simulation_interval, bounce=False):
        duration = duration / 1_000  # ms to s
        self.x = round(self.x + vector.velocity * duration * math.cos(vector.heading), Config.granularity)  # Determine new x
        self.y = round(self.y + vector.velocity * duration * math.sin(vector.heading), Config.granularity)  # Determine new y

        if bounce:
            c = point_bounce(Coordinate(self.x, self.y))
            self.x = c.x
            self.y = c.y


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
        self.nodes_in_range = set()
        self.node_estimations = {}  # key: dst_id, value: velocity_payload

        # Display properties
        self.display_show_waypoints = False
        self.display_objects = []

        self.time = 0
        self.finished = False

    def update_pos(self):
        if math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]) \
                < self.vector.velocity:
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
                dst_estimation = self.estimate_current_coordinate(packet.dst)
                partial_vector_key = functools.partial(self.vector_key, dst_estimation)
                relay = sorted([*self.node_estimations.items()], key=lambda item: partial_vector_key(item[1]))
                print(relay[0])
                # Todo
                pass
            else:
                # No position estimate for destination -> forward randomly
                # Todo
                pass

    def estimate_current_coordinate(self, target_id):
        dst_mobility_payload: MobilityPayload = copy.deepcopy(self.node_estimations[target_id])
        age = self.time - dst_mobility_payload.timestamp
        return dst_mobility_payload.coordinate.move(dst_mobility_payload.vector, duration=age, bounce=True)

    def vector_key(self, dst_coordinate_estimate, mobility_payload: MobilityPayload):
        # dst_coordinate_estimate: estimate of the location of the destination
        # mobility_payload: mobility_payload object of possible relay

        angle = math.atan2(dst_coordinate_estimate.y - mobility_payload.coordinate.y
                           , dst_coordinate_estimate.x - mobility_payload.coordinate.x)

        return abs((angle - mobility_payload.vector.heading) % (2*math.pi))






