# skill-guard: Scan skills for security issues before installing
# PowerShell port of safe-install.sh
param(
    [string]$SkillSlug,
    [string]$Version,
    [switch]$Force,
    [switch]$SkipScan
)

$ErrorActionPreference = "Stop"
$StagingDir = "$env:TEMP\skill-guard-staging"
$SkillsDir = "$env:USERPROFILE\.openclaw\workspace\skills"
$StagedPath = "$StagingDir\skills\$SkillSlug"

$RED   = "`e[0;31m"; $GREEN = "`e[0;32m"; $YELLOW = "`e[1;33m"; $BLUE = "`e[0;34m"; $NC = "`e[0m"
function Write-Err  { Write-Host "${RED}ERROR:${NC} $args" -ForegroundColor Red }
function Write-OK   { Write-Host "${GREEN}✓${NC} $args" -ForegroundColor Green }
function Write-Warn { Write-Host "${YELLOW}⚠${NC} $args" -ForegroundColor Yellow }
function Write-Info { Write-Host "${BLUE}→${NC} $args" -ForegroundColor Cyan }

# Check dependencies
$hub = Get-Command clawhub -ErrorAction SilentlyContinue
if (-not $hub) { Write-Err "clawhub not found. Run: npm i -g clawhub"; exit 1 }

$scanBin = $null
$snyk = Get-Command snyk-agent-scan -ErrorAction SilentlyContinue
if ($snyk) { $scanBin = $snyk.Source }
if (-not $scanBin) {
    $mcp = Get-Command "$env:USERPROFILE\.local\bin\mcp-scan.exe" -ErrorAction SilentlyContinue
    if ($mcp) { $scanBin = $mcp.Source }
}
if (-not $scanBin) { Write-Err "mcp-scan/snyk-agent-scan not found. Run: uv tool install mcp-scan"; exit 1 }

# Stage skill
Write-Info "Fetching $SkillSlug to staging area..."
Remove-Item -Recurse -Force "$StagingDir\skills\$SkillSlug" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path "$StagingDir" | Out-Null

$env:CLAWHUB_WORKDIR = $StagingDir
$installArgs = @("install", $SkillSlug, "--force")
if ($Version -and $Version.Trim()) { $installArgs += "--version"; $installArgs += $Version }

$output = & clawhub @installArgs 2>&1
if ($LASTEXITCODE -ne 0) { Write-Err "Failed to fetch skill: $output"; exit 1 }
if (-not (Test-Path $StagedPath)) { Write-Err "Skill not found in staging"; exit 1 }
Write-OK "Skill staged at $StagedPath"

if ($SkipScan) {
    Write-Warn "Skipping security scan (-SkipScan)"
    if (-not (Test-Path $SkillsDir)) { New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null }
    if ((Test-Path "$SkillsDir\$SkillSlug") -and -not $Force) { Write-Err "Already exists. Use -Force."; exit 1 }
    if (Test-Path "$SkillsDir\$SkillSlug") { Remove-Item -Recurse -Force "$SkillsDir\$SkillSlug" }
    Move-Item -Path $StagedPath -Destination "$SkillsDir\"
    Write-OK "Installed to $SkillsDir\$SkillSlug"
    exit 0
}

# Scan
Write-Info "Scanning $SkillSlug..."
Write-Host ""
$env:SNYK_TOKEN = [Environment]::GetEnvironmentVariable("SNYK_TOKEN", "User") ?? "dummy"  # Use stored token if available
$output = & $scanBin scan --skills $StagedPath 2>&1
$scanExit = $LASTEXITCODE
Write-Host $output
Write-Host ""

# Check for real issues (exclude "needs SNYK_TOKEN" auth prompts)
$needsTokenOnly = $output -match "SNYK_TOKEN" -and $output -notmatch "vulnerability|injection|malware|secret found|unsafe|high risk|medium risk|critical"
$hasIssues = $output -match "vulnerability|injection|malware|secret found|unsafe|high risk|medium risk|critical"

if ($hasIssues) {
    Write-Warn "Security issues detected in $SkillSlug"
    Write-Host "Staged at: $StagedPath (NOT installed)"
    Write-Host "Options: 1) Review, 2) Move-Item '$StagedPath' '$SkillsDir\' to install, 3) Remove-Item '$StagedPath' to discard"
    exit 2
}

if ($needsTokenOnly) {
    Write-Warn "Scanner needs SNYK_TOKEN (set it to enable full scan)"
    Write-Host "Skipping scan - installing without security check (not recommended)"
    # Fall through to install
} elseif ($scanExit -ne 0) {
    Write-Warn "Scanner exited with code $scanExit"
}

# Install
if (-not (Test-Path $SkillsDir)) { New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null }
if ((Test-Path "$SkillsDir\$SkillSlug") -and -not $Force) { Write-Err "Already exists. Use -Force."; exit 1 }
if (Test-Path "$SkillsDir\$SkillSlug") { Remove-Item -Recurse -Force "$SkillsDir\$SkillSlug" }
Move-Item -Path $StagedPath -Destination "$SkillsDir\"
Remove-Item -Recurse -Force "$StagingDir\skills\$SkillSlug" -ErrorAction SilentlyContinue
Write-OK "No issues detected. Installed to $SkillsDir\$SkillSlug"
