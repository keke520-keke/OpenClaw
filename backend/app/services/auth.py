"""用户认证与会员系统"""
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class MemberTier(str, Enum):
    FREE = "free"         # 免费：行情、1个选股策略
    BASIC = "basic"       # 基础：全选股、基础因子、纸盘
    PRO = "pro"           # 专业：AI信号、回测、自动交易、全部因子


TIER_PERMISSIONS = {
    MemberTier.FREE: {
        "max_screener_presets": 1,
        "max_watchlist": 10,
        "features": ["market", "screener_basic"],
    },
    MemberTier.BASIC: {
        "max_screener_presets": 4,
        "max_watchlist": 50,
        "features": ["market", "screener_full", "factors_basic", "paper_trading"],
    },
    MemberTier.PRO: {
        "max_screener_presets": 99,
        "max_watchlist": 999,
        "features": ["market", "screener_full", "factors_full", "paper_trading",
                     "ai_signals", "backtest", "auto_trading", "priority_support"],
    },
}

TIER_PRICES = {
    MemberTier.FREE: 0,
    MemberTier.BASIC: 29.9,   # 元/月
    MemberTier.PRO: 99.9,      # 元/月
}


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    password_hash: str
    email: str = ""
    phone: str = ""
    tier: MemberTier = MemberTier.FREE
    tier_expires_at: str = ""      # 会员到期时间
    created_at: str = ""
    last_login: str = ""
    tokens: dict = field(default_factory=dict)  # {token: expires_ts}
    is_active: bool = True

    def has_permission(self, feature: str) -> bool:
        """检查是否有某功能权限"""
        if self.tier_expires_at and datetime.now() > datetime.strptime(self.tier_expires_at, "%Y-%m-%d"):
            self.tier = MemberTier.FREE  # 过期降级
        return feature in TIER_PERMISSIONS.get(self.tier, MemberTier.FREE)["features"]

    def get_limits(self) -> dict:
        """获取当前等级限制"""
        return TIER_PERMISSIONS.get(self.tier, TIER_PERMISSIONS[MemberTier.FREE])


class AuthManager:
    """认证管理器"""

    def __init__(self):
        self.users: dict[str, User] = {}  # user_id -> User
        self._tokens: dict[str, str] = {}  # token -> user_id
        # 创建演示账户
        self._create_demo_users()

    def _create_demo_users(self):
        """创建演示账户"""
        self.register("demo", "demo123", "demo@openclaw.com", MemberTier.PRO, tier_expires_at="2027-12-31")
        self.register("free", "free123", "free@openclaw.com", MemberTier.FREE)
        self.register("basic", "basic123", "basic@openclaw.com", MemberTier.BASIC, tier_expires_at="2027-06-30")

    def _hash(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str, email: str = "",
                 tier: MemberTier = MemberTier.FREE, tier_expires_at: str = "") -> Optional[User]:
        """注册"""
        for u in self.users.values():
            if u.username == username:
                return None  # 用户名已存在

        uid = f"U_{secrets.token_hex(6).upper()}"
        user = User(
            user_id=uid, username=username,
            password_hash=self._hash(password),
            email=email, tier=tier,
            tier_expires_at=tier_expires_at,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        self.users[uid] = user
        logger.info(f"新用户注册: {username} ({tier.value})")
        return user

    def login(self, username: str, password: str) -> Optional[dict]:
        """登录 → 返回 token"""
        for u in self.users.values():
            if u.username == username and u.password_hash == self._hash(password):
                if not u.is_active:
                    return None
                token = secrets.token_urlsafe(32)
                expires = time.time() + 86400 * 7  # 7天有效
                u.tokens[token] = expires
                self._tokens[token] = u.user_id
                u.last_login = datetime.now().strftime("%Y-%m-%d %H:%M")
                return {
                    "token": token,
                    "user_id": u.user_id,
                    "username": u.username,
                    "tier": u.tier.value,
                    "expires_in": 86400 * 7,
                }
        return None

    def verify_token(self, token: str) -> Optional[User]:
        """验证 token"""
        uid = self._tokens.get(token)
        if not uid:
            return None
        user = self.users.get(uid)
        if not user:
            return None
        expires = user.tokens.get(token, 0)
        if time.time() > expires:
            del user.tokens[token]
            del self._tokens[token]
            return None
        return user

    def logout(self, token: str):
        uid = self._tokens.pop(token, None)
        if uid and uid in self.users:
            self.users[uid].tokens.pop(token, None)

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def upgrade_tier(self, user_id: str, tier: MemberTier, months: int = 1):
        """升级会员"""
        user = self.users.get(user_id)
        if not user:
            return False

        user.tier = tier
        if user.tier_expires:
            current_expiry = datetime.strptime(user.tier_expires, "%Y-%m-%d")
        else:
            current_expiry = datetime.now()
        user.tier_expires = (current_expiry + timedelta(days=30 * months)).strftime("%Y-%m-%d")
        logger.info(f"会员升级: {user.username} → {tier.value} ({months}个月)")
        return True

    def list_users(self) -> list[dict]:
        return [{
            "user_id": u.user_id, "username": u.username,
            "tier": u.tier.value, "email": u.email,
            "tier_expires": u.tier_expires_at,
            "created_at": u.created_at, "last_login": u.last_login,
            "is_active": u.is_active,
        } for u in self.users.values()]


# 全局单例
_auth: Optional[AuthManager] = None


def get_auth() -> AuthManager:
    global _auth
    if _auth is None:
        _auth = AuthManager()
    return _auth
