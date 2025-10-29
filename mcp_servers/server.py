import time
import httpx
import requests
import asyncio
import anyio

from typing import Annotated

from fastmcp import FastMCP, Context
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from contextlib import asynccontextmanager
from utils.args import args_builder
from playwright.async_api import async_playwright

from loguru import logger

"""
SELECT count(DISTINCT url) FROM `tblinfluencerextension` WHERE create_time >= "2025-08-01 00:00:00" AND (contact IS NOT NULL OR other_contact IS NOT NULL)

"""


class BrowserInstanceManager:
    """浏览器实例管理器"""

    def __init__(self, max_instances=10, cache_timeout=300):
        self.max_instances = max_instances
        self.cache_timeout = cache_timeout

        # 创建异步信号量，限制最大并发实例数
        self.instance_semaphore = asyncio.Semaphore(max_instances)
        # 跟踪当前活跃实例数
        self.current_instances = 0
        self.instance_lock = asyncio.Lock()
        # 实例缓存字典
        self.instance_cache = {}
        self.cache_lock = asyncio.Lock()

    async def create_instance(self) -> tuple[str, str]:
        """创建浏览器实例，支持缓存复用"""
        instance_id = f"bs_{self.current_instances}_{int(time.time())}"

        async with self.cache_lock:
            # 检查缓存中是否有可用实例
            for cached_id, cached_instance in self.instance_cache.items():
                if not cached_instance.get("in_use", False):
                    cached_instance["in_use"] = True
                    logger.debug(f"复用缓存实例: {cached_id}")
                    return cached_id, cached_instance["data"]

            # 创建浏览器 - 使用异步HTTP请求
            logger.info(f"http://127.0.0.1:{args_builder.port}/browser/launch")

            try:
                async with httpx.AsyncClient(verify=False) as client:
                    response = await client.post(
                        f"http://127.0.0.1:{args_builder.port}/browser/launch",
                        json={
                            "browser_cache_dir": instance_id,
                            "headless": False,
                            "window_size": "1920,1080",
                            "proxy": None,
                            "type": 1,
                            "disable_image": False,
                        },
                        headers={
                            "content-type": "application/json",
                            "skip-auth-token": "mcjniasidf--===skldkdjflkjsdf--===",
                        },
                    )
                    response.raise_for_status()  # 检查HTTP状态码
                    resp = response.json()
            except Exception as e:
                logger.error(f"创建浏览器实例失败: {e}")
                raise RuntimeError(f"创建浏览器实例失败: {str(e)}")

            logger.info(f"Launch response: {resp}")
            new_instance = {
                "created_at": time.time(),
                "in_use": True,
                "data": "http://localhost:" + resp["resp"]["address"].split(":")[-1],
            }
            self.instance_cache[instance_id] = new_instance
            logger.debug(f"创建新实例: {instance_id}")
            return instance_id, new_instance["data"]

    async def release_instance(self, instance_id):
        """释放实例，标记为可复用"""
        async with self.cache_lock:
            if instance_id in self.instance_cache:
                self.instance_cache[instance_id]["in_use"] = False
                logger.debug(f"释放实例到缓存: {instance_id}")

    async def cleanup_cache(self):
        """清理超时的缓存实例"""
        current_time = time.time()

        async with self.cache_lock:
            expired_keys = []
            for instance_id, instance_data in self.instance_cache.items():
                if (
                    not instance_data["in_use"]
                    and (current_time - instance_data["created_at"])
                    > self.cache_timeout
                ):
                    expired_keys.append(instance_id)

            for key in expired_keys:
                del self.instance_cache[key]
                logger.debug(f"清理过期实例: {key}")

    @asynccontextmanager
    async def get_instance_browser(self):
        """获取浏览器实例的异步上下文管理器"""
        # 初始化变量，避免 UnboundLocalError
        instance_id = None
        browser_instance = None

        # 使用异步信号量
        await self.instance_semaphore.acquire()
        try:
            async with self.instance_lock:
                self.current_instances += 1
                logger.debug(
                    f"获取浏览器实例，当前实例数: {self.current_instances}/{self.max_instances}"
                )

            # 使用异步的 create_instance
            instance_id, browser_instance = await self.create_instance()
            yield instance_id, browser_instance

        finally:
            # 只有当 instance_id 被成功赋值时才释放实例
            if instance_id is not None:
                await self.release_instance(instance_id)

            # 释放资源
            async with self.instance_lock:
                self.current_instances -= 1
                logger.debug(
                    f"释放浏览器实例，当前实例数: {self.current_instances}/{self.max_instances}"
                )

            # 释放异步信号量
            self.instance_semaphore.release()

    async def get_current_instance_count(self):
        """获取当前活跃实例数"""
        async with self.instance_lock:
            return self.current_instances


# 创建全局实例管理器
browser_manager = BrowserInstanceManager(max_instances=10)


verifier = StaticTokenVerifier(
    tokens={
        "dev-alice-token": {
            "client_id": "alice@company.com",
            "scopes": ["read:data", "write:data", "admin:users"],
        },
        "dev-guest-token": {"client_id": "guest-user", "scopes": ["read:data"]},
    },
    required_scopes=["read:data"],
)

mcp = FastMCP("Browser MCP Server")


@mcp.tool
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
        logger.info("respoonse ", resp.text)
        return resp.json()["resp"]

    result = await asyncio.to_thread(req)
    return result.get("count", 0)


@mcp.tool
async def get_total_resource(
    create_time: Annotated[str, "日期时间,格式为%Y-%m-%d %H:%M:%S"],
) -> dict:
    """
    根据创建时间获取新增红人数量
    """

    def req():
        resp = requests.post(
            "http://36.32.174.26:5059/mcp/total-resource",
            json={
                "create_time": create_time,
            },
            headers={"skip-verify": "asdf1asdf-0a8df==asdfi1n"},
        )
        logger.info("respoonse ", resp.text)
        return resp.json()["resp"]
    result = await asyncio.to_thread(req)
    return result


@mcp.tool
async def crawl(
    url: Annotated[str, "需要抓取的url"],
    selector: Annotated[str | None, "playwright选择器"],
    ctx: Context,
) -> str:
    """
    使用 Playwright 抓取指定 URL 的内容
    """
    logger.debug(f"crawl url: {url}")
    async with browser_manager.get_instance_browser() as (instance_id, cdp_url):
        logger.debug(f"instance id {instance_id}, cdp url {cdp_url}")
        # result = await ctx.elicit(f"crawl url is {url}", response_type=str)
        # if result.action == "accept":
        #     url = result.data
        #     logger.info(f"User accepted the URL: {url}")
        await ctx.info(f"crawl url {url}")
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(cdp_url)
            page = await browser.new_page()
            await page.goto(url)
            if selector is None:
                content = await page.content()
            else:
                content = await page.locator(selector).inner_html()
            await page.close()
        return content


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="localhost", port=8000)
