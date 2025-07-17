import streamlit as st
import anthropic
import sqlite3
import json
import os
import anyio
import fastmcp
from contextlib import closing
from config.config_loader import load_mcp_config, MCP_CLIENT_CONFIG_PATH

# Load configuration
try:
    config = load_mcp_config()
    required_keys = ["anthropicApiKey", "dbPath", "mcpServers"]
    if not all(key in config for key in required_keys):
        st.error(
            f"Missing required keys for client in {MCP_CLIENT_CONFIG_PATH}")
        st.stop()
    if "master-server" not in config["mcpServers"] or "url" not in config["mcpServers"]["master-server"]:
        st.error(
            f"Invalid mcpServers configuration for client in {MCP_CLIENT_CONFIG_PATH}")
        st.stop()
    ANTHROPIC_API_KEY = config["anthropicApiKey"]
    DB_PATH = config["dbPath"]
    SERVER_URL = config["mcpServers"]["master-server"]["url"]
except Exception as e:
    st.error(f"Failed to load configuration: {str(e)}")
    st.stop()


def save_api_key(api_key: str):
    """Save Anthropic API key to mcp_client_config.json with restricted permissions."""
    try:
        config = load_mcp_config()
        config["anthropicApiKey"] = api_key
        with open(MCP_CLIENT_CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        os.chmod(MCP_CLIENT_CONFIG_PATH, 0o600)
        return True
    except Exception as e:
        st.error(f"Failed to save API key: {str(e)}")
        return False


def init_conversation_db():
    """Initialize conversation database."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def load_conversation_history():
    """Load conversation history from database."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT role, content FROM conversation ORDER BY id")
        return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]


def add_to_history(role: str, content: str):
    """Add a message to the conversation database."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO conversation (role, content) VALUES (?, ?)", (role, content))
        conn.commit()


def clear_conversation_history():
    """Clear the conversation database."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM conversation")
        conn.commit()


async def get_available_tools():
    """Fetch available tools from the MCP server using FastMCP Client."""
    try:
        async with fastmcp.Client(SERVER_URL, timeout=10) as client:
            tools = await client.list_tools()
            if isinstance(tools, list):
                tool_names = [tool.name.replace("_", ".") for tool in tools]
            elif isinstance(tools, dict):
                tool_names = [name.replace("_", ".") for name in tools.keys()]
            else:
                tool_names = []
            return tool_names
    except Exception as e:
        st.session_state.tool_error = f"Failed to connect to {SERVER_URL}: {str(e)}"
        return []


def sync_get_available_tools():
    """Synchronous wrapper for get_available_tools."""
    try:
        return anyio.run(get_available_tools)
    except Exception as e:
        st.session_state.tool_error = f"Error fetching tools: {str(e)}"
        return []


# Initialize database
init_conversation_db()

# Initialize Streamlit app
st.set_page_config(page_title="MCP Client with AI Agents", layout="wide")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Page", ["Chat", "Configuration"])

# Load API key
api_key = ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    st.error("No Anthropic API key found. Please set it in the Configuration page or as ANTHROPIC_API_KEY environment variable.")
    st.stop()

# Initialize Anthropic client
if "client" not in st.session_state:
    st.session_state.client = anthropic.Anthropic(api_key=api_key)

# Fetch and cache available tools
if "tools" not in st.session_state:
    st.session_state.tools = sync_get_available_tools()

# Display available tools in sidebar
st.sidebar.subheader("Available Tools")
if st.session_state.tools:
    for tool in st.session_state.tools:
        st.sidebar.write(f"- {tool}")
else:
    error_msg = st.session_state.get(
        "tool_error", "No tools available. Ensure the master server is running or check the ngrok URL.")
    st.sidebar.markdown(f"[red]{error_msg}[/red]")

if page == "Configuration":
    st.title("Configuration")
    st.markdown(
        "Enter your Anthropic API key below. It will be saved securely in `mcp_client_config.json`.")

    api_key_input = st.text_input(
        "Anthropic API Key", type="password", value=api_key or "")
    if st.button("Save API Key"):
        if api_key_input:
            if save_api_key(api_key_input):
                st.success("API key saved successfully!")
                st.session_state.client = anthropic.Anthropic(
                    api_key=api_key_input)
                st.session_state.tools = sync_get_available_tools()
            else:
                st.error("Failed to save API key.")
        else:
            st.error("Please enter a valid API key.")

else:
    st.title("MCP Client with AI Agents")
    st.markdown("Interact with SQLite, Filesystem, AWS IAM, and Gmail MCP servers (using SMTP for sending emails) via a master MCP server, or ask general questions. Supports Claude, Grok, and OpenAI models.")

    if st.button("Clear Conversation History"):
        clear_conversation_history()
        st.success("Conversation history cleared!")
        st.rerun()

    conversation_history = load_conversation_history()

    st.subheader("Conversation History")
    for message in conversation_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(f"**You**: {message['content']}")
        else:
            with st.chat_message("assistant"):
                st.markdown(f"**AI Agent**: {message['content']}")

    user_input = st.chat_input(
        "Enter your query (e.g., 'SELECT * FROM table LIMIT 3', 'send email', 'list IAM users', or 'create a web app')")

    if user_input:
        conversation_history.append({"role": "user", "content": user_input})
        add_to_history("user", user_input)

        with st.chat_message("user"):
            st.markdown(f"**You**: {user_input}")

        tool_keywords = ["select ", " from ", "file", "directory", "search files", "iam", "user",
                         "group", "role", "policy", "access key", "cost", "email", "send", "read", "trash", "unread"]
        requires_tool = any(keyword in user_input.lower()
                            for keyword in tool_keywords)

        try:
            with st.chat_message("assistant"):
                response_container = st.empty()
                full_response = []
                if requires_tool:
                    with st.session_state.client.beta.messages.stream(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1000,
                        messages=conversation_history,
                        mcp_servers=[
                            {"type": "url", "url": SERVER_URL,
                                "name": "master-server"}
                        ],
                        extra_headers={
                            "anthropic-beta": "mcp-client-2025-04-04"
                        }
                    ) as stream:
                        for event in stream:
                            if event.type == "content_block_start" and hasattr(event.content_block, "text"):
                                full_response.append(event.content_block.text)
                                response_container.markdown(
                                    f"**AI Agent**: {''.join(full_response)}")
                            elif event.type == "content_block_delta" and hasattr(event.delta, "text"):
                                full_response.append(event.delta.text)
                                response_container.markdown(
                                    f"**AI Agent**: {''.join(full_response)}")
                            elif event.type == "content_block_stop":
                                continue
                else:
                    with st.session_state.client.beta.messages.stream(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1000,
                        messages=conversation_history
                    ) as stream:
                        for event in stream:
                            if event.type == "content_block_start" and hasattr(event.content_block, "text"):
                                full_response.append(event.content_block.text)
                                response_container.markdown(
                                    f"**AI Agent**: {''.join(full_response)}")
                            elif event.type == "content_block_delta" and hasattr(event.delta, "text"):
                                full_response.append(event.delta.text)
                                response_container.markdown(
                                    f"**AI Agent**: {''.join(full_response)}")
                            elif event.type == "content_block_stop":
                                continue

                if full_response:
                    add_to_history("assistant", "".join(full_response))
                else:
                    response_container.markdown(
                        "[red]No valid response received[/red]")
                    add_to_history("assistant", "No valid response received")

        except Exception as e:
            with st.chat_message("assistant"):
                st.markdown(f"[red]Client error: {str(e)}[/red]")
            add_to_history("assistant", f"Error: {str(e)}")

        st.rerun()
