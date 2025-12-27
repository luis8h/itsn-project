import carla
import time


def main():
    client = carla.Client("localhost", 2000)
    client.set_timeout(5.0)
    world = client.get_world()

    # Get a blueprint for a vehicle
    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter('model3')[0]  # Tesla Model 3

    # Choose a spawn point
    spawn_points = world.get_map().get_spawn_points()
    spawn_point = spawn_points[0]

    vehicle = None
    try:
        # Spawn the vehicle
        vehicle = world.spawn_actor(vehicle_bp, spawn_point)

        # Print type and actor ID
        print(f"Spawned {vehicle.type_id} with actor ID {vehicle.id}")

        vehicle.set_autopilot(True)

        print("Vehicle running. Press CTRL+C to quit.")

        # Keep the script alive until user quits
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Script interrupted by user.")

    finally:
        if vehicle is not None:
            vehicle.destroy()
            print("[INFO] Vehicle destroyed. Bye.")

if __name__ == "__main__":
    main()

