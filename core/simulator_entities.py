

class Node:
    def __init__(self, x, y, waypoints=None):
        if waypoints is None:
            waypoints = []

        self.x = x
        self.y = y
        self.waypoints = waypoints
        self.queue = []

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
