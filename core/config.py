class Config:
    width = 1920
    height = 1080

    min_node_d = 10
    max_node_d = 30
    node_dd = 2

    granularity = 5  # Decimals

    num_waypoints = 2000
    h_factor = 0.2
    v_factor = 0.5

    node_velocity = 60

    n_nodes = 100
    node_transmit_power = 300

    frame_interval = 16  # ms
    simulation_interval = 50  # ms
    mean_packet_production_interval = 10_000  # ms

    # max_age_traffic_data = 10_000  # ms
    max_sim_time = 100_000  # ms

    max_tx_failure = 50
    max_hops = 20
    max_queue_length = 3
    min_relay_improvement = 0.7




