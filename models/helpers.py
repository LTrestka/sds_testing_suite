import subprocess
import sys

class Runner:
    def __init__(self, config, user=None):
        self.command = []
        if config.is_remote():
            self.node = config.node if not user else f"{user}@{config.node}"
            self.command = ["ssh"]
            if not user:
                self.command.append("-K") # delegate gssapi credentials to server
            self.command.append(self.node)
        else:
            self.node = None
        self.load_env(config.service)
        
    def load_env(self, service):
        if service == "cta":
            pass
        elif service == "enstore":
            self.command.extend([f"source ~{service}/.bashrc;"])
    
    def add_commands(self, commands):
        for command in commands:
            self.command.append(command)
    
    def run(self):
        try:
            result = subprocess.Popen(
                    self.command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
            result.wait()
            stdout, stderr = result.communicate()
            
            if result.returncode != 0:
                print(f"Error: {stderr}")
            else:
                print(f"Output: {stdout}")

            return stdout, stderr
        except subprocess.CalledProcessError as e:
            return f"Command failed: {e.stderr}"