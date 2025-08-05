import json
import platform
import subprocess
from typing import Any, Dict, List

from mcp import types

# Import platform-specific libraries if available
try:
    import Quartz
    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False


def get_active_apps_tool():
    """Define the get_active_apps tool."""
    return {
        "name": "get_active_apps",
        "description": "List currently active applications. "
                       "USE: Understand user's active software, provide app-specific assistance. "
                       "NOT: Window details (use get_available_windows), screenshots. "
                       "RETURNS: JSON with platform, app count, array of apps with names/windows. "
                       "Cross-platform: macOS, Windows, Linux",
        "inputSchema": {
            "type": "object",
            "properties": {
                "with_details": {
                    "type": "boolean",
                    "description": "Include app details (window_count, visible_windows). Default: false."
                }
            },
            "required": []
        },
    }


def _get_active_apps_macos(with_details: bool = False) -> List[Dict[str, Any]]:
    """Get a list of currently active applications on macOS."""
    active_apps = []
    
    # Attempt to use Quartz directly first, as it's more reliable
    if QUARTZ_AVAILABLE:
        try:
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, 
                Quartz.kCGNullWindowID
            )
            
            # Create a map of app names to their details
            app_map = {}
            for window in window_list:
                owner = window.get('kCGWindowOwnerName', '')
                
                # Skip empty app names or system components we don't want to include
                if not owner or owner in ["SystemUIServer", "osascript"]:
                    continue
                
                # Create new entry for this app if we haven't seen it before
                if owner not in app_map:
                    app_map[owner] = {
                        "name": owner,
                        "has_windows": False,
                        "window_count": 0,
                        "visible_windows": [] if with_details else None
                    }
                
                # Count this window
                app_map[owner]["window_count"] += 1
                
                # Check if this is a visible application window
                layer = window.get('kCGWindowLayer', 999)
                name = window.get('kCGWindowName', '')
                
                # Layer 0 typically indicates a standard application window
                if layer <= 0:
                    app_map[owner]["has_windows"] = True
                    
                    # Add details about this window if detailed info was requested
                    if with_details and name:
                        app_map[owner]["visible_windows"].append({
                            "name": name,
                            "id": window.get('kCGWindowNumber', 0)
                        })
            
            # Convert the map to a list
            active_apps = list(app_map.values())
            
            # If we got results from Quartz, we're done
            if active_apps:
                return active_apps
                
        except Exception as e:
            print(f"Error getting applications with Quartz: {str(e)}")
    
    # Fall back to AppleScript if Quartz failed or isn't available
    if not active_apps:
        try:
            # Modified AppleScript that tries to avoid including itself
            script = '''
            tell application "System Events"
                set appList to {}
                set allProcesses to application processes whose background only is false
                
                repeat with proc in allProcesses
                    set procName to name of proc
                    set procVisible to (windows of proc is not {})
                    
                    # Skip the scripting process itself
                    if procName is not "osascript" and procName is not "System Events" then
                        set end of appList to {name:procName, has_windows:procVisible}
                    end if
                end repeat
                
                return appList
            end tell
            '''
            
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse the output from AppleScript
                output = result.stdout.strip()
                if output:
                    # AppleScript returns a list of records, we need to parse it
                    lines = output.split(", {")
                    for i, line in enumerate(lines):
                        if i == 0:
                            line = line.replace("{", "")
                        if i == len(lines) - 1:
                            line = line.replace("}", "")
                        
                        if "name:" in line and "has_windows:" in line:
                            parts = line.split(", ")
                            app_info = {}
                            for part in parts:
                                if "name:" in part:
                                    app_info["name"] = part.replace("name:", "").strip()
                                elif "has_windows:" in part:
                                    app_info["has_windows"] = part.replace("has_windows:", "").strip().lower() == "true"
                            
                            if app_info:
                                active_apps.append(app_info)
        except Exception as e:
            print(f"Error getting apps with AppleScript: {str(e)}")
    
    # Add window details if requested and if we got results from AppleScript
    if active_apps and with_details and QUARTZ_AVAILABLE:
        try:
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly, 
                Quartz.kCGNullWindowID
            )
            
            # Create a map of app names to window details
            app_details = {}
            for window in window_list:
                owner = window.get('kCGWindowOwnerName', '')
                if not owner:
                    continue
                
                if owner not in app_details:
                    app_details[owner] = {
                        "window_count": 0,
                        "windows": []
                    }
                
                app_details[owner]["window_count"] += 1
                
                # Add window details if this is a visible window
                layer = window.get('kCGWindowLayer', 999)
                name = window.get('kCGWindowName', '')
                
                if layer <= 0 and name:
                    app_details[owner]["windows"].append({
                        "name": name,
                        "id": window.get('kCGWindowNumber', 0)
                    })
            
            # Enhance the active_apps list with these details
            for app in active_apps:
                app_name = app["name"]
                if app_name in app_details:
                    app["window_count"] = app_details[app_name]["window_count"]
                    app["visible_windows"] = app_details[app_name]["windows"]
        except Exception as e:
            print(f"Error getting window details with Quartz: {str(e)}")
    
    return active_apps


def _get_active_apps_windows(with_details: bool = False) -> List[Dict[str, Any]]:
    """Get a list of currently active applications on Windows."""
    active_apps = []
    
    # Basic list without details
    if not with_details:
        try:
            # Use a PowerShell command to get running applications
            script = '''
            Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | 
            Select-Object ProcessName, MainWindowTitle | 
            ConvertTo-Json
            '''
            
            cmd = ["powershell", "-Command", script]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                try:
                    apps_data = json.loads(process.stdout)
                    # Handle single item (not in a list)
                    if isinstance(apps_data, dict):
                        apps_data = [apps_data]
                    
                    for app in apps_data:
                        active_apps.append({
                            "name": app.get("ProcessName", ""),
                            "has_windows": True,
                            "window_title": app.get("MainWindowTitle", "")
                        })
                except json.JSONDecodeError:
                    print("Failed to parse JSON from PowerShell output")
        except Exception as e:
            print(f"Error getting basic app list on Windows: {str(e)}")
    
    # More detailed list with PyGetWindow if available
    elif PYGETWINDOW_AVAILABLE:
        try:
            # Get the list of windows
            all_windows = gw.getAllWindows()
            
            # Group by application (approximate, since we only have window titles)
            app_windows = {}
            
            for window in all_windows:
                if not window.title:
                    continue
                
                # Try to extract application name from window title
                # This is an approximation and might not be accurate for all applications
                title_parts = window.title.split(' - ')
                app_name = title_parts[-1] if len(title_parts) > 1 else window.title
                
                if app_name not in app_windows:
                    app_windows[app_name] = {
                        "name": app_name,
                        "has_windows": True,
                        "window_count": 0,
                        "visible_windows": []
                    }
                
                app_windows[app_name]["window_count"] += 1
                app_windows[app_name]["visible_windows"].append({
                    "name": window.title,
                    "width": window.width,
                    "height": window.height
                })
            
            active_apps = list(app_windows.values())
        except Exception as e:
            print(f"Error getting detailed app list with PyGetWindow: {str(e)}")
    
    # Fallback to a basic PowerShell approach
    if not active_apps:
        try:
            script = '''
            Get-Process | Where-Object {$_.MainWindowHandle -ne 0} | 
            Select-Object ProcessName | ConvertTo-Json
            '''
            
            cmd = ["powershell", "-Command", script]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                try:
                    apps_data = json.loads(process.stdout)
                    # Handle single item (not in a list)
                    if isinstance(apps_data, dict):
                        apps_data = [apps_data]
                    
                    for app in apps_data:
                        active_apps.append({
                            "name": app.get("ProcessName", ""),
                            "has_windows": True
                        })
                except json.JSONDecodeError:
                    print("Failed to parse JSON from PowerShell output")
        except Exception as e:
            print(f"Error getting fallback app list on Windows: {str(e)}")
    
    return active_apps


def _get_active_apps_linux(with_details: bool = False) -> List[Dict[str, Any]]:
    """Get a list of currently active applications on Linux."""
    active_apps = []
    
    # Try using wmctrl if available
    try:
        # Check if wmctrl is installed
        check_process = subprocess.run(["which", "wmctrl"], capture_output=True)
        if check_process.returncode == 0:
            # Get window list with wmctrl
            wmctrl_process = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            
            if wmctrl_process.returncode == 0:
                window_data = wmctrl_process.stdout.strip().split('\n')
                
                # Process each window line
                app_windows = {}
                for line in window_data:
                    if not line:
                        continue
                    
                    parts = line.split(None, 3)  # Split by whitespace, max 3 splits
                    if len(parts) >= 4:
                        window_id, desktop, host, title = parts
                        
                        # Try to determine app name from window title
                        app_name = title.split(' - ')[-1] if ' - ' in title else title
                        
                        if app_name not in app_windows:
                            app_windows[app_name] = {
                                "name": app_name,
                                "has_windows": True,
                                "window_count": 0,
                                "visible_windows": []
                            }
                        
                        app_windows[app_name]["window_count"] += 1
                        
                        if with_details:
                            app_windows[app_name]["visible_windows"].append({
                                "name": title,
                                "id": window_id,
                                "desktop": desktop
                            })
                
                active_apps = list(app_windows.values())
    except Exception as e:
        print(f"Error getting apps with wmctrl: {str(e)}")
    
    # If wmctrl failed or isn't available, try using ps
    if not active_apps:
        try:
            # List GUI applications
            cmd = ["ps", "-e", "-o", "comm="]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                all_processes = process.stdout.strip().split('\n')
                
                # Filter for likely GUI applications (very basic heuristic)
                gui_indicators = ["-bin", "x11", "gtk", "qt", "wayland", "gnome", "kde"]
                
                for proc in all_processes:
                    proc = proc.strip()
                    if not proc:
                        continue
                    
                    # Skip system processes that typically don't have UIs
                    if proc.startswith(("ps", "bash", "sh", "zsh", "systemd", "login", "dbus")):
                        continue
                    
                    # Include if it looks like a GUI app
                    if any(indicator in proc.lower() for indicator in gui_indicators) or "/" not in proc:
                        active_apps.append({
                            "name": proc,
                            "has_windows": True  # Assuming these have windows, though we can't be sure
                        })
        except Exception as e:
            print(f"Error getting apps with ps: {str(e)}")
    
    return active_apps


def get_active_apps(with_details: bool = False) -> Dict[str, Any]:
    """
    Get a list of currently active applications on the user's system.
    
    Args:
        with_details: Whether to include additional details about each application
    
    Returns:
        Dictionary with platform, success status, and list of active applications
    """
    system_name = platform.system().lower()
    
    # Get active apps based on platform
    if system_name == "darwin" or system_name == "macos":
        active_apps = _get_active_apps_macos(with_details)
    elif system_name == "windows":
        active_apps = _get_active_apps_windows(with_details)
    elif system_name == "linux":
        active_apps = _get_active_apps_linux(with_details)
    else:
        return {
            "success": False,
            "platform": system_name,
            "error": f"Unsupported platform: {system_name}. This tool currently supports macOS, Windows, and Linux.",
            "apps": []
        }
    
    # If no apps were found, provide a descriptive error message
    if not active_apps:
        error_message = "No active applications could be detected. "
        if system_name == "darwin":
            error_message += ("This is most likely due to missing screen recording permissions. "
                             "Please go to System Settings > Privacy & Security > Screen Recording "
                             "and ensure that your terminal or IDE application has permission to record the screen.")
        elif system_name == "windows":
            error_message += "This might be due to insufficient permissions or no applications with visible windows."
        elif system_name == "linux":
            error_message += "This might be due to wmctrl not being installed or no applications with visible windows."
        
        return {
            "success": False,
            "platform": system_name,
            "error": error_message,
            "apps": []
        }
    
    # Sort by name
    active_apps.sort(key=lambda app: app.get("name", "").lower())
    
    return {
        "success": True,
        "platform": system_name,
        "app_count": len(active_apps),
        "apps": active_apps
    }


async def handle_get_active_apps(arguments: dict) -> List[types.TextContent]:
    """Handle getting active applications."""
    with_details = arguments.get("with_details", False)
    
    result = get_active_apps(with_details)
    
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))] 
