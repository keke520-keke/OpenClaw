"""OpenClaw 安全模块 - 认证、授权、输入验证、CSRF防护"""
import hashlib
import hmac
import os
import secrets
import time
import json
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any

# ═══════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════
SECRET_KEY = os.environ.get("OPENCLAW_SECRET_KEY", secrets.token_hex(32))
API_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "api_keys.json")
RATE_LIMIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "rate_limit.json")

# 速率限制配置
RATE_LIMIT_WINDOW = 60  # 1分钟
RATE_LIMIT_MAX_REQUESTS = 100  # 每窗口最大请求数
RATE_LIMIT_BURST = 20  # 突发请求上限

# ═══════════════════════════════════════════
# API密钥管理
# ═══════════════════════════════════════════
_api_keys: Dict[str, Dict[str, Any]] = {}
_rate_limits: Dict[str, list] = {}

def _load_api_keys():
    """加载API密钥"""
    global _api_keys
    try:
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, "r", encoding="utf-8") as f:
                _api_keys = json.load(f)
    except Exception:
        pass

def _save_api_keys():
    """保存API密钥"""
    try:
        os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
        with open(API_KEY_FILE, "w", encoding="utf-8") as f:
            json.dump(_api_keys, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Security] 保存API密钥失败: {e}")

def generate_api_key(name: str, permissions: list = None) -> str:
    """生成新的API密钥"""
    key = f"oc_{secrets.token_hex(32)}"
    _api_keys[key] = {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "permissions": permissions or ["read", "trade"],
        "enabled": True,
        "last_used": None,
    }
    _save_api_keys()
    return key

def validate_api_key(key: str) -> Optional[Dict]:
    """验证API密钥"""
    if not key:
        return None
    key_data = _api_keys.get(key)
    if key_data and key_data.get("enabled", True):
        key_data["last_used"] = datetime.now().isoformat()
        return key_data
    return None

def revoke_api_key(key: str) -> bool:
    """撤销API密钥"""
    if key in _api_keys:
        _api_keys[key]["enabled"] = False
        _save_api_keys()
        return True
    return False

def list_api_keys() -> list:
    """列出所有API密钥（隐藏完整key）"""
    result = []
    for key, data in _api_keys.items():
        result.append({
            "key_preview": key[:8] + "..." + key[-4:],
            "name": data.get("name", ""),
            "permissions": data.get("permissions", []),
            "enabled": data.get("enabled", True),
            "created_at": data.get("created_at"),
            "last_used": data.get("last_used"),
        })
    return result

# ═══════════════════════════════════════════
# 速率限制
# ═══════════════════════════════════════════
def _load_rate_limits():
    """加载速率限制数据"""
    global _rate_limits
    try:
        if os.path.exists(RATE_LIMIT_FILE):
            with open(RATE_LIMIT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 只保留当前窗口的数据
                now = time.time()
                _rate_limits = {
                    k: [t for t in v if now - t < RATE_LIMIT_WINDOW]
                    for k, v in data.items()
                }
    except Exception:
        pass

def _check_rate_limit(client_id: str) -> tuple[bool, int]:
    """检查速率限制，返回(是否允许, 剩余请求数)"""
    now = time.time()
    if client_id not in _rate_limits:
        _rate_limits[client_id] = []
    
    # 清理过期记录
    _rate_limits[client_id] = [t for t in _rate_limits[client_id] if now - t < RATE_LIMIT_WINDOW]
    
    current_count = len(_rate_limits[client_id])
    if current_count >= RATE_LIMIT_MAX_REQUESTS:
        return False, 0
    
    # 检查突发请求
    recent_count = len([t for t in _rate_limits[client_id] if now - t < 1])
    if recent_count >= RATE_LIMIT_BURST:
        return False, 0
    
    _rate_limits[client_id].append(now)
    return True, RATE_LIMIT_MAX_REQUESTS - current_count - 1

def _save_rate_limits():
    """保存速率限制数据"""
    try:
        os.makedirs(os.path.dirname(RATE_LIMIT_FILE), exist_ok=True)
        with open(RATE_LIMIT_FILE, "w", encoding="utf-8") as f:
            json.dump(_rate_limits, f)
    except Exception:
        pass

# ═══════════════════════════════════════════
# CSRF防护
# ═══════════════════════════════════════════
_csrf_tokens: Dict[str, float] = {}
CSRF_TOKEN_EXPIRY = 3600  # 1小时过期

def generate_csrf_token(session_id: str = "default") -> str:
    """生成CSRF令牌"""
    token = secrets.token_hex(32)
    _csrf_tokens[f"{session_id}:{token}"] = time.time()
    return token

def validate_csrf_token(token: str, session_id: str = "default") -> bool:
    """验证CSRF令牌"""
    if not token:
        return False
    
    key = f"{session_id}:{token}"
    expiry = _csrf_tokens.get(key)
    if expiry is None:
        return False
    
    if time.time() - expiry > CSRF_TOKEN_EXPIRY:
        del _csrf_tokens[key]
        return False
    
    # 使用后立即删除（一次性令牌）
    del _csrf_tokens[key]
    return True

def cleanup_expired_csrf_tokens():
    """清理过期的CSRF令牌"""
    now = time.time()
    expired = [k for k, v in _csrf_tokens.items() if now - v > CSRF_TOKEN_EXPIRY]
    for k in expired:
        del _csrf_tokens[k]

# ═══════════════════════════════════════════
# 输入验证
# ═══════════════════════════════════════════
def validate_stock_code(code: str) -> bool:
    """验证股票代码格式"""
    if not code or not isinstance(code, str):
        return False
    code = code.strip()
    if len(code) != 6:
        return False
    if not code.isdigit():
        return False
    # 验证前缀：支持主板、创业板、科创板、ETF、可转债
    valid_prefixes = ("0", "1", "3", "5", "6")
    if not code.startswith(valid_prefixes):
        return False
    return True

def validate_order_side(side: str) -> bool:
    """验证订单方向"""
    return side in ("buy", "sell")

def validate_quantity(qty: int) -> bool:
    """验证交易数量"""
    if not isinstance(qty, (int, float)):
        return False
    qty = int(qty)
    if qty <= 0:
        return False
    if qty % 100 != 0:  # A股必须是100的整数倍
        return False
    return True

def validate_price(price: float) -> bool:
    """验证价格"""
    if not isinstance(price, (int, float)):
        return False
    if price <= 0:
        return False
    if price > 100000:  # 合理价格上限
        return False
    return True

def validate_strategy(strategy: str) -> bool:
    """验证策略名称"""
    allowed_strategies = {
        "breakout", "bluechip", "limitup", "active",
        "放量突破", "低估值蓝筹", "涨停板", "高换手活跃",
        "手动", "自动", "黑天鹅-强制平仓"
    }
    return strategy in allowed_strategies

def sanitize_string(s: str, max_length: int = 100) -> str:
    """清理字符串输入"""
    if not isinstance(s, str):
        return ""
    # 移除危险字符
    s = s.replace("<", "").replace(">", "").replace('"', "").replace("'", "")
    return s[:max_length]

# ═══════════════════════════════════════════
# 安全装饰器
# ═══════════════════════════════════════════
def require_auth(permissions: list = None):
    """要求认证的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from fastapi import Request, HTTPException
            
            # 获取请求对象
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if hasattr(arg, "headers"):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(status_code=500, detail="无法获取请求对象")
            
            # 获取API密钥
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                api_key = request.query_params.get("api_key")
            
            if not api_key:
                raise HTTPException(status_code=401, detail="缺少API密钥")
            
            # 验证密钥
            key_data = validate_api_key(api_key)
            if not key_data:
                raise HTTPException(status_code=401, detail="无效的API密钥")
            
            # 检查权限
            if permissions:
                user_perms = key_data.get("permissions", [])
                for perm in permissions:
                    if perm not in user_perms:
                        raise HTTPException(status_code=403, detail=f"缺少权限: {perm}")
            
            # 速率限制
            client_id = api_key[:16]  # 使用密钥前16位作为客户端ID
            allowed, remaining = _check_rate_limit(client_id)
            if not allowed:
                raise HTTPException(status_code=429, detail="请求过于频繁")
            
            # 将密钥信息传递给处理函数
            kwargs["api_key_data"] = key_data
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_post(func):
    """要求POST方法的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        from fastapi import Request, HTTPException
        
        request = kwargs.get("request")
        if not request:
            for arg in args:
                if hasattr(arg, "method"):
                    request = arg
                    break
        
        if request and request.method != "POST":
            raise HTTPException(status_code=405, detail="仅支持POST方法")
        
        return await func(*args, **kwargs)
    return wrapper

def validate_csrf(func):
    """验证CSRF令牌的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        from fastapi import Request, HTTPException
        
        request = kwargs.get("request")
        if not request:
            for arg in args:
                if hasattr(arg, "headers"):
                    request = arg
                    break
        
        if not request:
            raise HTTPException(status_code=500, detail="无法获取请求对象")
        
        token = request.headers.get("X-CSRF-Token")
        session_id = request.headers.get("X-Session-ID", "default")
        
        if not validate_csrf_token(token, session_id):
            raise HTTPException(status_code=403, detail="CSRF验证失败")
        
        return await func(*args, **kwargs)
    return wrapper

# ═══════════════════════════════════════════
# 日志脱敏
# ═══════════════════════════════════════════
def mask_sensitive_data(data: str) -> str:
    """脱敏敏感数据"""
    if not isinstance(data, str):
        return data
    
    # 脱敏API密钥
    if "oc_" in data:
        import re
        data = re.sub(r'oc_[a-f0-9]{8}[a-f0-9]+[a-f0-9]{4}', lambda m: m.group()[:12] + "..." + m.group()[-4:], data)
    
    # 脱敏股票代码（保留前2位）
    if len(data) == 6 and data.isdigit():
        data = data[:2] + "****"
    
    return data

# ═══════════════════════════════════════════
# 初始化
# ═══════════════════════════════════════════
def init_security():
    """初始化安全模块"""
    _load_api_keys()
    _load_rate_limits()
    
    # 如果没有API密钥，生成一个默认的
    if not _api_keys:
        default_key = generate_api_key("default", ["read", "trade", "admin"])
        print(f"[Security] 生成默认API密钥: {default_key}")
    
    print(f"[Security] 已加载 {len(_api_keys)} 个API密钥")

# 模块加载时初始化
init_security()
