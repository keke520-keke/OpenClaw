"""快速启动服务器 - 自动处理端口占用"""
import subprocess
import time
import os
import signal

def kill_port(port):
    """杀死占用端口的进程"""
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port} | findstr LISTENING',
            shell=True, capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                pid = line.strip().split()[-1]
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                print(f"  已停止进程: {pid}")
    except:
        pass

def start_server():
    """启动服务器"""
    port = 8000
    
    print(f"[1/3] 清理端口 {port}...")
    kill_port(port)
    time.sleep(0.5)
    
    print(f"[2/3] 启动服务器...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 使用subprocess启动，不阻塞
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(port)],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )
    
    print(f"[3/3] 等待服务器启动...")
    time.sleep(2)
    
    # 验证服务器
    try:
        import urllib.request
        r = urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=5)
        data = eval(r.read().decode())
        print(f"[OK] 服务器启动成功: {data.get('status')}")
        print(f"[OK] 版本: {data.get('version')}")
        print(f"[OK] 地址: http://localhost:{port}")
        return True
    except Exception as e:
        print(f"[ERROR] 服务器启动失败: {e}")
        return False

if __name__ == "__main__":
    import sys
    start_server()
