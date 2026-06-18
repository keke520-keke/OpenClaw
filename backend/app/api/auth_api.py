"""认证 API"""
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from app.services.auth import get_auth, MemberTier, TIER_PRICES

router = APIRouter()
auth = get_auth()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""


class UpgradeRequest(BaseModel):
    user_id: str
    tier: str   # free / basic / pro
    months: int = 1


@router.post("/register")
async def register(req: RegisterRequest):
    """注册"""
    if len(req.username) < 3 or len(req.password) < 6:
        return {"code": 400, "msg": "用户名>=3位，密码>=6位"}
    user = auth.register(req.username, req.password, req.email)
    if not user:
        return {"code": 409, "msg": "用户名已存在"}
    return {"code": 0, "data": {"user_id": user.user_id, "username": user.username, "tier": user.tier.value}}


@router.post("/login")
async def login(req: LoginRequest):
    """登录"""
    result = auth.login(req.username, req.password)
    if not result:
        return {"code": 401, "msg": "用户名或密码错误"}
    return {"code": 0, "data": result}


@router.post("/logout")
async def logout(authorization: str = Header(None)):
    """登出"""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        auth.logout(token)
    return {"code": 0, "msg": "已登出"}


@router.get("/me")
async def current_user(authorization: str = Header(None)):
    """当前用户信息"""
    if not authorization or not authorization.startswith("Bearer "):
        return {"code": 401, "msg": "未登录"}
    token = authorization[7:]
    user = auth.verify_token(token)
    if not user:
        return {"code": 401, "msg": "Token无效或过期"}
    limits = user.get_limits()
    return {
        "code": 0,
        "data": {
            "user_id": user.user_id, "username": user.username,
            "email": user.email, "tier": user.tier.value,
            "tier_expires": user.tier_expires,
            "permissions": limits["features"],
            "limits": limits,
        },
    }


@router.post("/upgrade")
async def upgrade(req: UpgradeRequest):
    """升级会员"""
    tier = MemberTier.FREE
    if req.tier == "basic":
        tier = MemberTier.BASIC
    elif req.tier == "pro":
        tier = MemberTier.PRO
    ok = auth.upgrade_tier(req.user_id, tier, req.months)
    if not ok:
        return {"code": 404, "msg": "用户不存在"}
    price = TIER_PRICES[tier] * req.months
    return {"code": 0, "msg": f"已升级至{tier.value}，费用{price:.1f}元"}


@router.get("/check")
async def check_permission(feature: str = Query(...), authorization: str = Header(None)):
    """检查功能权限"""
    if not authorization or not authorization.startswith("Bearer "):
        return {"code": 401, "msg": "未登录"}
    user = auth.verify_token(authorization[7:])
    if not user:
        return {"code": 401, "msg": "Token无效"}
    ok = user.has_permission(feature)
    return {"code": 0, "feature": feature, "allowed": ok, "tier": user.tier.value}


@router.get("/tiers")
async def list_tiers():
    """会员等级信息"""
    return {
        "code": 0,
        "data": [
            {
                "tier": "free", "name": "免费版", "price": "0元/月",
                "features": ["实时行情", "1个选股策略", "10只自选"],
            },
            {
                "tier": "basic", "name": "基础版", "price": "29.9元/月",
                "features": ["全部选股策略", "基础因子", "纸盘交易", "50只自选"],
            },
            {
                "tier": "pro", "name": "专业版", "price": "99.9元/月",
                "features": ["全部因子", "AI信号", "回测系统", "自动交易", "优先支持"],
            },
        ],
    }
