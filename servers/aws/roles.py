from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
from .utils import get_aws_session, handle_aws_error

mcp = FastMCP("IAMRoles")


class CreateRoleArgs(BaseModel):
    role_name: str = Field(description="IAM role name to create")
    trust_policy: Dict[str, Any] = Field(description="Trust policy document")


class ListRolesArgs(BaseModel):
    max_items: Optional[int] = Field(
        default=100, description="Maximum number of roles to return")


class DeleteRoleArgs(BaseModel):
    role_name: str = Field(description="IAM role name to delete")


@mcp.tool()
async def create_iam_role(args: Dict[str, Any]) -> str:
    """Create an IAM role with a trust policy."""
    try:
        parsed = CreateRoleArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.create_role(
            RoleName=parsed.role_name,
            AssumeRolePolicyDocument=json.dumps(parsed.trust_policy)
        )
        return json.dumps({"role_name": response["Role"]["RoleName"], "arn": response["Role"]["Arn"]})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def list_iam_roles(args: Dict[str, Any]) -> str:
    """List IAM roles in the AWS account."""
    try:
        parsed = ListRolesArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.list_roles(MaxItems=parsed.max_items)
        roles = [role["RoleName"] for role in response["Roles"]]
        return json.dumps({"roles": roles})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def delete_iam_role(args: Dict[str, Any]) -> str:
    """Delete an IAM role."""
    try:
        parsed = DeleteRoleArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.delete_role(RoleName=parsed.role_name)
        return json.dumps({"message": f"Role {parsed.role_name} deleted"})
    except Exception as e:
        return json.dumps(handle_aws_error(e))
