import socket
import sys

class ServiceNotInstalledError(Exception):
    """Exception raised when a required service is not installed."""
    def __init__(self, node):
        self.node = "this node" if node == socket.gethostname() else node
        super().__init__(f"Neither CTA or Enstore is not installed on {self.node}. Exiting.")
        sys.exit(1)

class ConfigurationError(Exception):
    """Exception raised when a required service is not installed."""
    def __init__(self, config=None, message=None):
        if message:
            super().__init__(message)
            sys.exit(1)
        if not config:
            super().__init__(f"No configuration detected. Exiting.")
            sys.exit(1)
        missing = []
        for item in ["node", "service", "device", "mover"]:
            if not getattr(config, item):
                missing.append(item)
        super().__init__(f"Configuration items missing: {missing}")
        sys.exit(1)

class ExecutionError(Exception):
    """Exception raised when a required service is not installed."""
    def __init__(self, cmd=None):
        if not cmd:
            super().__init__(f"ExecutionError | No command specified")
        else:
            super().__init__(f"ExecutionError | Command Failed, please review | Command: {cmd}")
        sys.exit(1)