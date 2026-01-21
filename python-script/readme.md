## Getting Started

#### General Start
Start a carla server and then run the script:
```sh
uv run main.py
```

#### Test Setup Start
The test setup means starting two versions of the application which have different ecu configs and letting them communicate with each other.

Start the first (normal) version:
```sh
uv run main.py
```

Start the second script (using different ecu configs - simulating a physical ecu):
```sh
uv run main_ecu_mock.py -p 9001
```


## Notes
The difference between `Publisher` and `Subscriber` services might be a bit unintuitive at first. For more info look into the [class definitions](./config/base.py) and into the [sample config](./config/ecus.py).

