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
from graphics.text_formatting import Color

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
        self.id = uuid.uuid4()
        self.aether_time = None

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
    def __init__(self, packet, queue_time, prio=0):
        self.packet: Packet = packet
        self.failure_count = 0
        self.prio: int = prio
        self.queue_time = queue_time
        self.backup_time = 0

    def __str__(self):
        return f"Packet with {self.failure_count} Failure(s)"


class RadioTask:
    def __init__(self, queue_item: QueueItem, relay):
        self.queue_item: QueueItem = queue_item
        self.relay: Node = relay
        self.remaining_tx = queue_item.packet.tx_time


class Node:
    sim_time = 0
    count_sent = 0
    count_success = 0
    count_failure_hop_limit_exceeded = 0
    count_failure_tx_limit_exceeded = 0
    count_failure_queue_limit_exceeded = 0
    count_failure_time_limit_exceeded = 0
    count_duplicate_received = 0
    def __init__(self, id: str, coordinate, velocity, waypoints=None):
        # print(random.randint(0, 100))
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
        self.prophet_old_nodes_in_range = set()
        self.nodes_in_range = set()
        self.node_estimations = {}  # key: dst_id, value: velocity_payload
        self.radioTask: Optional[RadioTask] = None

        # Display properties
        self.display_show_waypoints = False
        self.display_objects = []

        # self.time = 0
        self.finished = False

        # Traffic generation
        self.gen_timestamps = compute_packet_generation_times(Config.mean_packet_production_interval)

        self.received_packets = []
        self.sent_packet_ids = []

        self.all_node_ids = []  # WARNING: Do not touch except for target selection!

    def update_core(self):
        """
        Used to check for things that need to be done when time steps pass
        """
        if Config.strategy == 'prophet' and self.sim_time % 1000 == 0:
            # Age probabilities
            self.prophet_age()

        self.process_time_limits()

        if len(self.gen_timestamps):
            if self.sim_time == self.gen_timestamps[0]:
                # Generation timestamp reached!
                self.gen_timestamps.pop(0)
                self.queue_new_data_packet()

        if self.radioTask is None:
            self.check_and_set_radio_task()

        if self.radioTask is not None:
            # Radio is working on something
            ids_in_range = [n.id for n in self.nodes_in_range]

            if self.radioTask.relay is None and self.radioTask.queue_item.packet.dst in ids_in_range:
                # We can deliver directly to the destination, set destination as relay
                self.radioTask.relay = self.get_node_in_range_by_id(self.radioTask.queue_item.packet.dst)

            if self.radioTask.relay in self.nodes_in_range:  # radioTask is not of type RadioTask here...
                # Check if relay in range
                if self.radioTask.remaining_tx <= 0:
                    # Check if transmission is complete, if so -> relay receives transmission
                    self.radioTask.relay.receive(self.radioTask.queue_item.packet)
                    if self.radioTask.relay.id != self.radioTask.queue_item.packet.dst:
                        # If relay was not packet's destination, insert item back into queue
                        self.queue_insert(self.radioTask.queue_item)  # Do not delete packet after sending (unless no buffer)
                    self.radioTask = None

                    self.order_queue()
                    self.check_and_set_radio_task()

                # elif self.radioTask.queue_item.packet.dst not in ids_in_range:
                #     # Final destination of current radio task is not in range
                #     for queue_item in self.queue:
                #         # Check for other queue items
                #         if queue_item.packet.dst in ids_in_range:
                #             # But an item currently in the queue has a destination currently in range
                #             rt_copy = copy.copy(self.radioTask.queue_item)
                #             rt_copy.remaining_tx = rt_copy.packet.tx_time
                #             self.radioTask = RadioTask(queue_item, relay=self.select_relay(queue_item.packet.dst))    # Set radio task to queue item with dst in range
                #             self.queue.remove(queue_item)  # Remove queue item from queue
                #             self.queue_insert(rt_copy,  0)
                #             break
                else:
                    self.radioTask.remaining_tx -= Config.simulation_interval
            else:
                # Relay no longer in range OR relay is already self, find new relay
                self.radioTask.remaining_tx = self.radioTask.queue_item.packet.tx_time
                self.radioTask.relay = self.select_relay(self.radioTask.queue_item.packet.dst, strategy=Config.strategy)

                if self.radioTask.relay is not None and self.radioTask.relay not in self.nodes_in_range:
                    raise Exception(f'Selected relay {self.radioTask.relay} not in range, impossible')

                if self.radioTask.relay is None and len(self.queue) > 1:
                    # No relay found, if other packets are waiting, increase failure
                    self.radioTask.queue_item.failure_count += 1
                    if self.radioTask.queue_item.failure_count > Config.max_tx_failure:
                        # Tx failed too many times for packet, drop
                        self.count_failure_tx_limit_exceeded += 1
                        print(f'Dropping radioTask {self.radioTask} due to too many tx failures!')
                        self.radioTask = None
                        return
                    self.queue_insert(self.radioTask.queue_item)
                    if len(self.queue):
                        # Set next queue item as radio task
                        queue_item = self.queue.pop(0)
                        self.radioTask = RadioTask(queue_item, relay=self.select_relay(queue_item.packet.dst))

    def check_and_set_radio_task(self, queue_item=None):
        """
        Warning: only functions if self.radioTask is None
        """
        if self.radioTask is None:
            if queue_item is not None:
                relay = self.select_relay(queue_item.packet.dst, Config.strategy)
                self.radioTask = RadioTask(queue_item, relay)
                self.queue.remove(queue_item)

            for queue_item in self.queue:
                relay = self.select_relay(queue_item.packet.dst, Config.strategy)
                if relay == self:
                    # If relay is this node, we have no proper relay candidate -> do nothing
                    continue
                else:
                    # Otherwise, we have a new radioTask
                    self.radioTask = RadioTask(queue_item, relay=relay)
                    self.queue.remove(queue_item)
                    break
        else:
            raise Exception('RadioTask was not none, but tried to be set')

    def process_time_limits(self):
        # Remove too old packets from queue
        if self.radioTask and self.sim_time - self.radioTask.queue_item.packet.c_time > Config.max_packet_age:
            self.radioTask = None
            self.count_failure_time_limit_exceeded += 1
        for queue_item in self.queue:
            if self.sim_time - queue_item.packet.c_time > Config.max_packet_age:
                self.queue.remove(queue_item)
                self.count_failure_time_limit_exceeded += 1

    def update_pos(self):
        if math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]) \
                < self.vector.velocity:
            if self.waypointer >= len(self.waypoints) - 1:
                self.finished = True
                return
            self.waypointer += 1

            new_velocity = min(max(Config.min_node_velocity, self.vector.velocity
                               + random.uniform(-0.5 * Config.node_velocity_dd
                                                , 0.5 * Config.node_velocity_dd)), Config.max_node_velocity)

            self.update_vector(new_velocity)  # Update velocity here

        elif math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]) \
                <= self.vector.velocity:
            self.coordinate = self.coordinate.move(
                Vector(math.dist([self.coordinate.x, self.coordinate.y], [self.waypoints[self.waypointer].x, self.waypoints[self.waypointer].y]),
                       self.vector.heading))
            return

        self.coordinate = self.coordinate.move(self.vector)

    def update_vector(self, velocity):
        self.vector = Vector(velocity, math.atan2(self.waypoints[self.waypointer].y - self.coordinate.y, self.waypoints[self.waypointer].x - self.coordinate.x))

    def update_traffic_table(self, src_id, traffic_data, c_time, strategy=Config.strategy):
        if strategy == 'mbf':
            for node_id in [node_id for node_id in traffic_data.keys() if node_id != self.id]:
                self.node_estimations[node_id] = traffic_data[node_id]
        if strategy == 'prophet':

            if src_id not in [n.id for n in self.prophet_old_nodes_in_range] and src_id in [n.id for n in self.nodes_in_range]:
                start_p_src = self.node_estimations[src_id]
                # NEW ENCOUNTER
                # Update probability to encountered node according to PRoPHET algorithm
                self.node_estimations[src_id] = self.node_estimations[src_id] + (1 - self.node_estimations[src_id]) * Config.prophet_p_init
                # print(f'Src_diff: {self.node_estimations[src_id] - start_p_src}')

                for node_id in [node_id for node_id in traffic_data.keys() if node_id != self.id]:
                    start_p_n = self.node_estimations[node_id]
                    # Update all other nodes according to PRoPHET algorithm
                    self.node_estimations[node_id] \
                        = self.node_estimations[node_id] + (1 - self.node_estimations[node_id]) \
                          * self.node_estimations[src_id] * traffic_data[node_id] * Config.prophet_beta
                    # print(f'N_diff: {self.node_estimations[node_id] - start_p_n}')

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
        packet_ = copy.deepcopy(packet)  # Make deepcopy before continuing
        packet_.hop_count += 1
        if packet_.hop_count > Config.max_hops:
            self.count_failure_hop_limit_exceeded += 1
            print(f'Dropping packet {packet_} due to exceeding hop count!')
            return

        if self.sim_time - packet_.c_time > Config.max_packet_age:
            self.count_failure_time_limit_exceeded += 1
            # 3rd does not have this code in it. Other two are random/mbf with this.
            return

        if packet_.p_type == PacketType.TRAFFIC_UPDATE:
            self.update_traffic_table(packet_.src, packet_.payload, packet_.c_time)
        elif packet_.p_type == PacketType.DATA:
            if packet_.dst == self.id:
                packet_.aether_time = self.sim_time - packet_.c_time
                print(f'Packet {packet_.id} received at destination succesfully in '
                      f'{packet_.hop_count} hops and {packet_.aether_time} ms!')
                self.process_packet(packet_)
            elif packet.id not in [q_i.packet.id for q_i in self.queue] \
                    and (self.radioTask is None or packet.id != self.radioTask.queue_item.packet.id):
                self.queue_insert(QueueItem(packet_, self.sim_time))

    def process_packet(self, packet):
        if packet.id not in [p.id for p in self.received_packets]:
            # Check if this packet was already received before
            # We care only interested in the first time this packet was received, ignore others
            self.received_packets.append(packet)
            self.count_success += 1
        else:
            self.count_duplicate_received += 1

    def estimate_current_coordinate(self, target_id):
        """
        This function estimates the coordinate of a certain node, based on what is
        known about it through other node's updates (or directly from that node)
        """
        if target_id not in self.node_estimations:
            return None
        dst_mobility_payload: MobilityPayload = copy.deepcopy(self.node_estimations[target_id])
        age = self.sim_time - dst_mobility_payload.timestamp
        return dst_mobility_payload.coordinate.move(dst_mobility_payload.vector, duration=age, bounce=True)

    def vector_key(self, dst_coordinate_estimate, mobility_payload: MobilityPayload):
        # dst_coordinate_estimate: estimate of the location of the destination
        # mobility_payload: mobility_payload object of possible relay
        angle = math.atan2(dst_coordinate_estimate.y - mobility_payload.coordinate.y
                           , dst_coordinate_estimate.x - mobility_payload.coordinate.x)

        # # Calculate the age of the mobility vector, then add the uncertainty (factor * 2pi) to the calculated angle
        # mobility_age = self.sim_time - mobility_payload.timestamp
        # relay_uncertainty_factor = math.pi * mobility_age / Config.max_vector_age

        delta = abs(angle - mobility_payload.vector.heading)
        if delta > math.pi:
            delta = 2 * math.pi - delta

        return delta # * (1 - (mobility_payload.timestamp / Config.max_age_traffic_data))

    def select_relay(self, target_id, strategy=Config.strategy):  # Forwarding algo input here
        """
        strategy='mbf' -> The relay is selected based on the estimated location of the destination.
        We do not have to take into account the inaccuracy here, because the node
        with the best vector towards the estimated point is the best effort option
        regardless of how accurate our guess was
        """
        if strategy == 'mbf':
            dst_estimation = self.estimate_current_coordinate(target_id)
            if dst_estimation is None:
                return None
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
            relay_angle = self.vector_key(dst_estimation, MobilityPayload(relay.coordinate, relay.vector, self.sim_time))

            delta = abs(self_angle - relay_angle)
            if delta > math.pi:
                delta = 2 * math.pi - delta
            if self_angle < relay_angle or delta < Config.min_relay_improvement: # Second one has this code
                # Do not forward, keep packet ourselves
                return None
            return relay
        elif strategy == 'prophet':
            relays = sorted(self.nodes_in_range, key=lambda node: self.node_estimations[node.id], reverse=True)
            if len(relays) == 0 or self.node_estimations[relays[0].id] < self.node_estimations[self.id]:
                return None
            return relays[0]
        elif strategy == 'random':
            if random.randint(0, 1) == 0 or len(self.nodes_in_range) == 0:
                return None
            else:
                choice = random.randint(0, len(self.nodes_in_range) - 1)
                return list(self.nodes_in_range)[choice]

    def queue_new_data_packet(self, payload=None, tx_mode='unicast', prio=0):

        destination_id = random.choice(self.all_node_ids)
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
        # relay = self.select_relay(destination_id, strategy=Config.strategy)
        queue_item = QueueItem(packet, self.sim_time, prio=prio)
        if self.radioTask is None:
            # Set queue item as radioTask if there was none
            self.radioTask = RadioTask(queue_item, relay=self.select_relay(packet.dst))
        elif prio - self.radioTask.queue_item.prio > 10:
            # If priority of new packet is significantly higher, immediately replace current radioTask
            self.queue_insert(0, self.radioTask.queue_item)
            self.radioTask = RadioTask(queue_item, relay=self.select_relay(packet.dst))
        else:
            # Otherwise, append to queue as usual
            self.queue_insert(queue_item)
            # Order queue by priority
            # self.queue = sorted(self.queue, key=lambda q_i: q_i.prio, reverse=True) # ToDo sort by relay
        #print('new packet generated!')
        self.sent_packet_ids.append(packet.id)
        self.count_sent += 1

    def queue_insert(self, queue_item, index=None):
        old_len = len(self.queue)
        if len(self.queue) == Config.max_queue_length:
            # print(f'Exceeding queue length of {Config.max_queue_length} evicting with {Color.UNDERLINE}SHLI{Color.END}')
            self.count_failure_queue_limit_exceeded += 1
            shli_select = sorted([q_i for q_i in self.queue], key=lambda q_i: q_i.packet.c_time)[0]
            if shli_select.packet.c_time < queue_item.packet.c_time:
                # New queue item is younger than one or more other queue items -> evict oldest one
                self.queue.remove(shli_select)
            else:
                # Otherwise, new queue item is older than all current queue items
                return
        if index is None:
            self.queue.append(queue_item)
        else:
            self.queue.insert(index, queue_item)
        if len(self.queue) - old_len > 1:
            raise Exception('More than one queue item added, ERROR')

    def order_queue(self):
        if Config.strategy == 'random':
            return
        if Config.strategy == 'mbf':
            # self.queue = sorted(self.queue, key=lambda queue_item: self.vector_key(self.estimate_current_coordinate(queue_item.packet.dst), ))
            return
        if Config.strategy == 'prophet':
            self.queue = sorted(self.queue, key=lambda queue_item: self.node_estimations[queue_item.packet.dst], reverse=True)


    def get_node_in_range_by_id(self, node_id):
        for node in self.nodes_in_range:
            if node.id == node_id:
                return node

    def prophet_init(self):
        for n_id in self.all_node_ids:
            self.node_estimations[n_id] = 0

    def prophet_age(self):
        for node_id in self.node_estimations.keys():
            self.node_estimations[node_id] = self.node_estimations[node_id] * Config.prophet_gamma


    def __str__(self):
        return f"Node at {self.coordinate.x} x {self.coordinate.y}"





