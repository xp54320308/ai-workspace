# OpenClaw Auto Monitor Pro v3.1
# Auto-monitoring + Self-healing + Smart Fallback
# Optimized: Trust Ollama service, fallback only on service failure

param(
    [switch]$Auto,
    [int]$IntervalSeconds = 300
)

$ErrorActionPreference = "Continue"
$LogDir = "$env:USERPROFILE\.openclaw\workspace\memory"
$StateFile = "$LogDir\model-state.json"
$TodayLog = "$LogDir\monitor-$(Get-Date -Format 'yyyy-MM-dd').md"

# ==================== Model Priority Config ====================
$ModelPriority = @{
    Primary = "ollama/qwen3.5:9b"
    Fallback = @("ollama/qwen2.5:14b", "ollama/gemma4:26b", "ollama/deepseek-r1:8b")
    MiniMax = "minimax/MiniMax-M2.7"
}

# ==================== Functions ====================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $entry = "[$timestamp] [$Level] $Message"
    Write-Host $entry
    
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    
    Add-Content -Path $TodayLog -Value $entry -Encoding UTF8
}

function Get-State {
    if (Test-Path $StateFile) {
        try {
            $content = Get-Content -Path $StateFile -Raw -Encoding UTF8
            return $content | ConvertFrom-Json
        } catch {
            return @{
                CurrentModel = $ModelPriority.Primary
                PrimaryAvailable = $true
                LastSwitch = $null
                SwitchCount = 0
            }
        }
    }
    return @{
        CurrentModel = $ModelPriority.Primary
        PrimaryAvailable = $true
        LastSwitch = $null
        SwitchCount = 0
    }
}

function Set-State {
    param($State)
    $State | ConvertTo-Json -Depth 3 | Set-Content -Path $StateFile -Encoding UTF8
}

function Test-Gateway {
    try {
        $start = Get-Date
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:18789/health" -TimeoutSec 3 -UseBasicParsing
        $elapsed = ((Get-Date) - $start).TotalMilliseconds
        if ($response.StatusCode -eq 200) {
            return @{ Status = "OK"; ResponseTime = [math]::Round($elapsed); Message = "OK" }
        }
    } catch {
        return @{ Status = "FAIL"; ResponseTime = -1; Message = $_.Exception.Message }
    }
    return @{ Status = "UNKNOWN"; ResponseTime = -1; Message = "Unknown" }
}

function Get-OllamaModels {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $models = ($response.Content | ConvertFrom-Json).models
            return @{
                Status = "OK"
                Models = $models
                ModelNames = $models | ForEach-Object { $_.name }
            }
        }
    } catch {
        return @{ Status = "FAIL"; Models = @(); ModelNames = @() }
    }
    return @{ Status = "UNKNOWN"; Models = @(); ModelNames = @() }
}

function Test-OllamaService {
    try {
        $start = Get-Date
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 -UseBasicParsing
        $elapsed = ((Get-Date) - $start).TotalMilliseconds
        
        if ($response.StatusCode -eq 200) {
            $models = ($response.Content | ConvertFrom-Json).models
            return @{ 
                Status = "OK"; 
                ResponseTime = [math]::Round($elapsed); 
                Message = "OK";
                ModelCount = $models.Count
            }
        }
    } catch {
        # Check WSL2
        $wslCheck = wsl -e bash -c "systemctl is-active ollama 2>/dev/null || pgrep -a ollama"
        if ($wslCheck -match "active" -or $wslCheck -match "ollama") {
            return @{ Status = "WARN"; ResponseTime = -1; Message = "WSL2 running but port not responding" }
        }
        return @{ Status = "FAIL"; ResponseTime = -1; Message = $_.Exception.Message }
    }
    return @{ Status = "UNKNOWN"; ResponseTime = -1; Message = "Unknown" }
}

function Test-MiniMax {
    try {
        $headers = @{ "Authorization" = "Bearer sk-cp-gnEp0ft0GOHr-40mLI4HEoxzbKVjIAIsCVkVSo4FXzREcZV0QLNS5AKW38GUiXFDmMQOVHcOREHNFzqweuPrStS4ie1FjXHh481HP7-QzWU90nvLmnwU2xs" }
        $body = '{"model": "MiniMax-M2.7", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}'
        
        $start = Get-Date
        $response = Invoke-WebRequest -Uri "https://api.minimax.io/v1/text/chatcompletion_v2" -Method POST -Headers $headers -Body $body -TimeoutSec 5 -UseBasicParsing
        $elapsed = ((Get-Date) - $start).TotalMilliseconds
        
        if ($response.StatusCode -eq 200) {
            return @{ Status = "OK"; ResponseTime = [math]::Round($elapsed); Message = "OK" }
        }
    } catch {
        return @{ Status = "FAIL"; ResponseTime = -1; Message = $_.Exception.Message }
    }
    return @{ Status = "UNKNOWN"; ResponseTime = -1; Message = "Unknown" }
}

function Repair-Ollama {
    Write-Log "Attempting to repair Ollama..." "WARN"
    
    $result = wsl -e bash -c "sudo systemctl restart ollama 2>/dev/null"
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Ollama restarted successfully" "INFO"
        Start-Sleep -Seconds 3
        return $true
    }
    
    $result = wsl -e bash -c "ollama serve &"
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Ollama service started" "INFO"
        Start-Sleep -Seconds 3
        return $true
    }
    
    return $false
}

function Repair-Gateway {
    Write-Log "Attempting to repair Gateway..." "WARN"
    
    $output = & openclaw gateway restart 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Gateway restarted successfully" "INFO"
        Start-Sleep -Seconds 5
        return $true
    }
    
    return $false
}

function Get-SystemInfo {
    try {
        $disk = Get-PSDrive -Name C | Select-Object -First 1
        $memory = Get-CimInstance Win32_OperatingSystem
        $cpu = Get-CimInstance Win32_Processor
        
        return @{
            DiskUsed = [math]::Round($disk.Used / 1GB, 1)
            DiskTotal = [math]::Round(($disk.Used + $disk.Free) / 1GB, 1)
            DiskPercent = [math]::Round(($disk.Used / ($disk.Used + $disk.Free)) * 100, 1)
            MemoryUsed = [math]::Round($memory.TotalVisibleMemorySize / 1MB - $memory.FreePhysicalMemory / 1MB, 1)
            MemoryTotal = [math]::Round($memory.TotalVisibleMemorySize / 1MB, 1)
            MemoryPercent = [math]::Round((1 - $memory.FreePhysicalMemory / $memory.TotalVisibleMemorySize) * 100, 1)
            CpuLoad = [math]::Round($cpu.LoadPercentage, 1)
        }
    } catch {
        return @{
            DiskPercent = 0
            MemoryPercent = 0
            CpuLoad = 0
        }
    }
}

function Get-BestModel {
    # Returns the best available model based on Ollama service status
    $ollamaModels = Get-OllamaModels
    
    if ($ollamaModels.Status -eq "OK") {
        # Check if primary model is in the list
        $primaryName = ($ModelPriority.Primary -split "/")[1]
        
        if ($ollamaModels.ModelNames -contains $primaryName) {
            return @{
                Model = $ModelPriority.Primary
                Available = $true
                Reason = "Primary available"
            }
        }
        
        # Try fallbacks
        foreach ($fallback in $ModelPriority.Fallback) {
            $fallbackName = ($fallback -split "/")[1]
            if ($ollamaModels.ModelNames -contains $fallbackName) {
                return @{
                    Model = $fallback
                    Available = $true
                    Reason = "Fallback: $fallback"
                }
            }
        }
        
        # Ollama running but none of our preferred models
        if ($ollamaModels.ModelNames.Count -gt 0) {
            $anyModel = "ollama/" + $ollamaModels.ModelNames[0]
            return @{
                Model = $anyModel
                Available = $true
                Reason = "Using: $($ollamaModels.ModelNames[0])"
            }
        }
    }
    
    return @{
        Model = "NONE"
        Available = $false
        Reason = "No model available"
    }
}

# ==================== Main Program ====================

Write-Log "========== OpenClaw Auto Monitor Pro v3.1 Started ==========" "INFO"
Write-Log "Primary: $($ModelPriority.Primary)" "INFO"
Write-Log "Fallbacks: $($ModelPriority.Fallback -join ", ")" "INFO"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$summary = @()

# 1. Check Gateway
Write-Log "Checking Gateway..." "INFO"
$gateway = Test-Gateway
if ($gateway.Status -eq "OK") {
    Write-Log "Gateway: OK ${gateway.ResponseTime}ms" "INFO"
    $summary += "Gateway: OK"
} else {
    Write-Log "Gateway: FAIL ${gateway.Message}" "ERROR"
    $summary += "Gateway: FAIL"
    
    if (Repair-Gateway) {
        Write-Log "Gateway auto-repaired" "INFO"
        $summary += " [Repaired]"
    }
}

# 2. Check Ollama Service
Write-Log "Checking Ollama (WSL2)..." "INFO"
$ollama = Test-OllamaService
if ($ollama.Status -eq "OK") {
    Write-Log "Ollama: OK ${ollama.ModelCount} models available" "INFO"
    $summary += "Ollama: OK"
} elseif ($ollama.Status -eq "WARN") {
    Write-Log "Ollama: WARN ${ollama.Message}" "WARN"
    $summary += "Ollama: WARN"
    
    if (Repair-Ollama) {
        Write-Log "Ollama auto-repaired" "INFO"
        $summary += " [Repaired]"
    }
} else {
    Write-Log "Ollama: FAIL ${ollama.Message}" "ERROR"
    $summary += "Ollama: FAIL"
    
    if (Repair-Ollama) {
        Write-Log "Ollama auto-repaired" "INFO"
        $summary += " [Repaired]"
    }
}

# 3. Smart Model Selection
Write-Log "Selecting best available model..." "INFO"
$bestModel = Get-BestModel
$state = Get-State

if ($bestModel.Available) {
    if ($state.CurrentModel -ne $bestModel.Model) {
        Write-Log "Model changed: $($state.CurrentModel) -> $($bestModel.Model)" "WARN"
        $state.CurrentModel = $bestModel.Model
        $state.LastSwitch = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $state.SwitchCount++
        Set-State -State $state
        Write-Log "SWITCHED TO: $($bestModel.Model) (#$($state.SwitchCount))" "WARN"
    }
    Write-Log "Current Model: $($bestModel.Model)" "INFO"
    $summary += "Model: $($bestModel.Model)"
} else {
    Write-Log "Model: FAIL - No models available" "ERROR"
    $summary += "Model: FAIL"
}

# 4. Check MiniMax
Write-Log "Checking MiniMax API..." "INFO"
$minimax = Test-MiniMax
if ($minimax.Status -eq "OK") {
    Write-Log "MiniMax: OK ${minimax.ResponseTime}ms" "INFO"
    $summary += "MiniMax: OK"
} else {
    Write-Log "MiniMax: FAIL ${minimax.Message}" "ERROR"
    $summary += "MiniMax: FAIL (using local)"
}

# 5. System Info
Write-Log "Getting system resources..." "INFO"
$sys = Get-SystemInfo
$memColor = if ($sys.MemoryPercent -gt 85) { "WARN" } else { "INFO" }
$diskColor = if ($sys.DiskPercent -gt 80) { "WARN" } else { "INFO" }

Write-Log "Memory: ${sys.MemoryUsed}GB / ${sys.MemoryTotal}GB ($([math]::Round($sys.MemoryPercent))%)" $memColor
Write-Log "Disk: ${sys.DiskUsed}GB / ${sys.DiskTotal}GB ($($sys.DiskPercent)%)" $diskColor
Write-Log "CPU: ${sys.CpuLoad}%" "INFO"

# ==================== Summary ====================
Write-Log "========== Check Complete ==========" "INFO"
Write-Log ($summary -join " | ") "INFO"

# Save latest state
$state = Get-State
Write-Log "Model: $($state.CurrentModel) | Switches: $($state.SwitchCount)" "INFO"

$script:LastCheck = @{
    Time = Get-Date
    Gateway = $gateway
    Ollama = $ollama
    BestModel = $bestModel
    MiniMax = $minimax
    System = $sys
    State = $state
}

if ($Auto) {
    Write-Log "Auto mode: Next check in ${IntervalSeconds} seconds..." "INFO"
    Start-Sleep -Seconds $IntervalSeconds
    & $MyInvocation.MyCommand.Path -Auto -IntervalSeconds $IntervalSeconds
}
