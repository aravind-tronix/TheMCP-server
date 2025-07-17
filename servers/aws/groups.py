from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from .utils import get_aws_session, handle_aws_error
import json

mcp = FastMCP("IAMGroups")


class CreateGroupArgs(BaseModel):
    group_name: str = Field(description="IAM group name to create")


class ListGroupsArgs(BaseModel):
    max_items: Optional[int] = Field(
        default=100, description="Maximum number of groups to return")


class AddUserToGroupArgs(BaseModel):
    group_name: str = Field(description="IAM group name")
    username: str = Field(description="IAM username to add to group")


class RemoveUserFromGroupArgs(BaseModel):
    group_name: str = Field(description="IAM group name")
    username: str = Field(description="IAM username to remove from group")


@mcp.tool()
async def create_iam_group(args: Dict[str, Any]) -> str:
    """Create an IAM group."""
    try:
        parsed = CreateGroupArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.create_group(GroupName=parsed.group_name)
        return json.dumps({"group_name": response["Group"]["GroupName"], "arn": response["Group"]["Arn"]})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def list_iam_groups(args: Dict[str, Any]) -> str:
    """List IAM groups in the AWS account."""
    try:
        parsed = ListGroupsArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.list_groups(MaxItems=parsed.max_items)
        groups = [group["GroupName"] for group in response["Groups"]]
        return json.dumps({"groups": groups})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def add_user_to_group(args: Dict[str, Any]) -> str:
    """Add an IAM user to a group."""
    try:
        parsed = AddUserToGroupArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.add_user_to_group(
            GroupName=parsed.group_name, UserName=parsed.username)
        return json.dumps({"message": f"User {parsed.username} added to group {parsed.group_name}"})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def remove_user_from_group(args: Dict[str, Any]) -> str:
    """Remove an IAM user from a group."""
    try:
        parsed = RemoveUserFromGroupArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.remove_user_from_group(
            GroupName=parsed.group_name, UserName=parsed.username)
        return json.dumps({"message": f"User {parsed.username} removed from group {parsed.group_name}"})
    except Exception as e:
        return json.dumps(handle_aws_error(e))
