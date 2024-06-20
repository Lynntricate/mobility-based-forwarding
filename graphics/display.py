import datetime
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


class Simulator:
    def __init__(self, seed):
        random.seed(seed)

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

        self.root.geometry(f"{Config.width}x{Config.height}")

        self.paused = False

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

    def initialize_nodes(self):
        for i in range(Config.n_nodes):
            self.create_node(Config.num_waypoints)

    def space_bar_pressed(self, event):
        self.paused = not self.paused

    def left_mouse_clicked(self, event):
        self.display_node(Node(event.x, event.y))

    def display_node(self, node: Node):
        tk_id = self.canvas.create_oval(
            node.coordinate.x - self.node_size, node.coordinate.y - self.node_size, node.coordinate.x + self.node_size,
            node.coordinate.y + self.node_size, tags=f"Node_{node.id}"
        )
        self.canvas.itemconfig(tk_id, fill="cyan")
        # self.canvas.tag_bind(f"Node_{node.id}", "<Button-1>", lambda event: self.toggle_node_waypoints(node))
        self.canvas.tag_bind(f"Node_{node.id}", "<Button-1>", lambda event: self.select_debug_source(node))

        self.canvas.tag_bind(f"Node_{node.id}", "<ButtonPress-2>", lambda event: self.show_nodes_in_range(node))
        self.canvas.tag_bind(f"Node_{node.id}", "<ButtonRelease-2>", lambda event: self.hide_nodes_in_range())

        self.canvas.tag_bind(f"Node_{node.id}", "<Button-3>", lambda event: self.select_debug_destination(node))

        self.nodes.add((node, tk_id))

        self.canvas.pack()

    def view_update(self):
        if not self.paused:
            for node, display_node in [(node, display_node) for (node, display_node) in self.nodes if
                                       not node.finished]:
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
        self.root.after(Config.simulation_interval, self.simulation_loop)

    def queue_hook(self):
        for node, _ in self.nodes:
            old_len = len(node.nodes_in_range)
            new_nodes = nodes_in_range(node, Config.node_transmit_power, [n for (n, _) in self.nodes if n.id != node.id])
            new_len = len(new_nodes)
            node.nodes_in_range = new_nodes
            if old_len != new_len:
                # Create update
                packet = Packet(
                    p_type=PacketType.TRAFFIC_UPDATE,
                    src=node.id,
                    dst=None,
                    c_time=self.sim_time,
                    hop_count=0,
                    payload={
                        **node.node_estimations,
                        **{node.id: MobilityPayload(
                                   coordinate=node.coordinate,
                                   vector=node.vector,
                                   timestamp=node.sim_time
                        )}},
                )
                # Broadcast update
                node.transmit(packet, relay='broadcast')

    def node_time_hook(self):
        for node, _ in self.nodes:
            Node.sim_time = self.sim_time
            # node.update_time(self.sim_time)

    def toggle_waypoints(self):
        for node, _ in self.nodes:
            self.toggle_node_waypoints(node, True)

        self.show_waypoints = not self.show_waypoints

    def show_nodes_in_range(self, node: Node):
        self.show_circle(node.coordinate, Config.node_transmit_power)
        for tk_id in [tk_id for n, tk_id in self.nodes if n in node.nodes_in_range]:
            print(tk_id)
            self.canvas.itemconfig(tk_id, fill='red')

        # [print(n) for n in node.node_estimations.values()]

    def select_debug_source(self, node: Node):
        if self.debug_destination is None:
            print('No debug destination selected...')
            return
        packet = Packet(
            p_type=PacketType.DATA,
            src=node.id,
            dst=self.debug_destination.id,
            c_time=self.sim_time,
            hop_count=0,
            payload='DUMMYPAYLOAD'
        )
        node.transmit(packet, relay='unicast')

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

    def show_circle(self, center: Coordinate, diameter):
        self.canvas.create_oval(center.x - diameter / 2, center.y - diameter / 2 ,center.x + diameter / 2, center.y + diameter / 2, outline='red', width=2, tags='range_oval')

    def toggle_node_waypoints(self, node: Node, hide_all=False):
        #### DEBUG #####
        print(len(node.nodes_in_range))
        #### DEBUG #####

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
        if v_factor is None: v_factor = Config.v_factor
        if coordinate is None: coordinate = generate_coordinate(Config.width, Config.height)
        node = Node(coordinate, Config.node_velocity, generate_waypoint_array(coordinate, num_waypoints, h_factor, v_factor))
        self.display_node(node)

    def reset_handler(self):
        print('reset not implemented')
        pass

    def restart_handler(self):
        print(f'Restarting...')

    def exit_handler(self):
        print(f"{Color.RED}{Color.BOLD}Simulation stopped at:{Color.END} "
              f"{Color.UNDERLINE}{datetime.datetime.now()}{Color.END}")
        self.root.quit()
