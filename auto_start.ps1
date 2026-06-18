# OpenClaw 自启动脚本 — 添加到 Windows 计划任务：
# 管理员 PowerShell 运行: .\auto_start.ps1

$taskName = "OpenClaw-AutoStart"
$scriptPath = Join-Path (Split-Path $MyInvocation.MyCommand.Path) "start.bat"

# 删除旧任务
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# 创建新任务：开机自动启动 + 每隔5分钟检测
$action = New-ScheduledTaskAction -Execute $scriptPath
$trigger1 = New-ScheduledTaskTrigger -AtLogon
$trigger2 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -At (Get-Date) -RepetitionDuration (New-TimeSpan -Days 365)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger1,$trigger2 -Settings $settings -RunLevel Highest -Description "OpenClaw量化交易系统自启动" | Out-Null

Write-Host "[OK] 已创建计划任务: $taskName"
Write-Host "  - 开机自动启动"
Write-Host "  - 每5分钟检测一次"
Write-Host "  - 崩溃自动重启(最多3次)"
Write-Host ""
Write-Host "启动: Ctrl+R -> taskschd.msc -> 找到 OpenClaw-AutoStart"
Write-Host "或直接双击 start.bat 手动启动"
