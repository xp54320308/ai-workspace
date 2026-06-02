---
name: openclaw-gateway-ops
description: OpenClaw Gateway 运维 — 诊断崩溃、修复插件缓存、配置管理和健康检查。触发条件：gateway 掉线、channel 加载失败、配置修改后被回滚、插件报错 Cannot find module。
category: devops
---

# OpenClaw Gateway 运维

## 快速诊断流程

### 1. 检查 Gateway 是否在线
```bash
powershell.exe -Command "Get-NetTCPConnection -LocalPort 18789 -ErrorAction SilentlyContinue | Select-Object OwningProcess | Sort-Object -Unique"
```

### 2. 查看实时日志（过滤 ERROR/WARN）
```bash
powershell.exe -Command "Get-Content 'C:\Users\qw\AppData\Local\Temp\openclaw\openclaw-2026-04-27.log' -Tail 50" | python3 -c "
import sys,json
for l in sys.stdin:
    l=l.strip()
    if not l: continue
    try:
        d=json.loads(l)
        t=d.get('time','')[11:19]
        msg=str(d.get('1','') or d.get('0',''))
        if any(k in msg.lower() for k in ['error','warn','fail','stuck','exit','restart','channel']):
            print(t, msg[:200])
    except: pass
"
```

### 3. 检查 Plugin Runtime 缓存
```bash
powershell.exe -Command "Get-ChildItem 'C:\Users\qw\.openclaw\plugin-runtime-deps' -ErrorAction SilentlyContinue | Select-Object Name"
```

## 常见故障

### 故障 A：plugin-runtime-deps 缓存损坏（最常见掉线原因）

**症状**：日志出现 `Cannot find module './xxx-XXXXX.js'`（feishu/qqbot channel）

**根因**：gateway 启动时生成插件运行时缓存（`plugin-runtime-deps/`），如果生成过程被中断（网络超时、磁盘 I/O 中断、进程强制终止），会留下不完整的缓存，导致 channel 加载失败并不断 auto-restart，最终 gateway 进入异常状态被 supervisor 终止。

**诊断**：检查各 plugin runtime 目录下的关键 JS 文件是否存在：
```bash
# feishu 关键文件：monitor-*.js, policy-*.js
powershell.exe -Command "Get-ChildItem 'C:\Users\qw\.openclaw\plugin-runtime-deps\*\dist\extensions\feishu\' -ErrorAction SilentlyContinue | Select-Object Name"

# qqbot 关键文件：gateway-*.js
powershell.exe -Command "Get-ChildItem 'C:\Users\qw\.openclaw\plugin-runtime-deps\*\dist\extensions\qqbot\' -ErrorAction SilentlyContinue | Select-Object Name"

# 损坏特征：文件缺失（size=0 或文件不存在）
# feishu 常见缺失：monitor-*.js, policy-*.js
# qqbot 常见缺失：gateway-*.js
```

**修复**：
1. 先找到所有损坏的 runtime 目录（可能有多个版本残留）
```bash
powershell.exe -Command "Get-ChildItem 'C:\Users\qw\.openclaw\plugin-runtime-deps\' -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime"
```
2. 删除全部 runtime 目录（让 gateway 重新生成干净的）
```bash
powershell.exe -Command "Remove-Item -Recurse -Force 'C:\Users\qw\.openclaw\plugin-runtime-deps\*' -ErrorAction SilentlyContinue"
```
3. 重启 gateway
```bash
powershell.exe -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','C:\Users\qw\.openclaw\gateway.cmd' -WindowStyle Hidden -PassThru | Select-Object Id"
```

### 故障 B：config-health hash 不匹配导致配置被回滚（仅旧版本）

**症状**：修改了 `openclaw.json`（添加 agents.list、启用 channel），重启后修改消失了。

**注意**：此故障仅存在于旧版 OpenClaw（使用 `config-health.json` 管理 hash 的版本）。**2026.4.21 版本已改用 `config.yaml`，不涉及 hash 回滚机制**，无需同步 hash。

**旧版修复**（如遇老版本）：
```python
import hashlib, json
with open(r'C:\Users\qw\.openclaw\openclaw.json', 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest()
health = r'C:\Users\qw\.openclaw\config-health.json'
with open(health) as f:
    cfg = json.load(f)
cfg['lastKnownGood'] = h
with open(health, 'w') as f:
    json.dump(cfg, f, indent=2)
```

### 故障 C：alsoAllow 无效工具名警告

**症状**：日志出现 `tools.profile allowlist contains unknown entries (tavily_search, ollama_web_search, ollama_web_fetch)`

**影响**：仅产生 WARNING，不影响 gateway 核心功能。这些工具名在配置中存在但系统中不存在。

**修复**：从 `openclaw.json` 的 `tools.alsoAllow` 数组中删除不存在的工具名：
```python
import json
with open(r'C:\Users\qw\.openclaw\openclaw.json') as f:
    cfg = json.load(f)
# 也清理 alsoAllow
alsoallow = cfg.get('tools', {}).get('alsoAllow', [])
valid = [x for x in alsoallow if x in ['claude_code', 'github', 'filesystem', 'web_search', 'execute_code', 'bash']]  # 根据实际工具名过滤
cfg['tools']['alsoAllow'] = valid
with open(r'C:\Users\qw\.openclaw\openclaw.json', 'w') as f:
    json.dump(cfg, f, indent=2)
```

### 故障 D：MCP server 启动失败触发连锁反应

**症状**：日志出现 `spawn npx ENOENT`。

**根因**：MCP server 配置了 `npx` command，但 `npx` 不在系统 PATH。spawn 失败触发 config reload 循环。

**修复**：删除问题 MCP 配置（`chrome-devtools` 等不在 PATH 的 npx-based MCP）：
```python
import json
with open(r'C:\Users\qw\.openclaw\openclaw.json') as f:
    cfg = json.load(f)
cfg.get('mcp', {}).get('servers', {}).pop('chrome-devtools', None)
with open(r'C:\Users\qw\.openclaw\openclaw.json', 'w') as f:
    json.dump(cfg, f, indent=2)
```

### 故障 E：Plugin-runtime-deps 缓存损坏导致 gateway 静默挂起（多触发源）

**症状**：进程存活（PID 不变、内存稳定）、端口 18789 仍被持有、日志文件停止增长、HTTP/WebSocket 请求无响应。

**根因**：plugin-runtime-deps 缓存被破坏（生成过程被中断），channel 加载失败并不断 auto-restart，gateway 进入静默错误状态。两类触发源：

1. **Config 热重载触发**（旧版本，2026.4.21 已改用 config.yaml 不涉及）
   - gateway 的 config reload subsystem 直接监听文件系统变更并立即应用，绕过 Zod schema 验证
   - 某些配置变更（如删除 `tools.alsoAllow` 字段）触发内部 agent 配置引用不存在的工具

2. **Channel 加载 EBUSY 触发**（本次实际根因）
   - qqbot 或其他 channel 在启动时尝试 copy 文件到 plugin-runtime-deps
   - 恰好有另一个 node 进程（之前的 zombie）持有源文件或目标目录的句柄
   - 结果：`EBUSY: resource busy or locked, copyfile '...setup-surface-*.js'`
   - channel 加载失败 → auto-restart 循环 → gateway 最终静默 hung

**识别特征**：
- **Config reload 特征**：日志最后一条是 `config change detected; evaluating reload`，之后日志完全停止
- **EBUSY 特征**：日志出现 `EBUSY: resource busy or locked, copyfile` 后，channel 加载失败，进程最终 hung
- **通用特征**：进程活着、内存稳定、端口被持有但不监听、日志断裂
- **辅助判断**：大量 zombie node 进程堆积（`Get-Process -Name node` 显示多个），每个 ~270MB
- **辅助判断**：日志最新时间距离当前超过 30 分钟且无新条目

**日志关键证据**（EBUSY 触发）：
```
[channels] failed to load bundled channel qqbot: EBUSY: resource busy or locked, copyfile
  'C:\Users\qw\AppData\Roaming\npm\node_modules\openclaw\dist\setup-surface-1wR-0ZSt.js'
  -> 'C:\Users\qw\.openclaw\plugin-runtime-deps\openclaw-2026.4.24-...\dist\setup-surface-1wR-0ZSt.js'
```

**修复**：不能再用热重载，必须 kill + 重启：
```bash
# 1. 强制杀死挂起的 gateway
powershell.exe -Command "Stop-Process -Id <PID> -Force -ErrorAction SilentlyContinue"

# 2. 清除 plugin-runtime-deps（确保重新生成干净缓存）
powershell.exe -Command "Remove-Item -Recurse -Force 'C:\Users\qw\.openclaw\plugin-runtime-deps\*' -ErrorAction SilentlyContinue"

# 3. 重启（不要依赖热重载，配置修改后直接重启）
powershell.exe -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','C:\Users\qw\.openclaw\gateway.cmd' -WindowStyle Hidden -PassThru | Select-Object Id"
```

**预防**：
- Config 修改后（尤其是 `tools`、`agents`、`channels` 等核心字段）不要依赖热重载，直接重启
- 日志中一旦出现 `config change detected` 但后续无新日志，立即 kill + 重启
- 经常检查 node 进程数量（`Get-Process -Name node`），超过 4 个说明有 zombie 残留需清理
- **两种 gateway 失败模式**：
  1. **进程消失**（被外部杀死/supervisor 重启）——日志断裂，PID 变化，需检查重启原因
  2. **进程存活但挂起**（内部静默错误）——日志停止，PID 不变，HTTP 无响应，必须手动 kill + 重启
- **建议**：在 Windows 任务计划程序配置一个定时任务（每 5 分钟一次），检测 port 18789 无响应时自动 kill 并重启 gateway

## Gateway 关键路径

| 类型 | 路径 |
|------|------|
| 启动脚本 | `C:\Users\qw\.openclaw\gateway.cmd` |
| Config | `C:\Users\qw\.openclaw\openclaw.json`（2026.4.21 使用 `config.yaml`，无需 hash 同步） |
| 插件缓存 | `C:\Users\qw\.openclaw\plugin-runtime-deps\` |
| 日志 | `C:\Users\qw\AppData\Local\Temp\openclaw\openclaw-YYYY-MM-DD.log` |
| 锁文件 | `C:\Users\qw\AppData\Local\Temp\openclaw\gateway.*.lock` |

## 健康检查（正确姿势）

**检查进程**：确认 gateway 进程存活
```bash
powershell.exe -Command "Get-NetTCPConnection -LocalPort 18789 -ErrorAction SilentlyContinue | Select-Object OwningProcess | Sort-Object -Unique"
```

**检查日志活跃性**：日志文件是否在继续增长（不只是看进程）
```bash
powershell.exe -Command "Get-Content 'C:\Users\qw\AppData\Local\Temp\openclaw\openclaw-$(Get-Date -Format 'yyyy-MM-dd').log' -Tail 5 | Select-Object -Last 1"
```

**检查 HTTP 响应**：确认 gateway 在实际处理请求（不能只靠进程存活判断）
```bash
powershell.exe -Command "
try {
    \$r = Invoke-WebRequest -Uri 'http://127.0.0.1:18789/__openclaw__/api/v1/node/list' -TimeoutSec 5 -ErrorAction Stop
    Write-Host 'Gateway OK: HTTP' \$r.StatusCode
} catch {
    Write-Host 'Gateway HUNG or Unreachable:' \$_.Exception.Message
}
"
```

**三步全绿才算健康**：进程在 + 日志在增长 + HTTP 有响应

**三步全绿但 gateway 仍可能挂的情况**（进程活着、内存稳定、但端口不监听）：
1. `Get-Process -Name node` 显示 2+ 个 node 进程 → 有 zombie 残留
2. `Get-Content log -Tail 5` 日志最后时间距今超过 30 分钟 → 日志断裂
3. `Get-NetTCPConnection -LocalPort 18789` 返回空 → 端口未监听
→ 此时 gateway 进程处于静默 hung 状态，必须 kill + 重启，不能依赖热重载

**注意**：日志文件本身不会自动轮转，gateway 进程退出后日志时间戳停止。日志文件有新的 LastWriteTime ≠ gateway 在写日志（可能是其他进程 touch 了该文件）。必须比对日志最后一条的时间戳判断是否真正活跃。

### 故障 F：Stuck Session 导致 Health Monitor 强制重启

**症状**：日志出现 `stuck session: sessionId=main sessionKey=agent:main:main state=processing age=XXXs`，之后 gateway 被关闭（`gateway closed (1000)`）。

**根因**：主 session 在 `processing` 状态卡死（age 持续增长），health monitor（300s 间隔检测）判定为无响应，强制关闭 gateway 造成崩溃重启。

**识别特征**：
- 日志中出现连续多条 `stuck session` WARN（age 从 219s → 249s 递增）
- 之后出现大量 `gateway connect failed: Error: gateway closed (1000)` ERROR
- 新进程被 spawn，每隔几分钟又卡死，形成 crash loop
- 主机发出蜂鸣声（系统崩溃/重启信号，不是 OpenClaw 软件本身）

**修复**：
1. 先终止所有 node 进程（包括僵尸进程）
```bash
powershell.exe -Command "Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force"
```
2. 删除 plugin-runtime-deps（确保干净的 runtime 重生成）
```bash
powershell.exe -Command "Remove-Item -Recurse -Force 'C:\Users\qw\.openclaw\plugin-runtime-deps' -ErrorAction SilentlyContinue"
```
3. 重启 gateway
```bash
powershell.exe -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','gateway.cmd' -WorkingDirectory 'C:\Users\qw\.openclaw' -WindowStyle Hidden -PassThru | Select-Object Id"
```

### 故障 G：僵尸 Node 进程堆积

**症状**：大量 `node` 和 `node_repl` 进程堆积（可达数十个），每次 gateway 崩溃都留下一对进程（主进程 ~320MB + 辅助进程 ~56MB）。主机内存逐渐被消耗。

**根因**：gateway 崩溃或被强制终止时，Node.js 子进程没有被正确回收，成为僵尸进程（状态为 `Terminated` 但句柄未释放）。系统没有自动清理机制。

**诊断**：
```bash
powershell.exe -Command "Get-Process -Name node -ErrorAction SilentlyContinue | Select-Object Id, @{N='MemMB';E={[math]::Round(\$_.WorkingSet64/1MB)}}, StartTime | Sort-Object StartTime -Descending | Format-Table -AutoSize"
```

**修复**：强制终止所有 node 进程后重启（见故障 F）

**预防**：经常检查进程数量，如果发现 node 进程数量超过 4 个（gateway 主进程 + 辅助进程），说明之前有未清理的崩溃残留。

## Channel 状态判断

| Channel | 正常标志 | 故障标志 |
|---------|---------|---------|
| feishu | `bot open_id resolved` / `bot open_id recovered` | `Cannot find module` / `open_id unknown` 持续不恢复 |
| qqbot | `Gateway ready` | `Cannot find module` / auto-restart 循环 |
