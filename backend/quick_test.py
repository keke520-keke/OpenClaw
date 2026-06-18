"""快速API测试 - 用于验证服务器是否正常"""
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def test_api(url, name):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url), timeout=5)
        d = json.loads(r.read().decode())
        print(f"[OK] {name}: code={d.get('code', 'N/A')}")
        return True
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return False

def main():
    base = "http://localhost:8000"
    
    print("测试服务器...")
    tests = [
        (f"{base}/api/health", "健康检查"),
        (f"{base}/api/trailing/status", "追踪止盈"),
        (f"{base}/api/scoring/score?code=600519", "打分API"),
        (f"{base}/api/market/overview", "市场概览"),
    ]
    
    success = 0
    for url, name in tests:
        if test_api(url, name):
            success += 1
    
    print(f"\n结果: {success}/{len(tests)} 通过")
    return success == len(tests)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
