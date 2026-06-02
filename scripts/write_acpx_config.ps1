$config = @{
    defaultAgent = "codex"
    defaultPermissions = "approve-all"
    nonInteractivePermissions = "deny"
    authPolicy = "skip"
    ttl = 300
    timeout = $null
    queueMaxDepth = 16
    format = "text"
    agents = @{
        openclaw = @{
            command = "openclaw"
            args = @("acp", "--url", "ws://127.0.0.1:18789", "--token-file", "C:/Users/qw/.openclaw/gateway.token", "--session", "agent:main:main")
        }
    }
    auth = @{}
}
$config | ConvertTo-Json -Depth 10 | Set-Content 'C:\Users\qw\.acpx\config.json' -Encoding UTF8
