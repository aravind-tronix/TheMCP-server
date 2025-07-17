from fastmcp import FastMCP
import logging
import json
import os
from .users import mcp as users_mcp
from .groups import mcp as groups_mcp
from .roles import mcp as roles_mcp
from .policies import mcp as policies_mcp
from .access_keys import mcp as access_keys_mcp
from .cost_explorer import mcp as cost_explorer_mcp
from config.config_loader import load_mcp_config

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="./aws-iam-mcp.log",
    filemode="a"
)
logger = logging.getLogger("mcp_server_aws")

# Load configuration
try:
    config = load_mcp_config()
    if "mcpServers" not in config or "aws-server" not in config["mcpServers"]:
        raise ValueError(
            f"Invalid mcpServers configuration: missing aws-server")
    server_config = config["mcpServers"]["aws-server"]
    if "serverName" not in server_config:
        raise ValueError(f"Missing serverName in aws-server configuration")
    SERVER_NAME = server_config["serverName"]
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    raise

# Initialize MCP server
mcp = FastMCP(SERVER_NAME)

# Mount subservers
try:
    mcp.mount(users_mcp, prefix="users")
    logger.info("Mounted users subserver")
except Exception as e:
    logger.error(f"Failed to mount users subserver: {str(e)}")
    raise

try:
    mcp.mount(groups_mcp, prefix="groups")
    logger.info("Mounted groups subserver")
except Exception as e:
    logger.error(f"Failed to mount groups subserver: {str(e)}")
    raise

try:
    mcp.mount(roles_mcp, prefix="roles")
    logger.info("Mounted roles subserver")
except Exception as e:
    logger.error(f"Failed to mount roles subserver: {str(e)}")
    raise

try:
    mcp.mount(policies_mcp, prefix="policies")
    logger.info("Mounted policies subserver")
except Exception as e:
    logger.error(f"Failed to mount policies subserver: {str(e)}")
    raise

try:
    mcp.mount(access_keys_mcp, prefix="access-keys")
    logger.info("Mounted access-keys subserver")
except Exception as e:
    logger.error(f"Failed to mount access-keys subserver: {str(e)}")
    raise

try:
    mcp.mount(cost_explorer_mcp, prefix="cost-explorer")
    logger.info("Mounted cost-explorer subserver")
except Exception as e:
    logger.error(f"Failed to mount cost-explorer subserver: {str(e)}")
    raise

if __name__ == "__main__":
    logger.info(f"Starting {SERVER_NAME}")
    # Note: Not running standalone; will be mounted by master server
