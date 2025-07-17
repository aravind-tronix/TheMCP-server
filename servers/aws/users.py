from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from .utils import get_aws_session, handle_aws_error
import json

mcp = FastMCP("IAMUsers")


class CreateUserArgs(BaseModel):
    username: str = Field(description="IAM username to create")


class ListUsersArgs(BaseModel):
    max_items: Optional[int] = Field(
        default=100, description="Maximum number of users to return")


class UpdateUserArgs(BaseModel):
    username: str = Field(description="IAM username to update")
    new_username: Optional[str] = Field(
        default=None, description="New username (optional)")


class DeleteUserArgs(BaseModel):
    username: str = Field(description="IAM username to delete")


@mcp.tool()
async def create_iam_user(args: Dict[str, Any]) -> str:
    """Create an IAM user."""
    try:
        parsed = CreateUserArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.create_user(UserName=parsed.username)
        return json.dumps({"username": response["User"]["UserName"], "arn": response["User"]["Arn"]})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def list_iam_users(args: Dict[str, Any]) -> str:
    """List IAM users in the AWS account."""
    try:
        parsed = ListUsersArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.list_users(MaxItems=parsed.max_items)
        users = [user["UserName"] for user in response["Users"]]
        return json.dumps({"users": users})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def update_iam_user(args: Dict[str, Any]) -> str:
    """Update an IAM user’s name."""
    try:
        parsed = UpdateUserArgs(**args)
        iam_client = get_aws_session().client("iam")
        if parsed.new_username:
            response = iam_client.update_user(
                UserName=parsed.username, NewUserName=parsed.new_username)
            return json.dumps({"message": f"User {parsed.username} updated to {parsed.new_username}"})
        return json.dumps({"message": f"No changes applied to user {parsed.username}"})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def delete_iam_user(args: Dict[str, Any]) -> str:
    """Delete an IAM user."""
    try:
        parsed = DeleteUserArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.delete_user(UserName=parsed.username)
        return json.dumps({"message": f"User {parsed.username} deleted"})
    except Exception as e:
        return json.dumps(handle_aws_error(e))
