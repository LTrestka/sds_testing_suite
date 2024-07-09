#!/usr/bin/python3

import argparse
import sys
from models.globals import *

import socket


from models.helpers import WorkflowParser
from models.operator import Operator
from models.settings import Configuration
from models.workflow import Workflow
from models.globals import SUPPORTED_WORKFLOWS

def load_workflows():
    global SUPPORTED_WORKFLOWS
    for service in ["cta", "enstore"]:
        printv(f"Checking if workflows exist for: {service}...")
        if os.path.exists(f"tests/{service}/scripts/workflows.json"):
            printv(f"Workflows exist, loading workflows for {service}.")
            with open(f"tests/{service}/scripts/workflows.json", "r") as f:
                workflows = json.load(f)
                for name, definition in workflows.items():
                    SUPPORTED_WORKFLOWS[service][name] = Workflow(definition)

class SDSAdminCLI:
    def __init__(self):
        load_workflows()
        self.parser, self.cta_parser, self.enstore_parser = self.get_arg_parser()
        
    def get_arg_parser(self):
        # Create the parser
        parser = argparse.ArgumentParser(description="Storage Operations Testing Suite")
        parser.add_argument('-u', '--user', default='root', help="User to log in as on remote nodes (default: root).")
        parser.add_argument('-n', '--node', default=socket.gethostname(), help="Node to run tests on (default: local).")
        parser.add_argument(
            "--filter",
            default=None,
            help="(string) Use to filter results in the 'list' flag.",
        )
        parser.add_argument(
            '-l', 
            '--list', 
            action=self.list_workflows_action(),  # type: ignore
            nargs=0,
            #action='store_true', 
            help="List available tests for this configuration."
        )
        parser.add_argument('-r', '--run', help="Run the specified test.")
        parser.add_argument('-c', '--cmd', nargs='+', help="Run custom command(s) sequentially.")
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
        
        return parser, cta_parser, enstore_parser
    
    @staticmethod
    def get_filter_args() -> argparse.Namespace:
        global SUPPORTED_WORKFLOWS
        filter_parser = WorkflowParser()
        filter_parser.set_arguments(
            [
                {
                    "name": "filter",
                    "description": "Filter by workflow title (contains)",
                    "type": "string",
                    "required": False,
                }
            ]
        )
        filter_args, _ = filter_parser.parse_known_args()
        return filter_args
    
    def list_workflows_action(self):  # type: ignore
        """List all available workflows for a given service"""
        global SUPPORTED_WORKFLOWS
        class _ListWorkflows(argparse.Action):
            def __call__(  # type: ignore
                self: "_ListWorkflows", parser, args, values, option_string=None
            ) -> None:
                filter_args = SDSAdminCLI.get_filter_args()
                filter_str = (
                    f' (filtering for "{filter_args.filter}")'
                    if filter_args.filter
                    else ""
                )
                
                for service in ["cta", "enstore"]:
                    print(
                    f"""\n******************************** All supported {service} workflows{filter_str} ********************************"""
                )
                    for name, workflow in SUPPORTED_WORKFLOWS[service].items():
                        if filter_args.filter:
                            if filter_args.filter.lower() in name.lower():
                                workflow.get_description()
                        else:
                            workflow.get_description()

                sys.exit(0)

        return _ListWorkflows
    
    def workflow_params_action(self):  # type: ignore
        class _WorkflowParams(argparse.Action):
            def __call__(  # type: ignore
                self: "_WorkflowParams", parser, args, values, option_string=None
            ) -> None:
                try:
                    # Finds workflow inherited class in dictionary if exists, and initializes it.
                    for service in ["cta", "enstore"]:
                        if values in SUPPORTED_WORKFLOWS[service]:
                            workflow = SUPPORTED_WORKFLOWS[service][values]
                    if workflow:
                        workflow.get_info()
                    sys.exit(0)
                except KeyError:
                    # pylint: disable=raise-missing-from
                    raise KeyError(f"Error: '{values}' is not a supported workflow.")

        return _WorkflowParams


def main(extra_args=None):
    admin_cli = SDSAdminCLI()
    args, operator_args = admin_cli.parser.parse_known_args()
    extra_args = None
    set_quiet_mode(args.quiet)
    set_verbose_mode(args.verbose)
        
    if args.suite == "cta":
        extra_args = admin_cli.cta_parser.parse_args()
    elif args.suite == "enstore":
        extra_args = admin_cli.enstore_parser.parse_args()
        
    ops = Operator(args, extra_args)
    
    if not ops.valid and args.node:
        ops.detect_remote_service(args)
    elif not ops.valid and args.suite is None:
        ops.detect_service(args)
    elif not ops.valid and extra_args:
        ops.config = Configuration(args.node, args.suite, extra_args.device, extra_args.mover)
    
    if ops.config and ops.config.service == "cta" or args.suite == "cta":
        ops.parser = admin_cli.cta_parser
    elif ops.config and ops.config.service == "enstore" or args.suite == "enstore":
        ops.parser = admin_cli.enstore_parser
    
    if ops.valid:
        print(ops.config.get())
    if args.cmd:
        ops.run_command(args.cmd)
    elif args.run:
        if args.run in SUPPORTED_WORKFLOWS[ops.config.service]:
            workflow = SUPPORTED_WORKFLOWS[ops.config.service][args.run]
            workflow_params, _ = workflow.parser.parse_known_args(operator_args)
            workflow.run(ops, workflow_params)
        #ops.run_tests(args.run)
    else:
        ops.parser.print_help()
        

if __name__ == "__main__":
    main()
