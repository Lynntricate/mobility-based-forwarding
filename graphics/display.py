import datetime
import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk

from core.config import Config
from core.node_factory import generate_waypoint_array, generate_coordinate
from core.simulator_entities import *
import time
from graphics.text_formatting import *
from functools import partial
import atexit


class Simulator:
    def __init__(self, seed):
        self.seed = seed

        self.nodes = []
        self.s_nodes = []
        self.s_display_objects = []

        self.selected = None

        # Initialize TKinter
        self.root = Tk()

        # Config
        self.waypoints_visible = False
        self.w = 1280
        self.h = 720

        self.node_size = 10
        self.waypoint_size = 5

        self.num_waypoints = 10

        self.root.title("NodeSim™")

        icon_image = Image.open('graphics/network.png')
        icon_photo = ImageTk.PhotoImage(icon_image)
        self.root.iconphoto(False, icon_photo)

        self.root.geometry(f"{self.w}x{self.h}")

        self.paused = False

        # Keybindings
        self.root.bind('<space>', self.space_bar_pressed)

        # Canvas
        self.canvas = Canvas(self.root, width=self.w, height=self.h)  # Can specify options

        # Add buttons to simulator

        button_restart = tk.Button(self.root, text="Reset    ", command=self.reset_handler)
        button_restart.place(x=1200, y=10)

        button_waypoints = tk.Button(self.root, text="Generate ", command=self.create_node)
        button_waypoints.place(x=1200, y=40)

        button_waypoints = tk.Button(self.root, text="Waypoints", command=self.toggle_waypoints)
        button_waypoints.place(x=1200, y=70)

        button_stop = tk.Button(self.root, text="Shutdown", command=self.exit_handler)
        button_stop.place(x=1200, y=100)

        # Start simulation
        self.root.update()
        print(f"{Color.GREEN}{Color.BOLD}Simulation started at:{Color.END}"
              f" {Color.UNDERLINE}{datetime.datetime.now()}{Color.END}")
        self.root.mainloop()

    def space_bar_pressed(self, event):
        self.paused = not self.paused

    def left_mouse_clicked(self, event):
        self.display_node(Node(event.x, event.y))

    def display_node(self, node: Node):
        s_node = self.canvas.create_oval(
            node.coordinate.x - self.node_size, node.coordinate.y - self.node_size, node.coordinate.x + self.node_size, node.coordinate.y + self.node_size, tags=f"Node_{node.id}"
        )
        self.canvas.itemconfig(s_node, fill="cyan")
        self.canvas.tag_bind(f"Node_{node.id}", "<Button-1>", lambda event: self.display_node_waypoints(node))
        self.s_nodes.append(s_node)

        self.canvas.pack()

    def display_node_waypoints(self, node: Node):
        last_coord = Coordinate(node.coordinate.x, node.coordinate.y)
         # Delete all waypoints
        for display_object in [tup[1] for tup in self.s_display_objects if tup[0] == node]:
            self.canvas.delete(display_object)
        self.s_display_objects = [tup for tup in self.s_display_objects if tup[0] == node]

        # ToDo visibility map

        for waypoint in node.waypoints:
            arrow = self.canvas.create_line(last_coord.x, last_coord.y, waypoint.x, waypoint.y, arrow=tk.LAST)
            self.s_display_objects.append((node, arrow))

            self.s_display_objects.append((node, self.canvas.create_oval(
                waypoint.x - self.waypoint_size, waypoint.y - self.waypoint_size
                , waypoint.x + self.waypoint_size, waypoint.y + self.waypoint_size
            )))
            last_coord = Coordinate(waypoint.x, waypoint.y)

    def physics_update(self):
        if not self.paused:
            for node in self.s_nodes:
                pass

    def toggle_waypoints(self):
        if not self.waypoints_visible:
            for node in self.nodes:
                self.display_node_waypoints(node)
        else:
            for display_node in self.s_display_objects:
                self.canvas.delete(display_node)
            self.s_display_objects = []
        self.waypoints_visible = not self.waypoints_visible

    def create_node(self, num_waypoints=None, h_factor=None, v_factor=None, coordinate=None):
        if num_waypoints is None: num_waypoints = Config.num_waypoints
        if h_factor is None: h_factor = Config.h_factor
        if v_factor is None: v_factor = Config.v_factor
        if coordinate is None: coordinate = generate_coordinate(Config.width, Config.height)
        node = Node(coordinate, generate_waypoint_array(coordinate, num_waypoints, h_factor, v_factor))
        self.nodes.append(node)
        self.display_node(node)

    def reset_handler(self):
        self.nodes = []
        for s_node in self.s_nodes:
            self.canvas.delete(s_node)
        for _, s_display_object in self.s_display_objects:
            self.canvas.delete(s_display_object)
        self.canvas.pack()

    def restart_handler(self):
        print(f'Restarting...')


    def exit_handler(self):
        print(f"{Color.RED}{Color.BOLD}Simulation stopped at:{Color.END} "
              f"{Color.UNDERLINE}{datetime.datetime.now()}{Color.END}")
        print(len(self.s_nodes))
        self.root.quit()



