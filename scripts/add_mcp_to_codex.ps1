$configPath = "C:\Users\qw\.codex\config.toml"
$content = Get-Content $configPath -Raw
$newEntry = @"

[mcp_servers.openclaw]
command = "openclaw"
args = ["mcp", "serve", "--url", "ws://127.0.0.1:18789", "--token-file", "C:/Users/qw/.openclaw/gateway.token"]
"@
$content + $newEntry | Set-Content $configPath -NoNewline
