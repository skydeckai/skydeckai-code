import json
import platform
import subprocess
from typing import Any, Dict, List
import importlib.util

from mcp import types

# Use importlib.util.find_spec to check for availability of optional packages
def is_package_available(package_name):
    """Check if a package is available using importlib.util.find_spec."""
    return importlib.util.find_spec(package_name) is not None

# Check for PyGetWindow
PYGETWINDOW_AVAILABLE = is_package_available("pygetwindow")

# Check for macOS-specific Quartz framework
QUARTZ_AVAILABLE = False
if platform.system().lower() == "darwin":
    QUARTZ_AVAILABLE = is_package_available("Quartz")
    if QUARTZ_AVAILABLE:
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGNullWindowID,
            kCGWindowListOptionOnScreenOnly,
        )


def get_available_windows_tool():
    """Define the get_available_windows tool."""
    return {
        "name": "get_available_windows",
        "description": "List all visible windows with details. "
                       "USE: Find specific windows by title, get window-level context. "
                       "NOT: App-level info (use get_active_apps), screen capture. "
                       "RETURNS: JSON with window count, array of windows with title/app/visibility. "
                       "Cross-platform: macOS, Windows, Linux",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        },
    }


def _get_windows_macos() -> List[Dict[str, Any]]:
    """
    Get information about all available windows on macOS.
    
    Returns:
        List of dictionaries containing window information
    """
    windows = []
    
    if not QUARTZ_AVAILABLE:
        print("Quartz framework not available. Unable to list windows on macOS.")
        return windows
    
    try:
        # Get the list of windows from Quartz
        window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
        
        for window in window_list:
            window_id = window.get('kCGWindowNumber', 0)
            owner = window.get('kCGWindowOwnerName', '')
            name = window.get('kCGWindowName', '')
            layer = window.get('kCGWindowLayer', 0)
            alpha = window.get('kCGWindowAlpha', 1.0)
            
            # Create the window info dictionary
            window_info = {
                "id": window_id,
                "title": name,
                "app": owner,
                "visible": layer <= 0 and alpha > 0.1,
            }
            
            windows.append(window_info)
        
        # Sort windows by application name and then by window title
        windows.sort(key=lambda w: (w.get("app", "").lower(), w.get("title", "").lower()))
        
    except Exception as e:
        print(f"Error getting windows on macOS: {str(e)}")
    
    return windows


def _get_windows_windows() -> List[Dict[str, Any]]:
    """
    Get information about all available windows on Windows.
    
    Returns:
        List of dictionaries containing window information
    """
    windows = []
    
    # Try using PyGetWindow if available
    if PYGETWINDOW_AVAILABLE:
        try:
            import pygetwindow as gw
            all_windows = gw.getAllWindows()
            
            for window in all_windows:
                # Skip windows with empty titles
                if not window.title:
                    continue
                
                # Try to determine the application name from the window title
                # This is an approximation and may not be accurate for all applications
                app_name = ""
                title_parts = window.title.split(' - ')
                if len(title_parts) > 1:
                    app_name = title_parts[-1]
                
                # Create the window info dictionary
                window_info = {
                    "title": window.title,
                    "visible": window.visible,
                    "active": window.isActive
                }
                
                # Add app name if we were able to determine it
                if app_name:
                    window_info["app"] = app_name
                
                windows.append(window_info)
            
            # Sort windows by application name and then by window title
            windows.sort(key=lambda w: (w.get("app", "").lower() if "app" in w else "", w.get("title", "").lower()))
            
        except Exception as e:
            print(f"Error getting windows with PyGetWindow: {str(e)}")
    
    # If PyGetWindow failed or isn't available, try using PowerShell
    if not windows:
        try:
            script = '''
            Add-Type @"
            using System;
            using System.Runtime.InteropServices;
            using System.Text;
            
            public class Window {
                [DllImport("user32.dll")]
                [return: MarshalAs(UnmanagedType.Bool)]
                public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
                
                [DllImport("user32.dll")]
                public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
                
                [DllImport("user32.dll")]
                public static extern bool IsWindowVisible(IntPtr hWnd);
                
                [DllImport("user32.dll", SetLastError=true)]
                public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
                
                public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
            }
            "@
            
            $windows = @()
            
            $enumWindowsCallback = {
                param($hwnd, $lParam)
                
                # Get the window title
                $sb = New-Object System.Text.StringBuilder(256)
                [void][Window]::GetWindowText($hwnd, $sb, $sb.Capacity)
                $title = $sb.ToString()
                
                # Only process windows with titles
                if($title -and $title -ne "") {
                    # Check if the window is visible
                    $visible = [Window]::IsWindowVisible($hwnd)
                    
                    # Get process ID and name
                    $processId = 0
                    [void][Window]::GetWindowThreadProcessId($hwnd, [ref]$processId)
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    $processName = if($process) { $process.ProcessName } else { "Unknown" }
                    
                    # Create the window object
                    $window = @{
                        title = $title
                        app = $processName
                        visible = $visible
                    }
                    
                    $windows += $window
                }
                
                # Continue enumeration
                return $true
            }
            
            # Enumerate all windows
            [void][Window]::EnumWindows($enumWindowsCallback, [IntPtr]::Zero)
            
            # Sort the windows
            $windows = $windows | Sort-Object -Property @{Expression="app"}, @{Expression="title"}
            
            # Convert to JSON
            $windows | ConvertTo-Json -Depth 3
            '''
            
            cmd = ["powershell", "-Command", script]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0 and process.stdout.strip():
                try:
                    windows_data = json.loads(process.stdout)
                    # Handle single item (not in a list)
                    if isinstance(windows_data, dict):
                        windows_data = [windows_data]
                    
                    windows = windows_data
                except json.JSONDecodeError:
                    print("Failed to parse JSON from PowerShell output")
            
        except Exception as e:
            print(f"Error getting windows with PowerShell: {str(e)}")
    
    return windows


def _get_windows_linux() -> List[Dict[str, Any]]:
    """
    Get information about all available windows on Linux.
    
    Returns:
        List of dictionaries containing window information
    """
    windows = []
    
    # Try using wmctrl if available
    try:
        # Check if wmctrl is installed
        check_process = subprocess.run(["which", "wmctrl"], capture_output=True)
        if check_process.returncode == 0:
            # Get the list of windows
            wmctrl_process = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
            
            if wmctrl_process.returncode == 0:
                window_data = wmctrl_process.stdout.strip().split('\n')
                
                for line in window_data:
                    if not line:
                        continue
                    
                    parts = line.split(None, 3)
                    if len(parts) < 4:
                        continue
                    
                    window_id, desktop, owner, *title_parts = parts
                    title = title_parts[0] if title_parts else ""
                    
                    # Create the window info dictionary
                    window_info = {
                        "id": window_id,
                        "title": title,
                        "app": owner,
                        "desktop": desktop,
                        "visible": True  # wmctrl -l only shows visible windows
                    }
                    
                    windows.append(window_info)
                
                # Sort windows by application name and then by window title
                windows.sort(key=lambda w: (w.get("app", "").lower(), w.get("title", "").lower()))
    except Exception as e:
        print(f"Error getting windows with wmctrl: {str(e)}")
    
    # If wmctrl failed, try using xwininfo and xprop
    if not windows:
        try:
            # Get the list of window IDs
            xwininfo_process = subprocess.run(["xwininfo", "-root", "-children"], capture_output=True, text=True)
            
            if xwininfo_process.returncode == 0:
                lines = xwininfo_process.stdout.strip().split('\n')
                
                # Parse the output to find window IDs
                window_ids = []
                for line in lines:
                    # Look for lines with window IDs in hexadecimal format
                    if "0x" in line and "child" in line.lower():
                        parts = line.split()
                        for part in parts:
                            if part.startswith("0x"):
                                window_ids.append(part)
                                break
                
                # Get information for each window
                for window_id in window_ids:
                    # Get window name
                    xprop_name_process = subprocess.run(["xprop", "-id", window_id, "WM_NAME"], capture_output=True, text=True)
                    
                    # Get window class (application)
                    xprop_class_process = subprocess.run(["xprop", "-id", window_id, "WM_CLASS"], capture_output=True, text=True)
                    
                    # Extract the window title
                    title = ""
                    if xprop_name_process.returncode == 0:
                        output = xprop_name_process.stdout.strip()
                        if "=" in output:
                            title = output.split("=", 1)[1].strip().strip('"')
                    
                    # Extract the application name
                    app_name = ""
                    if xprop_class_process.returncode == 0:
                        output = xprop_class_process.stdout.strip()
                        if "=" in output:
                            classes = output.split("=", 1)[1].strip().strip('"').split('", "')
                            app_name = classes[-1] if classes else ""
                    
                    # Create the window info dictionary
                    window_info = {
                        "id": window_id,
                        "title": title,
                        "app": app_name,
                        "visible": True  # Assuming all retrieved windows are visible
                    }
                    
                    windows.append(window_info)
                
                # Sort windows by application name and then by window title
                windows.sort(key=lambda w: (w.get("app", "").lower(), w.get("title", "").lower()))
        except Exception as e:
            print(f"Error getting windows with xwininfo/xprop: {str(e)}")
    
    return windows


def get_available_windows() -> Dict[str, Any]:
    """
    Get detailed information about all available windows currently displayed on screen.
    
    Returns:
        Dictionary with platform, success status, and list of windows
    """
    system_name = platform.system().lower()
    
    # Get windows based on platform
    if system_name == "darwin" or system_name == "macos":
        windows = _get_windows_macos()
    elif system_name == "windows":
        windows = _get_windows_windows()
    elif system_name == "linux":
        windows = _get_windows_linux()
    else:
        return {
            "success": False,
            "platform": system_name,
            "error": f"Unsupported platform: {system_name}. This tool currently supports macOS, Windows, and Linux.",
            "windows": []
        }
    
    # If no windows were found, provide a descriptive error message
    if not windows:
        error_message = "No windows could be detected on your screen. "
        if system_name == "darwin":
            error_message += "This might be due to missing screen recording permissions. Please check System Settings > Privacy & Security > Screen Recording."
        elif system_name == "windows":
            error_message += "This might be due to insufficient permissions or no windows being displayed."
        elif system_name == "linux":
            error_message += "This might be due to wmctrl or xwininfo not being installed or no windows being displayed."
        
        return {
            "success": False,
            "platform": system_name,
            "error": error_message,
            "windows": []
        }
    
    return {
        "success": True,
        "platform": system_name,
        "count": len(windows),
        "windows": windows
    }


async def handle_get_available_windows(arguments: dict) -> List[types.TextContent]:
    """Handle getting available windows."""
    result = get_available_windows()
    
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))] 
