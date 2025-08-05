import json
import os
import platform
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from mcp import types

from .state import state

# Import the required libraries for improved screenshot functionality
try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False

# Import macOS-specific libraries if available
try:
    import Quartz
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGNullWindowID,
        kCGWindowListOptionOnScreenOnly,
    )
    QUARTZ_AVAILABLE = True
except ImportError:
    QUARTZ_AVAILABLE = False

# Define platform-specific permission error messages
PERMISSION_ERROR_MESSAGES = {
    "darwin": "Permission denied to capture the screen. Please grant screen recording permission in System Settings > Privacy & Security > Screen Recording."
}


def _check_macos_screen_recording_permission() -> Dict[str, Any]:
    """
    Check if the application has screen recording permission on macOS.

    For macOS 11+, this function uses the official Apple API:
    - CGPreflightScreenCaptureAccess() to check if permission is already granted
    - CGRequestScreenCaptureAccess() to request permission if needed

    Requesting access will present the system prompt and automatically add your app
    in the list so the user just needs to enable access. The system prompt will only
    appear once per app session.

    Returns:
        Dict with keys:
        - has_permission (bool): Whether permission is granted
        - error (str or None): Error message if permission is denied
        - details (dict): Additional context about the permission check
    """
    result = {"has_permission": False, "error": None, "details": {}}

    # Check if Quartz is available
    if not QUARTZ_AVAILABLE:
        result["error"] = "Quartz framework not available. Cannot check screen recording permission."
        result["details"] = {"error": "Quartz not available"}
        return result

    # Check if the API is available (macOS 11+)
    if not hasattr(Quartz, 'CGPreflightScreenCaptureAccess'):
        result["error"] = "CGPreflightScreenCaptureAccess not available. Your macOS version may be too old (requires macOS 11+)."
        result["details"] = {"error": "API not available"}
        return result

    try:
        # Check if we already have permission
        has_permission = Quartz.CGPreflightScreenCaptureAccess()
        result["details"]["preflight_result"] = has_permission

        if has_permission:
            # We already have permission
            result["has_permission"] = True
            return result
        else:
            # We don't have permission, request it
            # This will show the system prompt to the user
            permission_granted = Quartz.CGRequestScreenCaptureAccess()
            result["details"]["request_result"] = permission_granted

            if permission_granted:
                result["has_permission"] = True
                return result
            else:
                # User denied permission
                result["error"] = PERMISSION_ERROR_MESSAGES["darwin"]
                return result
    except Exception as e:
        result["details"]["exception"] = str(e)
        result["error"] = f"Error checking screen recording permission: {str(e)}"

    return result


def capture_screenshot_tool():
    """Define the capture_screenshot tool."""
    return {
        "name": "capture_screenshot",
        "description": "Screenshot full screen, active window, or named window. "
                      "USE: Visual documentation, troubleshooting, UI reference. "
                      "NOT: Window info without capture (use get_available_windows). "
                      "Captures windows in background. Requires permissions on macOS. "
                      "RETURNS: JSON with success, path, message",
        "inputSchema": {
            "type": "object",
            "properties": {
                "output_path": {
                    "type": "string",
                    "description": "Optional save path. Examples: 'screenshots/main_window.png', 'docs/current_state.png'."
                },
                "capture_mode": {
                    "type": "object",
                    "description": "What to capture.",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Screenshot type: 'full' (entire screen), 'active_window' (foreground), 'named_window' (specific window).",
                            "enum": ["full", "active_window", "named_window"]
                        },
                        "window_name": {
                            "type": "string",
                            "description": "Application/window name (required for 'named_window'). Case-insensitive. Examples: 'Chrome', 'Terminal'."
                        }
                    },
                    "required": ["type"]
                },
                "debug": {
                    "type": "boolean",
                    "description": "Include debug info on failure (shows available windows, match attempts). Default: false.",
                }
            },
            "required": ["capture_mode"]
        },
    }


def _get_default_screenshot_path() -> str:
    """Generate a default path for saving screenshots."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"

    # Use the allowed directory from state if available, otherwise use temp directory
    if hasattr(state, 'allowed_directory') and state.allowed_directory:
        base_dir = os.path.join(state.allowed_directory, "screenshots")
        # Create screenshots directory if it doesn't exist
        os.makedirs(base_dir, exist_ok=True)
    else:
        base_dir = tempfile.gettempdir()

    return os.path.join(base_dir, filename)


def _capture_with_mss(output_path: str, region: Optional[Dict[str, int]] = None) -> bool:
    """
    Capture screenshot using MSS library.

    Args:
        output_path: Path where to save the screenshot
        region: Optional dictionary with top, left, width, height for specific region

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with mss.mss() as sct:
            if region:
                # Capture specific region
                monitor = region
            else:
                # Capture entire primary monitor
                monitor = sct.monitors[1]  # monitors[0] is all monitors combined, monitors[1] is the primary

            # Grab the picture
            sct_img = sct.grab(monitor)

            # Save it to the output path
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_path)

            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        print(f"MSS screenshot error: {str(e)}")
        return False


def _find_window_by_name(window_name: str) -> Tuple[Optional[Dict[str, int]], Dict[str, Any]]:
    """
    Find a window by name and return its position and size along with debug info.

    Args:
        window_name: Name of the window to find

    Returns:
        Tuple containing:
            - Window region dict with top, left, width, height (or None if not found)
            - Debug info dictionary with search results and details
    """
    # Check if we're on macOS
    if platform.system().lower() in ["darwin", "macos"]:
        # Use the macOS-specific function
        window_region, detailed_debug_info = find_macos_window_by_name(window_name)
        if window_region:
            return window_region, {
                "search_term": window_name,
                "found_window": True,
                "match_type": "quartz_window_search",
                "detailed_info": detailed_debug_info
            }
        else:
            # Get active apps for better error message
            active_apps = _get_active_apps_macos()
            return None, {
                "search_term": window_name,
                "reason": "No matching window title",
                "active_apps": active_apps,
                "quartz_available": QUARTZ_AVAILABLE,
                "detailed_info": detailed_debug_info
            }

    # For non-macOS platforms, use PyGetWindow
    if not PYGETWINDOW_AVAILABLE:
        print("PyGetWindow is not available")
        return None, {"error": "PyGetWindow is not available"}

    try:
        # Get all available windows
        all_windows = gw.getAllWindows()

        # Collect window titles for debugging
        window_titles = []
        for w in all_windows:
            if w.title:
                window_titles.append(f"'{w.title}' ({w.width}x{w.height})")
                print(f"  - '{w.title}' ({w.width}x{w.height})")

        # Standard window matching (case-insensitive)
        matching_windows = []
        for window in all_windows:
            if window.title and window_name.lower() in window.title.lower():
                matching_windows.append(window)

        if not matching_windows:
            print(f"No window found with title containing '{window_name}'")
            return None, {
                "search_term": window_name,
                "reason": "No matching window title",
                "matching_method": "case_insensitive_substring",
                "all_windows": window_titles
            }

        # Get the first matching window
        window = matching_windows[0]
        print(f"Found matching window: '{window.title}'")

        # Check if window dimensions are valid
        if window.width <= 0 or window.height <= 0:
            print(f"Window has invalid dimensions: {window.width}x{window.height}")
            return None, {
                "search_term": window_name,
                "found_window": window.title,
                "reason": f"Invalid dimensions: {window.width}x{window.height}",
                "all_windows": window_titles
            }

        # Return the window position and size
        return {
            "top": window.top,
            "left": window.left,
            "width": window.width,
            "height": window.height
        }, {
            "search_term": window_name,
            "found_window": window.title,
            "match_type": "standard_case_insensitive"
        }
    except Exception as e:
        print(f"Error finding window: {str(e)}")
        return None, {
            "search_term": window_name,
            "error": str(e)
        }


def _get_active_apps_macos() -> List[str]:
    """Get a list of currently active applications on macOS."""
    try:
        script = '''
        tell application "System Events"
            set appList to {}
            set allProcesses to application processes

            repeat with proc in allProcesses
                if windows of proc is not {} then
                    set end of appList to name of proc
                end if
            end repeat

            return appList
        end tell
        '''

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse the comma-separated list from AppleScript
            apps = result.stdout.strip()
            if apps:
                return [app.strip() for app in apps.split(",")]
        return []
    except Exception as e:
        print(f"Error getting active apps: {str(e)}")
        return []

def _format_error_with_available_windows(window_name: str, debug_info: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Format error message with available windows list and store debug info for later use."""
    # Check for debug_info from macOS specific format
    if debug_info and "available_windows" in debug_info:
        available_windows = []
        for window in debug_info["available_windows"]:
            window_desc = f"'{window['owner']}'"
            if window['name']:
                window_desc += f" - '{window['name']}'"
            available_windows.append(window_desc)

        # Create a formatted list of available windows for the error message
        windows_list = ", ".join(available_windows) if available_windows else "No windows found"
        result["error"] = f"Window '{window_name}' not found. Available windows: {windows_list}"
        result["_debug_info"] = debug_info  # Store with underscore prefix for later use
    # Check for debug_info from PyGetWindow format
    elif debug_info and "all_windows" in debug_info:
        window_titles = debug_info["all_windows"]
        windows_list = ", ".join(window_titles) if window_titles else "No windows found"
        result["error"] = f"Window '{window_name}' not found. Available windows: {windows_list}"
        result["_debug_info"] = debug_info  # Store with underscore prefix for later use
    else:
        result["error"] = f"Window '{window_name}' not found"
        if debug_info:
            result["_debug_info"] = debug_info  # Store with underscore prefix for later use


def _verify_screenshot_success(output_path: str) -> bool:
    """Verify if a screenshot was successfully saved to the output path."""
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0


def _try_mss_capture(output_path: str, window_region: Optional[Dict[str, int]], result: Dict[str, Any],
                     window_name: Optional[str] = None, debug_info: Optional[Dict[str, Any]] = None) -> bool:
    """
    Try to capture a screenshot using MSS library.

    Args:
        output_path: Path where the screenshot should be saved
        window_region: Region to capture (with top, left, width, height keys) or None for full screen
        result: Dictionary to store error information if capture fails
        window_name: Optional name of the window being captured, for error messages
        debug_info: Optional debug information to include in result on failure

    Returns:
        bool: True if capture was successful, False otherwise

    Note:
        - When window_region is None, captures the full primary screen.
        - Updates the result dictionary with success=True on success.
        - On failure, updates result with error message and debug_info if provided.
    """
    if MSS_AVAILABLE:
        try:
            if _capture_with_mss(output_path, window_region):
                # Simply check if the file exists and has non-zero size
                if _verify_screenshot_success(output_path):
                    result["success"] = True
                    # Debug info will be added by the caller if debug mode is enabled
                    return True
                else:
                    result["error"] = "Failed to save screenshot (file is empty or not created)"
            else:
                if window_name:
                    result["error"] = f"Failed to capture window '{window_name}' using MSS"
                else:
                    result["error"] = "MSS failed to capture full screen"
        except Exception as e:
            result["error"] = f"MSS error: {str(e)}"
    return False


def _capture_screenshot_macos(output_path: str, capture_area: str = "full", window_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture screenshot on macOS.

    Returns:
        Dict with success status and error message if failed
    """
    result = {"success": False, "error": None}
    internal_debug_info = None  # Store debug info internally but don't add to result yet

    # Check for screen recording permission first
    perm_check = _check_macos_screen_recording_permission()
    if not perm_check["has_permission"]:
        result["error"] = perm_check["error"]
        result["_debug_info"] = perm_check["details"]  # Store with underscore prefix for later use
        return result

    # If window_name is specified, try to capture that specific window
    if window_name:
        # Try to find the window using our macOS-specific function
        window_region, debug_info = _find_window_by_name(window_name)

        # Store debug info internally but don't add to result yet
        internal_debug_info = debug_info

        if window_region:
            # If we have a window ID from Quartz, use it directly without activating the window
            if 'id' in window_region:
                try:
                    # Capture using the window ID without activating the window
                    cmd = ["screencapture", "-l", str(window_region['id']), output_path]
                    process = subprocess.run(cmd, capture_output=True)

                    # Check if file exists and has non-zero size
                    if _verify_screenshot_success(output_path):
                        result["success"] = True
                        # Debug info will be added by the caller if debug mode is enabled
                        result["_debug_info"] = internal_debug_info  # Store for later use but with underscore prefix
                        return result
                    else:
                        result["error"] = f"Native screencapture failed with return code {process.returncode}"
                except Exception as e:
                    result["error"] = f"Screenshot error: {str(e)}"

            # If direct window ID capture failed or no ID available, try using MSS
            if _try_mss_capture(output_path, window_region, result, window_name):
                # If successful, store debug info for later use
                result["_debug_info"] = internal_debug_info  # Store for later use but with underscore prefix
                return result
        else:
            # Window not found - create a more detailed error message with available windows
            _format_error_with_available_windows(window_name, internal_debug_info, result)

        # No fallback to capturing the active window - return the result
        return result
    elif capture_area == "window":
        # Capture active window
        try:
            cmd = ["screencapture", "-w", output_path]
            process = subprocess.run(cmd, capture_output=True)

            # Check if file exists and has non-zero size
            if _verify_screenshot_success(output_path):
                result["success"] = True
                return result
            else:
                result["error"] = f"Active window capture failed with return code {process.returncode}"
        except Exception as e:
            result["error"] = f"Active window screenshot error: {str(e)}"

        # No fallback to full screen here either
        return result

    # For full screen capture
    if _try_mss_capture(output_path, None, result):
        return result

    # Fall back to native macOS screencapture for full screen only
    try:
        cmd = ["screencapture", "-x", output_path]
        process = subprocess.run(cmd, capture_output=True)

        # Check if file exists and has non-zero size
        if _verify_screenshot_success(output_path):
            result["success"] = True
            return result
        else:
            result["error"] = f"Native screencapture failed with return code {process.returncode}"
    except Exception as e:
        result["error"] = f"Screenshot error: {str(e)}"

    return result


def _capture_screenshot_linux(output_path: str, capture_area: str = "full", window_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture screenshot on Linux.

    Returns:
        Dict with success status and error message if failed
    """
    result = {"success": False, "error": None}

    # If window_name is specified, try to capture that specific window
    if window_name:
        # Try to use MSS first if available
        if MSS_AVAILABLE and PYGETWINDOW_AVAILABLE:
            try:
                window_region, debug_info = _find_window_by_name(window_name)
                if window_region:
                    if _try_mss_capture(output_path, window_region, result, window_name):
                        # Store debug info for later use
                        result["_debug_info"] = debug_info
                        return result
                else:
                    # Window not found - create a more detailed error message with available windows
                    _format_error_with_available_windows(window_name, debug_info, result)
                    return result
            except Exception as e:
                result["error"] = f"PyGetWindow error: {str(e)}"
                return result

        # Try native Linux methods only if MSS is not available
        if not MSS_AVAILABLE or not PYGETWINDOW_AVAILABLE:
            try:
                # Try to find the window using xdotool
                if subprocess.run(["which", "xdotool"], capture_output=True).returncode == 0:
                    # Search for the window
                    find_cmd = ["xdotool", "search", "--name", window_name]
                    result_cmd = subprocess.run(find_cmd, capture_output=True, text=True)

                    if result_cmd.returncode == 0 and result_cmd.stdout.strip():
                        # Get the first window ID
                        window_id = result_cmd.stdout.strip().split('\n')[0]

                        # Now capture the window
                        if subprocess.run(["which", "gnome-screenshot"], capture_output=True).returncode == 0:
                            cmd = ["gnome-screenshot", "-w", "-f", output_path, "-w", window_id]
                            process = subprocess.run(cmd, capture_output=True)

                            # Check if file exists and has non-zero size
                            if _verify_screenshot_success(output_path):
                                result["success"] = True
                                return result
                            else:
                                result["error"] = f"gnome-screenshot failed with return code {process.returncode}"
                        elif subprocess.run(["which", "scrot"], capture_output=True).returncode == 0:
                            cmd = ["scrot", "-u", output_path]
                            process = subprocess.run(cmd, capture_output=True)

                            # Check if file exists and has non-zero size
                            if _verify_screenshot_success(output_path):
                                result["success"] = True
                                return result
                            else:
                                result["error"] = f"scrot failed with return code {process.returncode}"
                        else:
                            result["error"] = "No screenshot tool found (gnome-screenshot or scrot)"
                    else:
                        result["error"] = f"Window '{window_name}' not found using xdotool"
                        # Store debug info
                        result["_debug_info"] = {"error": "Window not found using xdotool"}
                else:
                    result["error"] = "xdotool not available for window capture"
            except Exception as e:
                result["error"] = f"Screenshot error: {str(e)}"

        # No fallback to full screen - just return the error
        return result
    elif capture_area == "window":
        # Capture active window
        try:
            if subprocess.run(["which", "gnome-screenshot"], capture_output=True).returncode == 0:
                cmd = ["gnome-screenshot", "-w", "-f", output_path]
                process = subprocess.run(cmd, capture_output=True)

                # Check if file exists and has non-zero size
                if _verify_screenshot_success(output_path):
                    result["success"] = True
                    return result
                else:
                    result["error"] = f"Active window capture failed with return code {process.returncode}"
            elif subprocess.run(["which", "scrot"], capture_output=True).returncode == 0:
                cmd = ["scrot", "-u", output_path]
                process = subprocess.run(cmd, capture_output=True)

                # Check if file exists and has non-zero size
                if _verify_screenshot_success(output_path):
                    result["success"] = True
                    return result
                else:
                    result["error"] = f"scrot failed with return code {process.returncode}"
            else:
                result["error"] = "No screenshot tool found (gnome-screenshot or scrot)"
        except Exception as e:
            result["error"] = f"Active window screenshot error: {str(e)}"

        # No fallback to full screen here either
        return result

    # For full screen capture
    if _try_mss_capture(output_path, None, result):
        return result

    # Fall back to native Linux methods for full screen only
    try:
        if subprocess.run(["which", "gnome-screenshot"], capture_output=True).returncode == 0:
            cmd = ["gnome-screenshot", "-f", output_path]
            process = subprocess.run(cmd, capture_output=True)

            # Check if file exists and has non-zero size
            if _verify_screenshot_success(output_path):
                result["success"] = True
                return result
            else:
                result["error"] = f"gnome-screenshot failed with return code {process.returncode}"
        elif subprocess.run(["which", "scrot"], capture_output=True).returncode == 0:
            cmd = ["scrot", output_path]
            process = subprocess.run(cmd, capture_output=True)

            # Check if file exists and has non-zero size
            if _verify_screenshot_success(output_path):
                result["success"] = True
                return result
            else:
                result["error"] = f"scrot failed with return code {process.returncode}"
        else:
            result["error"] = "No screenshot tool found (gnome-screenshot or scrot)"
    except Exception as e:
        result["error"] = f"Screenshot error: {str(e)}"

    return result


def _capture_screenshot_windows(output_path: str, capture_area: str = "full", window_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture screenshot on Windows.

    Returns:
        Dict with success status and error message if failed
    """
    result = {"success": False, "error": None}

    # If window_name is specified, try to capture that specific window
    if window_name:
        # Try to use MSS first if available
        if MSS_AVAILABLE and PYGETWINDOW_AVAILABLE:
            try:
                window_region, debug_info = _find_window_by_name(window_name)
                if window_region:
                    if _try_mss_capture(output_path, window_region, result, window_name):
                        # Store debug info for later use
                        result["_debug_info"] = debug_info
                        return result
                else:
                    # Window not found - create a more detailed error message with available windows
                    _format_error_with_available_windows(window_name, debug_info, result)
                    return result
            except Exception as e:
                result["error"] = f"PyGetWindow error: {str(e)}"
                return result

        # Try native Windows methods only if MSS is not available
        if not MSS_AVAILABLE or not PYGETWINDOW_AVAILABLE:
            try:
                script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing

                # Function to find window by title
                function Find-Window($title) {{
                    $processes = Get-Process | Where-Object {{$_.MainWindowTitle -like "*$title*"}}
                    return $processes
                }}

                $targetProcess = Find-Window("{window_name}")

                if ($targetProcess -and $targetProcess.Count -gt 0) {{
                    # Use the first matching process
                    $process = $targetProcess[0]

                    # Get window bounds
                    $hwnd = $process.MainWindowHandle
                    $rect = New-Object System.Drawing.Rectangle
                    [void][System.Runtime.InteropServices.Marshal]::GetWindowRect($hwnd, [ref]$rect)

                    # Capture the window
                    $bitmap = New-Object System.Drawing.Bitmap ($rect.Width - $rect.X), ($rect.Height - $rect.Y)
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen($rect.X, $rect.Y, 0, 0, $bitmap.Size)
                    $bitmap.Save('{output_path}')

                    return $true
                }}
                else {{
                    # List all windows for diagnostics
                    $allWindows = Get-Process | Where-Object {{$_.MainWindowTitle}} | Select-Object MainWindowTitle, ProcessName | Format-List | Out-String
                    Write-Output "WINDOWS_LIST:$allWindows"
                    return $false
                }}
                """

                cmd = ["powershell", "-Command", script]
                process = subprocess.run(cmd, capture_output=True, text=True)

                output = process.stdout.strip()
                if output.startswith("True"):
                    # Check if file exists and has non-zero size
                    if _verify_screenshot_success(output_path):
                        result["success"] = True
                        return result
                    else:
                        result["error"] = "Failed to save screenshot of window"
                else:
                    # Check if we got a list of windows in the output
                    if "WINDOWS_LIST:" in output:
                        windows_list = output.split("WINDOWS_LIST:")[1].strip()
                        result["error"] = f"Window '{window_name}' not found. Available windows: {windows_list}"
                        # Store windows list as debug info
                        result["_debug_info"] = {"available_windows": windows_list}
                    else:
                        result["error"] = f"Window '{window_name}' not found or could not be captured"
            except Exception as e:
                result["error"] = f"Screenshot error: {str(e)}"

        # No fallback to full screen - just return the error
        return result
    elif capture_area == "window":
        # Capture active window using Windows methods
        try:
            script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing

            function Get-ActiveWindow {{
                $foregroundWindowHandle = [System.Windows.Forms.Form]::ActiveForm.Handle
                if (-not $foregroundWindowHandle) {{
                    # If no active form, try to get the foreground window
                    $foregroundWindowHandle = [System.Runtime.InteropServices.Marshal]::GetForegroundWindow()
                }}

                if ($foregroundWindowHandle) {{
                    $rect = New-Object System.Drawing.Rectangle
                    [void][System.Runtime.InteropServices.Marshal]::GetWindowRect($foregroundWindowHandle, [ref]$rect)

                    $bitmap = New-Object System.Drawing.Bitmap ($rect.Width - $rect.X), ($rect.Height - $rect.Y)
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen($rect.X, $rect.Y, 0, 0, $bitmap.Size)
                    $bitmap.Save('{output_path}')

                    return $true
                }}
                return $false
            }}

            Get-ActiveWindow
            """

            cmd = ["powershell", "-Command", script]
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.stdout.strip() == "True":
                # Check if file exists and has non-zero size
                if _verify_screenshot_success(output_path):
                    result["success"] = True
                    return result
                else:
                    result["error"] = "Failed to capture active window"
            else:
                result["error"] = "Failed to capture active window"
        except Exception as e:
            result["error"] = f"Active window screenshot error: {str(e)}"

        # No fallback to full screen here either
        return result
    else:
        # For full screen capture
        if _try_mss_capture(output_path, None, result):
            return result

        # Fall back to native Windows methods for full screen only
        try:
            script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screen.Size)
            $bitmap.Save('{output_path}')
            """

            cmd = ["powershell", "-Command", script]
            process = subprocess.run(cmd, capture_output=True)

            # Check if file exists and has non-zero size
            if _verify_screenshot_success(output_path):
                result["success"] = True
                return result
            else:
                result["error"] = f"PowerShell screenshot failed with return code {process.returncode}"
        except Exception as e:
            result["error"] = f"Screenshot error: {str(e)}"

    return result


def find_macos_window_by_name(window_name):
    """Find a window by name on macOS using Quartz."""
    try:
        if not QUARTZ_AVAILABLE:
            return None, {"error": "Quartz not available"}

        window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

        # Collect debug info instead of printing
        debug_info = {
            "search_term": window_name,
            "available_windows": []
        }

        all_windows = []
        for window in window_list:
            name = window.get('kCGWindowName', '')
            owner = window.get('kCGWindowOwnerName', '')
            layer = window.get('kCGWindowLayer', 0)
            window_id = window.get('kCGWindowNumber', 0)

            # Skip windows with layer > 0 (typically system UI elements)
            if layer > 0:
                continue

            window_info = {
                "id": window_id,
                "name": name,
                "owner": owner,
                "layer": layer
            }
            debug_info["available_windows"].append(window_info)

            all_windows.append({
                'id': window_id,
                'name': name,
                'owner': owner,
                'layer': layer,
                'bounds': window.get('kCGWindowBounds', {})
            })

        # Define matching categories with different priorities
        exact_app_matches = []  # Exact match on application name
        exact_window_matches = []  # Exact match on window title
        app_contains_matches = []  # Application name contains search term
        window_contains_matches = []  # Window title contains search term

        # Normalize the search term for comparison
        search_term_lower = window_name.lower()

        # First pass: categorize windows by match quality
        for window in all_windows:
            name = window['name'] or ''
            owner = window['owner'] or ''

            # Skip empty windows
            if not name and not owner:
                continue

            name_lower = name.lower()
            owner_lower = owner.lower()

            # Check for exact matches first (case-insensitive)
            if owner_lower == search_term_lower:
                exact_app_matches.append(window)
            elif name_lower == search_term_lower:
                exact_window_matches.append(window)
            # Then check for contains matches
            elif search_term_lower in owner_lower:
                app_contains_matches.append(window)
            elif search_term_lower in name_lower:
                window_contains_matches.append(window)

        # Process matches in priority order
        for match_list, reason in [
            (exact_app_matches, "Exact match on application name"),
            (exact_window_matches, "Exact match on window title"),
            (app_contains_matches, "Application name contains search term"),
            (window_contains_matches, "Window title contains search term")
        ]:
            if match_list:
                # Sort by layer (lower layer = more in front)
                match_list.sort(key=lambda w: w['layer'])
                selected_window = match_list[0]
                debug_info["selected_window"] = {
                    "id": selected_window['id'],
                    "name": selected_window['name'],
                    "owner": selected_window['owner'],
                    "layer": selected_window['layer'],
                    "selection_reason": reason
                }

                bounds = selected_window['bounds']
                return {
                    'id': selected_window['id'],
                    'top': bounds.get('Y', 0),
                    'left': bounds.get('X', 0),
                    'width': bounds.get('Width', 0),
                    'height': bounds.get('Height', 0)
                }, debug_info

        debug_info["error"] = f"No matching window found for '{window_name}'"
        return None, debug_info
    except Exception as e:
        return None, {"error": f"Error finding macOS window: {str(e)}"}


def capture_screenshot(output_path: Optional[str] = None, capture_mode: Optional[Dict[str, str]] = None, debug: bool = False) -> Dict[str, Any]:
    """
    Capture a screenshot and save it to the specified path.

    Args:
        output_path: Path where the screenshot should be saved. If None, a default path will be used.
        capture_mode: Dictionary specifying what to capture:
            - type: 'full' for entire screen, 'active_window' for current window, 'named_window' for specific window
            - window_name: Name of window to capture (required when type is 'named_window')
                          Windows can be captured in the background without bringing them to the front.
        debug: Whether to include debug information in the response on failure

    Returns:
        Dictionary with success status and path to the saved screenshot.
    """
    # Set defaults if capture_mode is not provided
    if not capture_mode:
        capture_mode = {"type": "full"}

    # Extract capture type and window name
    capture_type = capture_mode.get("type", "full")
    window_name = capture_mode.get("window_name") if capture_type == "named_window" else None

    if debug:
        print(f"Capture mode: {capture_type}")
        if window_name:
            print(f"Window name: {window_name}")

    # Use default path if none provided
    if not output_path:
        output_path = _get_default_screenshot_path()

    # Handle relative paths with respect to allowed directory
    if not os.path.isabs(output_path) and hasattr(state, 'allowed_directory') and state.allowed_directory:
        full_output_path = os.path.abspath(os.path.join(state.allowed_directory, output_path))
    else:
        full_output_path = os.path.abspath(output_path)

    # Security check
    if hasattr(state, 'allowed_directory') and state.allowed_directory:
        if not full_output_path.startswith(state.allowed_directory):
            return {
                "success": False,
                "error": f"Access denied: Path ({full_output_path}) must be within allowed directory"
            }

    # Ensure the output directory exists, creating it relative to the allowed directory
    os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

    # Convert to old parameters for compatibility with existing functions
    capture_area = "window" if capture_type in ["active_window", "named_window"] else "full"

    # Capture screenshot based on platform
    system_name = platform.system().lower()
    if debug:
        print(f"Detected platform: {system_name}")

    if system_name == "darwin" or system_name == "macos":
        result = _capture_screenshot_macos(full_output_path, capture_area, window_name)
    elif system_name == "linux":
        result = _capture_screenshot_linux(full_output_path, capture_area, window_name)
    elif system_name == "windows":
        result = _capture_screenshot_windows(full_output_path, capture_area, window_name)
    else:
        result = {"success": False, "error": f"Unsupported platform: {system_name}"}

    # Check if the error might be related to permission issues
    if not result["success"] and result.get("error"):
        # If the error already mentions permission, highlight it
        if "permission" in result["error"].lower():
            # Make the error message more prominent for permission issues
            modified_message = f"PERMISSION ERROR: {result['error']}"
            result["error"] = modified_message

            # Add additional hints for macOS
            if system_name == "darwin":
                result["error"] += " To fix this: Open System Settings > Privacy & Security > Screen Recording, and enable permission for this application."

    # Extract debug info if present
    debug_info = result.pop("_debug_info", None) if "_debug_info" in result else None

    # Format the final result
    response = {
        "success": result["success"],
        "path": full_output_path if result["success"] else None,
        "message": "Screenshot captured successfully" if result["success"] else result.get("error", "Failed to capture screenshot")
    }

    # Add warning if present
    if "warning" in result:
        response["warning"] = result["warning"]

    # Only include debug info if debug mode is enabled AND the operation failed
    if debug and not result["success"] and debug_info:
        response["debug_info"] = debug_info

    return response


async def handle_capture_screenshot(arguments: dict) -> List[types.TextContent]:
    """Handle capturing a screenshot."""
    output_path = arguments.get("output_path")
    debug = arguments.get("debug", False)

    # Handle legacy platform parameter (ignore it)
    if "platform" in arguments:
        print("Note: 'platform' parameter is deprecated and will be auto-detected")

    # Enforce new parameter format requiring capture_mode
    capture_mode = arguments.get("capture_mode")
    if not capture_mode:
        result = {
            "success": False,
            "error": "Missing required parameter 'capture_mode'. Please provide a capture_mode object with 'type' field."
        }
    else:
        # Ensure output_path is properly resolved within allowed directory
        if output_path:
            # Resolve using allowed directory
            if os.path.isabs(output_path):
                # If path is absolute, just use it directly (security check is done in capture_screenshot)
                resolved_path = output_path
            else:
                # For relative paths, resolve against the allowed directory
                resolved_path = os.path.join(state.allowed_directory, output_path)

            # Create parent directory if needed
            dir_path = os.path.dirname(resolved_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            result = capture_screenshot(resolved_path, capture_mode, debug)
        else:
            result = capture_screenshot(output_path, capture_mode, debug)

    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
