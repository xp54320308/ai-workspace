param(
    [string]$GatewayUrl = "http://127.0.0.1:18789",
    [int]$IntervalSeconds = 5,
    [int]$TimeoutSeconds = 3,
    [int]$HistorySize = 24,
    [string]$LogDirectory = "$env:USERPROFILE\.openclaw\monitor",
    [string]$FeishuWebhookUrl = $env:OPENCLAW_FEISHU_WEBHOOK,
    [int]$FeishuCooldownMinutes = 15,
    [int]$MaxIterations = 0,
    [switch]$NoClear
)

# OpenClaw Gateway Monitor
# Enhancements: response history, Feishu alerts, logs, reports

$ErrorActionPreference = "Stop"

$tokenPath = Join-Path $env:USERPROFILE ".openclaw\gateway.token"
if (-not (Test-Path -LiteralPath $tokenPath)) {
    throw "Gateway token not found: $tokenPath"
}

$token = (Get-Content -LiteralPath $tokenPath | Select-Object -First 1).Trim()
$headers = @{ Authorization = "Bearer $token" }

$script:RunStartedAt = Get-Date
$script:LastState = $null
$script:LastDownAlertAt = $null
$script:FailureStreak = 0
$script:History = [System.Collections.Generic.List[object]]::new()

function Ensure-Directory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Get-SampleLogPath {
    param([datetime]$Timestamp)

    Join-Path $LogDirectory ("gateway-monitor-{0}.csv" -f $Timestamp.ToString("yyyyMMdd"))
}

function Get-EventLogPath {
    param([datetime]$Timestamp)

    Join-Path $LogDirectory ("gateway-events-{0}.log" -f $Timestamp.ToString("yyyyMMdd"))
}

function Get-MarkdownReportPath {
    Join-Path $LogDirectory "gateway-report-latest.md"
}

function Get-JsonReportPath {
    Join-Path $LogDirectory "gateway-report-latest.json"
}

function Get-SafeStatusCode {
    param([System.Management.Automation.ErrorRecord]$ErrorRecord)

    if ($null -eq $ErrorRecord.Exception.Response) {
        return $null
    }

    try {
        return [int]$ErrorRecord.Exception.Response.StatusCode
    } catch {
        try {
            return [int]$ErrorRecord.Exception.Response.StatusCode.value__
        } catch {
            return $null
        }
    }
}

function Get-GatewayStatus {
    $startedAt = Get-Date

    try {
        $response = Invoke-WebRequest -Uri "$GatewayUrl/health" -Headers $headers -TimeoutSec $TimeoutSeconds -UseBasicParsing
        $elapsedMs = [math]::Round(((Get-Date) - $startedAt).TotalMilliseconds, 0)

        [pscustomobject]@{
            Status = "OK"
            StatusCode = $response.StatusCode
            ResponseTimeMs = [int]$elapsedMs
            Error = $null
        }
    } catch {
        $failureStatusCode = Get-SafeStatusCode $_
        [pscustomobject]@{
            Status = "FAIL"
            StatusCode = $failureStatusCode
            ResponseTimeMs = $null
            Error = $_.Exception.Message
        }
    }
}

function Get-SessionCount {
    $sessionsPath = Join-Path $env:USERPROFILE ".openclaw\agents\main\sessions"

    if (Test-Path -LiteralPath $sessionsPath) {
        return (Get-ChildItem -LiteralPath $sessionsPath -Filter "*.jsonl" -File | Measure-Object).Count
    }

    return 0
}

function Add-HistorySample {
    param([pscustomobject]$Sample)

    [void]$script:History.Add($Sample)
    while ($script:History.Count -gt $HistorySize) {
        $script:History.RemoveAt(0)
    }
}

function Write-SampleLog {
    param([pscustomobject]$Sample)

    $logPath = Get-SampleLogPath -Timestamp $Sample.Timestamp
    $row = [pscustomobject]@{
        Timestamp = $Sample.TimestampText
        Status = $Sample.Status
        StatusCode = $Sample.StatusCode
        ResponseTimeMs = $Sample.ResponseTimeMs
        Sessions = $Sample.Sessions
        Error = $Sample.Error
    }

    if (Test-Path -LiteralPath $logPath) {
        $row | Export-Csv -LiteralPath $logPath -Append -NoTypeInformation -Encoding UTF8
    } else {
        $row | Export-Csv -LiteralPath $logPath -NoTypeInformation -Encoding UTF8
    }
}

function Write-EventLog {
    param(
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level,
        [string]$Message,
        [datetime]$Timestamp = (Get-Date)
    )

    $logPath = Get-EventLogPath -Timestamp $Timestamp
    $line = "{0} [{1}] {2}" -f $Timestamp.ToString("yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

function Get-Percentile {
    param(
        [int[]]$Values,
        [double]$Percentile
    )

    if ($null -eq $Values -or $Values.Count -eq 0) {
        return $null
    }

    $sorted = @($Values | Sort-Object)
    $index = [math]::Ceiling(($Percentile / 100) * $sorted.Count) - 1
    $index = [math]::Max(0, [math]::Min($index, $sorted.Count - 1))
    return [int]$sorted[$index]
}

function Format-Number {
    param($Value)

    if ($null -eq $Value) {
        return "N/A"
    }

    if ($Value -is [double] -or $Value -is [float] -or $Value -is [decimal]) {
        $rounded = [math]::Round([double]$Value, 2)
        if ($rounded -eq [math]::Round($rounded, 0)) {
            return ([int][math]::Round($rounded, 0)).ToString()
        }

        return $rounded.ToString("0.##")
    }

    return [string]$Value
}

function Get-Statistics {
    param([System.Collections.Generic.List[object]]$Samples)

    $allSamples = @($Samples)
    $okSamples = @($allSamples | Where-Object { $_.Status -eq "OK" -and $null -ne $_.ResponseTimeMs })
    $responseValues = @($okSamples | ForEach-Object { [int]$_.ResponseTimeMs })
    $sessionValues = @($allSamples | ForEach-Object { [int]$_.Sessions })

    $total = $allSamples.Count
    $okCount = $okSamples.Count
    $failCount = @($allSamples | Where-Object { $_.Status -eq "FAIL" }).Count
    $uptimePercent = 0
    if ($total -gt 0) {
        $uptimePercent = [math]::Round(($okCount / $total) * 100, 2)
    }

    $avgResponseMs = $null
    $minResponseMs = $null
    $maxResponseMs = $null
    $avgSessions = 0
    $maxSessions = 0

    if ($responseValues.Count -gt 0) {
        $avgResponseMs = [math]::Round(($responseValues | Measure-Object -Average).Average, 0)
        $minResponseMs = ($responseValues | Measure-Object -Minimum).Minimum
        $maxResponseMs = ($responseValues | Measure-Object -Maximum).Maximum
    }

    if ($sessionValues.Count -gt 0) {
        $avgSessions = [math]::Round(($sessionValues | Measure-Object -Average).Average, 1)
        $maxSessions = ($sessionValues | Measure-Object -Maximum).Maximum
    }

    $p95ResponseMs = Get-Percentile -Values $responseValues -Percentile 95
    $windowMinutes = [math]::Round(($total * $IntervalSeconds) / 60, 1)

    [pscustomobject]@{
        TotalChecks = $total
        OkCount = $okCount
        FailCount = $failCount
        UptimePercent = $uptimePercent
        AvgResponseMs = $avgResponseMs
        MinResponseMs = $minResponseMs
        P95ResponseMs = $p95ResponseMs
        MaxResponseMs = $maxResponseMs
        AvgSessions = $avgSessions
        MaxSessions = $maxSessions
        ConsecutiveFailures = $script:FailureStreak
        WindowMinutes = $windowMinutes
    }
}

function Send-FeishuNotification {
    param(
        [string]$Title,
        [string]$Body
    )

    if ([string]::IsNullOrWhiteSpace($FeishuWebhookUrl)) {
        return $false
    }

    $payload = @{
        msg_type = "text"
        content = @{
            text = "$Title`n$Body"
        }
    } | ConvertTo-Json -Depth 4

    try {
        Invoke-RestMethod -Uri $FeishuWebhookUrl -Method Post -Body $payload -ContentType "application/json; charset=utf-8" | Out-Null
        return $true
    } catch {
        Write-EventLog -Level "ERROR" -Message ("Feishu notification failed: {0}" -f $_.Exception.Message)
        return $false
    }
}

function Handle-Alerts {
    param(
        [pscustomobject]$Sample,
        [pscustomobject]$Stats
    )

    $now = $Sample.Timestamp

    if ($Sample.Status -eq "FAIL") {
        $script:FailureStreak++
        $shouldAlert = $false

        if ($script:LastState -ne "FAIL") {
            Write-EventLog -Level "WARN" -Timestamp $now -Message ("Gateway DOWN | code={0} | error={1}" -f $Sample.StatusCode, $Sample.Error)
            $shouldAlert = $true
        } else {
            $cooldownExpired = $false
            if (-not [string]::IsNullOrWhiteSpace($FeishuWebhookUrl) -and $null -ne $script:LastDownAlertAt) {
                if (($now - $script:LastDownAlertAt).TotalMinutes -ge $FeishuCooldownMinutes) {
                    $cooldownExpired = $true
                }
            }

            if ($cooldownExpired) {
                $shouldAlert = $true
            }
        }

        if ($shouldAlert) {
            $statusCodeText = "N/A"
            if ($null -ne $Sample.StatusCode) {
                $statusCodeText = [string]$Sample.StatusCode
            }
            $bodyLines = @()
            $bodyLines += "Time: $($Sample.TimestampText)"
            $bodyLines += "Gateway: $GatewayUrl"
            $bodyLines += "Status code: $statusCodeText"
            $bodyLines += "Error: $($Sample.Error)"
            $bodyLines += "Consecutive failures: $($script:FailureStreak)"
            $bodyLines += "Window uptime: $($Stats.UptimePercent)%"
            $body = $bodyLines -join "`n"

            $downAlertSent = Send-FeishuNotification -Title "OpenClaw Gateway DOWN" -Body $body
            if ($downAlertSent) {
                Write-EventLog -Level "INFO" -Timestamp $now -Message "Feishu down alert sent."
                $script:LastDownAlertAt = $now
            }
        }
    } else {
        if ($script:LastState -eq "FAIL") {
            Write-EventLog -Level "INFO" -Timestamp $now -Message ("Gateway RECOVERED | response={0}ms" -f $Sample.ResponseTimeMs)

            if (-not [string]::IsNullOrWhiteSpace($FeishuWebhookUrl)) {
                $bodyLines = @()
                $bodyLines += "Time: $($Sample.TimestampText)"
                $bodyLines += "Gateway: $GatewayUrl"
                $bodyLines += "Response time: $($Sample.ResponseTimeMs) ms"
                $bodyLines += "Status code: $($Sample.StatusCode)"
                $bodyLines += "Window uptime: $($Stats.UptimePercent)%"
                $body = $bodyLines -join "`n"

                $recoveryAlertSent = Send-FeishuNotification -Title "OpenClaw Gateway RECOVERED" -Body $body
                if ($recoveryAlertSent) {
                    Write-EventLog -Level "INFO" -Timestamp $now -Message "Feishu recovery alert sent."
                }
            }
        }

        $script:FailureStreak = 0
    }

    $script:LastState = $Sample.Status
}

function Update-Reports {
    param(
        [pscustomobject]$CurrentSample,
        [pscustomobject]$Stats,
        [System.Collections.Generic.List[object]]$Samples
    )

    $markdownPath = Get-MarkdownReportPath
    $jsonPath = Get-JsonReportPath
    $sampleLogPath = Get-SampleLogPath -Timestamp $CurrentSample.Timestamp
    $eventLogPath = Get-EventLogPath -Timestamp $CurrentSample.Timestamp
    $recent = @($Samples | Select-Object -Last ([math]::Min($Samples.Count, 10)))
    $currentResponseText = "N/A"
    if ($null -ne $CurrentSample.ResponseTimeMs) {
        $currentResponseText = "$($CurrentSample.ResponseTimeMs) ms"
    }

    $lines = @()
    $lines += "# OpenClaw Gateway Monitor Report"
    $lines += ""
    $lines += ("Generated At: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
    $lines += ("Gateway URL: {0}" -f $GatewayUrl)
    $lines += ("Current Status: {0}" -f $CurrentSample.Status)
    $lines += ("Current Response: {0}" -f $currentResponseText)
    $lines += ("Current Sessions: {0}" -f $CurrentSample.Sessions)
    $lines += ""
    $lines += "## Summary"
    $lines += ("- Checks in window: {0}" -f $Stats.TotalChecks)
    $lines += ("- Window size: about {0} minutes" -f $Stats.WindowMinutes)
    $lines += ("- Uptime: {0}%" -f $Stats.UptimePercent)
    $lines += ("- Consecutive failures: {0}" -f $Stats.ConsecutiveFailures)
    $lines += ("- Avg / P95 / Max response: {0} / {1} / {2} ms" -f (Format-Number $Stats.AvgResponseMs), (Format-Number $Stats.P95ResponseMs), (Format-Number $Stats.MaxResponseMs))
    $lines += ("- Avg / Max sessions: {0} / {1}" -f (Format-Number $Stats.AvgSessions), (Format-Number $Stats.MaxSessions))
    $lines += ""
    $lines += "## Recent Samples"

    foreach ($item in $recent) {
        $responseText = "N/A"
        if ($null -ne $item.ResponseTimeMs) {
            $responseText = "$($item.ResponseTimeMs) ms"
        }
        $lines += ("- {0} | {1} | code={2} | response={3} | sessions={4}" -f $item.TimestampText, $item.Status, $item.StatusCode, $responseText, $item.Sessions)
    }

    Set-Content -LiteralPath $markdownPath -Value $lines -Encoding UTF8

    $reportObject = [pscustomobject]@{
        generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        gatewayUrl = $GatewayUrl
        intervalSeconds = $IntervalSeconds
        current = [pscustomobject]@{
            timestamp = $CurrentSample.TimestampText
            status = $CurrentSample.Status
            statusCode = $CurrentSample.StatusCode
            responseTimeMs = $CurrentSample.ResponseTimeMs
            sessions = $CurrentSample.Sessions
            error = $CurrentSample.Error
        }
        stats = $Stats
        recentSamples = $recent
        files = [pscustomobject]@{
            sampleLog = $sampleLogPath
            eventLog = $eventLogPath
            markdownReport = $markdownPath
        }
    }

    $reportObject | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
}

function Write-MonitorRow {
    param(
        [string]$Label,
        [string]$Value,
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    Write-Host ("{0,-22} : {1}" -f $Label, $Value) -ForegroundColor $Color
}

function Write-HistoryChart {
    param([System.Collections.Generic.List[object]]$Samples)

    $items = @($Samples)
    if ($items.Count -eq 0) {
        Write-Host "No history yet." -ForegroundColor DarkGray
        return
    }

    $values = @($items | Where-Object { $null -ne $_.ResponseTimeMs } | ForEach-Object { [int]$_.ResponseTimeMs })
    $maxValue = 1
    if ($values.Count -gt 0) {
        $maxValue = [math]::Max(1, ($values | Measure-Object -Maximum).Maximum)
    }
    $barWidth = 28

    foreach ($item in $items) {
        if ($item.Status -eq "FAIL") {
            $bar = ("!" * [math]::Min(8, $barWidth)).PadRight($barWidth)
            Write-Host ("{0} | {1} | DOWN" -f $item.Timestamp.ToString("HH:mm:ss"), $bar) -ForegroundColor Red
            continue
        }

        $ratio = [double]$item.ResponseTimeMs / [double]$maxValue
        $filled = [math]::Max(1, [math]::Round($ratio * $barWidth, 0))
        $bar = ("#" * $filled).PadRight($barWidth)
        Write-Host ("{0} | {1} | {2,4} ms" -f $item.Timestamp.ToString("HH:mm:ss"), $bar, $item.ResponseTimeMs) -ForegroundColor Green
    }
}

function Render-Screen {
    param(
        [pscustomobject]$CurrentSample,
        [pscustomobject]$Stats
    )

    if (-not $NoClear) {
        Clear-Host
    }

    Write-Host "=== OpenClaw Gateway Monitor ===" -ForegroundColor Cyan
    Write-Host ("Now: {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -ForegroundColor Gray
    Write-Host ("Running Since: {0}" -f $script:RunStartedAt.ToString("yyyy-MM-dd HH:mm:ss")) -ForegroundColor Gray
    Write-Host ""

    if ($CurrentSample.Status -eq "OK") {
        Write-MonitorRow "Gateway" "OK" "Green"
        Write-MonitorRow "Response" ("{0} ms" -f $CurrentSample.ResponseTimeMs) "Green"
    } else {
        $statusCodeText = "N/A"
        if ($null -ne $CurrentSample.StatusCode) {
            $statusCodeText = [string]$CurrentSample.StatusCode
        }
        Write-MonitorRow "Gateway" "DOWN" "Red"
        Write-MonitorRow "Status Code" $statusCodeText "Red"
        Write-MonitorRow "Error" $CurrentSample.Error "Red"
    }

    $feishuState = "enabled"
    if ([string]::IsNullOrWhiteSpace($FeishuWebhookUrl)) {
        $feishuState = "disabled"
    }

    Write-MonitorRow "Sessions" ("{0} active" -f $CurrentSample.Sessions) "Yellow"
    Write-MonitorRow "Gateway URL" $GatewayUrl "Cyan"
    Write-MonitorRow "Feishu Webhook" $feishuState "Magenta"
    Write-MonitorRow "Sample Log" (Get-SampleLogPath -Timestamp $CurrentSample.Timestamp) "DarkGray"
    Write-MonitorRow "Report" (Get-MarkdownReportPath) "DarkGray"
    Write-Host ""

    Write-Host "=== Window Stats ===" -ForegroundColor Cyan
    Write-MonitorRow "Checks" ([string]$Stats.TotalChecks) "White"
    Write-MonitorRow "Uptime" ("{0}%" -f $Stats.UptimePercent) "White"
    Write-MonitorRow "Failures" ([string]$Stats.FailCount) "White"
    Write-MonitorRow "Failure Streak" ([string]$Stats.ConsecutiveFailures) "White"
    Write-MonitorRow "Min Response" ("{0} ms" -f (Format-Number $Stats.MinResponseMs)) "White"
    Write-MonitorRow "Avg Response" ("{0} ms" -f (Format-Number $Stats.AvgResponseMs)) "White"
    Write-MonitorRow "P95 Response" ("{0} ms" -f (Format-Number $Stats.P95ResponseMs)) "White"
    Write-MonitorRow "Max Response" ("{0} ms" -f (Format-Number $Stats.MaxResponseMs)) "White"
    Write-MonitorRow "Avg Sessions" ([string](Format-Number $Stats.AvgSessions)) "White"
    Write-Host ""

    Write-Host ("=== Response History (last {0} checks) ===" -f $script:History.Count) -ForegroundColor Cyan
    Write-HistoryChart -Samples $script:History
    Write-Host ""
    Write-Host "Press Ctrl+C to stop" -ForegroundColor DarkGray
}

Ensure-Directory -Path $LogDirectory
Write-EventLog -Level "INFO" -Message "Gateway monitor started."

$iteration = 0
while ($true) {
    $timestamp = Get-Date
    $health = Get-GatewayStatus
    $sessions = Get-SessionCount
    $statusCode = $null
    if ($null -ne $health.StatusCode) {
        $statusCode = [int]$health.StatusCode
    }

    $sample = [pscustomobject]@{
        Timestamp = $timestamp
        TimestampText = $timestamp.ToString("yyyy-MM-dd HH:mm:ss")
        Status = $health.Status
        StatusCode = $statusCode
        ResponseTimeMs = $health.ResponseTimeMs
        Sessions = [int]$sessions
        Error = $health.Error
    }

    Add-HistorySample -Sample $sample
    Write-SampleLog -Sample $sample

    $stats = Get-Statistics -Samples $script:History
    Handle-Alerts -Sample $sample -Stats $stats
    Update-Reports -CurrentSample $sample -Stats $stats -Samples $script:History
    Render-Screen -CurrentSample $sample -Stats $stats

    $iteration++
    if ($MaxIterations -gt 0 -and $iteration -ge $MaxIterations) {
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}

Write-EventLog -Level "INFO" -Message "Gateway monitor stopped."
