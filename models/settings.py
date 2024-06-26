import json
import os
import socket

class Configuration:
    def __init__(self, node=None, service=None, device_type=None, mover_type=None):
        self.node = node or socket.gethostname()
        self.service = service
        self.device = device_type
        self.mover = mover_type
    
    @staticmethod
    def from_json(node):
        if os.path.exists("config/server_specs.json"):
            with open("config/server_specs.json", "r+") as cfg_file:
                config = json.loads(cfg_file.read())
                if config and node in config:
                    return Configuration(
                        node, 
                        config[node].get("service", None),
                        config[node].get("device_type", None),
                        config[node].get("mover_type", None)
                    )
        return Configuration(node)
    
    def is_remote(self):
        return self.node != socket.gethostname()
    
    def valid(self):
        return self.node and self.service and self.device and self.mover
    
    def get(self):
        return f"""Found Configuration:
       node: {self.node}
    service: {self.service}
device_type: {self.device}
 mover_type: {self.mover}
                """
        