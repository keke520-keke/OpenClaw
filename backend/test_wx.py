"""测试企业微信推送"""
import urllib.request
import json

# 测试推送
print("=" * 50)
print("测试企业微信推送")
print("=" * 50)

try:
    req = urllib.request.Request('http://localhost:8000/api/wx/test')
    r = urllib.request.urlopen(req, timeout=10)
    result = json.loads(r.read().decode())
    print(f"推送结果: {result}")
except Exception as e:
    print(f"推送失败: {e}")

# 检查止盈止损状态
print("\n" + "=" * 50)
print("检查止盈止损监控状态")
print("=" * 50)

try:
    req = urllib.request.Request('http://localhost:8000/api/tp-sl/status')
    r = urllib.request.urlopen(req, timeout=10)
    result = json.loads(r.read().decode())
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"获取状态失败: {e}")

# 检查自动交易状态
print("\n" + "=" * 50)
print("检查自动交易状态")
print("=" * 50)

try:
    req = urllib.request.Request('http://localhost:8000/api/autotrade/status')
    r = urllib.request.urlopen(req, timeout=10)
    result = json.loads(r.read().decode())
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"获取状态失败: {e}")
