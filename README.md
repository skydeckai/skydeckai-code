[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/skydeckai-code-badge.png)](https://mseep.ai/app/skydeckai-code)

# SkyDeckAI Code

An MCP server that provides a comprehensive set of tools for AI-driven development workflows. Features include file system operations, code analysis using tree-sitter for multiple programming languages, code execution, web content fetching with HTML-to-markdown conversion, multi-engine web search, code content searching, and system information retrieval. Designed to enhance AI's capability to assist in software development tasks by providing direct access to both local and remote resources.

# Formerly Known As MCP-Server-AIDD

This mcp server was formerly known as `mcp-server-aidd`. It was renamed to `skydeckai-code` to credit the team at [SkyDeck.ai](https://skydeck.ai) with creating this application along with [East Agile](https://eastagile.com). But more importantly we realized that the term AI Driven Development (AIDD) was just not catching on. People did not understand at a glance what it was about. And nor did LLMs. "Code" was far more intuitive. And linguistically intuitive is important in the world of agentic AI.

<a href="https://glama.ai/mcp/servers/mpixtij6se"><img width="380" height="200" src="https://glama.ai/mcp/servers/mpixtij6se/badge" alt="AiDD Server MCP server" /></a>

## Installation

```bash
# Using pip
pip install skydeckai-code
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

If you're using SkyDeck AI Helper app, you can search for "SkyDeckAI Code" and install it.

![SkyDeck AI Helper App](/screenshots/skydeck_ai_helper.png)

## Key Features

-   File system operations (read, write, edit, move, copy, delete)
-   Directory management and traversal
-   Multi-language code analysis using tree-sitter
-   Code content searching with regex pattern matching
-   Multi-language code execution with safety measures
-   GitHub integration for pull request management and code reviews
-   Web content fetching from APIs and websites with HTML-to-markdown conversion
-   Multi-engine web search with reliable fallback mechanisms
-   Batch operations for parallel and serial tool execution
-   Security controls with configurable workspace boundaries
-   Screenshot and screen context tools
-   Image handling tools

## Available Tools (29)

| Category         | Tool Name                      | Description                                  |
| ---------------- | ------------------------------ | -------------------------------------------- |
| **File System**  | `get_allowed_directory`        | Get the current working directory path       |
|                  | `update_allowed_directory`     | Change the working directory                 |
|                  | `create_directory`             | Create a new directory or nested directories |
|                  | `write_file`                   | Create or overwrite a file with new content  |
|                  | `edit_file`                    | Make line-based edits to a text file         |
|                  | `read_file`                    | Read the contents of one or more files       |
|                  | `list_directory`               | Get listing of files and directories         |
|                  | `move_file`                    | Move or rename a file or directory           |
|                  | `copy_file`                    | Copy a file or directory to a new location   |
|                  | `search_files`                 | Search for files matching a name pattern     |
|                  | `delete_file`                  | Delete a file or empty directory             |
|                  | `get_file_info`                | Get detailed file metadata                   |
|                  | `directory_tree`               | Get a recursive tree view of directories     |
|                  | `read_image_file`              | Read an image file as base64 data            |
| **Code Tools**   | `codebase_mapper`              | Analyze code structure across files          |
|                  | `search_code`                  | Find text patterns in code files             |
|                  | `execute_code`                 | Run code in various languages                |
|                  | `execute_shell_script`         | Run shell/bash scripts                       |
| **GitHub**       | `list_pull_requests`           | List and filter repository pull requests     |
|                  | `create_pull_request_review`   | Create a review for a pull request           |
|                  | `get_pull_request_files`       | Get files changed in a pull request          |
| **Web Tools**    | `web_fetch`                    | Get content from a URL                       |
|                  | `web_search`                   | Perform a web search                         |
| **Screen Tools** | `capture_screenshot`           | Take a screenshot of screen or window        |
|                  | `get_active_apps`              | List running applications                    |
|                  | `get_available_windows`        | List all open windows                        |
| **System**       | `get_system_info`              | Get detailed system information              |
| **Utility**      | `batch_tools`                  | Run multiple tool operations together        |
|                  | `think`                        | Document reasoning without making changes    |

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

**CLI Usage:**

```bash
# Read entire file
skydeckai-code-cli --tool read_file --args '{"files": [{"path": "src/main.py"}]}'

# Read 10 lines starting from line 20
skydeckai-code-cli --tool read_file --args '{"files": [{"path": "src/main.py", "offset": 20, "limit": 10}]}'

# Read from line 50 to the end of the file
skydeckai-code-cli --tool read_file --args '{"files": [{"path": "src/main.py", "offset": 50}]}'

# Read multiple files with different line ranges
skydeckai-code-cli --tool read_file --args '{"files": [
  {"path": "src/main.py", "offset": 1, "limit": 10},
  {"path": "README.md"}
]}'

# Write file
skydeckai-code-cli --tool write_file --args '{"path": "output.txt", "content": "Hello World"}'

# Copy file or directory
skydeckai-code-cli --tool copy_file --args '{"source": "config.json", "destination": "config.backup.json"}'

# Get file info
skydeckai-code-cli --tool get_file_info --args '{"path": "src/main.py"}'
```

### Complex File Operations

#### edit_file

Pattern-based file editing with preview support:

```json
{
    "path": "src/main.py",
    "edits": [
        {
            "oldText": "def old_function():",
            "newText": "def new_function():"
        }
    ],
    "dryRun": false,
    "options": {
        "partialMatch": true
    }
}
```

Returns: Diff of changes or preview in dry run mode.

### Directory Operations

| Tool                     | Parameters                                               | Returns                        |
| ------------------------ | -------------------------------------------------------- | ------------------------------ |
| get_allowed_directory    | none                                                     | Current allowed directory path |
| update_allowed_directory | directory: string (absolute path)                        | Success confirmation           |
| list_directory           | path: string                                             | Directory contents list        |
| create_directory         | path: string                                             | Success confirmation           |
| search_files             | pattern: string, path?: string, include_hidden?: boolean | Matching files list            |

The `search_files` tool searches for files by name pattern, while the `search_code` tool searches within file contents using regex. Use `search_files` when looking for files with specific names or extensions, and `search_code` when searching for specific text patterns inside files.

#### directory_tree

Generates complete directory structure:

```json
{
    "path": "src",
    "include_hidden": false
}
```

Returns: JSON tree structure of directory contents.

**CLI Usage:**

```bash
# List directory
skydeckai-code-cli --tool list_directory --args '{"path": "."}'

# Search for Python files
skydeckai-code-cli --tool search_files --args '{"pattern": ".py", "path": "src"}'
```

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

**CLI Usage:**

```bash
# Map the entire codebase structure
skydeckai-code-cli --tool codebase_mapper --args '{"path": "."}'

# Map only the source directory
skydeckai-code-cli --tool codebase_mapper --args '{"path": "src"}'

# Map a specific component or module
skydeckai-code-cli --tool codebase_mapper --args '{"path": "src/components"}'
```

#### search_code

Fast content search tool using regular expressions:

```json
{
    "patterns": ["function\\s+\\w+", "class\\s+\\w+"],
    "include": "*.js",
    "exclude": "node_modules/**",
    "max_results": 50,
    "case_sensitive": false,
    "path": "src"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| patterns | array of strings | Yes | List of regular expression patterns to search for in file contents |
| include | string | No | File pattern to include (glob syntax, default: "\*") |
| exclude | string | No | File pattern to exclude (glob syntax, default: "") |
| max_results | integer | No | Maximum results to return per pattern (default: 100) |
| case_sensitive | boolean | No | Whether search is case-sensitive (default: false) |
| path | string | No | Base directory to search from (default: ".") |

**Returns:**
Matching lines grouped by file with line numbers, sorted by file modification time with newest files first.

This tool uses ripgrep when available for optimal performance, with a Python fallback implementation. It's ideal for finding specific code patterns like function declarations, imports, variable usages, or error handling.

**CLI Usage:**

```bash
# Find function and class declarations in JavaScript files
skydeckai-code-cli --tool search_code --args '{
    "patterns": ["function\\s+\\w+", "class\\s+\\w+"],
    "include": "*.js"
}'

# Find all console.log statements with errors or warnings
skydeckai-code-cli --tool search_code --args '{
    "patterns": ["console\\.log.*[eE]rror", "console\\.log.*[wW]arning"],
    "path": "src"
}'

# Find import and export statements in TypeScript files
skydeckai-code-cli --tool search_code --args '{
    "patterns": ["import.*from", "export.*"],
    "include": "*.{ts,tsx}",
    "exclude": "node_modules/**"
}'
```

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

**CLI Usage:**

```bash
# Get system information
skydeckai-code-cli --tool get_system_info
```

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

**CLI Usage:**

```bash
# Fetch JSON from an API
skydeckai-code-cli --tool web_fetch --args '{
    "url": "https://api.github.com/users/octocat",
    "headers": {"Accept": "application/json"}
}'

# Download content to a file
skydeckai-code-cli --tool web_fetch --args '{
    "url": "https://github.com/github/github-mcp-server/blob/main/README.md",
    "save_to_file": "downloads/readme.md"
}'

# Fetch a webpage and convert to markdown for better readability
skydeckai-code-cli --tool web_fetch --args '{
    "url": "https://example.com",
    "convert_html_to_markdown": true
}'
```

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

**CLI Usage:**

```bash
# Search with default settings (auto engine selection)
skydeckai-code-cli --tool web_search --args '{
    "query": "latest python release features"
}'

# Try DuckDuckGo if you want alternative results
skydeckai-code-cli --tool web_search --args '{
    "query": "machine learning frameworks comparison",
    "search_engine": "duckduckgo"
}'

# Use Bing for reliable results
skydeckai-code-cli --tool web_search --args '{
    "query": "best programming practices 2023",
    "search_engine": "bing"
}'
```

### GitHub Tools

#### list_pull_requests

Lists and filters pull requests for a GitHub repository:

```json
{
    "owner": "octocat",
    "repo": "hello-world",
    "state": "open",
    "sort": "created",
    "direction": "desc",
    "per_page": 10
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| owner | string | Yes | Repository owner (username or organization) |
| repo | string | Yes | Repository name |
| state | string | No | Filter by pull request state: "open", "closed", or "all" (default: "open") |
| head | string | No | Filter by head user/org and branch name (format: "user:ref-name" or "org:ref-name") |
| base | string | No | Filter by base branch name |
| sort | string | No | How to sort the results: "created", "updated", "popularity", "long-running" (default: "created") |
| direction | string | No | Sort direction: "asc" or "desc" (default: "desc") |
| per_page | number | No | Results per page, max 100 (default: 30) |

**Returns:**
A formatted list of pull requests with details including number, title, state, creator, branch information, and creation date.

**CLI Usage:**

```bash
# List open pull requests in a repository
skydeckai-code-cli --tool list_pull_requests --args '{
    "owner": "octocat",
    "repo": "hello-world"
}'

# List closed pull requests sorted by update time
skydeckai-code-cli --tool list_pull_requests --args '{
    "owner": "octocat",
    "repo": "hello-world",
    "state": "closed",
    "sort": "updated"
}'
```

#### create_pull_request_review

Creates a review for a GitHub pull request:

```json
{
    "owner": "octocat",
    "repo": "hello-world",
    "pull_number": 42,
    "event": "APPROVE",
    "body": "LGTM! The code looks great."
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| owner | string | Yes | Repository owner (username or organization) |
| repo | string | Yes | Repository name |
| pull_number | number | Yes | Pull request number |
| event | string | Yes | Review action: "APPROVE", "REQUEST_CHANGES", or "COMMENT" |
| body | string | No | Text of the review |
| comments | array | No | Array of review comments (for inline comments) |
| commit_id | string | No | SHA of commit to review |

**Returns:**
Confirmation of the created review with details from the GitHub API response.

**CLI Usage:**

```bash
# Approve a pull request
skydeckai-code-cli --tool create_pull_request_review --args '{
    "owner": "octocat",
    "repo": "hello-world",
    "pull_number": 42,
    "event": "APPROVE",
    "body": "The changes look good!"
}'

# Request changes on a pull request
skydeckai-code-cli --tool create_pull_request_review --args '{
    "owner": "octocat",
    "repo": "hello-world",
    "pull_number": 42,
    "event": "REQUEST_CHANGES",
    "body": "Please add tests for this feature."
}'
```

#### get_pull_request_files

Retrieves the list of files changed in a GitHub pull request:

```json
{
    "owner": "octocat",
    "repo": "hello-world",
    "pull_number": 42
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| owner | string | Yes | Repository owner (username or organization) |
| repo | string | Yes | Repository name |
| pull_number | number | Yes | Pull request number |

**Returns:**
A formatted list of changed files with details including filename, status (added, modified, removed), additions, deletions, total changes, and file URLs. Also includes a diff patch for each file and summary statistics.

**CLI Usage:**

```bash
# Get files changed in a pull request
skydeckai-code-cli --tool get_pull_request_files --args '{
    "owner": "octocat",
    "repo": "hello-world",
    "pull_number": 42
}'
```

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

**CLI Usage:**

```bash
# Setup a new project with multiple steps in sequential order (using proper paths)
skydeckai-code-cli --tool batch_tools --args '{
    "description": "Setup new project",
    "sequential": true,
    "invocations": [
        {"tool": "create_directory", "arguments": {"path": "project"}},
        {"tool": "create_directory", "arguments": {"path": "project/src"}},
        {"tool": "write_file", "arguments": {"path": "project/README.md", "content": "# Project\n\nA new project."}}
    ]
}'

# Create nested structure using relative paths (without changing directory)
skydeckai-code-cli --tool batch_tools --args '{
    "description": "Create project structure",
    "sequential": true,
    "invocations": [
        {"tool": "create_directory", "arguments": {"path": "project/src"}},
        {"tool": "create_directory", "arguments": {"path": "project/docs"}},
        {"tool": "write_file", "arguments": {"path": "project/README.md", "content": "# Project"}}
    ]
}'

# Gather system information and take a screenshot (tasks can run in parallel)
skydeckai-code-cli --tool batch_tools --args '{
    "description": "System diagnostics",
    "sequential": false,
    "invocations": [
        {"tool": "get_system_info", "arguments": {}},
        {"tool": "capture_screenshot", "arguments": {
            "output_path": "diagnostics/screen.png",
            "capture_mode": {
                "type": "full"
            }
        }}
    ]
}'
```

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

**CLI Usage:**

```bash
# Analyze a bug and plan a fix
skydeckai-code-cli --tool think --args '{
    "thought": "# Bug Analysis\n\n## Observed Behavior\nThe login endpoint returns a 500 error when email contains Unicode characters.\n\n## Root Cause\nThe database adapter is not properly encoding Unicode strings before constructing the SQL query.\n\n## Potential Fixes\n1. Update the database adapter to use parameterized queries\n2. Add input validation to reject Unicode in emails\n3. Encode email input manually before database operations\n\nFix #1 is the best approach as it solves the core issue and improves security."
}'

# Evaluate design alternatives
skydeckai-code-cli --tool think --args '{
    "thought": "# API Design Options\n\n## REST vs GraphQL\nFor this use case, GraphQL would provide more flexible data fetching but adds complexity. REST is simpler and sufficient for our current needs.\n\n## Authentication Methods\nJWT-based authentication offers stateless operation and better scalability compared to session-based auth.\n\nRecommendation: Use REST with JWT authentication for the initial implementation."
}'
```

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

**CLI Usage:**

```bash
# Python example
skydeckai-code-cli --tool execute_code --args '{
    "language": "python",
    "code": "print(sum(range(10)))"
}'

# JavaScript example
skydeckai-code-cli --tool execute_code --args '{
    "language": "javascript",
    "code": "console.log(Array.from({length: 5}, (_, i) => i*2))"
}'

# Ruby example
skydeckai-code-cli --tool execute_code --args '{
    "language": "ruby",
    "code": "puts (1..5).reduce(:+)"
}'

# Go example
skydeckai-code-cli --tool execute_code --args '{
    "language": "go",
    "code": "fmt.Println(\"Hello, Go!\")"
}'
```

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

**CLI Usage:**

```bash
# List directory contents with details
skydeckai-code-cli --tool execute_shell_script --args '{
    "script": "ls -la"
}'

# Find all Python files recursively
skydeckai-code-cli --tool execute_shell_script --args '{
    "script": "find . -name \"*.py\" -type f"
}'

# Complex script with multiple commands
skydeckai-code-cli --tool execute_shell_script --args '{
    "script": "echo \"System Info:\" && uname -a && echo \"\nDisk Usage:\" && df -h"
}'
```

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

## Configuration

Configuration file: `~/.skydeckai_code/config.json`

```json
{
    "allowed_directory": "/path/to/workspace"
}
```

## CLI Usage

Basic command structure:

```bash
skydeckai-code-cli --tool <tool_name> --args '<json_arguments>'

# List available tools
skydeckai-code-cli --list-tools

# Enable debug output
skydeckai-code-cli --debug --tool <tool_name> --args '<json_arguments>'
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

-   Additional GitHub tools:
    -   PR Description Generator
    -   Actions Manager
    -   Issue Management
-   Pivotal Tracker tools:
    -   Story Generator
    -   Story Manager

## Development Status

Currently in active development. Features and API may change.

## License

Apache License 2.0 - see [LICENSE](LICENSE)

[![Star History Chart](https://api.star-history.com/svg?repos=skydeckai/skydeckai-code&type=Date)](https://www.star-history.com/#skydeckai/skydeckai-code&Date)
