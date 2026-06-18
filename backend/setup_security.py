"""OpenClaw 安全初始化脚本"""
import os
import sys
import secrets
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def setup_security():
    """初始化安全配置"""
    print("=" * 60)
    print("OpenClaw 安全初始化")
    print("=" * 60)
    
    backend_dir = Path(__file__).parent
    env_file = backend_dir / ".env"
    data_dir = backend_dir / "data"
    
    # 1. 创建数据目录
    data_dir.mkdir(exist_ok=True)
    print("[OK] 数据目录已创建")
    
    # 2. 生成.env文件（如果不存在）
    if not env_file.exists():
        secret_key = secrets.token_hex(32)
        env_content = f"""# OpenClaw 安全配置
# 自动生成于初始化脚本

# 安全密钥（用于加密和CSRF令牌）
OPENCLAW_SECRET_KEY={secret_key}

# CORS配置（允许的前端域名）
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5178

# 速率限制
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_BURST=20
"""
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(f"[OK] .env 文件已创建")
        print(f"   安全密钥: {secret_key[:8]}...{secret_key[-8:]}")
    else:
        print("[INFO] .env 文件已存在，跳过创建")
    
    # 3. 创建API密钥（如果不存在）
    api_key_file = data_dir / "api_keys.json"
    if not api_key_file.exists():
        from app.security import generate_api_key
        default_key = generate_api_key("default", ["read", "trade", "admin"])
        print(f"[OK] 默认API密钥已生成")
        print(f"   请保存此密钥: {default_key}")
    else:
        print("[INFO] API密钥文件已存在，跳过创建")
    
    # 4. 创建.gitignore（如果不存在）
    gitignore = backend_dir.parent / ".gitignore"
    gitignore_entries = {
        ".env",
        "data/api_keys.json",
        "data/openclaw.db",
        "data/rate_limit.json",
        "data/cache/",
        "__pycache__/",
        "*.pyc",
    }
    
    if gitignore.exists():
        with open(gitignore, "r", encoding="utf-8") as f:
            existing = set(f.read().strip().split("\n"))
        new_entries = gitignore_entries - existing
        if new_entries:
            with open(gitignore, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(new_entries) + "\n")
            print(f"[OK] .gitignore 已更新（新增 {len(new_entries)} 项）")
        else:
            print("[INFO] .gitignore 已包含所有必要条目")
    else:
        with open(gitignore, "w", encoding="utf-8") as f:
            f.write("\n".join(gitignore_entries) + "\n")
        print("[OK] .gitignore 已创建")
    
    print("\n" + "=" * 60)
    print("初始化完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 检查 .env 文件中的配置")
    print("2. 保存生成的API密钥")
    print("3. 运行 python security_check.py 验证配置")
    print("4. 启动服务器: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    print("=" * 60)


if __name__ == "__main__":
    setup_security()
