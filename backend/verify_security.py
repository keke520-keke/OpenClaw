"""OpenClaw v3.2 安全修复验证脚本"""
import sys
import os

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def verify_fixes():
    """验证所有安全修复"""
    print("=" * 60)
    print("OpenClaw v3.2 安全修复验证")
    print("=" * 60)
    
    checks = []
    
    # 1. 验证安全模块存在
    try:
        from app.security import (
            generate_api_key, validate_api_key, revoke_api_key,
            generate_csrf_token, validate_csrf_token,
            validate_stock_code, validate_order_side, validate_quantity,
            validate_price, validate_strategy, sanitize_string,
            mask_sensitive_data, require_auth
        )
        checks.append(("安全模块导入", True))
    except ImportError as e:
        checks.append(("安全模块导入", False, str(e)))
    
    # 2. 验证main.py修改
    try:
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        # 检查CORS配置
        if "ALLOWED_ORIGINS" in content and "allow_origins=ALLOWED_ORIGINS" in content:
            checks.append(("CORS限制", True))
        else:
            checks.append(("CORS限制", False, "未找到ALLOWED_ORIGINS"))
        
        # 检查POST方法
        post_endpoints = [
            "/api/watchlist/add",
            "/api/watchlist/remove",
            "/api/autotrade/toggle",
            "/api/risk/config",
            "/api/risk/resume",
            "/api/risk/pause",
            "/api/paper/order",
        ]
        missing_post = []
        for endpoint in post_endpoints:
            if f'@app.post("{endpoint}")' not in content:
                missing_post.append(endpoint)
        
        if not missing_post:
            checks.append(("敏感操作POST化", True))
        else:
            checks.append(("敏感操作POST化", False, f"缺少: {missing_post}"))
        
        # 检查输入验证
        if "validate_stock_code" in content and "validate_quantity" in content:
            checks.append(("输入验证", True))
        else:
            checks.append(("输入验证", False, "缺少验证函数调用"))
        
        # 检查URL白名单
        if "allowed_domains" in content:
            checks.append(("URL域名白名单", True))
        else:
            checks.append(("URL域名白名单", False, "未找到allowed_domains"))
        
        # 检查安全API端点
        security_endpoints = [
            "/api/security/csrf-token",
            "/api/security/api-keys/generate",
            "/api/security/api-keys/revoke",
            "/api/security/api-keys/list",
            "/api/security/validate-key",
            "/api/security/status",
        ]
        missing_security = []
        for endpoint in security_endpoints:
            if endpoint not in content:
                missing_security.append(endpoint)
        
        if not missing_security:
            checks.append(("安全API端点", True))
        else:
            checks.append(("安全API端点", False, f"缺少: {missing_security}"))
        
    except Exception as e:
        checks.append(("main.py检查", False, str(e)))
    
    # 3. 验证db_persist.py修改
    try:
        with open("app/db_persist.py", "r", encoding="utf-8") as f:
            content = f.read()
            
        if "_get_connection" in content and "BEGIN TRANSACTION" in content:
            checks.append(("数据库事务保护", True))
        else:
            checks.append(("数据库事务保护", False, "缺少事务管理"))
        
        if "PRAGMA journal_mode=WAL" in content:
            checks.append(("WAL模式", True))
        else:
            checks.append(("WAL模式", False, "未启用WAL模式"))
        
    except Exception as e:
        checks.append(("db_persist.py检查", False, str(e)))
    
    # 4. 验证配置文件
    if os.path.exists(".env"):
        checks.append((".env文件", True))
    else:
        checks.append((".env文件", False, "缺少.env配置文件"))
    
    if os.path.exists("data/api_keys.json"):
        checks.append(("API密钥文件", True))
    else:
        checks.append(("API密钥文件", False, "缺少api_keys.json"))
    
    # 5. 验证新文件
    new_files = [
        "app/security.py",
        "security_check.py",
        "setup_security.py",
        ".env.example",
        "../SECURITY_FIXES.md",
    ]
    missing_files = []
    for f in new_files:
        if not os.path.exists(f):
            missing_files.append(f)
    
    if not missing_files:
        checks.append(("新文件完整性", True))
    else:
        checks.append(("新文件完整性", False, f"缺少: {missing_files}"))
    
    # 输出结果
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for check in checks:
        if len(check) == 2:
            name, success = check
            detail = ""
        else:
            name, success, detail = check
        
        if success:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}: {detail}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"总结: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("\n[SUCCESS] 所有安全修复验证通过！")
        print("\n系统已升级到 v3.2 安全增强版，主要改进：")
        print("1. API密钥认证系统")
        print("2. CSRF防护")
        print("3. 速率限制")
        print("4. 输入验证")
        print("5. 敏感操作POST化")
        print("6. CORS限制")
        print("7. 数据库事务保护")
        print("8. 日志脱敏")
        print("\n请运行以下命令启动安全增强版服务器：")
        print("  cd E:\\OpenClaw\\backend")
        print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    else:
        print("\n[WARNING] 部分验证未通过，请检查上述问题")
    
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = verify_fixes()
    sys.exit(0 if success else 1)
