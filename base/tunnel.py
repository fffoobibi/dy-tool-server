# filepath: d:\work\local-browser\base\tunnel.py
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Dict, Any, Optional, Set
from loguru import logger
from utils.redis import get_redis
from .registry import BaseRegistry


class BaseTunnel(BaseRegistry):
    """隧道服务基础抽象类"""

    def __init__(
        self, proxy_name: str, local_port: int, local_ip: str = "127.0.0.1", **kwargs
    ):
        self.proxy_name = proxy_name
        self.local_port = local_port
        self.local_ip = local_ip
        self.redis_client = get_redis()
        self._process = None

        # 子类可以重写这些属性
        self.redis_key_prefix = "tunnel"
        self.redis_port_key = f"{self.redis_key_prefix}:used_ports"

    def __del__(self):
        """析构函数，确保资源清理"""
        self.stop()

    @cached_property
    def remote_port(self) -> Optional[int]:
        """获取远程端口，如果隧道未运行则返回 None"""
        if self.is_running:
            return self.get_remote_port()
        return None

    @property
    def is_running(self) -> bool:
        """检查隧道是否正在运行"""
        return self._process is not None and self._process.poll() is None

    @abstractmethod
    def start(self) -> bool:
        """启动隧道服务"""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """停止隧道服务"""
        pass

    @abstractmethod
    def get_remote_port(self) -> int:
        """获取远程端口"""
        pass

    @abstractmethod
    def get_tunnel_info(self) -> Dict[str, Any]:
        """获取隧道信息"""
        pass

    @abstractmethod
    def get_allowed_ports(self) -> range:
        """获取允许使用的端口范围 - 子类必须实现"""
        pass

    def _get_available_port(self, suggested_port: Optional[int] = None) -> int:
        """获取一个可用的端口"""
        used_ports = self._get_used_ports()
        allowed_ports = self.get_allowed_ports()

        # 如果提供了建议端口，优先使用
        if suggested_port is not None:
            if suggested_port not in used_ports and suggested_port in allowed_ports:
                self._reserve_port(suggested_port)
                return suggested_port

        # 随机选择一个可用端口
        available_ports = [port for port in allowed_ports if port not in used_ports]

        if not available_ports:
            raise ValueError("没有可用的远程端口")

        import random

        selected_port = random.choice(available_ports)
        self._reserve_port(selected_port)
        return selected_port

    def verify_config(self) -> bool:
        """验证配置是否正确"""
        try:
            # 基础验证
            if not self.proxy_name:
                logger.error("代理名称不能为空")
                return False

            if not (1 <= self.local_port <= 65535):
                logger.error(f"本地端口 {self.local_port} 无效")
                return False

            return True
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取隧道状态"""
        return {
            "proxy_name": self.proxy_name,
            "local_ip": self.local_ip,
            "local_port": self.local_port,
            "is_running": self.is_running,
            "remote_port": self.remote_port if self.is_running else None,
        }

    # 端口管理相关方法
    def _get_used_ports(self) -> Set[int]:
        """从 Redis 获取已使用的端口"""
        try:
            used_ports_str = self.redis_client.smembers(self.redis_port_key)
            return {int(port) for port in used_ports_str}
        except Exception as e:
            logger.warning(f"获取已使用端口失败: {e}")
            return set()

    def _reserve_port(self, port: int) -> bool:
        """预留端口"""
        try:
            # 将端口添加到已使用端口集合
            self.redis_client.sadd(self.redis_port_key, port)

            # 为代理分配端口
            assigned_port_key = f"{self.redis_key_prefix}:proxy:{self.proxy_name}:port"
            self.redis_client.set(assigned_port_key, port)

            # 设置过期时间（防止僵尸端口）
            self.redis_client.expire(assigned_port_key, 86400)  # 24小时

            logger.debug(f"为代理 {self.proxy_name} 预留端口: {port}")
            return True
        except Exception as e:
            logger.error(f"预留端口失败: {e}")
            return False

    def _release_port(self, port: int) -> bool:
        """释放端口"""
        try:
            # 从已使用端口集合中移除
            self.redis_client.srem(self.redis_port_key, port)

            # 删除代理端口分配
            assigned_port_key = f"{self.redis_key_prefix}:proxy:{self.proxy_name}:port"
            self.redis_client.delete(assigned_port_key)

            logger.debug(f"释放端口: {port}")
            return True
        except Exception as e:
            logger.error(f"释放端口失败: {e}")
            return False

    def _get_assigned_port(self) -> Optional[int]:
        """获取已分配的端口"""
        try:
            assigned_port_key = f"{self.redis_key_prefix}:proxy:{self.proxy_name}:port"
            assigned_port = self.redis_client.get(assigned_port_key)
            return int(assigned_port) if assigned_port else None
        except Exception as e:
            logger.warning(f"获取已分配端口失败: {e}")
            return None

    @classmethod
    def clear_all_ports(cls, redis_key_prefix: str = "tunnel") -> bool:
        """清空所有端口Redis信息"""
        try:
            redis_client = get_redis()
            redis_port_key = f"{redis_key_prefix}:used_ports"

            # 删除所有已使用端口集合
            redis_client.delete(redis_port_key)

            # 删除所有代理端口分配
            proxy_keys = redis_client.keys(f"{redis_key_prefix}:proxy:*:port")
            if proxy_keys:
                redis_client.delete(*proxy_keys)
                logger.info(f"清空了 {len(proxy_keys)} 个代理端口分配")

            logger.info(f"已清空所有 {redis_key_prefix} 端口Redis信息")
            return True
        except Exception as e:
            logger.error(f"清空端口信息失败: {e}")
            return False

    @classmethod
    def get_all_port_info(cls, redis_key_prefix: str = "tunnel") -> Dict[str, Any]:
        """获取所有端口分配信息"""
        try:
            redis_client = get_redis()
            redis_port_key = f"{redis_key_prefix}:used_ports"

            # 获取已使用的端口
            used_ports_str = redis_client.smembers(redis_port_key)
            used_ports = [int(port) for port in used_ports_str]

            result = {
                "used_ports": used_ports,
                "proxy_allocations": {},
            }

            # 获取所有代理端口分配
            proxy_keys = redis_client.keys(f"{redis_key_prefix}:proxy:*:port")
            for key in proxy_keys:
                # 提取代理名称: prefix:proxy:proxy_name:port -> proxy_name
                parts = key.split(":")
                if len(parts) >= 4:
                    proxy_name = parts[2]
                    port = redis_client.get(key)
                    if port:
                        result["proxy_allocations"][proxy_name] = int(port)

            return result
        except Exception as e:
            logger.error(f"获取端口信息失败: {e}")
            return {"used_ports": [], "proxy_allocations": {}}
