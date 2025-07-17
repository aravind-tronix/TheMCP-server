# MCP Project

The MCP (Model-Context Protocol) project is a modular system that integrates multiple services (SQLite, Filesystem, AWS IAM, Gmail) through a master MCP server, accessible via a custom Streamlit-based web interface optimized for Claude. To support other AI models (e.g., Grok, OpenAI), you need to modify the `client_streamlit.py` code.

**Note**: This project is specifically built for Claude, utilizing a custom Claude UI written in Streamlit that leverages the Claude API, which is more cost-effective than the Claude desktop application. It also supports interaction via the Claude desktop application if preferred. This is a developer tool requiring specific configurations (e.g., API keys, SMTP settings, file paths) before running. It is not a one-click solution and is intended for users comfortable with setting up and debugging development environments.

## Project Structure

```
<PROJECT_ROOT>/
├── client_streamlit.py        # Streamlit client for user interaction with Claude UI
├── mcp_server_master.py       # Master MCP server mounting subservers
├── config/
│   ├── config_loader.py       # Shared module for loading configuration
│   └── mcp_client_config.json # Configuration file for all components
├── servers/
│   ├── sqlite/
│   │   └── mcp_server_sqlite.py # SQLite subserver for database operations
│   ├── filesystem/
│   │   └── filesystem_mcp.py   # Filesystem subserver for file operations
│   ├── aws/
│   │   └── aws_iam_mcp.py      # AWS IAM subserver for AWS operations
│   ├── gmail/
│   │   ├── gmail_mcp.py        # Gmail subserver for email operations (SMTP)
│   │   └── smtp_config.json    # SMTP configuration for Gmail subserver
├── test/                      # Allowed directory for Filesystem operations
├── conversation.db            # SQLite database for conversation history
├── candidates.db              # SQLite database for candidate data
├── requirements.txt           # Python dependencies
├── mcp-server-master.log      # Master server log
├── filesystem-mcp.log         # Filesystem subserver log
├── servers/aws/aws-iam-mcp.log # AWS IAM subserver log
├── servers/gmail/gmail-mcp.log # Gmail subserver log
└── servers/sqlite/sqlite-mcp.log # SQLite subserver log
```

**Note**: Replace `<PROJECT_ROOT>` with your project directory path (e.g., `/home/user/mcp` or `C:\mcp` on Windows).

## Features

- **Streamlit Client**: Custom web interface built for Claude, with support for other AI models (Grok, OpenAI) via code modification in `client_streamlit.py`.
- **Master MCP Server**: Central server mounting subservers, with the ability to mount additional custom or available MCP servers for extended functionality.
- **Subservers**:
  - **SQLite**: Manages `candidates.db` with tools for SQL queries (`read_query`, `write_query`, `list_tables`, `describe_table`), candidate asset updates, and salary queries.
  - **Filesystem**: Handles file operations in `<PROJECT_ROOT>/test` (e.g., read, write, search, directory listing).
  - **AWS IAM**: Manages AWS IAM users, groups, roles, policies, access keys, and cost data.
  - **Gmail**: Sends emails via SMTP using settings from `smtp_config.json`.
- **AI Integration**: Optimized for Claude via the Claude API, with support for Grok and OpenAI models through code changes for natural language queries and tool execution.
- **Configuration**: Centralized JSON config (`mcp_client_config.json`) for all components, with SMTP settings in `smtp_config.json` for Gmail.

## Prerequisites

- **OS**: Linux (tested on Ubuntu or WSL2)
- **Python**: 3.8 or higher
- **ngrok**: For exposing the master server (optional for external access)
- **AWS Credentials**: Configured in `~/.aws/credentials` for AWS IAM operations
- **SMTP Credentials**: Configured in `<PROJECT_ROOT>/servers/gmail/smtp_config.json` for Gmail email sending
- **Anthropic API Key**: For Claude model integration

## Setup Instructions (Linux)

### 1. Clone or Set Up the Project Directory
```bash
mkdir -p <PROJECT_ROOT>
cd <PROJECT_ROOT>
# Copy all project files (client_streamlit.py, mcp_server_master.py, etc.) into <PROJECT_ROOT>
```

### 2. Install Dependencies
Create and activate a virtual environment, then install dependencies from `requirements.txt`:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Note**: The `fastmcp` package may be custom. If not on PyPI, install it manually:
```bash
pip install /path/to/fastmcp.whl
# or
pip install git+<fastmcp_repository_url>
```

### 3. Configure the Project
Create the main configuration file:
```bash
mkdir -p <PROJECT_ROOT>/config
nano <PROJECT_ROOT>/config/mcp_client_config.json
```

Paste the following content, replacing `YOUR_ANTHROPIC_API_KEY` with your Anthropic API key and `<your-ngrok-url>` with your ngrok URL:
```json
{
  "anthropicApiKey": "YOUR_ANTHROPIC_API_KEY",
  "dbPath": "<PROJECT_ROOT>/conversation.db",
  "mcpServers": {
    "master-server": {
      "url": "https://<your-ngrok-url>.ngrok-free.app/mcp",
      "serverName": "MasterMCPServer",
      "port": 8006
    },
    "filesystem-server": {
      "allowedDir": "<PROJECT_ROOT>/test",
      "serverName": "FilesystemServer",
      "port": 8002
    },
    "aws-server": {
      "serverName": "AWSServer"
    },
    "gmail-server": {
      "serverName": "GmailServer"
    },
    "sqlite-server": {
      "serverName": "SqliteServer",
      "port": 8000,
      "dbPath": "<PROJECT_ROOT>/candidates.db"
    }
  }
}
```

Set permissions:
```bash
chmod 600 <PROJECT_ROOT>/config/mcp_client_config.json
```

### 4. Configure SMTP for Gmail
Create the SMTP configuration file:
```bash
mkdir -p <PROJECT_ROOT>/servers/gmail
nano <PROJECT_ROOT>/servers/gmail/smtp_config.json
```

Paste the following content, replacing placeholders with your Gmail SMTP credentials:
```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_username": "your.email@gmail.com",
  "smtp_password": "your-app-specific-password"
}
```

**Note**: Use an [App Password](https://support.google.com/accounts/answer/185833) for `smtp_password` if 2-Step Verification is enabled on your Gmail account.

Set permissions:
```bash
chmod 600 <PROJECT_ROOT>/servers/gmail/smtp_config.json
```

### 5. Set Up ngrok (Optional)
For external access to the master server:
```bash
ngrok http 8006
```
Update `mcpServers.master-server.url` in `mcp_client_config.json` with the ngrok URL (e.g., `https://<your-ngrok-url>.ngrok-free.app/mcp`).

### 6. Configure AWS Credentials
Set up AWS credentials for IAM and Cost Explorer operations:
```bash
mkdir -p ~/.aws
nano ~/.aws/credentials
```
Add:
```
[default]
aws_access_key_id = YOUR_AWS_ACCESS_KEY
aws_secret_access_key = YOUR_AWS_SECRET_KEY
```
Set permissions:
```bash
chmod 600 ~/.aws/credentials
```

### 7. Create Directories and Set Permissions
```bash
mkdir -p <PROJECT_ROOT>/test
mkdir -p <PROJECT_ROOT>/servers/{sqlite,filesystem,aws,gmail}
chmod 755 <PROJECT_ROOT>/test
chmod 755 <PROJECT_ROOT>/servers/{sqlite,filesystem,aws,gmail}
chmod 644 <PROJECT_ROOT>/*.py
chmod 644 <PROJECT_ROOT>/config/config_loader.py
chmod 644 <PROJECT_ROOT>/servers/*/*.py
```

### 8. Initialize Databases
The Streamlit client and SQLite subserver will create `conversation.db` and `candidates.db` automatically if they don’t exist. To verify:
```bash
ls -l <PROJECT_ROOT>/{conversation.db,candidates.db}
chmod 644 <PROJECT_ROOT>/{conversation.db,candidates.db}
```

## Running the Application

1. **Start the Master Server**:
```bash
cd <PROJECT_ROOT>
source venv/bin/activate
pkill -f mcp_server_master.py
python mcp_server_master.py &
tail -f <PROJECT_ROOT>/mcp-server-master.log
```
Verify logs show subservers mounted (e.g., `Mounted sqlite-server`, `Mounted gmail-server`).

2. **Start the Streamlit Client**:
```bash
cd <PROJECT_ROOT>
source venv/bin/activate
streamlit run client_streamlit.py
```
Access the UI at `http://localhost:8501`.

3. **Optional: Run Subservers Standalone** (for debugging):
- Filesystem:
  ```bash
  cd <PROJECT_ROOT>/servers/filesystem
  pkill -f filesystem_mcp.py
  python filesystem_mcp.py &
  tail -f <PROJECT_ROOT>/filesystem-mcp.log
  ```
- SQLite:
  ```bash
  cd <PROJECT_ROOT>/servers/sqlite
  pkill -f mcp_server_sqlite.py
  python mcp_server_sqlite.py &
  tail -f <PROJECT_ROOT>/servers/sqlite/sqlite-mcp.log
  ```

## Usage

1. **Configuration Page**:
   - Navigate to the Configuration page in the Streamlit UI.
   - Enter your Anthropic API key and save it to update `mcp_client_config.json`.

2. **Chat Page**:
   - Interact via the chat input, e.g.:
     - **SQLite**: “SELECT * FROM candidates LIMIT 3”, “update candidate asset John Doe Tablet”
     - **Filesystem**: “search for *.txt files”, “create a web app” (in `<PROJECT_ROOT>/test`)
     - **Gmail**: “send email” (prompts for recipient, subject, message)
     - **AWS IAM**: “list IAM users”, “get cost data”
   - View available tools in the sidebar (e.g., `sqlite-server.read.query`, `gmail-server.emails.send.email`).

3. **Switching AI Models**:
   - Default: Claude (optimized via Claude API in `client_streamlit.py`).
   - For Grok or OpenAI, update `client_streamlit.py`:
     ```python
     from openai import OpenAI
     st.session_state.client = OpenAI(api_key="YOUR_OPENAI_API_KEY")
     ```
     Add `openai==1.51.0` to `requirements.txt` and reinstall:
     ```bash
     pip install -r requirements.txt
     ```
   - For Grok, use the xAI API (see https://x.ai/api).

4. **Mounting Additional MCP Servers**:
   - To mount custom or additional MCP servers, update `mcp_server_master.py` to include the new server:
     ```python
     from servers.custom.custom_mcp import mcp as custom_mcp
     master_mcp.mount(custom_mcp, prefix="custom-server")
     ```
   - Add the server to `mcp_client_config.json`:
     ```json
     "custom-server": {
       "serverName": "CustomServer",
       "port": 8003
     }
     ```

## Known Bugs

- **Path Configuration**: You may need to manually update file paths in `mcp_client_config.json` or other scripts if `<PROJECT_ROOT>` does not match your project directory structure. Double-check paths for `dbPath`, `allowedDir`, and `smtp_config.json`.

## Troubleshooting

- **Logs**:
  ```bash
  tail -f <PROJECT_ROOT>/mcp-server-master.log
  tail -f <PROJECT_ROOT>/servers/sqlite/sqlite-mcp.log
  tail -f <PROJECT_ROOT>/filesystem-mcp.log
  tail -f <PROJECT_ROOT>/servers/aws/aws-iam-mcp.log
  tail -f <PROJECT_ROOT>/servers/gmail/gmail-mcp.log
  ```

- **Config Issues**:
  ```bash
  cat <PROJECT_ROOT>/config/mcp_client_config.json
  chmod 600 <PROJECT_ROOT>/config/mcp_client_config.json
  cat <PROJECT_ROOT>/servers/gmail/smtp_config.json
  chmod 600 <PROJECT_ROOT>/servers/gmail/smtp_config.json
  ```

- **Filesystem Access**:
  ```bash
  ls -ld <PROJECT_ROOT>/test
  mkdir -p <PROJECT_ROOT>/test
  chmod 755 <PROJECT_ROOT>/test
  ```

- **Database Access**:
  ```bash
  ls -l <PROJECT_ROOT>/{conversation.db,candidates.db}
  chmod 644 <PROJECT_ROOT>/{conversation.db,candidates.db}
  ```

- **SMTP Issues**:
  - Ensure `smtp_config.json` has valid credentials.
  - Verify Gmail’s [Less Secure Apps](https://myaccount.google.com/lesssecureapps) or App Password settings.
  - Test SMTP connection:
    ```bash
    python -c "import smtplib; s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login('your.email@gmail.com', 'your-app-specific-password')"
    ```

- **AWS Credentials**:
  ```bash
  cat ~/.aws/credentials
  chmod 600 ~/.aws/credentials
  ```

- **ngrok URL Expired**:
  Update `mcpServers.master-server.url` in `mcp_client_config.json`:
  ```bash
  nano <PROJECT_ROOT>/config/mcp_client_config.json
  ```

## Dependencies

See `requirements.txt` for a full list:
```
fastmcp
streamlit==1.38.0
anthropic==0.34.2
anyio==4.6.0
pydantic==2.9.2
boto3==1.35.24
google-auth==2.35.0
google-auth-oauthlib==1.2.1
google-auth-httplib2==0.2.0
google-api-python-client==2.149.0
```

**Note**: Replace `fastmcp` with its installation source if not on PyPI. The Gmail subserver uses SMTP, so Google API packages may not be required if solely using SMTP; remove them from `requirements.txt` if unused.

## Contributing

Submit issues or pull requests to the project repository (if applicable). Ensure code changes align with the existing FastMCP framework and configuration structure.
