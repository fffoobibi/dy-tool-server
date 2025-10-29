import requests
import asyncio

from typing import Annotated
from loguru import logger

from fastmcp import FastMCP

__all__ = ("mediamz_mcp",)

mediamz_mcp = FastMCP("Mediamz MCP Server")


@mediamz_mcp.tool
async def get_influence_resource_email_count(
    create_time: Annotated[str, "日期时间,格式为%Y-%m-%d %H:%M:%S"],
) -> int:
    """
    根据创建时间获取influencer的邮箱数量
    """

    def req():
        resp = requests.post(
            "http://36.32.174.26:5059/mcp/tblinfluencerextension-email-count",
            json={
                "create_time": create_time,
            },
            headers={"skip-verify": "asdf1asdf-0a8df==asdfi1n"},
        )
        return resp.json()["resp"]

    result = await asyncio.to_thread(req)
    return result.get("count", 0)


@mediamz_mcp.tool
async def get_influence_resource_scraped_count(
    create_time: Annotated[str, "日期时间,格式为%Y-%m-%d %H:%M:%S"],
) -> int:
    """
    根据创建时间获取新增采集红人资源数量
    """

    def req():
        resp = requests.post(
            "http://36.32.174.26:5059/mcp/tblinfluencerextension-scraped-count",
            json={
                "create_time": create_time,
            },
            headers={"skip-verify": "asdf1asdf-0a8df==asdfi1n"},
        )
        return resp.json()["resp"]           

    result = await asyncio.to_thread(req)
    return result.get("count", 0)


@mediamz_mcp.tool
async def get_total_resource(
    create_time: Annotated[str, "日期时间,格式为%Y-%m-%d %H:%M:%S"],
) -> dict:
    """
    根据创建时间获取新增入库红人数量
    """

    def req():
        resp = requests.post(
            "http://36.32.174.26:5059/mcp/total-resource",
            json={
                "create_time": create_time,
            },
            headers={"skip-verify": "asdf1asdf-0a8df==asdfi1n"},
        )
        return resp.json()["resp"]

    result = await asyncio.to_thread(req)
    return result
