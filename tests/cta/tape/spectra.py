import configparser
import json
import subprocess
import re

from config import SPECTRA_CONFIG as _SPECTRA_CONFIG

_config = configparser.ConfigParser()
_config.read(_SPECTRA_CONFIG)

_host = '%s@%s' % (
    _config.get("ssa", "user"),
    _config.get("ssa", "host")
)
_slapi_cmd = "python3 ~/scripts/slapi.py --insecure --server %s --user %s --insecure-passwd %s" % (
    _config.get("slapi", "server"),
    _config.get("slapi", "user"),
    _config.get("slapi", "password")
)

def _slapi_call(method, *args):
    cmd = f"{_slapi_cmd} {method}"
    if args:
        for arg in args:
            cmd += f" {arg}"
    return cmd

def ssh_command_with_kerberos(command):
    try:
        result = subprocess.run(
            ["ssh", "-K", f"{_host}", command],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Command failed: {e.stderr}"
    
def get_library_name():
    command = _slapi_call("librarysettingslist")
    output = ssh_command_with_kerberos(command)
    lines = output.strip().split('\n')
    data_line = lines[-1]
    parts = data_line.split()
    library_name = parts[0]
    return library_name

def get_location(partition="zzCTA"):
    command = _slapi_call("inventorylist", "zzCTA")
    output = ssh_command_with_kerberos(command)
    lines = output.split('\n')
    retval = {}
    for line in lines[5:]:
        if line.strip():
            parts = line.split()
            if parts[0] == partition and parts[1] == "drive":
                retval[parts[3]] = parts[2]
    return retval
    
    
def get_drive_info(library_name, serial_numbers):
    if not isinstance(serial_numbers, list):
        serial_numbers = [serial_numbers]
    
    command = _slapi_call("drivelist")
    output = ssh_command_with_kerberos(command)
    if not output:
        return None
    
    pattern = re.compile(
        r'(\S+)\s+'            # ID (non-space characters, then spaces)
        r'\S+\s+'              # DriveStatus (skip this field)
        r'([^\d]+)\s+'         # Partition (non-digit characters, then spaces)
        r'(\d+)\s+'            # PartDriveNum (digits, then spaces)
    )
    
    def get_drive_name(input_id): # Convert full Drive ID to our preferred naming convention
        segments = input_id.split("/")
        result = ""
        for segment in segments:
            result += segment.replace("FR", "F").replace("DBA", "B").replace("fLTO-DRV", "D")
        return f"{library_name}_{result}"
    
    lines = output.split('\n')
    retval = {}
    for line in lines[5:]: 
        if line.strip():  # Skip empty lines
            # Use the regex to find all matches
            for sn in serial_numbers:
                if sn in line:
                    serial_num = sn
                    match = pattern.match(line)
                    if match:
                        id, partition, part_drive_num = match.groups()
                        if serial_num in serial_numbers:
                            retval[serial_num] = {
                            "id": id.strip(),
                            "driveName": get_drive_name(id.strip()),
                            "partition": partition.strip(),
                            "partDriveNumber": part_drive_num.strip()
                        }
                
    if retval:
        return retval
    return None

def get_device_info(serial_numbers=None, debug=False):
    print(
        f"""
                            Using SPECTRA method to get drive details
        (This method takes a little bit longer, please wait while we communicate with ssasrv nodes)
        """)
    assert serial_numbers, "No serial numbers to validate"

    LibraryName = get_library_name()
    libraryName = LibraryName[-2:].split("_")[0].upper() if LibraryName else None
    drives = get_drive_info(libraryName, serial_numbers)
    drives["LogicalLibrary"] = LibraryName
    locations = get_location()

    for sn in serial_numbers:
        if sn in drives:
            if "partDriveNumber" in drives[sn] and drives[sn]["partDriveNumber"] in locations:
                drives[sn]["elementAddress"] = locations[drives[sn]["partDriveNumber"]]
    if debug:
        print(json.dumps(drives, indent=4))
    
    return drives