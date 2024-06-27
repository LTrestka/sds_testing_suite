#!/usr/bin/python3

import argparse
from models.globals import *

import socket


from models.operator import Operator
from models.settings import Configuration

def main():
    
    parser = argparse.ArgumentParser(description="Storage Operations Testing Suite")
    parser.add_argument('-n', '--node', default=socket.gethostname(), help="Node to run tests on (default: local).")
    parser.add_argument('-l', '--list', action='store_true', help="List available tests for this configuration.")
    parser.add_argument('-r', '--run', help="Run the specified test.")
    parser.add_argument('-q', '--quiet', action='store_true', help="Doesn't print anything.")
    parser.add_argument('-v', '--verbose', action='store_true',  help="Prints detailed output.")
    
    subparsers = parser.add_subparsers(dest="suite", help="Choose the testing suite.", required=False)
    
    # Detects the systems installed on this machine
    subparsers.add_parser('auto', help="Detects the service applicable to this node (default).")

    # CTA Testing Suite Parser
    cta_parser = subparsers.add_parser('cta', help="CTA Testing Suite")
    cta_parser.add_argument('-d', '--device', choices=['tape', 'disk'], required=True, help="Device type.")
    cta_parser.add_argument('-m', '--mover', choices=['spectra', 'ibm'], required=True, help="Mover type.")

    # Enstore Testing Suite Parser
    enstore_parser = subparsers.add_parser('enstore', help="Enstore Testing Suite")
    enstore_parser.add_argument('-d', '--device', choices=['tape', 'disk'], required=True, help="Device type.")
    enstore_parser.add_argument('-m', '--mover', choices=['spectra', 'ibm'], required=True, help="Mover type.")
    
    args = parser.parse_args()
    extra_args = None
    set_quiet_mode(args.quiet)
    set_verbose_mode(args.verbose)
        
    if args.suite == "cta":
        extra_args = cta_parser.parse_args()
    elif args.suite == "enstore":
        extra_args = enstore_parser.parse_args()
        
    ops = Operator(args, extra_args)
    if not ops.valid and args.suite is None:
        ops.detect_service(args)
    elif not ops.valid and extra_args:
        ops.config = Configuration(args.node, args.suite, extra_args.device, extra_args.mover)
    
    if ops.config and ops.config.service == "cta" or args.suite == "cta":
        ops.parser = cta_parser
    elif ops.config and ops.config.service == "enstore" or args.suite == "enstore":
        ops.parser = enstore_parser
    
    if args.list:
        ops.list_tests()
    elif args.run:
        ops.run_tests(args.run)
    else:
        ops.parser.print_help()

if __name__ == "__main__":
    main()
