import json
import platform
import re
import subprocess
from typing import Any, Dict, List

import mcp.types as types
import psutil

from .state import state


def get_system_info_tool():
    return {
        "name": "get_system_info",
        "description": "System information: OS, hardware, resources, network. "
                    "USE: Environment analysis, compatibility checks, diagnostics. "
                    "NOT: Current directory (use get_allowed_directory), file info. "
                    "RETURNS: JSON with system stats, WiFi, Mac hardware details",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }

def get_size(bytes: int, suffix: str = "B") -> str:
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def get_wifi_info() -> str:
    """Get current WiFi network name across different platforms."""
    try:
        if platform.system() == "Darwin":  # macOS
            cmd = ["system_profiler", "SPAirPortDataType"]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                for line in process.stdout.split('\n'):
                    if "Current Network Information:" in line:
                        next_line = next((line_text.strip() for line_text in process.stdout.split('\n')[process.stdout.split('\n').index(line)+1:] if line_text.strip()), "")
                        return next_line.rstrip(':')
        elif platform.system() == "Linux":
            cmd = ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                for line in process.stdout.split('\n'):
                    if line.startswith('yes:'):
                        return line.split(':')[1]
        elif platform.system() == "Windows":
            cmd = ["netsh", "wlan", "show", "interfaces"]
            process = subprocess.run(cmd, capture_output=True, text=True)
            if process.returncode == 0:
                for line in process.stdout.split('\n'):
                    if "SSID" in line and "BSSID" not in line:
                        return line.split(":")[1].strip()
    except Exception:
        pass  # Silently handle any errors and return "Not available"
    return "Not available"

def get_mac_details() -> Dict[str, str]:
    """Get Mac-specific system details."""
    if platform.system() != "Darwin":
        return {}

    mac_info = {}
    try:
        # Get system_profiler output
        cmd = ["system_profiler", "SPHardwareDataType", "SPSoftwareDataType"]
        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode == 0:
            output = process.stdout

            # Extract model information
            model_match = re.search(r"Model Name: (.*?)\n", output)
            if model_match:
                mac_info["model"] = model_match.group(1).strip()

            # Extract chip information
            chip_match = re.search(r"Chip: (.*?)\n", output)
            if chip_match:
                mac_info["chip"] = chip_match.group(1).strip()

            # Extract serial number
            serial_match = re.search(r"Serial Number \(system\): (.*?)\n", output)
            if serial_match:
                mac_info["serial_number"] = serial_match.group(1).strip()

    except Exception:
        pass

    return mac_info

def get_system_details() -> Dict[str, Any]:
    """Gather detailed system information."""

    is_mac = platform.system() == "Darwin"
    disk_total = psutil.disk_usage('/').total
    disk_free = psutil.disk_usage('/').free
    disk_used_percentage = (disk_total - disk_free) / disk_total * 100

    # System and OS Information
    system_info = {
        "working_directory": state.allowed_directory,
        "system": {
            "os": platform.system(),
            "os_version": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        },
        "wifi_network": get_wifi_info(),

        # CPU Information
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "total_cpu_usage": f"{psutil.cpu_percent()}%"
        },

        # Memory Information
        "memory": {
            "total": get_size(psutil.virtual_memory().total),
            "available": get_size(psutil.virtual_memory().available),
            "used_percentage": f"{psutil.virtual_memory().percent}%"
        },

        # Disk Information
        "disk": {
            "total": get_size(psutil.disk_usage('/').total),
            "free": get_size(psutil.disk_usage('/').free),
            "used_percentage": f"{disk_used_percentage}%"
        }
    }

    # Add Mac-specific information if on macOS
    if is_mac:
        mac_details = get_mac_details()
        system_info["mac_details"] = mac_details

    # Example output will be much cleaner now:
    # {
    #   "working_directory": "/Users/user/projects/myproject",
    #   "system": {
    #     "os": "Darwin",
    #     "os_version": "22.1.0",
    #     "architecture": "arm64",
    #     "python_version": "3.12.2",
    #     "wifi_network": "MyWiFi"
    #   },
    #   "cpu": {
    #     "physical_cores": 8,
    #     "logical_cores": 8,
    #     "total_cpu_usage": "14.3%"
    #   },
    #   "memory": {
    #     "total": "16.00GB",
    #     "available": "8.50GB",
    #     "used_percentage": "46.9%"
    #   },
    #   "disk": {
    #     "total": "465.63GB",
    #     "free": "208.42GB",
    #     "used_percentage": "55.2%"
    #   },
    #   "mac_details": {  # Only present on macOS
    #     "model": "Mac mini",
    #     "chip": "Apple M2",
    #     "serial_number": "XXXXXX"
    #   }
    # }
    return system_info

async def handle_get_system_info(arguments: dict) -> List[types.TextContent]:
    """Handle getting system information."""
    system_info = get_system_details()
    return [types.TextContent(type="text", text=json.dumps(system_info, indent=2))]
