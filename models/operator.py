import argparse
import json
import os
import subprocess
import sys
from unittest import runner
from urllib import response
from models.globals import printv, SUPPORTED_WORKFLOWS
from models.errors import ConfigurationError, ServiceNotInstalledError
from models.helpers import Runner, WorkflowParser
from models.settings import Configuration


class Operator:
    global SUPPORTED_WORKFLOWS
    def __init__(self, args, extra_args):
        self.user = args.user
        self.parser = None
        self.config = None
        self.remote = False
        self.valid = False
        self.service_workflows = f"tests/$SERVICE/scripts/functions.json"
        self.quiet = args.quiet
        self.verbose = args.verbose
        if bool(args.node and args.suite and extra_args and extra_args.device and extra_args.mover):
            self.config = Configuration(args.node, args.suite, extra_args.device, extra_args.mover)
        elif args.node and (not extra_args or extra_args and not  (args.suite  or extra_args.device or extra_args.mover)):
            self._lookup_config(args.node, args.suite)
            
    
        
    def _lookup_config(self, node, service=None):
        self.config = Configuration.from_json(node)
        if self.config and not self.config.service and service:
            self.config.service = service
        self.valid = self.config.is_valid()
        self.remote = self.config.is_remote()
    
    def _print_results(self, stdout, stderr):
        if sys.version_info > (3, 6, 8):
            if stdout:
                print(f"    Response from {self.config.node}:\n".upper(), f"\n***************************************************\n\n", stdout, "\n***************************************************")
            if stderr:
                printv(stderr)
        else:
            if stdout:
                print("\nResponse: ", stdout.decode('utf-8'))
            if stderr:
                printv(stderr.decode('utf-8'))
    
    def create_workflow_parser(self, name, description, args) -> None:
        workflow_parser = WorkflowParser.create_subparser(
            name=name, description=description
        )
        workflow_parser.set_arguments(self.params)
        
    def print_help(self):
        self.parser.print_help()
        
    def list_tests(self):
        runner = Runner(self.config, self.user)
        
        if self.config.service == "cta":
            runner.add_commands(["ls /opt/enstore/tools"])
        elif self.config.service == "enstore":
            runner.add_commands(["ls /opt/enstore/tools"])
        
        cmd, stdout, stderr = runner.run()
        if stdout or stderr:
            printv(cmd)
            print("Available Tests:")
            self._print_results(stdout, stderr)

    def run_tests(self, test_name, test_args=None):
        if os.path.exists(f"tests/{self.config.service}/scripts/functions.json"):
            with open(f"tests/{self.config.service}/scripts/functions.json", "r") as f:
                functions = json.load(f)
                if test_name in functions:
                    test = functions[test_name]
                    args = test.get("args", [])
                    requirements = test.get("requirements", {})
                    commands = test.get("commands", [])
                    
                    # Validate user met requirements
                    self._validate_requirements(requirements)
                    
                    # Substitute arguments in commands as needed
                    commands = self._substitute_args(args, test_args, commands)
                    self.run_command(commands)
                    
                else:
                    raise ConfigurationError(f"Test: {test_name} not found in functions.json")
        else:    
            raise NotImplementedError(f"{test_name} not implemented")
    
        
    def run_command(self, cmd, test=False):
        if isinstance(cmd, str):
            cmd = cmd.replace("[", "").replace("]", "").split(",")
        runner = Runner(self.config, self.user)
        runner.add_commands(cmd)
        cmd, stdout, stderr = runner.run()
        if stdout or stderr:
            printv(cmd)
            if test:
                return stdout, stderr
            self._print_results(stdout, stderr)

    def detect_service(self, args):
        printv(f"Searching for installed services on {args.node}")
        for service, path in {"CTA": "/etc/cta", "Enstore": "/opt/enstore"}.items():
            if not args.suite:
                printv(f"Checking if {service} path exists at: {path}")
                if os.path.exists(path):
                    printv(f"Path exists: {path}")
                    args.suite = service.lower()
                else:
                    print(f"Path not found: {path}")
        if args.suite:
            printv(f"{args.suite} install detected, looking up configuration.")
            self._lookup_config(args.node, args.suite)
        else:
            raise ServiceNotInstalledError(args.node)
        
    
    def detect_remote_service(self, args):
        """Goes to the remote node and checks for the service"""
        runner = Runner(self.config, self.user)
        if runner.node:
            for service, path in {"CTA": "/etc/cta", "Enstore": "/opt/enstore", "Enstore": "/home/enstore"}.items():
                runner.add_commands([f'if [ -d "{path}" ]; then echo "{service}"; fi'])
            runner.add_commands(["/usr/bin/lsscsi -g"])
            cmd, stdout, stderr = runner.run()
            if stdout or stderr:
                lines = stdout.split("\n")
                movers = {}
                i = 0
                for line in lines:
                    if line.strip() and line in ["CTA", "Enstore"]:
                        printv(f"Service detected: {line.lower()}")
                        self.config.service = line.lower()
                    elif self.config.service and line.strip():
                        info = line.split()
                        if self.config.service == "cta":
                            if len(info) > 2 and info[1] in ["disk", "mediumx"]:
                                printv(f"Mover detected: {line[2:-1]}")
                                movers[i] = {"device_type": info[1], "mover_type": info[2], "slot": info[-1]}
                        elif self.config.service == "enstore":
                            if len(info) > 2 and info[1] in ["disk", "tape"]:
                                printv(f"Mover detected: {line[2:-1]}")
                                movers[i] = {"device_type": info[1], "mover_type": info[2], "slot": info[-1]}
                        else:
                            continue
                        i += 1
                        
                selected = self._select_remote_mover(movers)
                if selected:
                    self.config.device = selected["device_type"]
                    self.config.mover = selected["mover_type"]
                self.valid = self.config.is_valid()
                self.remote = self.config.is_remote()
            else:
                raise ServiceNotInstalledError(args.node)
                
    
    def _select_remote_mover(self, movers):
        prompt = ["Available movers: "]
        if not movers:
            return None
        for key, val in movers.items():
            prompt.append(f"    {key}: {val}")
        while True:
            response = input("\n".join(prompt) + "\nSelected Mover: ")
            if response and response.isnumeric() and int(response) in movers:
                return movers[int(response)]
            else:
                print("Invalid selection, please try again.")
        

    

    