import subprocess
import argparse
import textwrap
from typing import Any, List, Dict


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
            self.command.extend([
                f"source ~{service}/.bashrc",
                "export PYTHONPATH=/opt/enstore:/opt/enstore/src:/opt/enstore/modules:/opt/enstore/HTMLgen:/opt/enstore/PyGreSQL"
            ])
    
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
    

class WorkflowParser(argparse.ArgumentParser):
    """Custom ArgumentParser used for parsing Ferry's swagger.json file and custom workflows into CLI arguments and objects"""

    def __init__(self: "WorkflowParser", **kwargs) -> None:  # type: ignore
        super().__init__(**kwargs)

    def set_arguments(self, params: List[Dict[str, Any]]) -> None:
        """Initializes arguments for the parser from the

        Args:
            params (list): An array of Dictionary objects representing a parameter option
        """
        for param in params:
            req = "required" if param.get("required", False) else "optional"
            self.add_argument(
                f"--{param['name']}",
                type=str,
                help=WorkflowParser.parse_description(
                    name="",
                    description=param["description"],
                    method=f"{param['type']}: {req}",
                ),
                required=param.get("required", False),
            )

    @staticmethod
    def create(description: str, **kwargs: Any) -> "WorkflowParser":
        """Creates a WorkflowParser instance.

        Args:
            description (string): Name of the WorkflowParser.

        Returns:
            WorkflowParser
        """
        return WorkflowParser(description=description, **kwargs)

    @staticmethod
    def create_subparser(
        name: str, description: str, method: str = "GET"
    ) -> "WorkflowParser":
        """Create a WorkflowParser subparser.

        Args:
            name (str): Name of subparser
            description (str): What does this subparser do?
            method (str, optional): API Method Type. Defaults to GET.

        Returns:
            WorkflowParser
        """
        description = WorkflowParser.parse_description(name, method, description)
        return WorkflowParser(description=description)

    @staticmethod
    def parse_description(
        name: str = "Endpoint", method: str = "", description: str = ""
    ) -> str:
        description_lines = textwrap.wrap(description, width=60)
        first_line = description_lines[0]
        rest_lines = description_lines[1:]
        endpoint_description = name.replace("/", "")

        if len(f"({method})") <= 49:
            method_char_count = 49 - len(f"({method})")
        else:
            method_char_count = 0

        endpoint_description = (
            f"{endpoint_description:<{method_char_count}} ({method}) | {first_line}\n"
        )
        for line in rest_lines:
            endpoint_description += f"{'':<50} | {line}\n"
        return endpoint_description