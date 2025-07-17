from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
from .utils import get_aws_session, handle_aws_error

mcp = FastMCP("IAMPolicies")


class CreatePolicyArgs(BaseModel):
    policy_name: str = Field(description="IAM policy name to create")
    policy_document: Dict[str, Any] = Field(description="Policy document")


class ListPoliciesArgs(BaseModel):
    max_items: Optional[int] = Field(
        default=100, description="Maximum number of policies to return")
    scope: str = Field(default="All", description="Scope: All, AWS, Local")


class DeletePolicyArgs(BaseModel):
    policy_arn: str = Field(description="IAM policy ARN to delete")


@mcp.tool()
async def create_iam_policy(args: Dict[str, Any]) -> str:
    """Create an IAM policy."""
    try:
        parsed = CreatePolicyArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.create_policy(
            PolicyName=parsed.policy_name,
            PolicyDocument=json.dumps(parsed.policy_document)
        )
        return json.dumps({"policy_name": response["Policy"]["PolicyName"], "arn": response["Policy"]["Arn"]})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def list_iam_policies(args: Dict[str, Any]) -> str:
    """List IAM policies in the AWS account."""
    try:
        parsed = ListPoliciesArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.list_policies(
            Scope=parsed.scope, MaxItems=parsed.max_items)
        policies = [{"PolicyName": policy["PolicyName"], "Arn": policy["Arn"]}
                    for policy in response["Policies"]]
        return json.dumps({"policies": policies})
    except Exception as e:
        return json.dumps(handle_aws_error(e))


@mcp.tool()
async def delete_iam_policy(args: Dict[str, Any]) -> str:
    """Delete an IAM policy."""
    try:
        parsed = DeletePolicyArgs(**args)
        iam_client = get_aws_session().client("iam")
        response = iam_client.delete_policy(PolicyArn=parsed.policy_arn)
        return json.dumps({"message": f"Policy {parsed.policy_arn} deleted"})
    except Exception as e:
        return json.dumps(handle_aws_error(e))
