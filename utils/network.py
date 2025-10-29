import socket
import subprocess
import platform
from loguru import logger

def get_local_ip():
    """
    获取本地IP地址
    
    返回:
        str: 本地IP地址
    """
    try:
        # 方法1: 通过创建socket连接获取
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 不需要真正连接，只需要给定一个目标
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.error(f"通过socket获取IP失败: {e}")
    
    try:
        # 方法2: 获取主机名然后解析IP
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        # 过滤掉本地回环地址
        if not ip.startswith('127.'):
            return ip
    except Exception as e:
        logger.error(f"通过主机名获取IP失败: {e}")
    
    # 方法3: 针对不同操作系统使用命令行获取
    try:
        system = platform.system()
        if system == 'Windows':
            # Windows系统使用ipconfig命令
            cmd_output = subprocess.check_output('ipconfig', shell=True).decode('gbk')
            for line in cmd_output.split('\n'):
                if 'IPv4' in line and '.' in line:
                    ip = line.split(':')[-1].strip()
                    if not ip.startswith('127.'):
                        return ip
        elif system == 'Linux':
            # Linux系统使用ip addr命令
            cmd_output = subprocess.check_output("ip -4 addr | grep inet | grep -v '127.0.0.1' | awk '{print $2}' | cut -d/ -f1", shell=True).decode('utf-8')
            if cmd_output:
                return cmd_output.strip()
        elif system == 'Darwin':  # macOS
            cmd_output = subprocess.check_output("ifconfig | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}'", shell=True).decode('utf-8')
            if cmd_output:
                return cmd_output.strip()
    except Exception as e:
        logger.error(f"通过命令行获取IP失败: {e}")
    
    # 如果所有方法都失败，返回localhost
    return "127.0.0.1"

if __name__ == "__main__":
    # 测试函数
    print(f"本机IP地址: {get_local_ip()}")
