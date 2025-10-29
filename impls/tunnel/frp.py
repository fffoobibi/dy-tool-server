"""FRP 隧道实现"""
import os
import subprocess
import time
from loguru import logger
from typing import Dict, Any
from functools import cached_property

from constants.frp import FRP_FRP_CONFIG_PATH, FRP_FRPC_PATH, FRP_ALLOWED_PORTS
from base.tunnel import BaseTunnel


class FrpTunnel(BaseTunnel):
    """FRP 隧道实现类"""
    
    _tunnel_type = "frp"
    
    def __init__(
        self,
        proxy_name: str,
        local_port: int,
        local_ip: str = "127.0.0.1",
        admin_url: str = "http://127.0.0.1:7400",
        user: str = "admin",
        pwd: str = "admin",
    ):
        # 调用父类构造函数
        super().__init__(proxy_name, local_port, local_ip)
        
        # FRP 特有的配置
        self.admin_url = admin_url
        self.auth = (user, pwd)
        
        # 重写 Redis 键前缀为 FRP 专用
        self.redis_key_prefix = "frp"
        self.redis_port_key = f"{self.redis_key_prefix}:used_ports"

        # 兼容性：保留原有的 frpc_process 属性
        self.frpc_process = None

    @cached_property
    def allowed_remote_ports(self) -> range:
        """获取允许的远程端口范围"""
        start, end = map(int, FRP_ALLOWED_PORTS.split("-"))
        return range(start, end + 1)

    @cached_property
    def frpc_path(self) -> str:
        """获取 FRPC 可执行文件路径"""
        return FRP_FRPC_PATH

    @cached_property
    def config_path(self) -> str:
        """获取 FRP 配置文件路径"""
        return FRP_FRP_CONFIG_PATH

    @cached_property
    def frp_server_addr(self) -> str:
        """获取 FRP 服务器地址"""
        return os.getenv("APP_FRP_SERVER_ADDR", "")

    def get_allowed_ports(self) -> range:
        """获取允许使用的端口范围 - 实现基类抽象方法"""
        return self.allowed_remote_ports

    def get_remote_port(self) -> int:
        """获取远程端口 - 实现基类抽象方法"""
        assigned_port = self._get_assigned_port()
        if assigned_port:
            return assigned_port
        
        # 尝试从环境变量获取建议端口
        suggested_port = int(os.getenv("FRP_REMOTE_PORT", 6000))
        return self._get_available_port(suggested_port)

    def get_tunnel_info(self) -> Dict[str, Any]:
        """获取隧道信息 - 实现基类抽象方法"""
        return {
            "tunnel_type": self._tunnel_type,
            "proxy_name": self.proxy_name,
            "local_ip": self.local_ip,
            "local_port": self.local_port,
            "remote_port": self.get_remote_port() if self.is_running else None,
            "server_addr": self.frp_server_addr,
            "admin_url": self.admin_url,
            "is_running": self.is_running,
            "config_path": self.config_path,
            "frpc_path": self.frpc_path,
        }

    def start(self) -> bool:
        """启动 FRPC 进程 - 实现基类抽象方法"""
        try:
            if self._process is None:
                logger.debug(f"正在启动 FRPC 进程: {self.frpc_path} -c {self.config_path}")
                self._process = subprocess.Popen(
                    [self.frpc_path, "-c", self.config_path],
                    env=self._build_env(),
                    text=True,
                    encoding="utf8",
                    cwd=os.path.dirname(self.frpc_path),
                )
                self.frpc_process = self._process  # 保持向后兼容
                logger.debug(
                    f"{self.proxy_name} FRPC 已启动: {self._process.pid}, "
                    f"本地端口: {self.local_port}, 远程端口: {self.get_remote_port()}"
                )
                # 等待进程启动
                time.sleep(2)
                return True
            else:
                logger.warning("FRPC 已在运行中")
                return False
        except Exception as e:
            logger.error(f"启动 FRPC 失败: {e}")
            return False

    def stop(self) -> bool:
        """停止 frpc 进程并释放端口 - 实现基类抽象方法"""
        try:
            if self._process:
                logger.debug("正在停止 frpc 进程...")
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
                self._process = None
                self.frpc_process = None  # 保持向后兼容
                logger.debug("frpc 进程已停止")

            # 释放端口
            try:
                current_port = self._get_assigned_port()
                if current_port:
                    self._release_port(current_port)
            except Exception as e:
                logger.warning(f"释放端口时出错: {e}")

            return True
        except Exception as e:
            logger.error(f"停止 FRPC 失败: {e}")
            return False

    def verify_config(self) -> bool:
        """验证 FRP 配置"""
        if not super().verify_config():
            return False
            
        try:
            # FRP 特有的验证
            if not os.path.exists(self.frpc_path):
                logger.error(f"FRPC 可执行文件不存在: {self.frpc_path}")
                return False
                
            if not os.path.exists(self.config_path):
                logger.error(f"FRP 配置文件不存在: {self.config_path}")
                return False
                
            if not self.frp_server_addr:
                logger.error("FRP 服务器地址未配置")
                return False
                
            return True
        except Exception as e:
            logger.error(f"FRP 配置验证失败: {e}")
            return False

    def _build_env(self) -> dict:
        """构建 FRP 运行所需的环境变量"""
        cp = os.environ.copy()
        ret = {
            "APP_FRP_SERVER_ADDR": str(os.getenv("APP_FRP_SERVER_ADDR") or ""),
            "APP_FRP_SERVER_PORT": str(os.getenv("APP_FRP_SERVER_PORT") or ""),
            "APP_FRP_AUTH_TOKEN": str(os.getenv("APP_FRP_AUTH_TOKEN") or ""),
            "APP_FRP_LOCAL_IP": str(self.local_ip),
            "APP_FRP_LOCAL_PORT": str(self.local_port),
            "APP_FRP_REMOTE_PORT": str(self.get_remote_port()),
            "APP_FRP_PROXY_NAME": self.proxy_name,
        }
        cp.update(ret)
        logger.debug("构建 FRP 运行环境变量: {}", ret)
        return cp

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            # 这里可以添加具体的连接测试逻辑
            # 比如检查 FRP 服务器是否可达
            return True
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False

    @classmethod
    def clear_all_ports(cls) -> bool:
        """清空所有 FRP 端口 Redis 信息"""
        return BaseTunnel.clear_all_ports("frp")

    @classmethod
    def get_all_port_info(cls) -> dict:
        """获取所有 FRP 端口分配信息"""
        return BaseTunnel.get_all_port_info("frp")


# 为了向后兼容，保留原来的类名
Frp = FrpTunnel


if __name__ == "__main__":
    # 示例用法
    from dotenv import load_dotenv

    load_dotenv()
    frp = FrpTunnel(proxy_name="test_proxy", local_port=8080)
    try:
        if frp.verify_config():
            print("配置验证通过")
            frp.start()
            print(f"隧道信息: {frp.get_tunnel_info()}")
        else:
            print("配置验证失败")
    except Exception as e:
        logger.error(f"FRP 启动失败: {e}")
    finally:
        frp.stop()
