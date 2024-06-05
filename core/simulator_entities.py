import uuid


class Node:
    def __init__(self, coordinate, waypoints=None):
        if waypoints is None:
            waypoints = []

        self.coordinate = coordinate
        self.waypoints = waypoints
        self.queue = []
        self.id = uuid.uuid4()

    def update_pos(self):
        pass

    def transmit(self, packet, relay=None):
        if relay is None:
            # Broadcast
            pass
        pass

    def receive(self):
        pass


class Packet:
    def __init__(self, src, dst, c_time, hop_count):
        self.src = src
        self.dst = dst
        self.c_time = c_time
        self.hop_count = hop_count
        self.payload = None


class Coordinate:
    def __init__(self, x, y):
        self.x = x
        self.y = y

        self.distance = None


class Vector:
    def __init__(self, velocity, heading):
        self.velocity = velocity
        self.heading = heading


class MobilityPayload:
    def __init__(self, coordinate, vector):
        self.coordinate = coordinate
        self.vector = vector
