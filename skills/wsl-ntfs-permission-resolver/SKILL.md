---
name: wsl-ntfs-permission-resolver
description: A specialized troubleshooting workflow for resolving 'operation not permitted' (E13/EPERM) errors when using Linux tools (like ollama) on Windows-mounted drives (/mnt/c, /mnt/f) via WSL.
category: devops
---

# wsl-ntfs-permission-resolver

## Description
A specialized troubleshooting workflow for resolving `operation not permitted` (EPERM) and `chmod` errors encountered when running Linux-based tools (like `ollama`, `git`, or `docker`) inside WSL on Windows-mounted drives (`/mnt/c`, `/mnt/f`, etc.).

## Trigger
You encounter an error in WSL that looks like:
`Error: 500 Internal Server Error: chmod /mnt/.../path: operation not permitted`
or any error where a Linux tool fails to set permissions on a file located in a Windows-mounted directory.

## Workflow
1. **Identify the Root Cause**: Check if the target path starts with `/mnt/`. If it does, the issue is the incompatibility between Linux `chmod/ch_own` logic and the NTFS/FAT3-based Windows mount point.
2. **Analyze the Tool**: Determine if the tool being used (e.g., `ollama`) has a Windows-native counterpart or can be run from the Windows host.
3. **Execute the "Native Bypass"**: 
    - Open **Windows PowerShell** (or CMD) as the primary driver.
    - Execute the command directly in the Windows environment. 
    - *Example*: Instead of `wsl ollama create ...`, run `ollama create ...` directly in PowerShell.
4. **Verify Completion**: After the Windows-native command succeeds, return to WSL. The change (e.var. a new model or a new file) will be visible in WSL because both environments share the same underlying Windows filesystem.

## Pitfalls
- **Do not attempt to fix the mount flags**: While `metadata` mount options in `/etc/fstab` can technically allow some permissions, it often breaks other Windows integration aspects. The "Native Bypass" is cleaner and more reliable.
- **Environment Context**: Ensure that the Windows-native tool is pointing to the correct data directory (the same directory your WSL instance was using) by checking `OLLAMA_MODELS` or similar environment variables.
