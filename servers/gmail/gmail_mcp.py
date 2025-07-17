from fastmcp import FastMCP
import logging
import json
import os
from .emails import mcp as emails_mcp
from config.config_loader import load_mcp_config

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="/mnt/d/linux/TheMCP/servers/gmail/gmail-mcp.log",
    filemode="a"
)
logger = logging.getLogger("gmail_mcp")

# Load configuration
try:
    config = load_mcp_config()
    if "mcpServers" not in config or "gmail-server" not in config["mcpServers"]:
        raise ValueError(
            f"Invalid mcpServers configuration: missing gmail-server")
    server_config = config["mcpServers"]["gmail-server"]
    if "serverName" not in server_config:
        raise ValueError(f"Missing serverName in gmail-server configuration")
    SERVER_NAME = server_config["serverName"]
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    raise

# Initialize MCP server
mcp = FastMCP(SERVER_NAME)

# Mount subservers
try:
    mcp.mount(emails_mcp, prefix="emails")
    logger.info("Mounted emails subserver")
except Exception as e:
    logger.error(f"Failed to mount emails subserver: {str(e)}")
    raise

if __name__ == "__main__":
    logger.info(f"Starting {SERVER_NAME}")
    # Note: Not running standalone; will be mounted by master server
