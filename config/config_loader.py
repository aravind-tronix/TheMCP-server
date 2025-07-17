import json
import os
import logging
import streamlit as st

# Path to MCP client configuration file
MCP_CLIENT_CONFIG_PATH = "config/mcp_client_config.json"


def load_mcp_config() -> dict:
    """
    Load the entire MCP configuration from mcp_client_config.json.

    Returns:
        dict: The full configuration as a dictionary.

    Raises:
        FileNotFoundError: If the config file is missing.
        ValueError: If the config file is invalid JSON.
    """
    try:
        if not os.path.exists(MCP_CLIENT_CONFIG_PATH):
            raise FileNotFoundError(
                f"Config file not found: {MCP_CLIENT_CONFIG_PATH}")
        with open(MCP_CLIENT_CONFIG_PATH, "r") as f:
            config = json.load(f)
        if not isinstance(config, dict):
            raise ValueError(
                f"Invalid JSON format in {MCP_CLIENT_CONFIG_PATH}")
        return config
    except Exception as e:
        logging.error(f"Failed to load MCP config: {str(e)}")
        st.error(f"Failed to load MCP config: {str(e)}")
        raise
