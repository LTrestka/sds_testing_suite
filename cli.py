#!/usr/bin/python3

import argparse
import os
from pdb import run
import socket
import subprocess
import sys

from models.errors import ServiceNotInstalledError, ConfigurationError
from models.settings import Configuration
from models.helpers import Runner

class Operator:
    def __init__(self):
        self.parser = None
        self.config = None
        self.quiet = False
        self.verbose = False
        self.remote = False
        
        
    def list_tests(self):
        runner = Runner(self.config)
        
        if self.config.service == "cta":
            runner.add_commands(["ls /opt/enstore/tools;"])
        elif self.config.service == "enstore":
            runner.add_commands(["ls /opt/enstore/tools;"])
        
        print(runner.command)
        stdout, stderr = runner.run()
        self.log("Available Tests on this Node: ", 1)
        self._print_results(stdout, stderr)
    
    def print_help(self):
        self.parser.print_help()

    def run_tests(self):
        if self.config and self.config.valid():
            test_path = f'tests/{self.config.project}/{self.config.device}/{self.config.mover}_test.py'
            subprocess.run(['pytest', test_path])
        else:
            raise ConfigurationError(self.config)

    def detect_service(self, args):
        self.log(f"Searching for installed services on {args.node}")
        for service, path in {"CTA": "/etc/cta", "Enstore": "/opt/enstore"}.items():
            if not args.suite:
                self.log(f"Checking if {service} path exists at: {path}", 1)
                if os.path.exists(path):
                    self.log(f"Path exists: {path}", 1)
                    args.suite = service
                else:
                    self.log(f"Path not found: {path}", 1)
        if args.suite:
            self.log(f"{args.suite} install detected, looking up configuration.")
            self._lookup_config(args.node)
        else:
            raise ServiceNotInstalledError(args.node)

    def _lookup_config(self, node):
        self.config = Configuration.from_json(node)
        self.log(self.config.get(), 1)
    
    def log(self, output, verbose=0, force=False):
        if force or (verbose == 1 and self.verbose):
            print(output)
            return
        elif self.quiet:
            return
        elif verbose == 0 and not force:
            print(output)
        
        
    
    def _print_results(self, stdout, stderr):
        if sys.version_info > (3, 6, 8):
            if stdout:
                self.log(stdout, force=True)
            if stderr:
                self.log("Error:", stderr, force=True)
        else:
            if stdout:
                self.log(stdout.decode('utf-8'), force=True)
            if stderr:
                self.log("Error:", stderr.decode('utf-8'), force=True)
            
            
    
def main():
    ops = Operator()
    parser = argparse.ArgumentParser(description="Storage Operations Testing Suite")
    parser.add_argument('-n', '--node', default=socket.gethostname(), help="Node to run tests on")
    parser.add_argument('-l', '--list', action='store_true', help="List available tests for this configuration.")
    parser.add_argument('-r', '--run', help="Run the specified test.")
    parser.add_argument('-q', '--quiet', action='store_true', help="Doesn't print anything.")
    parser.add_argument('-v', '--verbose', action='store_true',  help="Prints detailed output.")
    
    subparsers = parser.add_subparsers(dest='suite', help="Choose the testing suite")
    
    # Detects the systems installed on this machine
    subparsers.add_parser('auto', help="Detects the service applicable to this node.")
    
    

    # CTA Testing Suite Parser
    cta_parser = subparsers.add_parser('cta', help="CTA Testing Suite")
    cta_parser.add_argument('-d', '--device', choices=['tape', 'disk'], required=True, help="Device type")
    cta_parser.add_argument('-m', '--mover', choices=['spectra', 'ibm'], required=True, help="Mover type")

    # Enstore Testing Suite Parser
    enstore_parser = subparsers.add_parser('enstore', help="Enstore Testing Suite")
    enstore_parser.add_argument('-d', '--device', choices=['tape', 'disk'], required=True, help="Device type")
    enstore_parser.add_argument('-m', '--mover', choices=['spectralogic', 'ibm'], required=True, help="Mover type")
    
    args = parser.parse_args()
    ops.verbose = args.verbose
    ops.quiet = args.quiet
    
    if args.suite is None:
        ops.detect_service(args)
    else:
        ops.config = Configuration(args.project, args.device, args.mover)
    
    if args.suite == "CTA":
        ops.parser = cta_parser
    elif args.suite == "Enstore":
        ops.parser = enstore_parser
        
    if args.list:
        ops.list_tests()
    elif args.run:
        ops.run_tests()
    else:
        ops.parser.print_help()

if __name__ == "__main__":
    main()
