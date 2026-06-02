---
name: cli-anything
version: 1.0.0
description: Run any CLI command locally or via SSH. Parse output, handle errors, stream results, support cross-platform compatibility. Use for shell commands, git operations, package management, system administration, and remote server control.
triggers:
  - "run command"
  - "execute"
  - "shell"
  - "terminal"
  - "ssh"
  - "bash"
  - "cmd"
  - "powershell"
  - "install package"
  - "git push"
tags: [cli, shell, ssh, terminal, automation]
allowed-tools: [terminal, read_file]
required_commands:
  - bash (Linux/macOS) or cmd/powershell (Windows)
  - ssh (for remote)
  - scp (for file transfer)
---

# CLI Anything

Run any CLI command locally or via SSH.

## Local Commands

### Basic Execution

```bash
# Simple command
ls -la

# With environment variables
DEBUG=1 npm run build

# Pipe output
cat file.txt | grep "error" | sort | uniq
```

### Cross-Platform Notes

| Linux/macOS | Windows | Notes |
|-------------|---------|-------|
| `bash`, `zsh` | `cmd`, `powershell` | Shell interpreter |
| `ls -la` | `dir` | List files |
| `rm file` | `del file` | Delete |
| `cp src dst` | `copy src dst` | Copy |
| `grep` | `findstr` | Text search |
| `which cmd` | `where cmd` | Find command |

### Error Handling

```bash
# Check exit code
command
if [ $? -eq 0 ]; then
    echo "Success"
else
    echo "Failed with code $?"
fi

# Exit on error
set -e
command_that_might_fail
```

## SSH Commands

### Basic SSH

```bash
# Run single command
ssh user@host "df -h"

# Run with key
ssh -i ~/.ssh/key.pem user@host "uptime"

# Multiple commands
ssh user@host "cd /tmp && ls -la"
```

### SSH Options

```bash
# Common flags
ssh -o ConnectTimeout=10      # Timeout
ssh -o StrictHostKeyChecking=no  # Skip host key
ssh -p 2222                   # Non-standard port
```

### File Transfer

```bash
# Copy to remote
scp file.txt user@host:/path/

# Copy from remote
scp user@host:/path/file.txt .

# Recursive copy
scp -r directory/ user@host:/path/
```

## Output Parsing

### Common Patterns

```bash
# Get specific column (space-delimited)
df -h | awk '{print $2}'  # 2nd column

# Extract with grep
ps aux | grep python | grep -v grep

# Parse JSON
cat config.json | jq '.key'

# Get exit code
command || echo "Command failed"
```

### Stream Processing

```bash
# Real-time output
tail -f /var/log/app.log

# Watch command
watch -n 5 "df -h"

# Background job
nohup ./long-running-script.sh > output.log 2>&1 &
```

## Package Management

### Linux

```bash
# Debian/Ubuntu
apt update && apt install package
apt search keyword

# RHEL/CentOS
yum install package
dnf install package

# Arch
pacman -S package
```

### macOS

```bash
# Homebrew
brew install package
brew search keyword
brew outdated
```

### Windows

```powershell
# Winget
winget install package
winget search keyword

# Chocolatey
choco install package
```

## Verification

```bash
# Check command exists
which git  # Linux/macOS
where git  # Windows

# Test SSH connectivity
ssh -o ConnectTimeout=5 user@host echo "ok"

# Verify file copy
md5sum file.txt  # Linux
md5 file.txt     # macOS
Get-FileHash file.txt -Algorithm MD5  # Windows PowerShell
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `command not found` | Not installed/in PATH | Install or use full path |
| `Permission denied` | No execute permission | `chmod +x script.sh` |
| `No such file or directory` | Wrong path | Check `pwd`, use absolute path |
| `Connection refused` | Service down | Check service status |
| `Timeout` | Network/server slow | Increase timeout, check connectivity |

## Best Practices

1. **Always check exit codes** - don't assume success
2. **Quote arguments** - handle spaces in paths
3. **Use full paths** - avoid PATH issues
4. **Log output** - capture stdout/stderr separately
5. **Set timeouts** - prevent hanging commands
6. **Escape special chars** - in SSH commands, escape `'` and `$`
