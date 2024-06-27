import subprocess
import sys

from models.errors import ExecutionError

class Runner:
    def __init__(self, config, user="root"):
        self.command = []
        self.remote = config.is_remote()
        if self.remote:
            self.node = f"{user}@{config.node}"
            self.command.append(f"ssh -Ktx {self.node} '")
        else:
            self.node = None
        self.load_env(config.service)
        
    def load_env(self, service):
        if service == "cta":
            pass
        elif service == "enstore":
            self.command.extend([f"source ~{service}/.bashrc"])
    
    def add_commands(self, commands):
        for command in commands:
            self.command.append(command)
    
    def run(self):
        cmd = ""
        try:
            if self.remote and  "ssh" in self.command[0]:
                cmd = f"{self.command[0]}{'; '.join(self.command[1:])};'"
            else:
                cmd = f"{'; '.join(self.command)};"
            result = subprocess.Popen(
                    [cmd],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
            result.wait()
            stdout = result.stdout.read()
            stderr = result.stderr.read()
            
            if not stdout and not stderr:
                raise ExecutionError(cmd)
            
            return f"Ran: {cmd}", stdout, stderr
        except subprocess.CalledProcessError as e:
            return f"Command failed: {cmd} \nError: {e.stderr}", None, None