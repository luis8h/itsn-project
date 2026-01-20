from typing import override
from tap import Tap

from config.base import ECUConfig
from config.ecus import ecu_1, ecu_2


class CmdLineConfig(Tap):
    remote_host: str = "127.0.0.1"
    remote_port: int = 9000

    @override
    def configure(self):
        self.add_argument("-H", "--remote_host", help="Hostname or IP-Address of the TCP Server")
        self.add_argument("-p", "--remote_port", help="Port of the TCP Server")


class Config:
    client_id: int = 0x0001
    proto_ver: int = 0x01
    ecus: list[ECUConfig] = [ecu_1, ecu_2]

    cmd: CmdLineConfig = CmdLineConfig().parse_args()


cfg = Config()
