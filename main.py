from graphics.display import *
from core.node_factory import *
import random

start_c = Coordinate(740, 360)


if __name__ == "__main__":
    ui = Simulator(23423098)

    atexit.register(ui.exit_handler)

