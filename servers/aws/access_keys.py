from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from .utils import get_aws_session, handle_aws_error
import json

mcp = FastMCP("IAMAccessKeys")


class CreateAccessKeyArgs(BaseModel):
    username: str = Field(description="IAM username to create access key for")


class ListAccessKeysArgs(BaseModel):
    username: str = Field(description="IAM username to list access keys for")


class DeleteAccessKeyArgs(BaseModel):
    username: str = Field(description="IAM username")
    access_key_id: str = Field(description="Access key ID to delete")


@mcp.tool()
async def create_access_key(args: Dict[str, Any]) -> str:
    """Create an IAM access key for a user."""
    try:
        parsed = CreateAccessKeyArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.create_access_key(UserName=parsed.username)
        return json.dumps({
            "access_key_id": response["AccessKey"]["AccessKeyId"],
            "secret_access_key": response["AccessKey"]["SecretAccessKey"]
        })
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def list_access_keys(args: Dict[str, Any]) -> str:
    """List IAM access keys for a user."""
    try:
        parsed = ListAccessKeysArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.list_access_keys(UserName=parsed.username)
        keys = [{"AccessKeyId": key["AccessKeyId"], "Status": key["Status"]}
                for key in response["AccessKeyMetadata"]]
        return json.dumps({"access_keys": keys})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def delete_access_key(args: Dict[str, Any]) -> str:
    """Delete an IAM access key for a user."""
    try:
        parsed = DeleteAccessKeyArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.delete_access_key(
            UserName=parsed.username, AccessKeyId=parsed.access_key_id)
        return json.dumps({"message": f"Access key {parsed.access_key_id} deleted for user {parsed.username}"})
    except Exception as e:
        return json.dumps(handle_aws_error(e))
