import logging
import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Any, Dict

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="./gmail-mcp.log",
    filemode="a"
)
logger = logging.getLogger("gmail_mcp_utils")

CREDS_FILE_PATH = "/mnt/d/linux/TheMCP/servers/gmail/credentials.json"
TOKEN_PATH = "/mnt/d/linux/TheMCP/servers/gmail/token.json"
SMTP_CONFIG_PATH = "/mnt/d/linux/TheMCP/servers/gmail/smtp_config.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def load_smtp_config() -> Dict[str, Any]:
    """Load SMTP configuration from smtp_config.json."""
    try:
        if not os.path.exists(SMTP_CONFIG_PATH):
            raise FileNotFoundError(
                f"SMTP config file not found: {SMTP_CONFIG_PATH}")
        with open(SMTP_CONFIG_PATH, "r") as f:
            config = json.load(f)
        required_keys = ["smtp_server", "smtp_port", "email", "app_password"]
        if not all(key in config for key in required_keys):
            raise ValueError(f"Missing required keys in {SMTP_CONFIG_PATH}")
        logger.info("SMTP configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"Failed to load SMTP config: {str(e)}")
        raise


def validate_pdf_attachment(attachment_path: str) -> str:
    """Validate PDF attachment path and ensure it’s readable."""
    try:
        if not attachment_path.endswith(".pdf"):
            raise ValueError("Attachment must be a PDF file")
        if not os.path.exists(attachment_path):
            raise FileNotFoundError(f"PDF file not found: {attachment_path}")
        if not os.access(attachment_path, os.R_OK):
            raise PermissionError(f"Cannot read PDF file: {attachment_path}")
        logger.info(f"PDF attachment validated: {attachment_path}")
        return os.path.basename(attachment_path)
    except Exception as e:
        logger.error(f"Failed to validate PDF attachment: {str(e)}")
        raise


def get_gmail_service() -> Any:
    """Initialize Gmail API service with OAuth2 credentials."""
    try:
        creds = None
        if os.path.exists(TOKEN_PATH):
            logger.info("Loading token from file")
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing token")
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDS_FILE_PATH):
                    raise FileNotFoundError(
                        f"Credentials file not found: {CREDS_FILE_PATH}")
                logger.info("Fetching new token")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDS_FILE_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(TOKEN_PATH, "w") as token_file:
                    token_file.write(creds.to_json())
                logger.info(f"Token saved to {TOKEN_PATH}")
                os.chmod(TOKEN_PATH, 0o600)

        service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail service initialized")
        return service
    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {str(e)}")
        raise


def get_user_email(service: Any) -> str:
    """Get user email address."""
    try:
        profile = service.users().getProfile(userId="me").execute()
        user_email = profile.get("emailAddress", "")
        logger.info(f"User email retrieved: {user_email}")
        return user_email
    except HttpError as e:
        logger.error(f"Failed to get user email: {str(e)}")
        raise


def handle_gmail_error(e: Exception) -> Dict[str, Any]:
    """Handle Gmail API errors and return JSON-serializable error response."""
    logger.error(f"Gmail API error: {str(e)}")
    return {"error": str(e)}
