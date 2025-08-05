import os
import re
import fnmatch
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple
import platform
import stat
from mcp.types import TextContent
from .state import state


def search_code_tool():
    return {
        "name": "search_code",
        "description": "Regex search in file contents. Uses ripgrep when available. "
                    "USE: Find function definitions, variable usage, code patterns. "
                    "NOT: File names (use search_files), semantic analysis. "
                    "RETURNS: Matching lines with file paths, line numbers, sorted by modification time",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patterns": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Regex patterns to search. Examples: ['function\\s+\\w+', 'class\\s+\\w+']."
                },
                "include": {
                    "type": "string",
                    "description": "File inclusion pattern (glob). Examples: '*.js', '*.{ts,tsx}', 'src/**/*.py'.",
                    "default": "*"
                },
                "exclude": {
                    "type": "string",
                    "description": "File exclusion pattern (glob). Examples: 'node_modules/**', '*.min.js'.",
                    "default": ""
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results per pattern. Default: 100.",
                    "default": 100
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Case-sensitive search. Default: false.",
                    "default": False
                },
                "path": {
                    "type": "string",
                    "description": "Base directory to search. Examples: '.', 'src'. Default: '.'.",
                    "default": "."
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files (.env, .config, etc). Default: false.",
                    "default": False,
                },
            },
            "required": ["patterns"]
        }
    }


async def handle_search_code(arguments: dict) -> List[TextContent]:
    """Handle searching for patterns in code files."""
    patterns = arguments.get("patterns", [])
    include = arguments.get("include", "*")
    exclude = arguments.get("exclude", "")
    max_results = arguments.get("max_results", 100)
    case_sensitive = arguments.get("case_sensitive", False)
    path = arguments.get("path", ".")
    include_hidden = arguments.get("include_hidden", False)

    if not patterns:
        raise ValueError("At least one pattern must be provided")

    # Determine full path for search start
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {path}")
    if not os.path.isdir(full_path):
        raise ValueError(f"Path is not a directory: {path}")

    # Results from all patterns
    all_results = []

    try:
        for i, pattern in enumerate(patterns):
            pattern_header = f"\n{'='*30}\nPattern {i+1}: {pattern}\n{'='*30}\n" if len(patterns) > 1 else ""
            try:
                # Use ripgrep if available for faster results
                try:
                    result = await _search_with_ripgrep(
                        pattern, include, exclude, max_results, case_sensitive, full_path, include_hidden
                    )
                except (subprocess.SubprocessError, FileNotFoundError):
                    # Fallback to Python implementation if ripgrep not available
                    result = await _search_with_python(
                        pattern, include, exclude, max_results, case_sensitive, full_path, include_hidden
                    )

                # Add pattern header for multiple patterns
                if len(patterns) > 1 and result and result[0].text != f"No matches found for pattern '{pattern}'.":
                    result[0].text = pattern_header + result[0].text

                all_results.extend(result)
            except Exception as e:
                all_results.append(TextContent(
                    type="text",
                    text=f"{pattern_header}Error searching for pattern '{pattern}': {str(e)}"
                ))

        return all_results
    except Exception as e:
        raise ValueError(f"Error searching code: {str(e)}")


async def _search_with_ripgrep(
    pattern: str,
    include: str,
    exclude: str,
    max_results: int,
    case_sensitive: bool,
    full_path: str,
    include_hidden: bool
) -> List[TextContent]:
    """Search using ripgrep for better performance."""
    cmd = ["rg", "--line-number"]

    # Add case sensitivity flag
    if not case_sensitive:
        cmd.append("--ignore-case")

    # Add include patterns if provided
    if include and include != "*":
        # Convert glob pattern to ripgrep glob
        cmd.extend(["--glob", include])

    # Add exclude patterns if provided
    if exclude:
        # Convert glob pattern to ripgrep glob
        cmd.extend(["--glob", f"!{exclude}"])

    # Add max results
    cmd.extend(["--max-count", str(max_results)])

    # Add hidden files
    if include_hidden:
        cmd.append("--hidden")

    # Add pattern and path
    cmd.extend([pattern, full_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout.strip()
        if not output:
            return [TextContent(
                type="text",
                text="No matches found."
            )]

        # Process output to add file modification times
        files_with_matches = {}
        current_file = None

        for line in output.split('\n'):
            if not line.strip():
                continue

            # ripgrep output format: file:line:content
            parts = line.split(':', 2)
            if len(parts) >= 3:
                file_path, line_num, content = parts[0], parts[1], parts[2]

                # Get relative path for display
                rel_path = os.path.relpath(file_path, state.allowed_directory)

                if rel_path not in files_with_matches:
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)
                    files_with_matches[rel_path] = {
                        "mod_time": mod_time,
                        "matches": []
                    }

                files_with_matches[rel_path]["matches"].append(f"{line_num}: {content}")

        # Sort files by modification time (newest first)
        sorted_files = sorted(
            files_with_matches.items(),
            key=lambda x: x[1]["mod_time"],
            reverse=True
        )

        # Format output
        formatted_output = []
        match_count = 0
        for file_path, data in sorted_files:
            formatted_output.append(f"\n{file_path} (modified: {datetime.fromtimestamp(data['mod_time']).strftime('%Y-%m-%d %H:%M:%S')})")
            formatted_output.extend(data["matches"])
            match_count += len(data["matches"])

        summary = f"Found {match_count} matches in {len(sorted_files)} files for pattern '{pattern}'"
        if match_count > 0:
            formatted_output.insert(0, summary)
        else:
            formatted_output = [summary]

        return [TextContent(
            type="text",
            text="\n".join(formatted_output)
        )]

    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not e.stderr:
            # ripgrep returns 1 when no matches are found
            return [TextContent(
                type="text",
                text=f"No matches found for pattern '{pattern}'."
            )]
        raise


async def _search_with_python(
    pattern: str,
    include: str,
    exclude: str,
    max_results: int,
    case_sensitive: bool,
    full_path: str,
    include_hidden: bool
) -> List[TextContent]:
    """Fallback search implementation using Python's regex and file operations."""
    # Compile the regex pattern
    try:
        if case_sensitive:
            regex = re.compile(pattern)
        else:
            regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regular expression: {str(e)}")

    # Convert glob patterns to regex patterns for matching
    include_pattern = fnmatch.translate(include)
    include_regex = re.compile(include_pattern)

    exclude_regex = None
    if exclude:
        exclude_pattern = fnmatch.translate(exclude)
        exclude_regex = re.compile(exclude_pattern)

    # Dictionary to store files with matches and their modification times
    files_with_matches = {}
    match_count = 0

    # Walk the directory tree
    for root, dirs, files in os.walk(full_path):
        if match_count >= max_results:
            break

        if not include_hidden:
            # Remove hidden directories from dirs list to prevent os.walk from entering them
            dirs[:] = [d for d in dirs if not is_hidden(os.path.join(root, d))] 

            # Filter out hidden files
            files = [f for f in files if not is_hidden(os.path.join(root, f))]

        for filename in files:
            if match_count >= max_results:
                break

            file_path = os.path.join(root, filename)

            # Get path relative to the search root for pattern matching
            rel_path = os.path.relpath(file_path, full_path)

            # Check if file matches include pattern
            if not include_regex.match(filename) and not include_regex.match(rel_path):
                continue

            # Check if file matches exclude pattern
            if exclude_regex and (exclude_regex.match(filename) or exclude_regex.match(rel_path)):
                continue

            # Get file modification time
            try:
                mod_time = os.path.getmtime(file_path)
            except (OSError, IOError):
                continue

            # Skip binary files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        # Try to read the first few bytes to check if it's a text file
                        f.read(4096)
                        # Rewind to beginning of file
                        f.seek(0)
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue

                    # Get relative path for display
                    display_path = os.path.relpath(file_path, state.allowed_directory)

                    # Initialize entry for this file
                    if display_path not in files_with_matches:
                        files_with_matches[display_path] = {
                            "mod_time": mod_time,
                            "matches": []
                        }

                    # Search for pattern in each line
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            files_with_matches[display_path]["matches"].append(f"{line_num}: {line.rstrip()}")
                            match_count += 1

                            if match_count >= max_results:
                                break

            except (OSError, IOError):
                # Skip files that can't be read
                continue

    # No matches found
    if not files_with_matches:
        return [TextContent(
            type="text",
            text=f"No matches found for pattern '{pattern}'."
        )]

    # Sort files by modification time (newest first)
    sorted_files = sorted(
        files_with_matches.items(),
        key=lambda x: x[1]["mod_time"],
        reverse=True
    )

    # Format output
    formatted_output = []
    total_matches = 0
    files_with_actual_matches = 0

    for file_path, data in sorted_files:
        if data["matches"]:  # Only include files that actually have matches
            formatted_output.append(f"\n{file_path} (modified: {datetime.fromtimestamp(data['mod_time']).strftime('%Y-%m-%d %H:%M:%S')})")
            formatted_output.extend(data["matches"])
            total_matches += len(data["matches"])
            files_with_actual_matches += 1

    summary = f"Found {total_matches} matches in {files_with_actual_matches} files for pattern '{pattern}'"
    if total_matches > 0:
        formatted_output.insert(0, summary)
    else:
        formatted_output = [summary]

    return [TextContent(
        type="text",
        text="\n".join(formatted_output)
    )]


def is_hidden_windows(filepath: str) -> bool:
    """Check if file/folder is hidden on Windows"""
    try:
        attrs = os.stat(filepath).st_file_attributes
        return attrs & stat.FILE_ATTRIBUTE_HIDDEN
    except (AttributeError, OSError):
        return False


def is_hidden_unix(name: str) -> bool:
    """Check if file/folder is hidden on Unix-like systems (Linux/macOS)"""
    return name.startswith('.')


def is_hidden(filepath: str) -> bool:
    """Cross-platform hidden file/folder detection"""
    name = os.path.basename(filepath)
    
    if platform.system() == 'Windows':
        return is_hidden_windows(filepath) or name.startswith('.')
    else:
        return is_hidden_unix(name)
