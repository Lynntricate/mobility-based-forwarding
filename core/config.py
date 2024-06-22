class Config:
    width = 1000
    height = 1000

    min_node_d = 100
    max_node_d = 400
    node_dd = 50     # Max difference between two waypoints

    granularity = 5  # Decimals

    num_waypoints = 100
    h_factor = 0.2
    v_factor = 0.3

    # node_velocity = 60
    max_node_velocity = 60
    min_node_velocity = 10
    node_velocity_dd = 5

    n_nodes = 60
    node_transmit_power = 300

    frame_interval = 16  # ms
    simulation_interval = 64  # ms
    mean_packet_production_interval = 6_000  # ms

    # max_age_traffic_data = 10_000  # ms
    max_sim_time = 60_000  # ms

    max_tx_failure = 9000
    max_hops = 10
    max_queue_length = 10
    min_relay_improvement = 0.2

    strategy = 'mbf'
    # ToDo do not remove from the queue the packet... (for count, count unique ids)




