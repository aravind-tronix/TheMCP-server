from fastmcp import FastMCP
from pydantic import BaseModel, Field
from typing import Dict, Any
from datetime import datetime
from .utils import get_aws_session, handle_aws_error
import json

mcp = FastMCP("CostExplorer")


class GetCostDataArgs(BaseModel):
    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")
    granularity: str = Field(
        default="DAILY", description="Granularity: DAILY or MONTHLY")
    group_by: str = Field(
        default="SERVICE", description="Group by: SERVICE, REGION, or USAGE_TYPE")


@mcp.tool()
async def get_cost_data(args: Dict[str, Any]) -> str:
    """Get AWS Cost Management cost and usage data."""
    try:
        parsed = GetCostDataArgs(**args)
        ce_client = get_aws_session().client("ce")
        start = datetime.strptime(parsed.start_date, "%Y-%m-%d")
        end = datetime.strptime(parsed.end_date, "%Y-%m-%d")
        if start >= end:
            return json.dumps({"error": "start_date must be before end_date"})
        if end > datetime.now():
            return json.dumps({"error": "end_date cannot be in the future"})

        response = ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": parsed.start_date,
                "End": parsed.end_date
            },
            Granularity=parsed.granularity,
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": parsed.group_by}]
        )
        results = []
        for result in response["ResultsByTime"]:
            time_period = result["TimePeriod"]
            for group in result["Groups"]:
                results.append({
                    "TimePeriod": time_period,
                    parsed.group_by: group["Keys"][0],
                    "Cost": group["Metrics"]["UnblendedCost"]["Amount"],
                    "Currency": group["Metrics"]["UnblendedCost"]["Unit"]
                })
        return json.dumps({"costs": results})
    except Exception as e:
        return json.dumps(handle_aws_error(e))
