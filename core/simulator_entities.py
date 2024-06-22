import functools
import math
import random
import uuid
import time

from core.config import Config
from core.types import PacketType
import copy
from core.compute import point_bounce, compute_packet_generation_times, nodes_in_range
from typing import Optional

class Packet:
    def __init__(self, p_type, src, dst, c_time, hop_count, tx_time,  tx_mode, payload=None):
        self.p_type = p_type
        self.src = src
        self.dst = dst
        self.c_time = c_time
        self.hop_count = hop_count
        self.payload = payload
        self.tx_time = tx_time
        self.tx_mode = tx_mode

    def __str__(self):
        return f"{self.p_type} from {self.src} to {self.dst} at hop {self.hop_count}"


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
        return self


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

    def __str__(self):
        return f"{self.coordinate}, {self.vector}, T: {self.timestamp}"

class QueueItem:
    def __init__(self, packet, relay, prio=0):
        self.packet: Packet = packet
        self.relay: Node = relay
        self.remaining_tx = packet.tx_time
        self.failure_count = 0
        self.prio = prio

    def __str__(self):
        return f"{self.packet} to {self.relay} with {self.remaining_tx}ms remaining in tx and {self.failure_count} Failure(s)"


class Node:
    sim_time = 0
    count_sent = 0
    count_success = 0
    count_failure_hop_limit_exceeded = 0
    count_failure_tx_limit_exceeded = 0
    count_failure_queue_limit_exceeded = 0
    # ToDo if neighborhood changes -> go over queue and see if something is available that can directly be transmitted
    # ToDo v updates
    def __init__(self, id: str, coordinate, velocity, waypoints=None):
        if waypoints is None:
            waypoints = []

        self.waypointer = 0
        # self.vector = Vector(velocity, 0)
        if len(waypoints) > 0:
            self.vector = Vector(velocity, math.atan2(waypoints[self.waypointer].y - coordinate.y, waypoints[self.waypointer].x - coordinate.x))

        self.coordinate = coordinate
        self.waypoints = waypoints
        self.queue = []
        self.id = id

        # Radio
        self.nodes_in_range = set()
        self.node_estimations = {}  # key: dst_id, value: velocity_payload
        self.radioTask: Optional[QueueItem] = None

        # Display properties
        self.display_show_waypoints = False
        self.display_objects = []

        # self.time = 0
        self.finished = False

        # Traffic generation
        self.gen_timestamps = compute_packet_generation_times(Config.mean_packet_production_interval)

    def update_core(self):
        """
        Used to check for things that need to be done when time steps pass
        """
        if len(self.gen_timestamps):
            if self.sim_time == self.gen_timestamps[0]:
                # Generation timestamp reached!
                self.gen_timestamps.pop(0)
                self.queue_new_data_packet()
        else:
            self.finished = True

        if self.radioTask is None:
            for _ in range(len(self.queue)):
                queue_item = self.queue.pop(0)
                if queue_item.relay == self:
                    # If relay is this node, we have no proper relay candidate. Put node back in queue and do nothing
                    self.queue_insert(queue_item)
                else:
                    # Otherwise, we have a new radioTask
                    self.radioTask = queue_item

        if self.radioTask is not None:
            # Radio is working on something
            ids_in_range = [n.id for n in self.nodes_in_range]
            if self.radioTask.relay in self.nodes_in_range:
                # Check if relay in range
                if self.radioTask.remaining_tx <= 0:
                    # Check if transmission is complete, if so -> relay receives transmission
                    self.radioTask.relay.receive(self.radioTask.packet)
                    self.radioTask = None
                elif self.radioTask.packet.dst not in ids_in_range:
                    # Final destination of current radio task is not in range
                    for queue_item in self.queue:
                        if queue_item.packet.dst in ids_in_range:
                            # But an item currently in the queue has a destination currently in range
                            rt_copy = copy.copy(self.radioTask)
                            rt_copy.remaining_tx = rt_copy.packet.tx_time
                            self.radioTask = queue_item
                            self.queue_insert(rt_copy, 0)
                            return
                else:
                    self.radioTask.remaining_tx -= Config.simulation_interval

            else:
                # Relay no longer in range OR relay is already self, find new relay
                self.radioTask.relay = self.select_relay(self.radioTask.packet.dst)

                if self.radioTask.relay is None and len(self.queue) > 1:
                    # No relay found, if other packets are waiting, increase failure
                    self.radioTask.failure_count += 1
                    if self.radioTask.failure_count > Config.max_tx_failure:
                        # Tx failed too many times for packet, drop
                        self.count_failure_tx_limit_exceeded += 1
                        print(f'Dropping radiotask {self.radioTask} due to too many tx failures!')
                        self.radioTask = None
                        return
                    self.queue_insert(self.radioTask)
                    if len(self.queue):
                        # Set next queue item as radio task
                        self.radioTask = self.queue.pop(0)

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
            self.coordinate = self.coordinate.move(
                Vector(math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]),
                       self.vector.heading))
            return

        self.coordinate = self.coordinate.move(self.vector)

    def update_vector(self, velocity):
        self.vector = Vector(velocity, math.atan2(self.waypoints[self.waypointer].y - self.coordinate.y, self.waypoints[self.waypointer].x - self.coordinate.x))

    def update_traffic_table(self, traffic_data, c_time):
        for node_id in [node_id for node_id in traffic_data.keys() if node_id != self.id]:
            self.node_estimations[node_id] = traffic_data[node_id]

    def broadcast_zero_time(self, packet):
        """
        Only use this function to send position/vector updates to other nodes. These
        update packets do not go through the queue, and also do not have any
        tx_time. This is not realistic for normal packets
        """
        if packet.tx_mode != 'broadcast':
            raise ValueError(f'Cannot Zero Time Broadcast this packet because it is not broadcast')
        for node in self.nodes_in_range:
            node.receive(packet)

    def receive(self, packet):
        if packet.p_type == PacketType.TRAFFIC_UPDATE:
            self.update_traffic_table(packet.payload, packet.c_time)
        elif packet.p_type == PacketType.DATA:
            if packet.dst == self.id:
                # ToDo Process success
                self.count_success += 1
                print(f'Packet received at destination succesfully in '
                      f'{packet.hop_count} hops and {self.sim_time - packet.c_time} ms!')
            elif packet.dst in self.node_estimations.keys():
                packet.hop_count += 1
                if packet.hop_count > Config.max_hops:
                    self.count_failure_hop_limit_exceeded += 1
                    print(f'Dropping packet {packet} due to exceeding hop count!')

                    return
                self.queue.append(QueueItem(packet, self.select_relay(packet.dst)))

            else:
                # Drop
                return
    def estimate_current_coordinate(self, target_id):
        """
        This function estimates the coordinate of a certain node, based on what is
        known about it through other node's updates (or directly from that node)
        """
        dst_mobility_payload: MobilityPayload = copy.deepcopy(self.node_estimations[target_id])
        age = self.sim_time - dst_mobility_payload.timestamp
        return dst_mobility_payload.coordinate.move(dst_mobility_payload.vector, duration=age, bounce=True)

    def vector_key(self, dst_coordinate_estimate, mobility_payload: MobilityPayload):
        # dst_coordinate_estimate: estimate of the location of the destination
        # mobility_payload: mobility_payload object of possible relay
        angle = math.atan2(dst_coordinate_estimate.y - mobility_payload.coordinate.y
                           , dst_coordinate_estimate.x - mobility_payload.coordinate.x)

        return abs((angle - mobility_payload.vector.heading) % (2*math.pi))

    def select_relay(self, target_id):
        """
        The relay is selected based on the estimated location of the destination.
        We do not have to take into account the inaccuracy here, because the node
        with the best vector towards the estimated point is the best effort option
        regardless of how accurate our guess was
        """
        dst_estimation = self.estimate_current_coordinate(target_id)
        partial_vector_key = functools.partial(self.vector_key, dst_estimation)
        relays = sorted(self.nodes_in_range, key=lambda node: partial_vector_key(
            MobilityPayload(
                coordinate=node.coordinate,
                vector=node.vector,
                timestamp=node.sim_time
            )))
        if len(relays) == 0:
            return None
        relay = relays[0]
        self_angle = self.vector_key(dst_estimation, MobilityPayload(self.coordinate, self.vector, self.sim_time))
        relay_angle = self.vector_key(dst_estimation, MobilityPayload(relay.coordinate,relay.vector, relay.sim_time))
        if abs(self_angle - relay_angle) < Config.min_relay_improvement:
            # Do not forward, keep packet ourselves
            return self
        return relays[0]

    def get_node_by_id(self, target_id):
        for node in self.nodes_in_range:
            if node.id == target_id:
                return node
        return None

    def queue_new_data_packet(self, payload=None, tx_mode='unicast', prio=0):
        self.count_sent += 1
        if len(self.node_estimations) == 0:
            # No known destinations
            print(f"Node {self} cannot append to queue because it has no known destinations!")
            return
        destination_id = random.choice(list(self.node_estimations.keys()))
        packet = Packet(
            p_type=PacketType.DATA,
            src=self.id,
            dst=destination_id,
            c_time=self.sim_time,
            hop_count=0,
            payload=payload,
            tx_time=100,
            tx_mode=tx_mode
        )
        relay = self.select_relay(destination_id)
        queue_item = QueueItem(packet, relay, prio=prio)
        if self.radioTask is None:
            # Set queue item as radioTask if there was none
            self.radioTask = queue_item
        elif prio - self.radioTask.prio > 10:
            # If priority of new packet is significantly higher, immediately replace current radioTask
            self.queue.insert(0, self.radioTask)
            self.radioTask = queue_item
        else:
            # Otherwise, append to queue as usual
            self.queue_insert(queue_item)
            # Order queue by priority
            sorted(self.queue, key=lambda q_i: q_i.prio, reverse=True)

    def queue_insert(self, queue_item, index=None):
        if len(self.queue) > Config.max_queue_length:
            print(f'Exceeding queue length of {Config.max_queue_length}')
            self.count_failure_queue_limit_exceeded += 1
        else:
            if index is None:
                self.queue.append(queue_item)
            else:
                self.queue.insert(index, queue_item)


    def __str__(self):
        return f"Node at {self.coordinate.x} x {self.coordinate.y}"





