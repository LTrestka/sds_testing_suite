import builtins
import json
import os

# Save the original print function
original_print = builtins.print

# Global variables for quiet and verbose modes
quiet = False
verbose = False

SUPPORTED_WORKFLOWS = {
    "cta": {},
    "enstore": {}
}                    

def custom_print(*args, **kwargs):
    global quiet
    # Check quiet mode
    if quiet:
        return  # Do not print anything if in quiet mode
    else:
        modified_args = list(args)
    # Call the original print function
    original_print(*modified_args, **kwargs)

def printv(*args, **kwargs):
    global verbose
    # Check verbose mode
    if not verbose:
        return
    # Call the original print function
    modified_args = ["\n[Verbose]"] + list(args)
    custom_print(*modified_args, **kwargs)
    
# Replace the built-in print with the custom print
builtins.print = custom_print

# Functions to set quiet and verbose modes
def set_quiet_mode(value):
    global quiet
    quiet = value

def set_verbose_mode(value):
    global verbose
    verbose = value