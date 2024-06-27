#!/usr/bin/env python3

import os
import subprocess
import json
import argparse
from models.globals import verbose, printv

from tape.ibm import get_device_info as get_device_info_ibm
from tape.spectra import get_device_info as get_device_info_spectra

class TapeInfo:
    def __init__(self):
        global verbose
        self.verbose = "-v" if verbose else str()
        self.methodology = None
        self.devices = {
            "tape": [],
            "mediumx":[]
        }

    def run_command(self, command, timeout=60):
        printv(f"\nRunning Command: {command}")
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout)
            response = result.stdout.strip()
            printv(f"Command Response: {response}")
            return response
        except subprocess.TimeoutExpired:
            print("The command did not complete within the timeout period")
        except Exception as e:
            print(f"An error occurred: {e}")
        

    def get_devices(self):
        all_devices =  self.run_command(f"/usr/bin/lsscsi -g").split("\n")
        for line in all_devices:
            if line.strip():
                info = line.split()
                if info[1] not in ["tape", "mediumx"]:
                    continue
                if info[1] == "mediumx":
                    if self.methodology and self.methodology != info[2]:
                        print(f"Multiple mediumx types present: {self.methodology} | {info[2]}")
                    self.methodology = info[2]
                    details = {
                        "serial_num": self.get_serial_number(info[-1]).lstrip('0'),
                        "drive_device": info[-1] 
                    }
                else:
                    details = {
                        "serial_num": self.get_serial_number(info[-1]).lstrip('0'),
                        "drive_device": info[-2] if self.methodology == "SPECTRA" else info[-1]
                    }  
                self.devices[info[1]].append(details)
        print(json.dumps(self.devices, indent=4))
        #return self.run_command(f"/usr/bin/lsscsi -g {self.verbose} | /usr/bin/grep ' {device_type} ' | /usr/bin/awk '{{print $7}}'").splitlines()

    def get_serial_number(self, device):
        printv(f"\nGeting Serial Number for device: {device}")
        return self.run_command(f"/usr/bin/sg_inq {self.verbose} {device} | /usr/bin/grep 'Unit serial number: ' | sed 's/Unit serial number: //'")

    def get_device_name(self, logical_library, location):
        printv(f"\nGenerating Device Name | logical_library: {logical_library} | location: {location}")
        locationName = location.split('_')[-1]
        libraryName = logical_library.split('_')[0][-2:].upper()
        device_name = f"{libraryName}_{locationName}"
        printv(f"Device Name Generated | returning: {device_name}")
        return device_name

    def format_json_filename(self, filename):
        printv(f"\nFormatting json")
        if not filename:
            printv(f"Formatting json | Filename not detected, using default: tape_drive_info.json")
            return "tape_drive_info.json"
        if not filename.endswith('.json'):
            filename = f"{os.path.splitext(filename)[0]}.json"
        return filename


    def get_data(self):
        printv("Get Data | Begin")
        self.get_devices()
        if self.methodology == "IBM":
            data = get_device_info_ibm(self, self.devices)
        elif self.methodology == "SPECTRA":
            serial_numbers = [device["serial_num"] for device in self.devices["tape"]]
            data = get_device_info_spectra(serial_numbers)
        else:
            data = {}
            
        return data

    def generate_config_files(self, data, output_dir):
        config_file_template = open("config/templates/cta-taped_config.template", "r").read()
        sysconfig_file_template = open("config/templates/cta-taped_sysconfig.template", "r").read()
        os.makedirs(f"{output_dir}/sysconfig", exist_ok=True)
        os.makedirs(f"{output_dir}/cta", exist_ok=True)
        for key, val in data.items():
            # sysconfig file = /etc/sysconfig/cta-taped_{DriveName}
            sysconfig_output_file = os.path.join(output_dir, f"sysconfig/cta-taped-{val['DriveName']}")
            with open(sysconfig_output_file, 'w') as f:
                if output_dir != '/etc':
                    f.write(f"# To Install, place this file in /etc/sysconfig/cta-taped-{val['DriveName']}\n\n")
                f.write(sysconfig_file_template)
                f.write('\nCTA_TAPED_OPTIONS="--config=/etc/cta/cta-taped-%s.conf"' % val['DriveName'])
                f.close()
            os.system(f"chown -R -L root:root {sysconfig_output_file}")
            os.system(f"chmod 0644 {sysconfig_output_file}")
                
                
            # cta config file = /etc/cta/cta-taped_{DriveName}.conf
            cta_config_output_file = os.path.join(output_dir, f"cta/cta-taped-{val['DriveName']}.conf")
            with open(cta_config_output_file, 'w') as f:
                if output_dir != '/etc':
                    f.write(f"# To Install, place this file in /etc/cta/cta-taped-{val['DriveName']}.conf\n\n")
                f.write(config_file_template)
                f.write('# Tape Drive Details\n')
                for k, v in val.items():
                    f.write(f"taped {k} {v}\n")
                f.close()
            os.system(f"chown -R -L root:root {cta_config_output_file}")
            os.system(f"chmod 0644 {cta_config_output_file}")

def get_tape_info():
    tape_info = TapeInfo()
    data = tape_info.get_data()
    assert tape_info.devices and data, "Could not get tape info. Exiting"
        
    if tape_info.methodology == "SPECTRA":
        logicalLibrary = data.get("LogicalLibrary")
        for device in tape_info.devices["tape"]:
            if "serial_num" in device and device["serial_num"] in data:
                tape_item = data[device["serial_num"]]
                device["DriveLogicalLibrary"] = logicalLibrary
                device["DriveName"] = tape_item.get("driveName")
                tape_drive_device = tape_info.run_command(f"/usr/bin/sg_map | /usr/bin/grep {device['drive_device']} | /usr/bin/awk '{{print $2}}'")
                if not tape_drive_device:
                    print(f"Failed to fetch DriveDevice for tape device: {device['serial_num']}")
                else:
                    device["DriveDevice"] = tape_drive_device
                elementAddress = tape_item.get("elementAddress", None)
                if elementAddress:
                    ordinal = tape_info.run_command(f"cta-smc -q D | awk -v addr='{elementAddress}' '{{if ($2 == addr) print $1}}'", 5)
                    if ordinal:
                        device["DriveControlPath"] = f"smc{ordinal}"
                    else:
                        print(f"Failed to fetch DriveControlPath for tape device: {device['serial_num']}")
        return json.dumps(tape_info.devices, indent=4)
    
    return json.dumps(data, indent=4)

        