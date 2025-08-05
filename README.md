[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/skydeckai-code-badge.png)](https://mseep.ai/app/skydeckai-code)

# SkyDeckAI Code

An MCP server that provides a comprehensive set of tools for AI-driven development workflows. Features include file system operations, code analysis using tree-sitter for multiple programming languages, code execution, web content fetching with HTML-to-markdown conversion, multi-engine web search, code content searching, and system information retrieval. Designed to enhance AI's capability to assist in software development tasks by providing direct access to both local and remote resources.

# Formerly Known As MCP-Server-AIDD

This mcp server was formerly known as `mcp-server-aidd`. It was renamed to `skydeckai-code` to credit the team at [SkyDeck.ai](https://skydeck.ai) with creating this application along with [East Agile](https://eastagile.com). But more importantly we realized that the term AI Driven Development (AIDD) was just not catching on. People did not understand at a glance what it was about. And nor did LLMs. "Code" was far more intuitive. And linguistically intuitive is important in the world of agentic AI.

[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/fe7a40fd-30c1-4767-84f9-d33bf997497e)

## Installation

```bash
# Using uvx
uvx skydeckai-code
```

## Claude Desktop Setup

Add to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "skydeckai-code": {
            "command": "uvx",
            "args": ["skydeckai-code"]
        }
    }
}
```

## SkyDeck AI Helper App

If you're using MseeP AI Helper app, you can search for "SkyDeckAI Code" and install it.

![MseeP AI Helper App](/screenshots/mseep_ai_helper.png)

## Key Features

-   File system operations (read, write, edit, move, copy, delete)
-   Directory management and traversal
-   Multi-language code analysis using tree-sitter
-   Code content searching with regex pattern matching
-   Multi-language code execution with safety measures
-   Web content fetching from APIs and websites with HTML-to-markdown conversion
-   Multi-engine web search with reliable fallback mechanisms
-   Batch operations for parallel and serial tool execution
-   Security controls with configurable workspace boundaries
-   Screenshot and screen context tools
-   Image handling tools

## Available Tools (29)

| Category         | Tool Name                  | Description                                  |
| ---------------- | -------------------------- | -------------------------------------------- |
| **File System**  | `get_allowed_directory`    | Get the current working directory path       |
|                  | `update_allowed_directory` | Change the working directory                 |
|                  | `create_directory`         | Create a new directory or nested directories |
|                  | `write_file`               | Create or overwrite files with auto-directory creation |
|                  | `edit_file`                | Make targeted text replacements with diff output |
|                  | `read_file`                | Read file contents with optional line range support |
|                  | `list_directory`           | Get listing of files and directories         |
|                  | `move_file`                | Move or rename files/directories with auto-directory creation |
|                  | `copy_file`                | Copy files or directories with recursive support |
|                  | `search_files`             | Find files by name pattern (recursive, case-insensitive) |
|                  | `delete_file`              | Delete files or empty directories safely     |
|                  | `get_file_info`            | Get file metadata without reading content    |
|                  | `directory_tree`           | Get a recursive tree view of directories     |
|                  | `read_image_file`          | Read an image file as base64 data            |
| **Code Tools**   | `codebase_mapper`          | Analyze code structure across files          |
|                  | `search_code`              | Search file contents using regex patterns |
|                  | `execute_code`             | Run code in various languages                |
|                  | `execute_shell_script`     | Run shell/bash scripts                       |
| **Web Tools**    | `web_fetch`                | Get content from a URL                       |
|                  | `web_search`               | Perform a web search                         |
| **Screen Tools** | `capture_screenshot`       | Take a screenshot of screen or window        |
|                  | `get_active_apps`          | List running applications                    |
|                  | `get_available_windows`    | List all open windows                        |
| **System**       | `get_system_info`          | Get detailed system information              |
| **Utility**      | `batch_tools`              | Run multiple tool operations together        |
|                  | `think`                    | Document reasoning without making changes    |
| **Todo**         | `todo_read`                | Read current workspace todo list |
|                  | `todo_write`               | Create/replace todo list for workspace workflow |
|                  | `todo_update`              | Update todo status during task execution     |

## Detailed Tool Documentation

### Basic File Operations

| Tool          | Parameters                                                 | Returns                                       |
| ------------- | ---------------------------------------------------------- | --------------------------------------------- |
| read_file     | files: [{path: string, offset?: integer, limit?: integer}] | File content (single or multiple files)       |
| write_file    | path: string, content: string                              | Success confirmation                          |
| move_file     | source: string, destination: string                        | Success confirmation                          |
| copy_file     | source: string, destination: string, recursive?: boolean   | Success confirmation                          |
| delete_file   | path: string                                               | Success confirmation                          |
| get_file_info | path: string                                               | File metadata (size, timestamps, permissions) |

### Complex File Operations

#### edit_file

Targeted text replacement in files with efficient batch editing:

```json
{
    "path": "src/main.py",
    "edits": [
        {
            "oldText": "def old_function():",
            "newText": "def new_function():"
        }
    ],
    "options": {
        "partialMatch": true,
        "confidenceThreshold": 0.8
    }
}
```

Returns: Git-style diff with success/failure details for each edit.

### Directory Operations

| Tool                     | Parameters                                               | Returns                        |
| ------------------------ | -------------------------------------------------------- | ------------------------------ |
| get_allowed_directory    | none                                                     | Current allowed directory path |
| update_allowed_directory | directory: string (absolute path)                        | Success confirmation           |
| list_directory           | path: string                                             | Directory contents list        |
| create_directory         | path: string                                             | Success confirmation           |
| search_files             | pattern: string, path?: string, include_hidden?: boolean | Matching files list            |

The `search_files` tool finds files by name pattern (recursive, case-insensitive), while the `search_code` tool searches file contents using regex patterns. Use `search_files` for locating files by extension or name, and `search_code` for finding specific code patterns, function definitions, or variable usage within files.

#### directory_tree

Generates complete directory structure:

```json
{
    "path": "src",
    "include_hidden": false
}
```

Returns: JSON tree structure of directory contents.

### Code Analysis

#### codebase_mapper

Analyzes source code structure:

```json
{
    "path": "src"
}
```

Returns:

-   Classes and their methods
-   Functions and parameters
-   Module structure
-   Code organization statistics
-   Inheritance relationships

Supported Languages:

-   Python (.py)
-   JavaScript (.js/.jsx, .mjs, .cjs)
-   TypeScript (.ts/.tsx)
-   Java (.java)
-   C++ (.cpp, .hpp, .cc)
-   Ruby (.rb, .rake)
-   Go (.go)
-   Rust (.rs)
-   PHP (.php)
-   C# (.cs)
-   Kotlin (.kt, .kts)

#### search_code

Regex-based content search:

```json
{
    "patterns": ["function\\s+\\w+", "class\\s+\\w+"],
    "include": "*.js",
    "exclude": "node_modules/**",
    "max_results": 50,
    "case_sensitive": false,
    "path": "src",
    "include_hidden": false
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| patterns | array of strings | Yes | Regular expression patterns to search for in file contents |
| include | string | No | File inclusion pattern (glob syntax, default: "*") |
| exclude | string | No | File exclusion pattern (glob syntax, default: "") |
| max_results | integer | No | Maximum results to return per pattern (default: 100) |
| case_sensitive | boolean | No | Case-sensitive search (default: false) |
| path | string | No | Base directory to search from (default: ".") |
| include_hidden | boolean | No | Include hidden files (.env, .config, etc.) (default: false) |

**Returns:**
Matching lines with file paths and line numbers, sorted by file modification time (newest first).

This tool uses ripgrep when available for superior performance, with a Python fallback. Ideal for finding function definitions, variable usage, imports, or any code patterns across your codebase.

### System Information

| Tool            | Parameters | Returns                      |
| --------------- | ---------- | ---------------------------- |
| get_system_info | none       | Comprehensive system details |

Returns:

```json
{
  "working_directory": "/path/to/project",
  "system": {
    "os", "os_version", "architecture", "python_version"
  },
  "wifi_network": "MyWiFi",
  "cpu": {
    "physical_cores", "logical_cores", "total_cpu_usage"
  },
  "memory": { "total", "available", "used_percentage" },
  "disk": { "total", "free", "used_percentage" },
  "mac_details": {  // Only present on macOS
    "model": "Mac mini",
    "chip": "Apple M2",
    "serial_number": "XXX"
  }
}
```

Provides essential system information in a clean, readable format.

### Screen Context and Image Tools

#### get_active_apps

Returns a list of currently active applications on the user's system.

```json
{
    "with_details": true
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| with_details | boolean | No | Whether to include additional details about each application (default: false) |

**Returns:**

```json
{
    "success": true,
    "platform": "macos",
    "app_count": 12,
    "apps": [
        {
            "name": "Firefox",
            "has_windows": true,
            "window_count": 3,
            "visible_windows": [
                { "name": "GitHub - Mozilla Firefox", "width": 1200, "height": 800 }
            ]
        },
        {
            "name": "VSCode",
            "has_windows": true
        }
    ]
}
```

This tool provides valuable context about applications currently running on the user's system, which can help with providing more relevant assistance.

#### get_available_windows

Returns detailed information about all available windows currently displayed on the user's screen.

```json
{}
```

**Returns:**

```json
{
    "success": true,
    "platform": "macos",
    "count": 8,
    "windows": [
        {
            "id": 42,
            "title": "Document.txt - Notepad",
            "app": "Notepad",
            "visible": true
        },
        {
            "title": "Terminal",
            "app": "Terminal",
            "visible": true,
            "active": true
        }
    ]
}
```

This tool helps understand what's visible on the user's screen and can be used for context-aware assistance.

#### capture_screenshot

Captures a screenshot of the user's screen or a specific window.

```json
{
    "output_path": "screenshots/capture.png",
    "capture_mode": {
        "type": "named_window",
        "window_name": "Visual Studio Code"
    }
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| output_path | string | No | Path where the screenshot should be saved (default: generated path) |
| capture_mode | object | No | Specifies what to capture |
| capture_mode.type | string | No | Type of screenshot: 'full', 'active_window', or 'named_window' (default: 'full') |
| capture_mode.window_name | string | No | Name of window to capture (required when type is 'named_window') |

**Returns:**

```json
{
    "success": true,
    "path": "/path/to/screenshots/capture.png"
}
```

This tool captures screenshots for visualization, debugging, or context-aware assistance.

#### read_image_file

Reads an image file from the file system and returns its contents as a base64-encoded string.

```json
{
    "path": "images/logo.png"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| path | string | Yes | Path to the image file to read |
| max_size | integer | No | Maximum file size in bytes (default: 100MB) |

**Returns:**
Base64-encoded image data that can be displayed or processed.

This tool supports common image formats like PNG, JPEG, GIF, and WebP, and automatically resizes images for optimal viewing.

### Web Tools

#### web_fetch

Fetches content from a URL and optionally saves it to a file.

```json
{
    "url": "https://api.github.com/users/octocat",
    "headers": {
        "Accept": "application/json"
    },
    "timeout": 15,
    "save_to_file": "downloads/octocat.json",
    "convert_html_to_markdown": true
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| url | string | Yes | URL to fetch content from (http/https only) |
| headers | object | No | Optional HTTP headers to include in the request |
| timeout | integer | No | Maximum time to wait for response (default: 10s) |
| save_to_file | string | No | Path to save response content (within allowed directory) |
| convert_html_to_markdown | boolean | No | When true, converts HTML content to markdown for better readability (default: true) |

**Returns:**
Response content as text with HTTP status code and size information. For binary content, returns metadata and saves to file if requested. When convert_html_to_markdown is enabled, HTML content is automatically converted to markdown format for better readability.

This tool can be used to access web APIs, fetch documentation, or download content from the web while respecting size limits (10MB max) and security constraints.

#### web_search

Performs a robust web search using multiple search engines and returns concise, relevant results.

```json
{
    "query": "latest python release features",
    "num_results": 8,
    "convert_html_to_markdown": true,
    "search_engine": "bing"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| query | string | Yes | The search query to process. Be specific for better results. |
| num_results | integer | No | Maximum number of search results to return (default: 10, max: 20) |
| convert_html_to_markdown | boolean | No | When true, content will be converted from HTML to markdown for better readability (default: true) |
| search_engine | string | No | Specifies which search engine to use: "auto" (default), "bing", or "duckduckgo" |

**Returns:**
A list of search results formatted in markdown, including titles, URLs, and snippets for each result. Results are deduplicated and organized hierarchically for easy reading.

This tool uses a multi-engine approach that tries different search engines with various parsing strategies to ensure reliable results. You can specify a preferred engine, but some engines may block automated access, in which case the tool will fall back to alternative engines when "auto" is selected.

### Utility Tools

#### batch_tools

Execute multiple tool invocations in a single request with parallel execution when possible.

```json
{
    "description": "Setup new project",
    "sequential": true,
    "invocations": [
        {
            "tool": "create_directory",
            "arguments": {
                "path": "src"
            }
        },
        {
            "tool": "write_file",
            "arguments": {
                "path": "README.md",
                "content": "# New Project\n\nThis is a new project."
            }
        },
        {
            "tool": "execute_shell_script",
            "arguments": {
                "script": "git init"
            }
        }
    ]
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| description | string | Yes | Short description of the batch operation |
| sequential | boolean | No | Whether to run tools in sequence (default: false) |
| invocations | array | Yes | List of tool invocations to execute |
| invocations[].tool | string | Yes | Name of the tool to invoke |
| invocations[].arguments | object | Yes | Arguments for the specified tool |

**Returns:**
Combined results from all tool invocations, grouped by tool with success/error status for each. Results are presented in the original invocation order with clear section headers.

This tool provides efficient execution of multiple operations in a single request. When `sequential` is false (default), tools are executed in parallel for better performance. When `sequential` is true, tools are executed in order, and if any tool fails, execution stops.

**IMPORTANT**: All tools in the batch execute in the same working directory context. If a tool creates a directory and a subsequent tool needs to work inside that directory, you must either:

1. Use paths relative to the current working directory (e.g., "project/src" rather than just "src"), or
2. Include an explicit tool invocation to change directories using `update_allowed_directory`

#### think

A tool for complex reasoning and brainstorming without making changes to the repository.

```json
{
    "thought": "Let me analyze the performance issue in the codebase:\n\n## Root Cause Analysis\n\n1. The database query is inefficient because:\n   - It doesn't use proper indexing\n   - It fetches more columns than needed\n   - The JOIN operation is unnecessarily complex\n\n## Potential Solutions\n\n1. **Add database indexes**:\n   - Create an index on the user_id column\n   - Create a composite index on (created_at, status)\n\n2. **Optimize the query**:\n   - Select only necessary columns\n   - Rewrite the JOIN using a subquery\n   - Add LIMIT clause for pagination\n\n3. **Add caching layer**:\n   - Cache frequent queries using Redis\n   - Implement cache invalidation strategy\n\nAfter weighing the options, solution #2 seems to be the simplest to implement with the highest impact."
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| thought | string | Yes | Your detailed thoughts, analysis or reasoning process |

**Returns:**
Your thoughts formatted as markdown, with a note indicating this was a thinking exercise.

This tool is useful for thinking through complex problems, brainstorming solutions, or laying out implementation plans without making any actual changes. It's a great way to document your reasoning process, evaluate different approaches, or plan out a multi-step strategy before taking action.

### Code Execution

#### execute_code

Executes code in various programming languages with safety measures and restrictions.

```json
{
    "language": "python",
    "code": "print('Hello, World!')",
    "timeout": 5
}
```

**Supported Languages:**

-   Python (python3)
-   JavaScript (Node.js)
-   Ruby
-   PHP
-   Go
-   Rust

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| language | string | Yes | Programming language to use |
| code | string | Yes | Code to execute |
| timeout | integer | No | Maximum execution time (default: 5s) |

**Requirements:**

-   Respective language runtimes must be installed
-   Commands must be available in system PATH
-   Proper permissions for temporary file creation

⚠️ **Security Warning:**
This tool executes arbitrary code on your system. Always:

1. Review code thoroughly before execution
2. Understand the code's purpose and expected outcome
3. Never execute untrusted code
4. Be aware of potential system impacts
5. Monitor execution output

#### execute_shell_script

Executes shell scripts (bash/sh) with safety measures and restrictions.

```json
{
    "script": "echo \"Current directory:\" && pwd",
    "timeout": 300
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|---------|----------|---------------------------------------|
| script | string | Yes | Shell script to execute |
| timeout | integer | No | Maximum execution time (default: 300s, max: 600s) |

**Features:**

-   Uses /bin/sh for maximum compatibility across systems
-   Executes within the allowed directory
-   Separate stdout and stderr output
-   Proper error handling and timeout controls

⚠️ **Security Warning:**
This tool executes arbitrary shell commands on your system. Always:

1. Review the script thoroughly before execution
2. Understand the script's purpose and expected outcome
3. Never execute untrusted scripts
4. Be aware of potential system impacts
5. Monitor execution output

### Todo Tools

The todo tools provide mandatory workspace-bound task management for structured development workflows. Each workspace maintains isolated todo context, and todo checking is required before file operations.

#### todo_read

**CRITICAL**: Must be called first before any file/directory operations. Returns the active todo list for the current workspace.

```json
{}
```

**Returns:**
```json
{
  "todos": [
    {
      "id": "abc123",
      "content": "Implement user authentication",
      "status": "in_progress",
      "metadata": {
        "custom_key": "custom_value"
      },
      "created_at": "2023-10-01T10:00:00Z",
      "updated_at": "2023-10-01T11:30:00Z"
    }
  ],
  "count": 1,
  "workspace": "/path/to/workspace"
}
```

#### todo_write

Create or replace the complete todo list when no active todos exist. Triggered after `todo_read` returns empty or when starting new work.

```json
{
  "todos": [
    {
      "id": "task1",
      "content": "Set up database schema",
      "status": "pending"
    },
    {
      "id": "task2", 
      "content": "Create API endpoints",
      "status": "pending",
      "metadata": {
        "custom_key": "custom_value"
      }
    }
  ]
}
```

**Workflow Protocol:**
1. Call `todo_read` first
2. If empty → call `todo_write` 
3. Then proceed with file operations
4. Only one task "in_progress" at a time
5. Tasks execute sequentially in array order

#### todo_update

Update todo status during file operations. Required after each task completion to maintain workspace integrity.

```json
{
  "todo_id": "task1",
  "updates": {
    "status": "in_progress",
    "metadata": {
        "new_key": "new_value"
    }
  }
}
```

**Returns:**
```json
{
  "success": true,
  "updated_todo": {
    "id": "task1",
    "content": "Set up database schema",
    "status": "in_progress",
    "updated_at": "2023-10-01T12:00:00Z",
    "metadata": {
        "new_key": "new_value"
    }
  },
  "counts": {
    "pending": 1,
    "in_progress": 1,
    "completed": 0,
    "total": 2
  },
  "workspace": "/path/to/workspace"
}
```

**Critical**: Todo status must reflect actual work progress. Update after every file operation to maintain workspace protocol compliance.

## Configuration

Configuration file: `~/.skydeckai_code/config.json`

```json
{
    "allowed_directory": "/path/to/workspace"
}
```

## Debugging

Use MCP Inspector for debugging:

```bash
npx @modelcontextprotocol/inspector run
```

## Security

-   Operations restricted to configured allowed directory
-   Path traversal prevention
-   File permission preservation
-   Safe operation handling

## Upcoming Features

-   GitHub tools:
    -   PR Description Generator
    -   Code Review
    -   Actions Manager
-   Pivotal Tracker tools:
    -   Story Generator
    -   Story Manager

## Development Status

Currently in active development. Features and API may change.

## License

Apache License 2.0 - see [LICENSE](LICENSE)

[![Star History Chart](https://api.star-history.com/svg?repos=skydeckai/skydeckai-code&type=Date)](https://www.star-history.com/#skydeckai/skydeckai-code&Date)
