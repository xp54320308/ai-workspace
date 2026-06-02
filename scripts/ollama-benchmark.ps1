# Ollama Model Benchmark
# Date: 2026-04-10
# Hardware: RTX 5090 D v2 (24GB) / WSL2 Ubuntu

$models = @(
    "qwen2.5:7b",
    "qwen2.5:14b",
    "qwen2.5:7b-instruct-q4_0",
    "qwen3.5:9b",
    "deepseek-r1:8b",
    "deepseek-r1:32b",
    "gemma4:26b",
    "glm-4.7-flash:latest",
    "moondream:latest",
    "llava:latest",
    "fredrezones55/Qwopus3.5:latest",
    "qwen3.5-9b-toolhub:latest"
)

$prompts = @{
    "math" = "If a chicken has 1 head and 2 legs, a rabbit has 1 head and 4 legs. There are 35 heads and 94 legs total. How many chickens and rabbits are there? Show your reasoning briefly."
    "creative" = "Write a short English poem about the night sky, 4 lines"
    "coding" = "Write a Python quicksort function with comments"
    "knowledge" = "What is quantum computing? Explain in simple terms."
}

$results = @()

foreach ($model in $models) {
    Write-Host ""
    Write-Host "========== MODEL: $model ==========" -ForegroundColor Cyan
    
    $modelCheck = ollama list | Out-String
    if (-not ($modelCheck -match [regex]::Escape($model))) {
        Write-Host "  [SKIP] Model not found" -ForegroundColor Yellow
        continue
    }
    
    foreach ($testName in $prompts.Keys) {
        $prompt = $prompts[$testName]
        Write-Host "  [$testName]" -NoNewline
        
        $start = Get-Date
        $output = ollama run $model $prompt --verbose 2>&1 | Out-String
        $end = Get-Date
        $duration = ($end - $start).TotalSeconds
        
        $totalDuration = 0
        $loadDuration = 0
        $promptEvalRate = 0
        $evalRate = 0
        $evalCount = 0
        
        if ($output -match "total duration:\s+(\d+\.?\d*)s") { $totalDuration = [double]$matches[1] }
        if ($output -match "load duration:\s+(\d+\.?\d*)s") { $loadDuration = [double]$matches[1] }
        if ($output -match "prompt eval rate:\s+(\d+\.?\d*)\s+tokens/s") { $promptEvalRate = [double]$matches[1] }
        if ($output -match "eval rate:\s+(\d+\.?\d*)\s+tokens/s") { $evalRate = [double]$matches[1] }
        if ($output -match "eval count:\s+(\d+)\s+token") { $evalCount = [int]$matches[1] }
        
        Write-Host " OK | ${duration}s | ${evalRate} tok/s | ${evalCount} tokens" -ForegroundColor Green
        
        $results += [PSCustomObject]@{
            Model = $model
            Test = $testName
            Duration_S = [Math]::Round($duration, 2)
            Load_S = [Math]::Round($loadDuration, 2)
            TPS = [Math]::Round($evalRate, 1)
            Prompt_TPS = [Math]::Round($promptEvalRate, 1)
            Tokens = $evalCount
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "           BENCHMARK SUMMARY" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

$summary = $results | Group-Object Model | ForEach-Object {
    $avgDur = ($_.Group | Measure-Object -Property Duration_S -Average).Average
    $avgTPS = ($_.Group | Measure-Object -Property TPS -Average).Average
    $totalTok = ($_.Group | Measure-Object -Property Tokens -Sum).Sum
    [PSCustomObject]@{
        Model = $_.Name
        "Avg_Duration_s" = [Math]::Round($avgDur, 1)
        "Avg_TPS" = [Math]::Round($avgTPS, 1)
        "Total_Tokens" = $totalTok
    }
}

$summary | Sort-Object Avg_TPS -Descending | Format-Table -AutoSize

$csvPath = "$HOME/Desktop/ollama_benchmark.csv"
$results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host ""
Write-Host "Results saved: $csvPath" -ForegroundColor Green
