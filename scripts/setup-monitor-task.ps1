$scriptPath = "C:\Users\qw\.openclaw\workspace\scripts\auto-monitor.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`" -Auto -IntervalSeconds 300"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "OpenClawMonitor" -Action $action -Trigger $trigger -Settings $settings -Description "OpenClaw Auto Monitor Pro v3.1" -Force
Write-Host "OK - Task created"
