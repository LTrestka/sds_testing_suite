import json

def get_device_info(tape_info, devices):
    print(
        f"""
                            Using IBM method to get drive details
        """)
    mediumx_devices = devices.get("mediumx", [])
    tape_devices = devices.get("tape", [])
    data = {}
    for device in mediumx_devices:
        log_level = "-LL debug -LP /dev/NULL" if tape_info.debug or tape_info.verbose else ""
        json_data = json.loads(tape_info.run_command(f"/root/ITDT/itdt {log_level} -f {device['drive_device']} RoS GET /v1/drives"))
        for item in json_data:
            tape_device = None
            for tp in tape_devices:
                if item.get('sn') == tp["serial_num"]:
                    tape_device = tp["drive_device"]
            if not tape_device:
                continue      
            
            serial_number = item['sn']
            logical_library = item['logicalLibrary'].upper()
            location = item['location']
            elementAddress = item['elementAddress']
            drive_ordinal = tape_info.run_command(f"cta-smc -q D | awk -v addr='{elementAddress}' '{{if ($2 == addr) print $1}}c'")
            tape_drive_device = tape_info.run_command(f"/usr/bin/sg_map | /usr/bin/grep {tape_device} | /usr/bin/awk '{{print $2}}'")
            drive_name = tape_info.get_device_name(logical_library, location)
            entry = {
                "DriveLogicalLibrary": logical_library,
                "DriveName": drive_name,
                "DriveDevice": tape_drive_device,
                "DriveControlPath": f"smc{drive_ordinal}"
            }
            data[serial_number] = entry
    return data