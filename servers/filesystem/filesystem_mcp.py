from fastmcp import FastMCP
import logging
import os
import pathlib
import fnmatch
import difflib
import stat
import secrets
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict, Any
from config.config_loader import load_mcp_config
import json

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="./filesystem-mcp.log",
    filemode="a"
)
logger = logging.getLogger("mcp_server_filesystem")

# Load configuration
try:
    config = load_mcp_config()
    if "mcpServers" not in config or "filesystem-server" not in config["mcpServers"]:
        raise ValueError(
            f"Invalid mcpServers configuration: missing filesystem-server")
    server_config = config["mcpServers"]["filesystem-server"]
    if not all(key in server_config for key in ["allowedDir", "serverName", "port"]):
        raise ValueError(
            f"Missing allowedDir, serverName, or port in filesystem-server configuration")
    ALLOWED_DIR = server_config["allowedDir"]
    SERVER_NAME = server_config["serverName"]
    PORT = server_config["port"]
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    raise

# Path validation


def normalize_path(p: str) -> str:
    """Normalize path, handling home directory and ensuring absolute paths."""
    p = p.strip().strip("'\"")
    if p.startswith("~/") or p == "~":
        p = os.path.join(os.path.expanduser("~"), p[1:])
    p = os.path.normpath(p)
    if not os.path.isabs(p):
        p = os.path.abspath(os.path.join(os.getcwd(), p))
    return p


def is_path_within_allowed_directory(absolute_path: str, allowed_dir: str = ALLOWED_DIR) -> bool:
    """Check if absolute_path is within allowed_dir."""
    normalized_path = normalize_path(absolute_path)
    normalized_allowed = normalize_path(allowed_dir)
    if not os.path.isabs(normalized_path) or not os.path.isabs(normalized_allowed):
        raise ValueError("Paths must be absolute")
    if "\x00" in normalized_path:
        return False
    if normalized_path == normalized_allowed:
        return True
    return normalized_path.startswith(normalized_allowed + os.sep)


def validate_path(requested_path: str, allowed_dir: str = ALLOWED_DIR) -> str:
    """Validate and resolve path, handling symlinks and parent directories."""
    absolute_path = normalize_path(requested_path)
    if not is_path_within_allowed_directory(absolute_path, allowed_dir):
        raise ValueError(
            f"Access denied - path outside allowed directory: {absolute_path} not in {allowed_dir}")
    try:
        real_path = os.path.realpath(absolute_path)
        if not is_path_within_allowed_directory(real_path, allowed_dir):
            raise ValueError(
                f"Access denied - symlink target outside allowed directory: {real_path}")
        return real_path
    except FileNotFoundError:
        parent_dir = os.path.dirname(absolute_path)
        real_parent = os.path.realpath(parent_dir)
        if not is_path_within_allowed_directory(real_parent, allowed_dir):
            raise ValueError(
                f"Access denied - parent directory outside allowed directory: {real_parent}")
        return absolute_path

# Schema definitions using Pydantic


class ReadFileArgs(BaseModel):
    path: str
    tail: Optional[int] = Field(
        None, description="Return last N lines of the file")
    head: Optional[int] = Field(
        None, description="Return first N lines of the file")


class ReadMultipleFilesArgs(BaseModel):
    paths: List[str]


class WriteFileArgs(BaseModel):
    path: str
    content: str


class EditOperation(BaseModel):
    oldText: str = Field(description="Text to search for - must match exactly")
    newText: str = Field(description="Text to replace with")


class EditFileArgs(BaseModel):
    path: str
    edits: List[EditOperation]
    dryRun: bool = Field(
        default=False, description="Preview changes using git-style diff format")


class CreateDirectoryArgs(BaseModel):
    path: str


class ListDirectoryArgs(BaseModel):
    path: str


class ListDirectoryWithSizesArgs(BaseModel):
    path: str
    sortBy: str = Field(
        default="name", description="Sort entries by name or size")


class DirectoryTreeArgs(BaseModel):
    path: str


class MoveFileArgs(BaseModel):
    source: str
    destination: str


class SearchFilesArgs(BaseModel):
    path: str
    pattern: str
    excludePatterns: List[str] = Field(default_factory=list)


class GetFileInfoArgs(BaseModel):
    path: str


# Initialize MCP server
mcp = FastMCP(SERVER_NAME)

# Helper functions


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to \n."""
    return text.replace("\r\n", "\n")


def create_unified_diff(original: str, modified: str, filepath: str = "file") -> str:
    """Create a git-style unified diff."""
    original_lines = normalize_line_endings(original).splitlines()
    modified_lines = normalize_line_endings(modified).splitlines()
    diff = difflib.unified_diff(
        original_lines, modified_lines,
        fromfile=filepath, tofile=filepath,
        fromfiledate="original", tofiledate="modified",
        n=3
    )
    return "\n".join(diff)


async def get_file_stats(file_path: str) -> Dict[str, Any]:
    """Get file metadata."""
    stats = os.stat(file_path)
    return {
        "size": stats.st_size,
        "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stats.st_atime).isoformat(),
        "isDirectory": stat.S_ISDIR(stats.st_mode),
        "isFile": stat.S_ISREG(stats.st_mode),
        "permissions": oct(stats.st_mode)[-3:],
    }


async def search_files(root_path: str, pattern: str, exclude_patterns: List[str] = []) -> List[str]:
    """Recursively search for files matching pattern."""
    results = []
    pattern = pattern.lower()
    for root, _, files in os.walk(root_path):
        if not is_path_within_allowed_directory(root, ALLOWED_DIR):
            continue
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, root_path)
            if any(fnmatch.fnmatch(relative_path, exclude) for exclude in exclude_patterns):
                continue
            if pattern in file.lower():
                results.append(full_path)
    return results


async def tail_file(file_path: str, num_lines: int) -> str:
    """Get last N lines of a file efficiently."""
    chunk_size = 1024
    stats = os.stat(file_path)
    if stats.st_size == 0:
        return ""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = []
        position = stats.st_size
        lines_found = 0
        remaining_text = ""
        while position > 0 and lines_found < num_lines:
            size = min(chunk_size, position)
            position -= size
            f.seek(position)
            chunk = f.read(size)
            chunk_text = chunk + remaining_text
            chunk_lines = normalize_line_endings(chunk_text).splitlines()
            if position > 0:
                remaining_text = chunk_lines[0]
                chunk_lines = chunk_lines[1:]
            for line in reversed(chunk_lines):
                if lines_found < num_lines:
                    lines.insert(0, line)
                    lines_found += 1
        return "\n".join(lines)


async def head_file(file_path: str, num_lines: int) -> str:
    """Get first N lines of a file efficiently."""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = []
        for i, line in enumerate(f):
            if i >= num_lines:
                break
            lines.append(line.rstrip("\n"))
        return "\n".join(lines)


async def apply_file_edits(file_path: str, edits: List[EditOperation], dry_run: bool = False) -> str:
    """Apply line-based edits and return a unified diff."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = normalize_line_endings(f.read())
    modified_content = content
    for edit in edits:
        old_lines = normalize_line_endings(edit.oldText).splitlines()
        content_lines = modified_content.splitlines()
        match_found = False
        for i in range(len(content_lines) - len(old_lines) + 1):
            potential_match = content_lines[i:i + len(old_lines)]
            if all(old.strip() == content.strip() for old, content in zip(old_lines, potential_match)):
                original_indent = content_lines[i].split(
                    old_lines[0].strip())[0]
                new_lines = normalize_line_endings(edit.newText).splitlines()
                new_lines[0] = original_indent + new_lines[0].lstrip()
                content_lines[i:i + len(old_lines)] = new_lines
                modified_content = "\n".join(content_lines)
                match_found = True
                break
        if not match_found:
            raise ValueError(
                f"Could not find exact match for edit: {edit.oldText}")
    diff = create_unified_diff(content, modified_content, file_path)
    num_backticks = 3
    while "```" * num_backticks in diff:
        num_backticks += 1
    formatted_diff = f"{'```' * num_backticks}diff\n{diff}\n{'```' * num_backticks}\n"
    if not dry_run:
        temp_path = f"{file_path}.{secrets.token_hex(16)}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(modified_content)
            os.rename(temp_path, file_path)
        except Exception as e:
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
    return formatted_diff


def format_size(bytes: int) -> str:
    """Format file size in human-readable format."""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    if bytes == 0:
        return '0 B'
    i = int((bytes).bit_length() / 10)
    if i == 0:
        return f"{bytes} {units[i]}"
    return f"{bytes / (1024 ** i):.2f} {units[i]}"

# Tool definitions


@mcp.tool()
async def read_file(args: Dict[str, Any]) -> str:
    """Read the complete contents of a file from the file system."""
    try:
        parsed = ReadFileArgs(**args)
        if parsed.head and parsed.tail:
            return json.dumps({"error": "Cannot specify both head and tail parameters"})
        valid_path = validate_path(parsed.path)
        if parsed.tail:
            content = await tail_file(valid_path, parsed.tail)
        elif parsed.head:
            content = await head_file(valid_path, parsed.head)
        else:
            with open(valid_path, "r", encoding="utf-8") as f:
                content = f.read()
        return json.dumps({"content": content})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def read_multiple_files(args: Dict[str, Any]) -> str:
    """Read the contents of multiple files simultaneously."""
    try:
        parsed = ReadMultipleFilesArgs(**args)
        results = []
        for file_path in parsed.paths:
            try:
                valid_path = validate_path(file_path)
                with open(valid_path, "r", encoding="utf-8") as f:
                    content = f.read()
                results.append(f"{file_path}:\n{content}\n")
            except Exception as e:
                results.append(f"{file_path}: Error - {str(e)}")
        return json.dumps({"content": "\n---\n".join(results)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def write_file(args: Dict[str, Any]) -> str:
    """Create or overwrite a file with new content."""
    try:
        parsed = WriteFileArgs(**args)
        valid_path = validate_path(parsed.path)
        temp_path = f"{valid_path}.{secrets.token_hex(16)}.tmp"
        try:
            with open(temp_path, "x", encoding="utf-8") as f:
                f.write(parsed.content)
            os.rename(temp_path, valid_path)
        except FileExistsError:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(parsed.content)
            os.rename(temp_path, valid_path)
        except Exception as e:
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
        return json.dumps({"message": f"Successfully wrote to {parsed.path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def edit_file(args: Dict[str, Any]) -> str:
    """Make line-based edits to a text file."""
    try:
        parsed = EditFileArgs(**args)
        valid_path = validate_path(parsed.path)
        result = await apply_file_edits(valid_path, parsed.edits, parsed.dryRun)
        return json.dumps({"content": result})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def create_directory(args: Dict[str, Any]) -> str:
    """Create a new directory or ensure it exists."""
    try:
        parsed = CreateDirectoryArgs(**args)
        valid_path = validate_path(parsed.path)
        os.makedirs(valid_path, exist_ok=True)
        return json.dumps({"message": f"Successfully created directory {parsed.path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_directory(args: Dict[str, Any]) -> str:
    """Get a listing of files and directories."""
    try:
        parsed = ListDirectoryArgs(**args)
        valid_path = validate_path(parsed.path)
        entries = os.listdir(valid_path)
        formatted = []
        for entry in entries:
            entry_path = os.path.join(valid_path, entry)
            prefix = "[DIR]" if os.path.isdir(entry_path) else "[FILE]"
            formatted.append(f"{prefix} {entry}")
        return json.dumps({"content": "\n".join(formatted)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_directory_with_sizes(args: Dict[str, Any]) -> str:
    """Get a listing of files and directories with sizes."""
    try:
        parsed = ListDirectoryWithSizesArgs(**args)
        valid_path = validate_path(parsed.path)
        entries = []
        for entry in os.listdir(valid_path):
            entry_path = os.path.join(valid_path, entry)
            try:
                stats = os.stat(entry_path)
                entries.append({
                    "name": entry,
                    "isDirectory": os.path.isdir(entry_path),
                    "size": stats.st_size,
                    "mtime": stats.st_mtime
                })
            except:
                entries.append({
                    "name": entry,
                    "isDirectory": os.path.isdir(entry_path),
                    "size": 0,
                    "mtime": 0
                })
        entries.sort(key=lambda e: e["size"] if parsed.sortBy ==
                     "size" else e["name"], reverse=(parsed.sortBy == "size"))
        formatted = [
            f"{'[DIR]' if e['isDirectory'] else '[FILE]'} {e['name'].ljust(30)} {'' if e['isDirectory'] else format_size(e['size']).rjust(10)}" for e in entries]
        total_files = sum(1 for e in entries if not e["isDirectory"])
        total_dirs = sum(1 for e in entries if e["isDirectory"])
        total_size = sum(e["size"] for e in entries if not e["isDirectory"])
        formatted.extend(
            ["", f"Total: {total_files} files, {total_dirs} directories", f"Combined size: {format_size(total_size)}"])
        return json.dumps({"content": "\n".join(formatted)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def directory_tree(args: Dict[str, Any]) -> str:
    """Get a recursive tree view of files and directories."""
    try:
        parsed = DirectoryTreeArgs(**args)

        async def build_tree(current_path: str) -> List[Dict[str, Any]]:
            valid_path = validate_path(current_path)
            entries = []
            for entry in os.listdir(valid_path):
                entry_path = os.path.join(valid_path, entry)
                entry_data = {"name": entry, "type": "directory" if os.path.isdir(
                    entry_path) else "file"}
                if os.path.isdir(entry_path):
                    entry_data["children"] = await build_tree(entry_path)
                entries.append(entry_data)
            return entries
        tree_data = await build_tree(parsed.path)
        return json.dumps({"content": json.dumps(tree_data, indent=2)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def move_file(args: Dict[str, Any]) -> str:
    """Move or rename files and directories."""
    try:
        parsed = MoveFileArgs(**args)
        valid_source = validate_path(parsed.source)
        valid_dest = validate_path(parsed.destination)
        os.rename(valid_source, valid_dest)
        return json.dumps({"message": f"Successfully moved {parsed.source} to {parsed.destination}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def search_files(args: Dict[str, Any]) -> str:
    """Recursively search for files matching a pattern."""
    try:
        parsed = SearchFilesArgs(**args)
        valid_path = validate_path(parsed.path)
        results = await search_files(valid_path, parsed.pattern, parsed.excludePatterns)
        return json.dumps({"content": "\n".join(results) if results else "No matches found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def get_file_info(args: Dict[str, Any]) -> str:
    """Retrieve detailed metadata about a file or directory."""
    try:
        parsed = GetFileInfoArgs(**args)
        valid_path = validate_path(parsed.path)
        info = await get_file_stats(valid_path)
        formatted = "\n".join(f"{key}: {value}" for key, value in info.items())
        return json.dumps({"content": formatted})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def list_allowed_directories(args: Dict[str, Any]) -> str:
    """List directories the server is allowed to access."""
    return json.dumps({"content": f"Allowed directories:\n{ALLOWED_DIR}"})

if __name__ == "__main__":
    logger.info(f"Starting {SERVER_NAME} on http://localhost:{PORT}")
    mcp.run(transport="http", port=PORT, host="0.0.0.0")
