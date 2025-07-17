import boto3
import logging
from typing import Any, Dict

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="./aws-iam-mcp.log",
    filemode="a"
)
logger = logging.getLogger("aws_iam_mcp_utils")

AWS_PROFILE = "mcp_aws"


def get_aws_session():
    """Initialize boto3 session with the configured AWS profile."""
    try:
        session = boto3.Session(profile_name=AWS_PROFILE)
        logger.info("AWS session initialized successfully")
        return session
    except Exception as e:
        logger.error(f"Failed to initialize AWS session: {str(e)}")
        raise


def handle_aws_error(e: Exception) -> Dict[str, Any]:
    """Handle AWS API errors and return JSON-serializable error response."""
    logger.error(f"AWS API error: {str(e)}")
    return {"error": str(e)}
