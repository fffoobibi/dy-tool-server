import time
import httpx
import threading
import hashlib
from contextlib import contextmanager


from utils.local_storage import storage
from typing_extensions import TypedDict
from urllib.parse import urlparse
from loguru import logger

HOUR = 3600
DAY = 3600 * 24
WEEK = 3600 * 24 * 7
MONTH = 3600 * 24 * 30


TIMEZONE = int | str
PROXY_SERVER = str | None
PROXY_AUTH = str | None


class ProxyInfo(TypedDict):
    ip: str
    city: str
    region: str
    country: str
    loc: str
    org: str
    postal: str
    timezone: str
    readme: str
    detected_at: int  # 时间戳
    ip_checked: str  # 检测的 IP 地址


class FailedProxyInfo(TypedDict):
    error: str
    ip_checked: str
    detected_at: int  # 时间戳


# 全局锁字典，用于保存每个IP的锁
_ip_locks = {}
_locks_lock = threading.Lock()  # 用于保护 _ip_locks 字典的访问


@contextmanager
def ip_lock(ip_key: str, timeout: int = 30):
    """
    为指定的IP获取锁的上下文管理器

    Args:
        ip_key: IP地址或标识符
        timeout: 获取锁的超时时间（秒）

    Yields:
        None: 当获取到锁时

    Raises:
        TimeoutError: 如果在指定的超时时间内无法获取锁
    """
    # 创建锁的唯一标识
    lock_key = hashlib.md5(ip_key.encode()).hexdigest()

    # 获取或创建对应的锁对象（线程安全）
    with _locks_lock:
        if lock_key not in _ip_locks:
            _ip_locks[lock_key] = threading.RLock()  # 使用可重入锁
        lock = _ip_locks[lock_key]

    # 尝试获取锁，超时则抛出异常
    start_time = time.time()
    last_log_time = start_time

    while True:
        if lock.acquire(False):  # 尝试非阻塞获取
            try:
                logger.debug(f"成功获取IP锁: {ip_key}")
                yield  # 返回控制权给使用者
            finally:
                lock.release()
                logger.debug(f"已释放IP锁: {ip_key}")
            return

        # 检查是否超时
        current_time = time.time()
        if current_time - start_time > timeout:
            logger.error(f"获取IP锁超时: {ip_key}, 超时: {timeout}秒")
            raise TimeoutError(f"获取IP锁超时: {ip_key}, 超时: {timeout}秒")

        # 每5秒输出一次等待日志
        if current_time - last_log_time > 5:
            logger.debug(
                f"正在等待IP锁: {ip_key}, 已等待: {round(current_time - start_time, 1)}秒"
            )
            last_log_time = current_time

        # 短暂等待后重试
        time.sleep(0.1)


class ProxyService:

    def _ipinfo(self):
        try:
            logger.info("正在获取本机 IP 信息...")
            resp = httpx.get(
                "https://ipinfo.io/json",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.error(f"获取 ipinfo.io 数据失败: {e}")
            return {"error": str(e)}

    def detect_from_ipinfo_current(
        self, cache_ttl: int = 0
    ) -> tuple[bool, ProxyInfo | FailedProxyInfo]:
        """
        检测当前机器的 IP 信息.

        :param cache_ttl: 缓存时间（秒），0表示不缓存
        :return: ProxyInfo 或 FailedProxyInfo 字典
        """
        ip_key = "current"

        with ip_lock(ip_key, timeout=30):
            cache_key = f"ipinfo_current.json"
            # 检查缓存
            if cache_ttl > 0:
                cached_data = storage.get(cache_key)
                if cached_data is not None:
                    logger.debug(f"从缓存获取当前IP信息")
                    return True, cached_data
            try:
                result = self._ipinfo()
                if "error" in result:
                    return False, {
                        "error": result["error"],
                        "ip_checked": "current",
                        "detected_at": int(time.time()),
                    }

                # 添加检测时间戳
                result["detected_at"] = int(time.time())
                result["ip_checked"] = "current"

                # 缓存结果
                if cache_ttl > 0:
                    storage.set(cache_key, result, cache_ttl=cache_ttl)

                return True, result
            except Exception as e:
                return False, {
                    "error": f"Unexpected error: {str(e)}",
                    "ip_checked": "current",
                    "detected_at": int(time.time()),
                }

    def detect_from_ipinfo(
        self, ip: str, cache_ttl: int = 0
    ) -> tuple[bool, ProxyInfo | FailedProxyInfo]:
        """
        从 ipinfo.io 检测代理信息.

        :param ip: 要检测的 IP 地址
        :param cache_ttl: 缓存时间（秒），0表示不缓存
        :return: ProxyInfo 或 FailedProxyInfo 字典

        ```json
        {
            "ip": "8.222.196.42",
            "city": "Singapore",
            "region": "Singapore",
            "country": "SG",
            "loc": "1.2897,103.8501",
            "org": "AS45102 Alibaba (US) Technology Co., Ltd.",
            "postal": "018989",
            "timezone": "Asia/Singapore",
            "readme": "https://ipinfo.io/missingauth"
            }
        ```
        """
        with ip_lock(ip, timeout=30):
            cache_key = f"ipinfo_{ip}.json"

            # 检查缓存
            if cache_ttl > 0:
                cached_data = storage.get(cache_key)
                if cached_data is not None:
                    logger.debug(f"从缓存获取IP信息: {ip}")
                    return cached_data

            try:
                logger.info(f"正在检测 IP: {ip} 的信息...")
                url = f"https://ipinfo.io/{ip}/json"
                response = httpx.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    result = response.json()

                    # 添加检测时间戳
                    import time

                    result["detected_at"] = int(time.time())
                    result["ip_checked"] = ip

                    # 缓存结果
                    if cache_ttl > 0:
                        storage.set(cache_key, result, cache_ttl=cache_ttl)

                    return True, result
                else:
                    error_result = {
                        "error": f"HTTP {response.status_code}: Unable to retrieve data from ipinfo.io",
                        "ip_checked": ip,
                        "detected_at": int(time.time()),
                    }
                    return False, error_result

            except httpx.TimeoutException:
                return False, {
                    "error": "Request timeout when connecting to ipinfo.io",
                    "ip_checked": ip,
                    "detected_at": int(time.time()),
                }
            except httpx.RequestError as e:
                return False, {
                    "error": f"Request error: {str(e)}",
                    "ip_checked": ip,
                    "detected_at": int(time.time()),
                }
            except Exception as e:
                return False, {
                    "error": f"Unexpected error: {str(e)}",
                    "ip_checked": ip,
                    "detected_at": int(time.time()),
                }

    def parse_proxy_info(
        self, proxy: str | None, cache_ttl: int = MONTH
    ) -> tuple[
        bool, TIMEZONE, PROXY_SERVER, PROXY_AUTH, ProxyInfo | FailedProxyInfo | None
    ]:
        """
        解析代理信息并获取时区

        Args:
            proxy: 代理服务器字符串，格式: schema://[user:pass@]host:port

        Returns:
            tuple: (flag, timezone, proxy_server, proxy_auth, info)
                - proxy_server: 不含认证信息的代理服务器地址
                - proxy_auth: 认证信息 (username:password)
                - timezone: 从IP检测服务获取的时区信息
        """
        if proxy is None:
            flag, detected = self.detect_from_ipinfo_current(cache_ttl)
            if flag:
                return True, detected.get("timezone"), None, None, detected
            else:
                return False, None, None, None, detected
        else:
            try:
                parsed = urlparse(proxy)
                proxy_auth = (
                    f"{parsed.username}:{parsed.password}"
                    if parsed.username and parsed.password
                    else None
                )
                proxy_server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
                flag, detected = self.detect_from_ipinfo(parsed.hostname, cache_ttl)
                logger.info("检测到代理 IP 信息: {}", detected)
                if flag:
                    return (
                        True,
                        detected.get("timezone") or None,
                        proxy_server,
                        proxy_auth,
                        detected,
                    )
                else:
                    return False, None, None, None, detected
            except Exception as e:
                # 解析失败时直接使用原始 proxy
                logger.warning("代理解析失败: {}", e)
                return False, None, None, None, None


proxy_service = ProxyService()
