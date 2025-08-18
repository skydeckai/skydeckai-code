import os
import platform
import shutil
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
            "Execute arbitrary code in various programming languages on the user's local machine within the current working directory. "
            "WHEN TO USE: When you need to run small code snippets to test functionality, compute values, process data, or "
            "demonstrate how code works. Useful for quick prototyping, data transformations, or explaining programming concepts with running "
            "examples. "
            "WHEN NOT TO USE: When you need to modify files (use write_file or edit_file instead), when running potentially harmful "
            "operations, or when you need to install external dependencies. "
            "RETURNS: Text output including stdout, stderr, and exit code of the "
            "execution. The output sections are clearly labeled with '=== stdout ===' and '=== stderr ==='. "
            "Supported languages: " + ", ".join(LANGUAGE_CONFIGS.keys()) + ". "
            "Always review the code carefully before execution to prevent unintended consequences. "
            "Examples: "
            "- Python: code='print(sum(range(10)))'. "
            "- JavaScript: code='console.log(Array.from({length: 5}, (_, i) => i*2))'. "
            "- Ruby: code='puts (1..5).reduce(:+)'. "
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "enum": list(LANGUAGE_CONFIGS.keys()),
                    "description": "Programming language to use. Must be one of the supported languages: "
                    + ", ".join(LANGUAGE_CONFIGS.keys())
                    + ". "
                    + "Each language requires the appropriate runtime to be installed on the user's machine. The code will be executed using: python3 for "
                    + "Python, node for JavaScript, ruby for Ruby, php for PHP, go run for Go, and rustc for Rust.",
                },
                "code": {
                    "type": "string",
                    "description": "Code to execute on the user's local machine in the current working directory. The code will be saved to a "
                    + "temporary file and executed within the allowed workspace. For Go and Rust, main function wrappers will be added automatically if "
                    + "not present. For PHP, <?php will be prepended if not present.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds. The execution will be terminated if it exceeds this time limit, returning a " + "timeout message. Must be between 1 and 30 seconds.",
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
            "Execute a shell script on the user's local machine within the current working directory. "
            "Cross-platform support: automatically uses bash/sh on Unix-like systems (Linux/macOS) and PowerShell/cmd on Windows. "
            "WHEN TO USE: When you need to automate system tasks, run shell commands, interact with the operating system, or perform operations "
            "that are best expressed as shell commands. Useful for file system operations, system configuration, or running system utilities. "
            "Also ideal when you need to run code linters to check for style issues or potential bugs in the codebase, "
            "or when you need to perform version control operations such as initializing git repositories, checking status, "
            "committing changes, cloning repositories, and other git commands without dedicated tools. "
            "WHEN NOT TO USE: When you need more structured programming (use execute_code instead), when you need to execute potentially "
            "dangerous system operations, or when you want to run commands outside the allowed directory. "
            "RETURNS: Text output including stdout, stderr, and exit code of the execution. The output sections are clearly labeled with "
            "'=== stdout ===' and '=== stderr ==='. "
            "This tool can execute shell commands and scripts for system automation and management tasks. "
            "It is designed to perform tasks on the user's local environment, such as opening applications, installing packages and more. "
            "Always review the script carefully before execution to prevent unintended consequences. "
            "Examples: "
            "- script='echo \"Current directory:\" && pwd' (Unix) or 'echo \"Current directory:\" && pwd' (Windows PowerShell). "
            "- script='for i in {1..5}; do echo $i; done' (Unix) or 'for ($i=1; $i -le 5; $i++) { Write-Host $i }' (Windows PowerShell). "
            "- script='eslint src/ --format stylish' (for linting, cross-platform). "
            "- script='git init && git add . && git commit -m \"Initial commit\"' (for git operations, cross-platform)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "Shell script to execute on the user's local machine. Can include any valid shell commands or scripts that would "
                    "run in a standard shell environment. The script is executed using /bin/sh for maximum compatibility across systems.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds. The execution will be terminated if it exceeds this time limit. Default is 300 seconds (5 minutes), with a maximum allowed value of 600 seconds (10 minutes).",
                    "default": 300,
                    "maximum": 600,
                },
            },
            "required": ["script"],
        },
    }


def is_command_available(command: str) -> bool:
    """Check if a command is available in the system."""
    return shutil.which(command) is not None


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


async def execute_shell_script_in_temp_file_windows(script: str, timeout: int) -> tuple[str, str, int]:
    """Execute a shell script in a temporary file on Windows and return stdout, stderr, and return code."""
    
    # Check if PowerShell is available
    use_powershell = is_command_available("powershell")
    
    if use_powershell:
        temp_file = "temp_script.ps1"
        shell_command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_file]
        header = "# PowerShell script\n"
    else:
        temp_file = "temp_script.bat"
        shell_command = ["cmd.exe", "/c", temp_file]
        header = "@echo off\n"
    
    try:
        # Change to allowed directory first
        os.chdir(state.allowed_directory)
        
        # Write script to temp file
        with open(temp_file, 'w') as f:
            f.write(header)
            f.write(script)
            f.flush()
        
        # Execute script
        try:
            result = subprocess.run(
                shell_command,
                capture_output=True,
                timeout=timeout,
                text=True,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return '', f'Execution timed out after {timeout} seconds', 124
    
    finally:
        # Cleanup
        try:
            os.unlink(temp_file)
        except Exception:
            pass

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
        # Use Windows-compatible function on Windows, Unix function otherwise
        if platform.system() == "Windows":
            stdout, stderr, returncode = await execute_shell_script_in_temp_file_windows(script, timeout)
        else:
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
