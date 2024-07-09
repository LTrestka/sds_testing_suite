import argparse
import os
import sys
from typing import Any, Dict, List

from models.errors import ConfigurationError
from models.helpers import WorkflowParser
from models.globals import printv



class Workflow:
    """Workflow object that as the baseline for our custom workflows"""

    def __init__(self, data) -> None:
        self.name: str = data.get("title")
        self.description: str = data.get("description")
        self.requirements: Dict[str, Any] = data.get("requirements")
        self.commands: List[str] = data.get("commands")
        self.params: List[Dict[str, Any]] = data.get("params")
        self.init_parser()

    def init_parser(self) -> None:
        self.parser = WorkflowParser.create_subparser(
            name=self.name, description=self.description
        )
        self.parser.set_arguments(self.params)

    def get_info(self) -> None:
        self.parser.print_help()

    def get_description(self) -> None:
        print(self.parser.description)
        
    def _validate_requirements(self, operator):
        if not operator or not operator.config:
            raise ConfigurationError(operator.config,"Operator is not configured properly.")
        if self.requirements.get("service", False) and operator.config.service != self.requirements["service"]:
            raise ConfigurationError(operator.config, "Selected Service  is incompatible with this test.")
        if self.requirements.get("user", False) and operator.user != self.requirements["user"]:
            raise ConfigurationError(operator.config, "User required for this test does not match input.")
        if self.requirements.get("nodes", False) and operator.config.node not in self.requirements["nodes"]:
            raise ConfigurationError(operator.config, "Selected node is incompatible with this test.")
        if self.requirements.get("mounts", False) and not self._validate_mounts(operator):
            raise ConfigurationError(operator.config, "Mounts required for this test are not present.")
        
    def _validate_mounts(self, operator):
        commands = []
        exists = {mount: False for mount in self.requirements["mounts"]}
        for mount in self.requirements["mounts"]:
            if operator.remote:
                commands.append(f'if [ -d "{mount}" ]; then echo "path exists: {mount}"; fi')
            else:
                exists[mount] = os.path.exists(mount)
        if operator.remote:
            stdout, stderr = operator.run_command(commands, test=True)
            if stdout:
                for line in stdout.split("\n"):
                    if line.strip() and "path exists" in line:
                        exists[line.split(":")[-1].strip()] = True
        return all(exists.values())
    
    def _finalized_commands(self, args):
        commands = []
        for line in self.commands:
            for params in self.params:
                if hasattr(args, params["name"]):
                    line = line.replace(f"${params['name']}", getattr(args, params["name"]))
            commands.append(line)
        return commands

    def run(self, operator, *args): 
        self._validate_requirements(operator)
        commands = self._finalized_commands(*args)
        operator.run_command(commands)

        