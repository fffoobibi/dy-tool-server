"""Ngrok 隧道实现示例"""
import subprocess
import time
from loguru import logger
from typing import Dict, Any

from base.tunnel import BaseTunnel


class NgrokTunnel(BaseTunnel):
    """Ngrok 隧道实现类"""
    
    _tunnel_type = "ngrok"
    
    def __init__(
        self,
        proxy_name: str,
        local_port: int,
        local_ip: str = "127.0.0.1",
        auth_token: str = "",
    ):
        super().__init__(proxy_name, local_port, local_ip)
        
        self.auth_token = auth_token
        self.redis_key_prefix = "ngrok"
        self.redis_port_key = f"{self.redis_key_prefix}:used_ports"
        self._tunnel_url = None

    def get_allowed_ports(self) -> range:
        """Ngrok 不限制端口范围"""
        return range(1, 65536)

    def get_remote_port(self) -> int:
        """Ngrok 使用动态端口，返回本地端口作为标识"""
        return self.local_port

    def get_tunnel_info(self) -> Dict[str, Any]:
        """获取隧道信息"""
        return {
            "tunnel_type": self._tunnel_type,
            "proxy_name": self.proxy_name,
            "local_ip": self.local_ip,
            "local_port": self.local_port,
            "tunnel_url": self._tunnel_url,
            "is_running": self.is_running,
        }

    def start(self) -> bool:
        """启动 Ngrok 隧道"""
        try:
            if self._process is None:
                cmd = ["ngrok", "http", f"{self.local_ip}:{self.local_port}"]
                if self.auth_token:
                    cmd.extend(["--authtoken", self.auth_token])
                
                logger.debug(f"正在启动 Ngrok: {' '.join(cmd)}")
                self._process = subprocess.Popen(
                    cmd,
                    text=True,
                    encoding="utf8",
                )
                logger.debug(f"Ngrok 已启动: {self._process.pid}")
                time.sleep(3)  # 等待 Ngrok 启动
                return True
            else:
                logger.warning("Ngrok 已在运行中")
                return False
        except Exception as e:
            logger.error(f"启动 Ngrok 失败: {e}")
            return False

    def stop(self) -> bool:
        """停止 Ngrok 隧道"""
        try:
            if self._process:
                logger.debug("正在停止 Ngrok...")
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
                self._process = None
                self._tunnel_url = None
                logger.debug("Ngrok 已停止")
            return True
        except Exception as e:
            logger.error(f"停止 Ngrok 失败: {e}")
            return False


if __name__ == "__main__":
    # 示例用法
    ngrok = NgrokTunnel(proxy_name="test_ngrok", local_port=8080)
    try:
        ngrok.start()
        print(f"隧道信息: {ngrok.get_tunnel_info()}")
    except Exception as e:
        logger.error(f"Ngrok 启动失败: {e}")
    finally:
        ngrok.stop()
