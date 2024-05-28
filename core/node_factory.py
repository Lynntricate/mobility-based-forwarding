import random


def generate_waypoint_array(length, max_x, max_y, min_x=0, min_y=0, seed=None):
    return [(generate_coordinate(max_x, max_y, min_x, min_y, seed=seed)) for _ in range(length)]


def generate_coordinate(max_x, max_y, min_x=0, min_y=0, seed=None):
    random.seed(seed)
    return random.randint(min_x, max_x), random.randint(min_y, max_y)




if __name__ == "__main__":
    print(generate_waypoint_array(10, 500, 500, seed=8908342))
    print(generate_waypoint_array(10, 500, 500, seed=8908341))