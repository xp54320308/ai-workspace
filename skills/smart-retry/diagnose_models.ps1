# OpenClaw 模型响应诊断
# 测试各模型的真实响应时间

param(
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Continue"

Write-Host "=== 模型响应诊断 $(Get-Date -Format 'HH:mm:ss') ===" -ForegroundColor Cyan
Write-Host ""

# 结果收集
$results = @()

# 1. MiniMax M2.7
Write-Host "[1/5] 测试 MiniMax M2.7..." -NoNewline
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $body = @{
        model = "minimax/M2.7"
        messages = @(@{role = "user"; content = "Hi"})
        max_tokens = 10
    } | ConvertTo-Json -Compress
    
    $resp = Invoke-RestMethod -Uri "https://api.minimax.chat/v1/chat/completions" `
        -Method Post `
        -Headers @{
            "Authorization" = "Bearer $env:MINIMAX_API_KEY"
            "Content-Type" = "application/json"
        } `
        -Body $body `
        -TimeoutSec $TimeoutSeconds
    
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " OK ${elapsed}ms" -ForegroundColor Green
    $results += @{name="MiniMax M2.7"; status="OK"; time=$elapsed}
} catch {
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " FAIL ${elapsed}ms: $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))" -ForegroundColor Red
    $results += @{name="MiniMax M2.7"; status="FAIL"; time=$elapsed; error=$_.Exception.Message}
}

# 2. Ollama gemma4:26b (WSL2)
Write-Host "[2/5] 测试 Ollama gemma4:26b..." -NoNewline
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $body = @{
        model = "gemma4:26b"
        prompt = "Hi"
        stream = $false
    } | ConvertTo-Json -Compress
    
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 15
    
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " OK ${elapsed}ms" -ForegroundColor Green
    $results += @{name="Ollama gemma4:26b"; status="OK"; time=$elapsed}
} catch {
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " FAIL ${elapsed}ms: $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))" -ForegroundColor Red
    $results += @{name="Ollama gemma4:26b"; status="FAIL"; time=$elapsed; error=$_.Exception.Message}
}

# 3. Ollama qwen3.5:9b
Write-Host "[3/5] 测试 Ollama qwen3.5:9b..." -NoNewline
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $body = @{
        model = "qwen3.5:9b"
        prompt = "Hi"
        stream = $false
    } | ConvertTo-Json -Compress
    
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 15
    
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " OK ${elapsed}ms" -ForegroundColor Green
    $results += @{name="Ollama qwen3.5:9b"; status="OK"; time=$elapsed}
} catch {
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " FAIL ${elapsed}ms: $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))" -ForegroundColor Red
    $results += @{name="Ollama qwen3.5:9b"; status="FAIL"; time=$elapsed; error=$_.Exception.Message}
}

# 4. Ollama qwen2.5:7b
Write-Host "[4/5] 测试 Ollama qwen2.5:7b..." -NoNewline
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $body = @{
        model = "qwen2.5:7b"
        prompt = "Hi"
        stream = $false
    } | ConvertTo-Json -Compress
    
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 15
    
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " OK ${elapsed}ms" -ForegroundColor Green
    $results += @{name="Ollama qwen2.5:7b"; status="OK"; time=$elapsed}
} catch {
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " FAIL ${elapsed}ms: $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))" -ForegroundColor Red
    $results += @{name="Ollama qwen2.5:7b"; status="FAIL"; time=$elapsed; error=$_.Exception.Message}
}

# 5. Ollama qwen2.5:14b
Write-Host "[5/5] 测试 Ollama qwen2.5:14b..." -NoNewline
$sw = [Diagnostics.Stopwatch]::StartNew()
try {
    $body = @{
        model = "qwen2.5:14b"
        prompt = "Hi"
        stream = $false
    } | ConvertTo-Json -Compress
    
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/generate" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 15
    
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " OK ${elapsed}ms" -ForegroundColor Green
    $results += @{name="Ollama qwen2.5:14b"; status="OK"; time=$elapsed}
} catch {
    $elapsed = $sw.ElapsedMilliseconds
    Write-Host " FAIL ${elapsed}ms: $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))" -ForegroundColor Red
    $results += @{name="Ollama qwen2.5:14b"; status="FAIL"; time=$elapsed; error=$_.Exception.Message}
}

Write-Host ""
Write-Host "=== 汇总 ===" -ForegroundColor Cyan
$results | ForEach-Object {
    $color = if ($_.status -eq "OK") { "Green" } else { "Red" }
    $timeStr = if ($_.time) { "$($_.time)ms" } else { "N/A" }
    Write-Host "$($_.name.PadRight(25)) $($_.status.PadRight(6)) $timeStr" -ForegroundColor $color
}
