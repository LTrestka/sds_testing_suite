import os
import subprocess
import sys
from models.globals import printv
from models.errors import ConfigurationError, ServiceNotInstalledError
from models.helpers import Runner
from models.settings import Configuration


class Operator:
    def __init__(self, args, extra_args):
        self.parser = None
        self.config = None
        self.remote = False
        self.valid = False
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
        if self.config and self.config.is_valid():
            self.valid = True
            self.remote = self.config.is_remote()
        print(self.config.get())
    
    def _print_results(self, stdout, stderr):
        if sys.version_info > (3, 6, 8):
            if stdout:
                print(stdout)
            if stderr:
                print(stderr)
        else:
            if stdout:
                print(stdout.decode('utf-8'))
            if stderr:
                print(stderr.decode('utf-8'))
        
    def print_help(self):
        self.parser.print_help()
        
    def list_tests(self):
        runner = Runner(self.config)
        
        if self.config.service == "cta":
            runner.add_commands(["ls /opt/enstore/tools"])
        elif self.config.service == "enstore":
            runner.add_commands(["ls /opt/enstore/tools"])
        
        cmd, stdout, stderr = runner.run()
        if stdout or stderr:
            printv(cmd)
            print("Available Tests:")
            self._print_results(stdout, stderr)

    def run_tests(self, test_name):
        raise NotImplementedError(f"{test_name} not implemented")

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
        raise NotImplementedError(f"detect_remote_service not implemented")
