import os
import stat
import subprocess
from typing import Any, Dict, List
import mcp.types as types
from pathlib import Path

from .state import state

# Language configurations
LANGUAGE_CONFIGS = {
    "python": {"file_extension": ".py", "command": ["python3"], "comment_prefix": "#"},
    "javascript": {"file_extension": ".js", "command": ["node"], "comment_prefix": "//"},
    "ruby": {"file_extension": ".rb", "command": ["ruby"], "comment_prefix": "#"},
    "php": {"file_extension": ".php", "command": ["php"], "comment_prefix": "//"},
    "go": {"file_extension": ".go", "command": ["go", "run"], "comment_prefix": "//", "wrapper_start": "package main\nfunc main() {", "wrapper_end": "}"},
    "rust": {
        "file_extension": ".rs",
        "command": ["rustc", "-o"],  # Special handling needed
        "comment_prefix": "//",
        "wrapper_start": "fn main() {",
        "wrapper_end": "}",
    },
}


def execute_code_tool() -> Dict[str, Any]:
    return {
        "name": "execute_code",
        "description": (
            "Execute code snippets in sandbox. Supports: python, javascript, ruby, php, go, rust. "
            "USE: Test functions, compute values, prototype. "
            "NOT: File modifications, system operations, dependencies. "
            "Auto-wraps Go/Rust main functions. Timeout: 30s max"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": list(LANGUAGE_CONFIGS.keys()),
                    "description": "Programming language. Requires runtime: python3, node, ruby, php, go, rustc.",
                },
                "code": {
                    "type": "string",
                    "description": "Code to execute. Auto-wraps Go/Rust main functions, adds PHP tags.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max execution time (1-30 seconds). Default: 5.",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 30,
                },
            },
            "required": ["language", "code"],
        },
    }


def execute_shell_script_tool() -> Dict[str, Any]:
    return {
        "name": "execute_shell_script",
        "description": (
            "Run bash/sh scripts for system tasks, git operations, linters. "
            "USE: System automation, file operations, version control, code linting. "
            "NOT: Structured programming (use execute_code), dangerous operations. "
            "Timeout: 10 minutes maximum"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "Shell script to execute (uses /bin/sh for compatibility).",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max execution time (up to 600 seconds). Default: 300.",
                    "default": 300,
                    "maximum": 600,
                },
            },
            "required": ["script"],
        },
    }


def is_command_available(command: str) -> bool:
    """Check if a command is available in the system."""
    try:
        subprocess.run(["which", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def prepare_code(code: str, language: str) -> str:
    """Prepare code for execution based on language requirements."""
    config = LANGUAGE_CONFIGS[language]

    if language == "go":
        if "package main" not in code and "func main()" not in code:
            return f"{config['wrapper_start']}\n{code}\n{config['wrapper_end']}"
    elif language == "rust":
        if "fn main()" not in code:
            return f"{config['wrapper_start']}\n{code}\n{config['wrapper_end']}"
    elif language == "php":
        if "<?php" not in code:
            return f"<?php\n{code}"

    return code


async def execute_code_in_temp_file(language: str, code: str, timeout: int) -> tuple[str, str, int]:
    """Execute code in a temporary file and return stdout, stderr, and return code."""
    config = LANGUAGE_CONFIGS[language]
    temp_file = f"temp_script{config['file_extension']}"

    try:
        # Change to allowed directory first
        os.chdir(state.allowed_directory)

        # Write code to temp file
        with open(temp_file, "w") as f:
            # Prepare and write code
            prepared_code = prepare_code(code, language)
            f.write(prepared_code)
            f.flush()

            # Prepare command
            if language == "rust":
                # Special handling for Rust
                output_path = "temp_script.exe"
                compile_cmd = ["rustc", temp_file, "-o", output_path]
                try:
                    subprocess.run(compile_cmd, check=True, capture_output=True, timeout=timeout)
                    cmd = [output_path]
                except subprocess.CalledProcessError as e:
                    return "", e.stderr.decode(), e.returncode
            else:
                cmd = config["command"] + [temp_file]

            # Execute code
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=timeout,
                    text=True,
                )
                return result.stdout, result.stderr, result.returncode
            except subprocess.TimeoutExpired:
                return "", f"Execution timed out after {timeout} seconds", 124

    finally:
        # Cleanup
        # Note: We stay in the allowed directory as all operations should happen there
        try:
            os.unlink(temp_file)
            if language == "rust" and os.path.exists(output_path):
                os.unlink(output_path)
        except Exception:
            pass


async def handle_execute_code(arguments: dict) -> List[types.TextContent]:
    """Handle code execution in various programming languages."""
    language = arguments.get("language")
    code = arguments.get("code")
    timeout = arguments.get("timeout", 5)

    if not language or not code:
        raise ValueError("Both language and code must be provided")

    if language not in LANGUAGE_CONFIGS:
        raise ValueError(f"Unsupported language: {language}")

    # Check if required command is available
    command = LANGUAGE_CONFIGS[language]["command"][0]
    if not is_command_available(command):
        return [types.TextContent(type="text", text=f"Error: {command} is not installed on the system")]

    try:
        stdout, stderr, returncode = await execute_code_in_temp_file(language, code, timeout)

        result = []
        if stdout:
            result.append(f"=== stdout ===\n{stdout.rstrip()}")
        if stderr:
            result.append(f"=== stderr ===\n{stderr.rstrip()}")
        if not stdout and not stderr:
            result.append("Code executed successfully with no output")
        if returncode != 0:
            result.append(f"\nProcess exited with code {returncode}")

        return [types.TextContent(type="text", text="\n\n".join(result))]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing code:\n{str(e)}")]


async def execute_shell_script_in_temp_file(script: str, timeout: int) -> tuple[str, str, int]:
    """Execute a shell script in a temporary file and return stdout, stderr, and return code."""
    temp_file = "temp_script.sh"

    try:
        # Change to allowed directory first
        os.chdir(state.allowed_directory)

        # Write script to temp file
        with open(temp_file, "w") as f:
            f.write("#!/bin/sh\n")  # Use sh for maximum compatibility
            f.write(script)
            f.flush()

        # Make the script executable
        os.chmod(temp_file, os.stat(temp_file).st_mode | stat.S_IEXEC)

        # Execute script
        try:
            path_env = get_comprehensive_shell_paths()
            env = os.environ.copy()
            env["PATH"] = path_env
            result = subprocess.run(
                ["/bin/sh", temp_file],  # Use sh explicitly for consistent behavior
                capture_output=True,
                timeout=timeout,
                text=True,
                env=env,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", f"Execution timed out after {timeout} seconds", 124

    finally:
        # Cleanup
        try:
            os.unlink(temp_file)
        except Exception:
            pass


async def handle_execute_shell_script(arguments: dict) -> List[types.TextContent]:
    """Handle shell script execution."""
    script = arguments.get("script")
    timeout = min(arguments.get("timeout", 300), 600)  # Default 5 minutes, cap at 10 minutes

    try:
        stdout, stderr, returncode = await execute_shell_script_in_temp_file(script, timeout)
        result = []
        if stdout:
            result.append(f"=== stdout ===\n{stdout.rstrip()}")
        if stderr:
            result.append(f"=== stderr ===\n{stderr.rstrip()}")
        if not stdout and not stderr:
            result.append("Script executed successfully with no output")
        if returncode != 0:
            result.append(f"\nScript exited with code {returncode}")

        return [types.TextContent(type="text", text="\n\n".join(result))]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing shell script:\n{str(e)}")]


def get_comprehensive_shell_paths():
    """
    Get PATH from shells using login mode to capture initialization files
    """
    shells_file = Path("/etc/shells")

    if not shells_file.exists():
        return os.environ.get("PATH", "")

    # Read available shells
    try:
        with open(shells_file, "r") as f:
            shells = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except IOError:
        return os.environ.get("PATH", "")

    all_paths = []

    # Get PATH from each shell as login shell
    for shell in shells:
        if not os.path.exists(shell):
            continue

        # Different approaches for different shells
        commands_to_try = [
            [shell, "--login", "-i", "-c", "echo $PATH"],
            [shell, "-l", "-i", "-c", "echo $PATH"],
            [shell, "--login", "-c", "echo $PATH"],
            [shell, "-l", "-c", "echo $PATH"],
            [shell, "-c", "echo $PATH"],
        ]

        # Try each command until one works
        for cmd in commands_to_try:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    shell_path = result.stdout.strip()
                    if shell_path and shell_path != "$PATH":
                        all_paths.extend(shell_path.split(":"))
                    break
            except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                continue

    # Add current PATH
    current_path = os.environ.get("PATH", "")
    if current_path:
        all_paths.extend(current_path.split(":"))

    # Remove duplicates while preserving order
    return deduplicate_paths(all_paths)


def deduplicate_paths(all_paths):
    """
    Remove duplicates while preserving order
    """
    seen = set()
    merged_path = []
    for path in all_paths:
        path = path.strip()
        if path and path not in seen and os.path.exists(path):
            seen.add(path)
            merged_path.append(path)

    return ":".join(merged_path)
