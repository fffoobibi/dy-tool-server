"""
启动脚本 - 同时运行 Flask 应用和 MCP 服务器
"""
import os
import sys
import subprocess
import threading
import time
import signal
from pathlib import Path


class ServiceManager:
    """服务管理器"""
    
    def __init__(self):
        self.processes = []
        self.running = True
    
    def start_flask_app(self):
        """启动 Flask 应用"""
        print("正在启动 Flask 应用...")
        try:
            process = subprocess.Popen([
                sys.executable, "app.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.processes.append(("Flask", process))
            
            # 监控输出
            def monitor_flask():
                for line in process.stdout:
                    print(f"[Flask] {line.strip()}")
            
            thread = threading.Thread(target=monitor_flask, daemon=True)
            thread.start()
            
            return process
        except Exception as e:
            print(f"启动 Flask 应用失败: {e}")
            return None
    
    def start_mcp_server(self):
        """启动 MCP 服务器"""
        print("正在启动 MCP 服务器...")
        try:
            process = subprocess.Popen([
                sys.executable, "mcp_server.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.processes.append(("MCP", process))
            
            # 监控输出
            def monitor_mcp():
                for line in process.stdout:
                    print(f"[MCP] {line.strip()}")
            
            thread = threading.Thread(target=monitor_mcp, daemon=True)
            thread.start()
            
            return process
        except Exception as e:
            print(f"启动 MCP 服务器失败: {e}")
            return None
    
    def check_dependencies(self):
        """检查依赖"""
        print("检查依赖...")
        
        # 检查关键文件
        required_files = [
            "app.py",
            "mcp_server.py",
            "requirements.txt",
            "requirements_mcp.txt"
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            print(f"缺少必要文件: {missing_files}")
            return False
        
        # 检查Python包
        try:
            import flask
            import fastmcp
            import httpx
            import pydantic
            print("依赖检查通过")
            return True
        except ImportError as e:
            print(f"缺少必要的Python包: {e}")
            print("请运行: pip install -r requirements.txt 和 pip install -r requirements_mcp.txt")
            return False
    
    def setup_environment(self):
        """设置环境"""
        # 创建必要目录
        dirs = [
            "data/knowledge_base",
            "logs",
            "uploads"
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        print("环境设置完成")
    
    def stop_all(self):
        """停止所有服务"""
        print("\n正在停止所有服务...")
        self.running = False
        
        for name, process in self.processes:
            try:
                print(f"停止 {name} 服务...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"强制杀死 {name} 服务...")
                process.kill()
            except Exception as e:
                print(f"停止 {name} 服务时出错: {e}")
        
        print("所有服务已停止")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n接收到信号 {signum}")
        self.stop_all()
        sys.exit(0)
    
    def run(self):
        """运行所有服务"""
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 检查依赖
        if not self.check_dependencies():
            return False
        
        # 设置环境
        self.setup_environment()
        
        print("=" * 50)
        print("DY Tool Server 启动中...")
        print("=" * 50)
        
        # 启动服务
        flask_process = self.start_flask_app()
        time.sleep(2)  # 等待Flask启动
        
        mcp_process = self.start_mcp_server()
        time.sleep(2)  # 等待MCP启动
        
        if not flask_process or not mcp_process:
            print("服务启动失败")
            self.stop_all()
            return False
        
        print("=" * 50)
        print("所有服务启动完成!")
        print("Flask 应用: http://localhost:5000")
        print("API 文档: http://localhost:5000/docs/")
        print("MCP 服务器: http://localhost:8000")
        print("按 Ctrl+C 停止所有服务")
        print("=" * 50)
        
        # 监控服务状态
        try:
            while self.running:
                time.sleep(1)
                
                # 检查进程状态
                for name, process in self.processes:
                    if process.poll() is not None:
                        print(f"\n警告: {name} 服务已停止 (返回码: {process.poll()})")
                        if name == "Flask":
                            # 输出错误信息
                            stderr = process.stderr.read()
                            if stderr:
                                print(f"Flask 错误输出: {stderr}")
                        elif name == "MCP":
                            stderr = process.stderr.read()
                            if stderr:
                                print(f"MCP 错误输出: {stderr}")
        
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all()
        
        return True


def main():
    """主函数"""
    print("DY Tool Server 服务管理器")
    print("功能: 知识库管理 + MCP 服务器")
    
    manager = ServiceManager()
    success = manager.run()
    
    if success:
        print("服务运行完成")
    else:
        print("服务运行失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
