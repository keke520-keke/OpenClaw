"""OpenClaw 安全检查脚本"""
import os
import sys
import json
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_security():
    """执行安全检查"""
    print("=" * 60)
    print("OpenClaw 安全检查")
    print("=" * 60)
    
    issues = []
    warnings = []
    
    # 1. 检查.env文件
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        issues.append("[FAIL] 缺少 .env 配置文件")
    else:
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "your_secret_key_here" in content:
                issues.append("[FAIL] OPENCLAW_SECRET_KEY 未修改为实际值")
            if "OPENCLAW_SECRET_KEY" not in content:
                warnings.append("[WARN] .env 中未定义 OPENCLAW_SECRET_KEY")
    
    # 2. 检查API密钥文件权限
    api_key_file = Path(__file__).parent / "data" / "api_keys.json"
    if api_key_file.exists():
        try:
            with open(api_key_file, "r", encoding="utf-8") as f:
                keys = json.load(f)
                if not keys:
                    warnings.append("[WARN] API密钥文件为空")
                else:
                    print(f"[OK] 已配置 {len(keys)} 个API密钥")
        except Exception as e:
            issues.append(f"[FAIL] API密钥文件读取失败: {e}")
    
    # 3. 检查数据库文件
    db_file = Path(__file__).parent / "data" / "openclaw.db"
    if db_file.exists():
        size_mb = db_file.stat().st_size / (1024 * 1024)
        if size_mb > 100:
            warnings.append(f"[WARN] 数据库文件较大 ({size_mb:.1f} MB)")
        else:
            print(f"[OK] 数据库文件大小正常 ({size_mb:.1f} MB)")
    
    # 4. 检查日志目录权限
    log_dir = Path(__file__).parent / "logs"
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if len(log_files) > 100:
            warnings.append(f"[WARN] 日志文件过多 ({len(log_files)} 个)，建议清理")
        else:
            print(f"[OK] 日志文件数量正常 ({len(log_files)} 个)")
    
    # 5. 检查敏感文件是否被git跟踪
    gitignore = Path(__file__).parent.parent / ".gitignore"
    if gitignore.exists():
        with open(gitignore, "r", encoding="utf-8") as f:
            ignored = f.read()
            sensitive_files = [".env", "api_keys.json", "openclaw.db"]
            for sf in sensitive_files:
                if sf not in ignored:
                    warnings.append(f"[WARN] {sf} 可能未被 .gitignore 忽略")
    
    # 6. 检查Python依赖
    try:
        import fastapi
        print(f"[OK] FastAPI 版本: {fastapi.__version__}")
    except ImportError:
        issues.append("[FAIL] FastAPI 未安装")
    
    # 7. 检查安全模块
    try:
        from app.security import SECRET_KEY, _api_keys
        if SECRET_KEY and len(SECRET_KEY) >= 32:
            print("[OK] 安全密钥长度足够")
        else:
            issues.append("[FAIL] 安全密钥长度不足")
        
        if _api_keys:
            print(f"[OK] 已加载 {len(_api_keys)} 个API密钥")
        else:
            warnings.append("[WARN] 无API密钥配置")
    except Exception as e:
        issues.append(f"[FAIL] 安全模块加载失败: {e}")
    
    # 输出结果
    print("\n" + "=" * 60)
    print("检查结果")
    print("=" * 60)
    
    if issues:
        print("\n[ERROR] 发现严重问题:")
        for issue in issues:
            print(f"  {issue}")
    
    if warnings:
        print("\n[WARNING] 警告:")
        for warning in warnings:
            print(f"  {warning}")
    
    if not issues and not warnings:
        print("\n[SUCCESS] 安全检查通过！")
    
    print("\n" + "=" * 60)
    
    return len(issues) == 0


if __name__ == "__main__":
    success = check_security()
    sys.exit(0 if success else 1)
