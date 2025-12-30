import carla
import time
import math

from config.cfg import cfg
from config.data import SpeedData
from ethernet import SOMEIPForwarder

# TODO: add retry after some time if it fails, so that the script can also be started before carla

def main():
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)

    try:
        world = client.get_world()

        while True:
            vehicle_list = world.get_actors().filter('vehicle.*')
            for vehicle in vehicle_list:
                v = vehicle.get_velocity()
                speed_ms = math.sqrt(v.x**2 + v.y**2 + v.z**2)
                print_data(vehicle.id, speed_ms)
                # send_to_ecu_someip(vehicle.id, speed_ms)
            time.sleep(1)

    except Exception as e:
        print(f"Error: {e}")


def print_data(vehicle_id: int, speed: float):
    print(f"{vehicle_id:<15} | {speed:<15.2f}m/s")


if __name__ == '__main__':
    # main()
    forwarder = SOMEIPForwarder("127.0.0.1", 9000, cfg.client_id)
    forwarder.register_config(cfg.ecus)
    while True:
        data = SpeedData(10)
        forwarder.send(data)
        time.sleep(1)
