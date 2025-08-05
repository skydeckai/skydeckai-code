import difflib
import json
import os
import re
import stat
import subprocess
import shutil
from datetime import datetime
from typing import List

import mcp.types as types
from mcp.types import TextContent

from .state import state


def read_file_tool():
    return {
        "name": "read_file",
        "description": "Read file contents with optional line range. "
                    "USE: View source code, config files, text content. "
                    "NOT: File metadata (use get_file_info), directory listing. "
                    "RETURNS: Complete text or specified line range with file headers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path (not directory). Examples: 'README.md', 'src/main.py'. Absolute/relative paths within workspace."
                            },
                            "offset": {
                                "type": "integer",
                                "description": "Start line number (1-indexed). Default: beginning of file."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max lines to read from offset. Default: to end of file."
                            }
                        },
                        "required": ["path"]
                    },
                    "description": "List of files to read with optional offset and limit for each file."
                }
            },
            "required": ["files"]
        },
    }

def write_file_tool():
    return {
        "name": "write_file",
        "description": "Create/overwrite file. Auto-creates parent directories. "
                    "USE: Save new content, generate files. "
                    "NOT: Targeted edits (use edit_file). "
                    "WARNING: Overwrites existing files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path within workspace. Examples: 'README.md', 'logs/debug.log'. Auto-creates parent dirs."
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write. Replaces existing content if file exists."
                }
            },
            "required": ["path", "content"]
        },
    }

def move_file_tool():
    return {
        "name": "move_file",
        "description": "Move/rename file or directory. "
                    "USE: Reorganize files, rename items. "
                    "NOT: Copy operations (use copy_file). "
                    "Auto-creates parent directories",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source file/directory path (must exist). Examples: 'document.txt', 'src/utils.js'."
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path (must not exist). Auto-creates parent dirs. Examples: 'renamed.txt', 'backup/document.txt'."
                }
            },
            "required": ["source", "destination"]
        },
    }

def copy_file_tool():
    return {
        "name": "copy_file",
        "description": "Copy file or directory to new location. "
                    "USE: Duplicate files, create backups, replicate structures. "
                    "NOT: Move operations (use move_file). "
                    "Recursive directory copying. Auto-creates parent directories",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source file/directory path (must exist). Examples: 'document.txt', 'src/utils.js'."
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path (must not exist). Auto-creates parent dirs. Examples: 'document.backup.txt', 'backup/document.txt'."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Copy directories recursively. If false and source is directory, operation fails. Default: true.",
                    "default": True
                }
            },
            "required": ["source", "destination"]
        },
    }

def search_files_tool():
    return {
        "name": "search_files",
        "description": "Find files/directories by name pattern. Recursive, case-insensitive. "
                    "USE: Locate files by extension, find items with specific names. "
                    "NOT: Content search (use search_code), single directory listing. "
                    "Shows tracked files in Git repos",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Name pattern (case-insensitive substring). Examples: '.js', 'test', 'config'."
                },
                "path": {
                    "type": "string",
                    "description": "Search root directory. Examples: '.', 'src'. Default: allowed directory."
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files/dirs (start with '.'). Default: false."
                }
            },
            "required": ["pattern"]
        },
    }

def get_file_info_tool():
    return {
        "name": "get_file_info",
        "description": "Get file metadata: size, timestamps, permissions, type. "
                    "USE: Check file properties without reading content. "
                    "NOT: Reading content (use read_file), directory listing. "
                    "RETURNS: Type, size, creation/modification times, permissions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File or directory path. Examples: 'README.md', 'src/components'."
                }
            },
            "required": ["path"]
        },
    }

def delete_file_tool():
    return {
        "name": "delete_file",
        "description": "Delete file or empty directory. "
                    "USE: Remove unwanted files, clean up temporary files. "
                    "NOT: Non-empty directories (will fail). "
                    "WARNING: Cannot be undone. Safety: only deletes empty directories",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File or empty directory path. Examples: 'temp.txt', 'empty-dir/'."
                }
            },
            "required": ["path"]
        },
    }

def edit_file_tool():
    return {
        "name": "edit_file",
        "description": "Targeted text replacement in files. "
            "CRITICAL: Use single call with multiple edits array for efficiency. "
            "USE: Modify specific parts while preserving rest. "
            "NOT: Complete rewrites (use write_file). "
            "RETURNS: Git-style diff with success/failure details",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Text file to edit. Examples: 'README.md', 'src/config.js'."
                },
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "oldText": {
                                "type": "string",
                                "description": "Text to find and replace. Include context for unique match."
                            },
                            "newText": {
                                "type": "string",
                                "description": "Replacement text. Empty string to delete."
                            }
                        },
                        "required": ["oldText", "newText"]
                    },
                    "description": "Array of edit objects with oldText/newText. Applied sequentially. Group all edits for same file."
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "partialMatch": {
                            "type": "boolean",
                            "description": "Enable fuzzy text matching. Uses confidenceThreshold (default 80%).",
                            "default": True
                        },
                        "confidenceThreshold": {
                            "type": "number",
                            "description": "Fuzzy match confidence (0.0-1.0). Higher = more exact. Default: 0.8.",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "default": 0.8
                        }
                    }
                }
            },
            "required": ["path", "edits"]
        }
    }

async def _read_single_file(path: str, offset: int = None, limit: int = None) -> List[TextContent]:
    """Helper function to read a single file with proper validation."""
    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(path):
        full_path = os.path.abspath(path)  # Just normalize the absolute path
    else:
        # For relative paths, join with allowed_directory
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")

    if not os.path.exists(full_path):
        raise ValueError(f"File does not exist: {full_path}")
    if not os.path.isfile(full_path):
        raise ValueError(f"Path is not a file: {full_path}")

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            # If we have offset/limit parameters, read only the specified lines
            if offset is not None or limit is not None:
                lines = f.readlines()

                # Determine start line - convert from 1-indexed to 0-indexed
                start_idx = 0
                if offset is not None:
                    start_idx = max(0, offset - 1)  # Convert 1-indexed to 0-indexed

                # Determine end line
                end_idx = len(lines)
                if limit is not None:
                    end_idx = min(len(lines), start_idx + limit)

                # Read only the specified range
                content = ''.join(lines[start_idx:end_idx])

                # Add summary information about the file before and after the selected range
                total_lines = len(lines)
                summary = []

                if start_idx > 0:
                    summary.append(f"[...{start_idx} lines before...]")

                if end_idx < total_lines:
                    summary.append(f"[...{total_lines - end_idx} lines after...]")

                if summary:
                    content = '\n'.join(summary) + '\n' + content

            else:
                # Read the entire file
                content = f.read()

            return [TextContent(
                type="text",
                text=content
            )]
    except UnicodeDecodeError:
        raise ValueError(f"File is not a text file or has unknown encoding: {full_path}")
    except PermissionError:
        raise ValueError(f"Permission denied reading file: {full_path}")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

async def handle_write_file(arguments: dict):
    """Handle writing content to a file."""
    path = arguments.get("path")
    content = arguments.get("content")

    if not path:
        raise ValueError("path must be provided")
    if content is None:
        raise ValueError("content must be provided")

    # Determine full path based on whether input is absolute or relative
    if os.path.isabs(path):
        full_path = os.path.abspath(path)  # Just normalize the absolute path
    else:
        # For relative paths, join with allowed_directory
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")

    try:
        # Create parent directories if they don't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write the file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return [TextContent(
            type="text",
            text=f"Successfully wrote to {path}"
        )]
    except Exception as e:
        raise ValueError(f"Error writing file: {str(e)}")

async def handle_read_file(arguments: dict):
    files = arguments.get("files")
    if not files:
        raise ValueError("files must be provided")
    if not isinstance(files, list):
        raise ValueError("files must be an array")
    if not files:
        raise ValueError("files array cannot be empty")

    # Validate each file entry
    for file_entry in files:
        if not isinstance(file_entry, dict):
            raise ValueError("each file entry must be an object")
        if "path" not in file_entry:
            raise ValueError("each file entry must have a path property")

    # Read each file with its own offset/limit
    results = []
    for file_entry in files:
        path = file_entry.get("path")
        offset = file_entry.get("offset")
        limit = file_entry.get("limit")

        try:
            # Add file path header first
            results.append(TextContent(
                type="text",
                text=f"\n==> {path} <==\n"
            ))
            # Then add file contents with specific offset/limit
            file_contents = await _read_single_file(path, offset, limit)
            results.extend(file_contents)
        except Exception as e:
            results.append(TextContent(
                type="text",
                text=f"Error: {str(e)}\n"
            ))

    return results

async def handle_move_file(arguments: dict):
    """Handle moving a file or directory to a new location."""
    source = arguments.get("source")
    destination = arguments.get("destination")

    if not source:
        raise ValueError("source must be provided")
    if not destination:
        raise ValueError("destination must be provided")

    # Determine full paths based on whether inputs are absolute or relative
    if os.path.isabs(source):
        full_source = os.path.abspath(source)
    else:
        full_source = os.path.abspath(os.path.join(state.allowed_directory, source))

    if os.path.isabs(destination):
        full_destination = os.path.abspath(destination)
    else:
        full_destination = os.path.abspath(os.path.join(state.allowed_directory, destination))

    # Security checks
    if not full_source.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Source path ({full_source}) must be within allowed directory")
    if not full_destination.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Destination path ({full_destination}) must be within allowed directory")

    # Validate source exists
    if not os.path.exists(full_source):
        raise ValueError(f"Source path does not exist: {source}")

    # Create parent directories of destination if they don't exist
    os.makedirs(os.path.dirname(full_destination), exist_ok=True)

    try:
        # Perform the move operation
        os.rename(full_source, full_destination)
        return [TextContent(
            type="text",
            text=f"Successfully moved {source} to {destination}"
        )]
    except OSError as e:
        raise ValueError(f"Error moving file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")

async def handle_copy_file(arguments: dict):
    """Handle copying a file or directory to a new location."""
    source = arguments.get("source")
    destination = arguments.get("destination")
    recursive = arguments.get("recursive", True)

    if not source:
        raise ValueError("source must be provided")
    if not destination:
        raise ValueError("destination must be provided")

    # Determine full paths based on whether inputs are absolute or relative
    if os.path.isabs(source):
        full_source = os.path.abspath(source)
    else:
        full_source = os.path.abspath(os.path.join(state.allowed_directory, source))

    if os.path.isabs(destination):
        full_destination = os.path.abspath(destination)
    else:
        full_destination = os.path.abspath(os.path.join(state.allowed_directory, destination))

    # Security checks
    if not full_source.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Source path ({full_source}) must be within allowed directory")
    if not full_destination.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Destination path ({full_destination}) must be within allowed directory")

    # Validate source exists
    if not os.path.exists(full_source):
        raise ValueError(f"Source path does not exist: {source}")

    # Check if destination already exists
    if os.path.exists(full_destination):
        raise ValueError(f"Destination already exists: {destination}")

    # Create parent directories of destination if they don't exist
    os.makedirs(os.path.dirname(full_destination), exist_ok=True)

    try:
        if os.path.isdir(full_source):
            if not recursive:
                raise ValueError(f"Cannot copy directory without recursive flag: {source}")
            # Copy directory recursively
            shutil.copytree(full_source, full_destination)
            return [TextContent(
                type="text",
                text=f"Successfully copied directory {source} to {destination}"
            )]
        else:
            # Copy file
            shutil.copy2(full_source, full_destination)
            return [TextContent(
                type="text",
                text=f"Successfully copied file {source} to {destination}"
            )]
    except Exception as e:
        raise ValueError(f"Error copying {source} to {destination}: {str(e)}")

async def handle_search_files(arguments: dict):
    """Handle searching for files matching a pattern."""
    pattern = arguments.get("pattern")
    start_path = arguments.get("path", ".")
    include_hidden = arguments.get("include_hidden", False)

    if not pattern:
        raise ValueError("pattern must be provided")

    # Determine full path for search start
    if os.path.isabs(start_path):
        full_start_path = os.path.abspath(start_path)
    else:
        full_start_path = os.path.abspath(os.path.join(state.allowed_directory, start_path))

    # Security check
    if not full_start_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_start_path}) must be within allowed directory")

    if not os.path.exists(full_start_path):
        raise ValueError(f"Start path does not exist: {start_path}")
    if not os.path.isdir(full_start_path):
        raise ValueError(f"Start path is not a directory: {start_path}")

    matches = []
    pattern = pattern.lower()  # Case-insensitive search

    # Try git ls-files first
    try:
        # First, check if this is a git repository and get tracked files
        result = subprocess.run(
            ['git', 'ls-files'],
            cwd=full_start_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Also get git directories (excluding .git itself)
        dirs_result = subprocess.run(
            ['git', 'ls-tree', '-d', '-r', '--name-only', 'HEAD'],
            cwd=full_start_path,
            capture_output=True,
            text=True,
            check=True
        )

        # Process git-tracked files
        files = result.stdout.splitlines()
        dirs = dirs_result.stdout.splitlines()

        # Process directories first
        for dir_path in dirs:
            if pattern in dir_path.lower():
                if include_hidden or not any(part.startswith('.') for part in dir_path.split(os.sep)):
                    matches.append(f"[DIR] {dir_path}")

        # Then process files
        for file_path in files:
            if pattern in file_path.lower():
                if include_hidden or not any(part.startswith('.') for part in file_path.split(os.sep)):
                    matches.append(f"[FILE] {file_path}")

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to regular directory walk if git is not available or not a git repository
        try:
            for root, dirs, files in os.walk(full_start_path):
                # Get paths relative to allowed directory
                rel_root = os.path.relpath(root, state.allowed_directory)

                # Skip hidden directories if not included
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]

                # Process directories
                for dir_name in dirs:
                    if pattern in dir_name.lower():
                        rel_path = os.path.join(rel_root, dir_name)
                        if include_hidden or not any(part.startswith('.') for part in rel_path.split(os.sep)):
                            matches.append(f"[DIR] {rel_path}")

                # Process files
                for file_name in files:
                    if pattern in file_name.lower():
                        rel_path = os.path.join(rel_root, file_name)
                        if include_hidden or not any(part.startswith('.') for part in rel_path.split(os.sep)):
                            matches.append(f"[FILE] {rel_path}")

        except Exception as e:
            raise ValueError(f"Error searching files: {str(e)}")

    # Sort matches for consistent output
    matches.sort()

    if not matches:
        return [TextContent(
            type="text",
            text="No matches found"
        )]

    return [TextContent(
        type="text",
        text="\n".join(matches)
    )]

async def handle_get_file_info(arguments: dict):
    """Handle getting detailed information about a file or directory."""
    path = arguments.get("path")
    if not path:
        raise ValueError("path must be provided")

    # Determine full path
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {path}")

    try:
        stat_info = os.stat(full_path)

        # Format file type
        file_type = "directory" if os.path.isdir(full_path) else "file"

        # Format permissions in octal
        perms = stat.filemode(stat_info.st_mode)

        info = f"""Type: {file_type}
Size: {stat_info.st_size:,} bytes
Created: {datetime.fromtimestamp(stat_info.st_ctime).isoformat()}
Modified: {datetime.fromtimestamp(stat_info.st_mtime).isoformat()}
Accessed: {datetime.fromtimestamp(stat_info.st_atime).isoformat()}
Permissions: {perms}"""

        return [TextContent(type="text", text=info)]

    except Exception as e:
        raise ValueError(f"Error getting file info: {str(e)}")

async def handle_delete_file(arguments: dict):
    """Handle deleting a file or empty directory."""
    path = arguments.get("path")
    if not path:
        raise ValueError("path must be provided")

    # Determine full path
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    # Security check
    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory")

    if not os.path.exists(full_path):
        raise ValueError(f"Path does not exist: {path}")

    try:
        if os.path.isdir(full_path):
            # Check if directory is empty
            if os.listdir(full_path):
                raise ValueError(f"Cannot delete non-empty directory: {path}")
            os.rmdir(full_path)
            return [TextContent(
                type="text",
                text=f"Successfully deleted empty directory: {path}"
            )]
        else:
            os.remove(full_path)
            return [TextContent(
                type="text",
                text=f"Successfully deleted file: {path}"
            )]
    except Exception as e:
        raise ValueError(f"Error deleting {path}: {str(e)}")

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving indentation."""
    lines = text.splitlines()
    normalized_lines = []

    for line in lines:
        # Preserve leading whitespace
        indent = re.match(r'^\s*', line).group(0)
        # Normalize other whitespace
        content = re.sub(r'\s+', ' ', line.lstrip())
        normalized_lines.append(f"{indent}{content}")

    return '\n'.join(normalized_lines)

def create_unified_diff(original: str, modified: str, filepath: str) -> str:
    """Create a unified diff between two texts."""
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f'a/{filepath}',
        tofile=f'b/{filepath}',
        n=0,  # No context lines needed for single line changes
        lineterm=''  # Don't add newlines here
    )

    # Join lines with single newlines and strip any extra whitespace
    return '\n'.join(line.rstrip() for line in diff)

def find_substring_position(content: str, pattern: str) -> tuple[int, int]:
    """Find the position of a substring in content."""
    pos = content.find(pattern)
    if pos >= 0:
        return pos, pos + len(pattern)
    return -1, -1

def find_best_match(content: str, pattern: str, partial_match: bool = True) -> tuple[int, int, float]:
    """Find the best matching position for a pattern in content."""
    if not partial_match:
        # Exact matching only
        pos = content.find(pattern)
        if pos >= 0:
            return pos, pos + len(pattern), 1.0
        return -1, -1, 0.0

    # Try exact substring match first
    start, end = find_substring_position(content, pattern)
    if start >= 0:
        return start, end, 1.0

    # If no exact substring match, try line-based fuzzy matching

    # Split into lines for line-based matching
    content_lines = content.splitlines()
    pattern_lines = pattern.splitlines()

    best_score = 0.0
    best_start = -1
    best_end = -1

    for i in range(len(content_lines) - len(pattern_lines) + 1):
        # Compare each potential match position
        window = content_lines[i:i + len(pattern_lines)]
        score = sum(difflib.SequenceMatcher(None, a, b).ratio()
                   for a, b in zip(window, pattern_lines)) / len(pattern_lines)

        if score > best_score:
            best_score = score
            best_start = sum(len(line) + 1 for line in content_lines[:i])
            best_end = best_start + sum(len(line) + 1 for line in window)

    return best_start, best_end, best_score

async def apply_file_edits(file_path: str, edits: List[dict], options: dict = None) -> tuple[str, bool, int, int]:
    """Apply edits to a file with optional formatting and return diff.
    
    Returns:
        tuple: (result_text, has_changes, successful_edits, failed_edits)
    """
    # Set default options
    options = options or {}
    partial_match = options.get('partialMatch', True)
    # Use 0.8 confidence threshold to prevent false positives while allowing reasonable fuzzy matches
    confidence_threshold = options.get('confidenceThreshold', 0.8)

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Track modifications
    modified_content = content
    failed_matches = []
    successful_edits = []

    # Apply each edit
    for edit_idx, edit in enumerate(edits):
        old_text = edit['oldText']
        new_text = edit['newText']

        # Use original text for matching
        search_text = old_text
        working_content = modified_content

        # Find best match
        start, end, confidence = find_best_match(working_content, search_text, partial_match)

        if confidence >= confidence_threshold:
            # Fix indentation while preserving relative structure
            if start >= 0:
                # Get the indentation of the first line of the matched text
                base_indent = re.match(r'^\s*', modified_content[start:].splitlines()[0]).group(0)

                # Split the new text into lines
                new_lines = new_text.splitlines()

                # If there are multiple lines, adjust indentation while preserving structure
                if len(new_lines) > 1:
                    # Find the minimum indentation level in the new text (ignoring empty lines)
                    non_empty_lines = [line for line in new_lines if line.strip()]
                    if non_empty_lines:
                        min_indent_length = min(len(re.match(r'^\s*', line).group(0)) for line in non_empty_lines)
                    else:
                        min_indent_length = 0

                    # Process each line to preserve relative indentation
                    processed_lines = []
                    for line in new_lines:
                        if line.strip():  # If line is not empty
                            # Get current indentation
                            current_indent = re.match(r'^\s*', line).group(0)
                            # Calculate relative indentation
                            relative_indent = len(current_indent) - min_indent_length
                            # Apply base indent plus relative indent
                            processed_lines.append(base_indent + ' ' * relative_indent + line.lstrip())
                        else:
                            # For empty lines, just use base indentation
                            processed_lines.append(base_indent)

                    replacement = '\n'.join(processed_lines)
                else:
                    # Single line - just use base indentation
                    replacement = base_indent + new_text.lstrip()
            else:
                replacement = new_text

            # Apply the edit
            modified_content = modified_content[:start] + replacement + modified_content[end:]
            successful_edits.append({
                'index': edit_idx,
                'oldText': old_text,
                'newText': new_text,
                'confidence': confidence
            })
        else:
            failed_matches.append({
                'index': edit_idx,
                'oldText': old_text,
                'newText': new_text,
                'confidence': confidence,
                'bestMatch': working_content[start:end] if start >= 0 and end > start else None
            })

    # Create diff
    diff = create_unified_diff(content, modified_content, os.path.basename(file_path))
    has_changes = modified_content != content

    # CRITICAL FIX: Write changes even if some edits failed (partial success)
    # This prevents the infinite retry loop
    if has_changes:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

    # Build comprehensive result message
    result_parts = []
    
    # Summary
    total_edits = len(edits)
    successful_count = len(successful_edits)
    failed_count = len(failed_matches)
    
    result_parts.append(f'=== Edit Summary ===')
    result_parts.append(f'Total edits: {total_edits}')
    result_parts.append(f'Successful: {successful_count}')
    result_parts.append(f'Failed: {failed_count}')
    result_parts.append(f'File modified: {has_changes}')
    result_parts.append('')
    
    # Failed matches details
    if failed_matches:
        result_parts.append('=== Failed Matches ===')
        for failed in failed_matches:
            result_parts.append(f"Edit #{failed['index'] + 1}: Confidence {failed['confidence']:.2f}")
            result_parts.append(f"  Searched for: {repr(failed['oldText'][:100])}...")
            if failed['bestMatch']:
                result_parts.append(f"  Best match: {repr(failed['bestMatch'][:100])}...")
            result_parts.append('')
    
    # Successful edits
    if successful_edits:
        result_parts.append('=== Successful Edits ===')
        for success in successful_edits:
            result_parts.append(f"Edit #{success['index'] + 1}: Confidence {success['confidence']:.2f}")
        result_parts.append('')
    
    # Diff
    if diff.strip():
        result_parts.append('=== Diff ===')
        result_parts.append(diff)
    else:
        result_parts.append('=== No Changes ===')
        result_parts.append('No modifications were made to the file.')
    
    return '\n'.join(result_parts), has_changes, successful_count, failed_count

async def handle_edit_file(arguments: dict):
    """Handle editing a file with pattern matching and formatting."""
    path = arguments.get("path")
    edits = arguments.get("edits")
    options = arguments.get("options", {})

    if not path:
        raise ValueError("path must be provided")
    if not edits or not isinstance(edits, list):
        raise ValueError("edits must be a non-empty list")

    # Validate edits structure
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("each edit must be an object")
        if 'oldText' not in edit or 'newText' not in edit:
            raise ValueError("each edit must have oldText and newText properties")

    # Determine full path and validate
    if os.path.isabs(path):
        full_path = os.path.abspath(path)
    else:
        full_path = os.path.abspath(os.path.join(state.allowed_directory, path))

    if not full_path.startswith(state.allowed_directory):
        raise ValueError(f"Access denied: Path ({full_path}) must be within allowed directory ({state.allowed_directory})")

    try:
        result_text, has_changes, successful_count, failed_count = await apply_file_edits(full_path, edits, options)
        
        # CRITICAL FIX: Raise an exception only if ALL edits failed AND no changes were made
        # This prevents silent failures that cause infinite retry loops
        if failed_count > 0 and successful_count == 0:
            raise ValueError(f"All {failed_count} edits failed to match. No changes were made to the file. Check the 'oldText' patterns and ensure they match the file content exactly.")
        
        return [TextContent(type="text", text=result_text)]
    except Exception as e:
        raise ValueError(f"Error editing file: {str(e)}")

