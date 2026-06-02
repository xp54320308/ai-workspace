Write-Host '=== 系统资源 ===' -ForegroundColor Cyan
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor
Write-Host "CPU: $($cpu.Name) ($($cpu.NumberOfCores) cores, $($cpu.NumberOfLogicalProcessors) threads)"
Write-Host "CPU Usage: $($cpu.LoadPercentage)%"
$totalRAM = [math]::Round($os.TotalVisibleMemorySize/1MB, 1)
$freeRAM = [math]::Round($os.FreePhysicalMemory/1MB, 1)
$usedRAM = [math]::Round($totalRAM - $freeRAM, 1)
Write-Host "RAM: ${usedRAM}GB / ${totalRAM}GB ($([math]::Round($usedRAM/$totalRAM*100,1))%)"

Write-Host ''
Write-Host '=== 磁盘空间 ===' -ForegroundColor Cyan
Get-CimInstance Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} | ForEach-Object {
    $total = [math]::Round($_.Size/1GB, 1)
    $free = [math]::Round($_.FreeSpace/1GB, 1)
    $used = [math]::Round($total - $free, 1)
    $pct = [math]::Round($used/$total*100, 1)
    Write-Host "$($_.DeviceID) ${used}GB/${total}GB (${pct}%) used"
}

Write-Host ''
Write-Host '=== GPU ===' -ForegroundColor Cyan
try { nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu --format=csv,noheader } catch { Write-Host 'nvidia-smi not available' }

Write-Host ''
Write-Host '=== Top 10 进程(内存) ===' -ForegroundColor Cyan
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, @{N='RAM_MB';E={[math]::Round($_.WorkingSet64/1MB,0)}}, @{N='CPU_s';E={[math]::Round($_.CPU,1)}} | Format-Table -AutoSize

Write-Host ''
Write-Host '=== 网络连通性 ===' -ForegroundColor Cyan
$targets = @('github.com', 'api.openai.com', '127.0.0.1:18789', '127.0.0.1:11434')
foreach ($t in $targets) {
    $h = $t.Split(':')[0]
    $result = Test-Connection -ComputerName $h -Count 1 -Quiet -TimeoutSeconds 3
    $status = if ($result) { 'OK' } else { 'FAIL' }
    Write-Host "$t => $status"
}

Write-Host ''
Write-Host '=== OpenClaw Gateway ===' -ForegroundColor Cyan
try {
    $resp = Invoke-RestMethod -Uri 'http://127.0.0.1:18789/health' -TimeoutSec 5
    Write-Host "Gateway: $($resp.status)"
} catch {
    Write-Host "Gateway: UNREACHABLE"
}

Write-Host ''
Write-Host '=== Ollama ===' -ForegroundColor Cyan
try {
    $models = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 5
    Write-Host "Models loaded: $($models.models.Count)"
} catch {
    Write-Host "Ollama: UNREACHABLE"
}

Write-Host ''
Write-Host '=== OpenClaw 版本 ===' -ForegroundColor Cyan
try { openclaw --version } catch { Write-Host 'version check failed' }

Write-Host ''
Write-Host '=== Node.js ===' -ForegroundColor Cyan
try { Write-Host "Node: $(node --version)" } catch {}
try { Write-Host "npm: $(npm --version)" } catch {}

Write-Host ''
Write-Host '=== Python ===' -ForegroundColor Cyan
try { python --version } catch { Write-Host 'python not found' }

Write-Host ''
Write-Host '=== Git ===' -ForegroundColor Cyan
try { Write-Host "Git: $(git --version)" } catch {}
