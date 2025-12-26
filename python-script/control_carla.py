import carla
import time

# Connect to CARLA server
client = carla.Client('localhost', 2000)
client.set_timeout(10.0)

world = client.get_world()

# Get a blueprint for a vehicle
blueprint_library = world.get_blueprint_library()
vehicle_bp = blueprint_library.filter('model3')[0]  # Tesla Model 3, example

# Choose a spawn point
spawn_points = world.get_map().get_spawn_points()
spawn_point = spawn_points[0]

# Spawn the vehicle
vehicle = world.spawn_actor(vehicle_bp, spawn_point)

try:
    # Control loop
    for i in range(50):
        vehicle.apply_control(carla.VehicleControl(throttle=0.5, steer=0.0))
        transform = vehicle.get_transform()
        velocity = vehicle.get_velocity()
        print(f"Position: {transform.location}, Velocity: {velocity}")
        time.sleep(0.1)

finally:
    vehicle.destroy()

