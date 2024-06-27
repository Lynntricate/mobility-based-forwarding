class Config:
    width = 800
    height = 800

    min_node_d = 20
    max_node_d = 100
    node_dd = 20     # Max difference between two waypoints

    granularity = 5  # Decimals

    num_waypoints = 500
    h_factor = 1
    # v_factor = 0.1

    # node_velocity = 60
    max_node_velocity = 60
    min_node_velocity = 10
    node_velocity_dd = 5

    n_nodes = 100
    node_transmit_power = 150  # Second 3 at 500, first at 200

    frame_interval = 16  # ms
    simulation_interval = 50  # ms
    mean_packet_production_interval = 1_500  # ms

    max_age_traffic_data = 10_000  # ms
    max_sim_time = 100_000  # ms

    generation_one_on_n = 10  # ToDo remember

    max_tx_failure = 9000
    max_hops = 6
    max_queue_length = 15  # 15
    max_packet_age = max_sim_time
    min_relay_improvement = 1.5  # 1.0

    strategy = 'random'

    # PRoPHET
    prophet_p_init = 0.9  # Used for adjusting probability to encountered nodes (0 < prophet_p_init < 1)
    prophet_beta = 0.75    # Used for adjusting probabilities to nodes known to encountered nodes (0 < prophet_beta < 1)
    # Aging occurs once every timestep (so once every simulation_interval in milliseconds)
    prophet_gamma = 0.95  # Used for aging probabilities, once per second (0 < prophet_gamma < 1)

    # MBF
    max_vector_age = max_sim_time / 10
    # After a packet has been in the queue for this time, it will be forwarded, regardless of vector, if possible
    queue_remain_time = max_sim_time / 30





