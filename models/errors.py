import socket

class ServiceNotInstalledError(Exception):
    """Exception raised when a required service is not installed."""
    def __init__(self, node):
        self.node = "this node" if node == socket.gethostname() else node
        super().__init__(f"Neither CTA or Enstore is not installed on {self.node}. Exiting.")

class ConfigurationError(Exception):
    """Exception raised when a required service is not installed."""
    def __init__(self, config=None):
        if not config:
            super().__init__(f"No configuration detected. Exiting.")
        
        missing = []
        for item in ["node", "service", "device", "mover"]:
            if not getattr(config, item):
                missing.append(item)
        super().__init__(f"Configuration items missing: {missing}")