import carla
import time
import math

def main():
    # 1. Connect to the CARLA server
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)

    try:
        # 2. Get the world and current actor list
        world = client.get_world()

        # We wait for a tick to ensure we have the latest data from the server
        world.wait_for_tick()

        # 3. Filter for vehicles only
        vehicle_list = world.get_actors().filter('vehicle.*')

        if not vehicle_list:
            print("No vehicles found in the simulation.")
            return

        print(f"Found {len(vehicle_list)} vehicles. Retrieving speeds...\n")
        print(f"{'Vehicle ID':<15} | {'Speed (m/s)':<15} | {'Speed (km/h)':<15}")
        print("-" * 50)

        # 4. Iterate and calculate speeds
        while True:
            vehicle_list = world.get_actors().filter('vehicle.*')
            for vehicle in vehicle_list:
                v = vehicle.get_velocity()

                # Speed is the magnitude of the velocity vector: sqrt(x^2 + y^2 + z^2)
                speed_ms = math.sqrt(v.x**2 + v.y**2 + v.z**2)
                speed_kmh = 3.6 * speed_ms

                print(f"{vehicle.id:<15} | {speed_ms:<15.2f} | {speed_kmh:<15.2f}")
            time.sleep(1)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
