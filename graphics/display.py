import csv
import datetime
import time
import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk

from core.config import Config
from core.node_factory import generate_waypoint_array, generate_coordinate
from core.simulator_entities import *
from graphics.text_formatting import *
from functools import partial
import atexit
import random
from core.compute import nodes_in_range
import numpy as np
import os
import shutil


class Simulator:
    def __init__(self, seed):
        # Seed random number generators
        random.seed(seed)
        np.random.seed(seed)

        self.nodes = set()  # Tuples of node, tk_id
        self.s_display_objects = []

        self.selected = None

        # Initialize TKinter
        self.root = Tk()

        # Config
        self.show_waypoints = False

        self.node_size = 10
        self.waypoint_size = 5

        self.root.title("NodeSim™")

        icon_image = Image.open('graphics/network.png')
        icon_photo = ImageTk.PhotoImage(icon_image)
        self.root.iconphoto(False, icon_photo)
        self.csv_path = None
        self.start_time = None
        self.h_factor = None

        self.root.geometry(f"{Config.width}x{Config.height}")

        self.paused = False

        # Initialize result files
        self.initialize_result_files()

        # Keybindings
        self.root.bind('<space>', self.space_bar_pressed)

        # Canvas
        self.canvas = Canvas(self.root, width=Config.width, height=Config.height)  # Can specify options

        # Add buttons to simulator

        button_restart = tk.Button(self.root, text="Reset    ", command=self.reset_handler)
        button_restart.place(x=1200, y=10)

        button_waypoints = tk.Button(self.root, text="Generate ", command=self.create_node)
        button_waypoints.place(x=1200, y=40)

        button_waypoints = tk.Button(self.root, text="Waypoints", command=self.toggle_waypoints)
        button_waypoints.place(x=1200, y=70)

        button_stop = tk.Button(self.root, text="Shutdown", command=self.exit_handler)
        button_stop.place(x=1200, y=100)

        self.initialize_nodes()

        # Debug
        self.debug_destination = None

        self.started = False
        # Start simulation
        self.sim_time = 0
        self.root.update()
        self.view_update()
        self.simulation_loop()
        print(f"{Color.GREEN}{Color.BOLD}Simulation started at:{Color.END}"
              f" {Color.UNDERLINE}{datetime.datetime.now()}{Color.END}")
        self.root.mainloop()

    def initialize_result_files(self):
        self.start_time = int(time.time())

        header = ['end_time', 'run_time', 'avg_delay', 'avg_hop_count', 'success_count', 'failure_count'
            , 'failure_queue_limit', 'failure_hop_limit', 'failure_tx_limit', 'failure_time_limit', 'total_in_queue', 'total_sent', 'config_h_factor']

        config_filename = f'config.py'
        result_filename = f'results_{Config.strategy}.csv'
        result_folder = 'results'
        run = 'test_run_1'
        dst_dir = f'{result_folder}/{run}/{self.start_time}'
        os.makedirs(dst_dir, exist_ok=True)
        dst_path_config = os.path.join(dst_dir, config_filename)
        shutil.copy('core/config.py', dst_path_config)
        print(vars(Config))
        self.h_factor = Config.h_factor

        self.csv_path = f'{result_folder}/{run}/{result_filename}'

        new_file = False
        if not os.path.exists(self.csv_path):
            new_file = True

        with open(self.csv_path, mode='a', newline='\n') as file:
            writer = csv.writer(file)

            if new_file:
                writer.writerow(header)

    def initialize_nodes(self):
        for i in range(Config.n_nodes):
            self.create_node(Config.num_waypoints)
        for node, _ in self.nodes:
            node.all_node_ids = [node.id for node, _ in self.nodes]
            if Config.strategy == 'prophet':
                # Set all probabilities to 0 at the start
                node.prophet_init()

    def space_bar_pressed(self, event):
        self.paused = not self.paused

    def display_node(self, node: Node):
        tk_id = self.canvas.create_oval(
            node.coordinate.x - self.node_size, node.coordinate.y - self.node_size, node.coordinate.x + self.node_size,
            node.coordinate.y + self.node_size, tags=f"Node_{node.id}"
        )
        self.canvas.itemconfig(tk_id, fill="cyan")
        self.canvas.tag_bind(f"Node_{node.id}", "<Button-1>", lambda event: self.toggle_node_waypoints(node))
        # self.canvas.tag_bind(f"Node_{node.id}", "<Button-1>", lambda event: self.select_debug_source(node))

        self.canvas.tag_bind(f"Node_{node.id}", "<ButtonPress-2>", lambda event: self.show_nodes_in_range(event, node))
        self.canvas.tag_bind(f"Node_{node.id}", "<ButtonRelease-2>", lambda event: self.hide_nodes_in_range())

        self.canvas.tag_bind(f"Node_{node.id}", "<Button-3>", lambda event: self.select_debug_destination(node))

        self.nodes.add((node, tk_id))

        self.canvas.pack()

    def view_update(self):
        if not self.paused:
            for node, display_node in self.nodes:
                node.update_pos()
                self.canvas.moveto(display_node, node.coordinate.x - self.waypoint_size,
                                   node.coordinate.y - self.waypoint_size)
        self.root.after(Config.frame_interval, self.view_update)

    def simulation_loop(self):
        if not self.paused:
            """Simulation hooks go here"""
            self.queue_hook()
            self.node_time_hook()
            """Simulation hooks go here"""
            if self.started:
                self.sim_time += Config.simulation_interval
            else:
                self.started = True
        if self.sim_time >= Config.max_sim_time:
            self.root.destroy()
        self.root.after(Config.simulation_interval, self.simulation_loop)

    def queue_hook(self):
        for node in [n for n, _ in self.nodes]:
            # Node processes
            if not node.finished:
                node.update_core()

            # print(nodes_in_range(node, Config.node_transmit_power, [n for (n, _) in self.nodes if n.id != node.id]))

            # For all nodes in simulator, check which ones are in range, and send update if necessary
            old_len = len(node.nodes_in_range)
            new_nodes = nodes_in_range(node, Config.node_transmit_power,
                                       [n for (n, _) in self.nodes if n.id != node.id])
            new_len = len(new_nodes)
            node.prophet_old_nodes_in_range = node.nodes_in_range
            node.nodes_in_range = new_nodes
            if old_len != new_len:
                self.send_service_broadcast_packet(src_node=node)

    def send_service_broadcast_packet(self, src_node, strategy=Config.strategy):
        packet = Packet(
            p_type=PacketType.TRAFFIC_UPDATE,
            src=src_node.id,
            dst=None,
            c_time=self.sim_time,
            hop_count=0,
            tx_time=0,
            tx_mode='broadcast'
        )
        if strategy == 'mbf':
            # Create payload for Mobility Based Forwarding
            packet.payload = {
                **src_node.node_estimations,
                **{src_node.id: MobilityPayload(
                    coordinate=src_node.coordinate,
                    vector=src_node.vector,
                    timestamp=src_node.sim_time
                )}}
        elif strategy == 'prophet':
            # Create payload for PRoPHET
            packet.payload = {
                **src_node.node_estimations
            }
        # Broadcast update
        src_node.broadcast_zero_time(packet)

    def node_time_hook(self):
        for node, _ in self.nodes:
            Node.sim_time = self.sim_time
            # node.update_time(self.sim_time)

    def toggle_waypoints(self):
        for node, _ in self.nodes:
            self.toggle_node_waypoints(node, True)

        self.show_waypoints = not self.show_waypoints

    def show_nodes_in_range(self, event, node: Node):
        print(node.vector.velocity)
        center = Coordinate(x=node.coordinate.x + 4, y=node.coordinate.y + (self.node_size / 2))
        self.show_circle(center, Config.node_transmit_power)
        for n, tk_id in [(n, tk_id) for (n, tk_id) in self.nodes if n in node.nodes_in_range]:
            self.canvas.itemconfig(tk_id, fill='red')

        arrow_self = self.canvas.create_line(node.coordinate.x + (self.node_size / 2)
                                             , node.coordinate.y + (self.node_size / 2)
                                             , node.waypoints[node.waypointer].x + (self.node_size / 2)
                                             , node.waypoints[node.waypointer].y + (self.node_size / 2),
                                             arrow=tk.LAST, fill='black', width=4)
        self.s_display_objects.append(arrow_self)

        if node.radioTask is not None:
            relay = node.radioTask.relay
            print(f'Relay: {relay}')
            if relay is not None:
                # print(f'Vector key: {node.vector_key(estimate, MobilityPayload(relay.coordinate, relay.vector, node.sim_time))}')
                arrow_relay = self.canvas.create_line(relay.coordinate.x + (self.node_size / 2)
                                                      , relay.coordinate.y + (self.node_size / 2)
                                                      , relay.waypoints[relay.waypointer].x + (self.node_size / 2)
                                                      , relay.waypoints[relay.waypointer].y + (self.node_size / 2),
                                                      arrow=tk.LAST, fill='yellow', width=4)
                self.s_display_objects.append(arrow_relay)

        if node.radioTask is not None:
            if Config.strategy == 'mbf' or Config.strategy == 'random':
                estimate = node.estimate_current_coordinate(node.radioTask.queue_item.packet.dst)
                if estimate is not None:
                    arrow_target = self.canvas.create_line(node.coordinate.x + (self.node_size/2)
                                                           , node.coordinate.y + (self.node_size/2)
                                                           , estimate.x + (self.node_size/2)
                                                           , estimate.y + (self.node_size/2),
                                                    arrow=tk.LAST, fill='green', width=4)
                    self.s_display_objects.append(arrow_target)

                for n, tk_id in self.nodes:
                    if node.radioTask is not None:
                        if n.id == node.radioTask.relay.id and n.id == node.radioTask.queue_item.packet.dst:
                            self.canvas.itemconfig(tk_id, fill='orange')
                        if n.id == node.radioTask.relay.id:
                            self.canvas.itemconfig(tk_id, fill='yellow')
                            print(node.radioTask.relay in node.nodes_in_range)
                if n.id == node.radioTask.queue_item.packet.dst:
                    self.canvas.itemconfig(tk_id, fill='green')
        if Config.strategy == 'prophet':
            print(node.id)
            print(f'Good: {[(node_id, value) for node_id, value in node.node_estimations.items() if value > 0.0001]}')

        # [print(n) for n in node.node_estimations.values()]
        # print(node.id, f'task_remaining: {node.radioTask}  queueLength: {len(node.queue)}')
        # print('------------------------Start--------------------------------')
        # print(node.coordinate, [event.x, event.y])
        # for nb in node.nodes_in_range:
        #     print(nb.coordinate)
        # print('------------------------ End --------------------------------') Node_73017958

    def select_debug_source(self, node: Node):
        if self.debug_destination is None:
            print('No debug destination selected...')
            return

        node.queue_new_data_packet(payload='DUMMYPAYLOAD', tx_mode='unicast', prio=999)

    def select_debug_destination(self, node: Node):
        if self.debug_destination:
            for n, tk_id in self.nodes:
                if n == self.debug_destination:
                    self.canvas.itemconfig(tk_id, fill='cyan')
                    self.debug_destination = None

        for n, tk_id in self.nodes:
            if n == node:
                self.canvas.itemconfig(tk_id, fill='green')
                self.debug_destination = n

    def hide_nodes_in_range(self):
        self.canvas.delete('range_oval')
        for tk_id in [tk_id for _, tk_id in self.nodes]:
            self.canvas.itemconfig(tk_id, fill='cyan')
        for tk_id in self.s_display_objects:
            self.canvas.delete(tk_id)

    def show_circle(self, center: Coordinate, diameter):
        self.canvas.create_oval(center.x - (diameter / 2), center.y - (diameter / 2), center.x + (diameter / 2),
                                center.y + (diameter / 2), outline='red', width=2, tags='range_oval')

    def toggle_node_waypoints(self, node: Node, hide_all=False):
        if node.display_show_waypoints or hide_all:
            # Remove all node waypoints if previously visible
            for display_object in node.display_objects:
                self.canvas.delete(display_object)
            node.display_objects.clear()
            node.display_show_waypoints = False
            return

        last_coord = Coordinate(node.coordinate.x, node.coordinate.y)
        if not node.display_show_waypoints:
            # Show all waypoints if previously not visible
            for waypoint in node.waypoints:
                arrow = self.canvas.create_line(last_coord.x, last_coord.y, waypoint.x, waypoint.y, arrow=tk.LAST)
                node.display_objects.append(arrow)
                node.display_objects.append(self.canvas.create_oval(
                    waypoint.x - self.waypoint_size, waypoint.y - self.waypoint_size
                    , waypoint.x + self.waypoint_size, waypoint.y + self.waypoint_size
                ))
                last_coord = Coordinate(waypoint.x, waypoint.y)
            node.display_show_waypoints = True
            return

    def create_node(self, num_waypoints=None, h_factor=None, v_factor=None, coordinate=None):
        if num_waypoints is None: num_waypoints = Config.num_waypoints
        if h_factor is None: h_factor = Config.h_factor
        if v_factor is None: v_factor = Config.h_factor
        if coordinate is None: coordinate = generate_coordinate(Config.width, Config.height)
        node = Node(f"Node_{random.randint(0, 99999999)}"
                    , coordinate
                    , random.uniform(Config.min_node_velocity, Config.max_node_velocity)
                    , generate_waypoint_array(coordinate
                                              , num_waypoints
                                              , h_factor
                                              , v_factor))
        self.display_node(node)

    def reset_handler(self):
        print('reset not implemented')
        pass

    def restart_handler(self):
        print(f'Restarting...')

    def exit_handler(self):
        total_success = 0
        total_sent = 0
        total_queue = 0
        total_queue_limit_exceeded = 0
        total_failure_hop_limit_exceeded = 0
        total_failure_tx_limit_exceeded = 0
        total_failure_time_limit_exceeded = 0
        total_duplicate_count = 0
        all_rcvd_packets = []
        for node, _ in self.nodes:
            total_success += node.count_success
            total_sent += node.count_sent
            total_queue += len(node.queue)
            if node.radioTask is not None:
                total_queue += 1
            total_queue_limit_exceeded += node.count_failure_queue_limit_exceeded
            total_failure_hop_limit_exceeded += node.count_failure_hop_limit_exceeded
            total_failure_tx_limit_exceeded += node.count_failure_tx_limit_exceeded
            total_failure_time_limit_exceeded += node.count_failure_time_limit_exceeded
            all_rcvd_packets.extend(node.received_packets)
            all_packet_delays = [p.aether_time for p in all_rcvd_packets]
            all_hop_counts = [p.hop_count for p in all_rcvd_packets]
            total_duplicate_count += node.count_duplicate_received


        # Count failures
        all_ids = set([p.id for p in all_rcvd_packets])
        print(len(all_ids))
        print(len(all_packet_delays))
        failure_count = 0
        success_count = 0

        for node, _ in self.nodes:
            for p_id in node.sent_packet_ids:
                if p_id not in all_ids:
                    failure_count += 1
                else:
                    success_count += 1

        avg_delay = self.get_average(all_packet_delays, 1000)
        avg_hops = self.get_average(all_hop_counts)


        print(f"{Color.RED}{Color.BOLD}Simulation stopped at:{Color.END} "
              f"{Color.UNDERLINE}{datetime.datetime.now()}{Color.END}")
        print("------------------------------SUMMARY-----------------------------------")
        print(f"Success: {Color.GREEN}{Color.BOLD}{total_success}{Color.END}")
        print(f"Total failed: {Color.RED}{Color.BOLD}{failure_count}{Color.END}")
        print(f"      Queue limit : {Color.RED}{Color.BOLD}{total_queue_limit_exceeded}{Color.END}")
        print(f"      Hop limit   : {Color.RED}{Color.BOLD}{total_failure_hop_limit_exceeded}{Color.END}")
        print(f"      Tx limit    : {Color.RED}{Color.BOLD}{total_failure_tx_limit_exceeded}{Color.END}")
        print(f"      Time limit  : {Color.RED}{Color.BOLD}{total_failure_time_limit_exceeded}{Color.END}")

        print(f"Total duplicates: {Color.RED}{Color.BOLD}{total_duplicate_count}{Color.END}")

        print(f"In queue : {Color.BLUE}{Color.BOLD}{total_queue}{Color.END}")
        print(f"Avg delay: {Color.PURPLE}{Color.BOLD}{avg_delay}{Color.END}")
        print(f"Avg hops: {Color.YELLOW}{Color.BOLD}{avg_hops}{Color.END}")

        print("------------------------------------------------------------------------")
        print(f"Total sent: {Color.CYAN}{total_sent}{Color.END}")
        print(f"Strategy: {Color.BOLD}{Color.BLUE}{Config.strategy}{Color.END}")

        self.root.quit()


        with open(self.csv_path, mode='a', newline='\n') as file:
            writer = csv.writer(file)
            writer.writerow([self.start_time, Config.max_sim_time, avg_delay, avg_hops, success_count, failure_count
                                , total_queue_limit_exceeded, total_failure_hop_limit_exceeded
                                , total_failure_tx_limit_exceeded, total_failure_time_limit_exceeded, total_queue, total_sent, self.h_factor])

    def get_average(self, array, divide_by=1):
        if len(array) == 0:
            return None
        return round((sum(array)/divide_by)/len(array), Config.granularity)

