import datetime
from tkinter import *
from PIL import Image, ImageTk
from core.simulator_entities import *
import time
from graphics.text_formatting import *
import atexit


class Simulator:
    def __init__(self, nodes):
        self.s_nodes = []

        # Initialize TKinter
        self.root = Tk()

        # Config
        self.w = 1280
        self.h = 720

        self.node_size = 10

        self.root.title("NodeSim™")

        icon_image = Image.open('graphics/network.png')
        icon_photo = ImageTk.PhotoImage(icon_image)
        self.root.iconphoto(False, icon_photo)

        self.root.geometry(f"{self.w}x{self.h}")

        self.paused = False

        # Keybindings
        self.root.bind('<space>', self.space_bar_pressed)
        self.root.bind('<Button-1>', self.left_mouse_clicked)

        # Canvas
        self.canvas = Canvas(self.root, width=self.w, height=self.h)  # Can specify options

        # Initialize nodes
        for node in nodes:
            self.display_node(node)

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
        self.s_nodes.append(self.canvas.create_oval(
            node.x - self.node_size, node.y - self.node_size, node.x + self.node_size, node.y + self.node_size
        ))
        self.canvas.pack()

    def physics_update(self):
        if not self.paused:
            for node in self.s_nodes:
                pass

    def exit_handler(self):
        print(f"{Color.RED}{Color.BOLD}Simulation stopped at:{Color.END} "
              f"{Color.UNDERLINE}{datetime.datetime.now()}{Color.END}")
        print(len(self.s_nodes))



