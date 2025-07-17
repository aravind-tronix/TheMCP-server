import fastmcp
import logging
import anyio
from servers.sqlite.mcp_server_sqlite import mcp as sqlite_mcp
from servers.filesystem.filesystem_mcp import mcp as filesystem_mcp
from servers.aws.aws_iam_mcp import mcp as aws_mcp
from servers.gmail.gmail_mcp import mcp as gmail_mcp
from config.config_loader import load_mcp_config

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="./mcp-server-master.log",
    filemode="a"
)
logger = logging.getLogger("mcp_server_master")

# Load configuration
try:
    config = load_mcp_config()
    if "mcpServers" not in config or "master-server" not in config["mcpServers"]:
        raise ValueError(
            f"Invalid mcpServers configuration: missing master-server")
    server_config = config["mcpServers"]["master-server"]
    if not all(key in server_config for key in ["serverName", "port"]):
        raise ValueError(
            f"Missing serverName or port in master-server configuration")
    SERVER_NAME = server_config["serverName"]
    PORT = server_config["port"]
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    raise

# Initialize master MCP server
master_mcp = fastmcp.FastMCP(SERVER_NAME)

# Import and mount subservers
try:
    master_mcp.mount(sqlite_mcp, prefix="sqlite-server")
    logger.info("Mounted sqlite-server")
except Exception as e:
    logger.error(f"Failed to mount sqlite-server: {str(e)}")
    raise

try:
    master_mcp.mount(filesystem_mcp, prefix="filesystem-server")
    logger.info("Mounted filesystem-server")
except Exception as e:
    logger.error(f"Failed to mount filesystem-server: {str(e)}")
    raise

try:
    master_mcp.mount(aws_mcp, prefix="aws-server")
    logger.info("Mounted aws-server")
except Exception as e:
    logger.error(f"Failed to mount aws-server: {str(e)}")
    raise

try:
    master_mcp.mount(gmail_mcp, prefix="gmail-server")
    logger.info("Mounted gmail-server")
except Exception as e:
    logger.error(f"Failed to mount gmail-server: {str(e)}")
    raise


async def log_tools():
    """Log registered tools."""
    try:
        tools = await master_mcp.get_tools()
        tool_names = list(tools.keys())
        logger.info(f"Registered tools: {tool_names}")
    except Exception as e:
        logger.error(f"Failed to log tools: {str(e)}")

if __name__ == "__main__":
    # Log registered tools
    anyio.run(log_tools)
    logger.info(f"Starting {SERVER_NAME} on http://localhost:{PORT}")
    master_mcp.run(transport="http", port=PORT, host="0.0.0.0")
