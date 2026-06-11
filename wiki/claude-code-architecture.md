# Claude Code 架构分析笔记

> 来源: claude-code-sourcemap (v2.1.88), 通过npm包source map还原
> 日期: 2026-04-25

## 一、整体架构

```
CLI入口 (main.tsx)
    ↓
┌─────────────────────────────────────────────────────────────┐
│                      Bootstrap State                         │
│  全局单例STATE: sessionId, modelUsage, totalCostUSD, etc.   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│                      AppState Store                          │
│  React风格订阅式存储: settings, tasks, mcp, plugins, etc.  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│                     Coordinator Mode                          │
│  多Agent协调: Research → Synthesis → Implementation → Verify│
└─────────────────────────────────────────────────────────────┘
```

## 二、工具系统架构

### 2.1 工具注册与执行

```typescript
// 工具定义通过 buildTool 工厂函数
export const BashTool = buildTool({
  name: 'Bash',
  inputSchema: lazySchema(() => z.object({...})),
  outputSchema: ...,
  
  async call(input, toolUseContext, canUseTool, assistantMessage, onProgress) {
    // 1. 权限检查
    const permissionResult = await BashTool.checkPermissions(input, context);
    if (permissionResult.behavior === 'deny') return { data: { success: false } };
    
    // 2. 沙箱检查
    const shouldSandbox = shouldUseSandbox(input);
    
    // 3. 执行命令
    const result = await spawnShellTask({ command, timeout, onProgress });
    
    // 4. 返回结果
    return { data: result };
  },
  
  // UI渲染完全分离
  renderToolUseMessage: (input) => <Text>{truncatedCommand}</Text>,
  renderToolResultMessage: (content) => <BashToolResultMessage {...} />,
})
```

### 2.2 工具列表 (tools.ts)

```
AgentTool (233KB)       - Agent委托
BashTool (160KB)        - Shell命令
PowerShellTool (144KB)  - PowerShell命令
FileEditTool            - 文件编辑
FileReadTool            - 文件读取
FileWriteTool           - 文件写入
GlobTool                - 文件搜索
GrepTool                - 内容搜索
WebSearchTool           - 网页搜索
WebFetchTool            - 网页获取
MCPTool                 - MCP协议工具
SkillTool               - 技能调用
TaskOutputTool (66KB)   - 任务输出
LSPTool                 - 语言服务器协议
ConfigTool              - 配置管理
...
```

### 2.3 工具结果存储

```typescript
// 大结果持久化到磁盘，避免内存压力
const { path, size } = await buildLargeToolResultMessage(output, toolResultDir);
return {
  data: {
    stdout: preview,  // 预览文本
    rawOutputPath: path,  // 完整结果路径
    persistedOutputSize: size
  }
};
```

## 三、权限系统架构

### 3.1 权限模式

```
default        - 标准模式，需要用户确认
plan           - 计划模式（只读）
acceptEdits    - 接受编辑模式
bypassPermissions - 完全绕过
dontAsk        - 拒绝所有询问
auto           - AI分类器自动决定
```

### 3.2 权限检查流程

```
1. 规则检查 (permissions.ts)
   ├── 1a: 工具是否被Deny规则直接拒绝
   ├── 1b: 是否有"总是询问"规则
   ├── 1c: 工具自身checkPermissions()
   └── 1d-1g: 安全检查(敏感路径等)

2. 模式检查
   ├── bypassPermissions → 直接放行
   └── alwaysAllow → 直接放行

3. 自动模式 (auto)
   ├── YOLO分类器: classifyYoloAction()
   ├── 拒绝追踪: 连续3次/总共20次后回退到交互
   └── 安全工具白名单
```

### 3.3 安全检查 (filesystem.ts)

```typescript
const DANGEROUS_FILES = [
  '.gitconfig', '.gitmodules', '.bashrc', '.bash_profile',
  '.zshrc', '.zprofile', '.profile', '.ripgreprc', 
  '.mcp.json', '.claude.json'
]

const DANGEROUS_DIRECTORIES = ['.git', '.vscode', '.idea', '.claude']
```

## 四、Bash安全架构 (纵深防御)

### Layer 1: 纯TS解析器 (bashParser.ts, 130KB)

- 手写递归下降parser，替代tree-sitter WASM
- UTF-8字节偏移（非JS字符串索引）
- 50ms超时保护，50K节点budget

### Layer 2: AST安全分析 (ast.ts, 112KB)

- **FAIL-CLOSED策略**: 未知节点类型 → 要求用户确认
- 变量追踪: `VAR=$(date) && jq --arg now "$VAR"` 中$VAR被追踪

```typescript
const DANGEROUS_TYPES = Set([
  'command_substitution',  // $(...)
  'process_substitution',  // <() >
  'expansion',            // ${}
  'simple_expansion',     // $VAR
  'brace_expression',     // {a,b}
  'subshell',            // (...)
  // ...
])
```

### Layer 3: 23种正则检查器 (bashSecurity.ts, 102KB)

```typescript
const BASH_SECURITY_CHECK_IDS = {
  INCOMPLETE_COMMANDS: 1,      // 不完整命令
  JQ_SYSTEM_FUNCTION: 2,       // jq的system()
  OBFUSCATED_FLAGS: 4,        // 混淆flags
  COMMAND_SUBSTITUTION: 8,     // 命令替换
  INPUT_REDIRECTION: 9,        // 输入重定向
  OUTPUT_REDIRECTION: 10,      // 输出重定向
  BRACE_EXPANSION: 16,         // Brace扩展
  CONTROL_CHARACTERS: 17,      // 控制字符
  // ...共23种
}
```

### Layer 4: 路径验证 (pathValidation.ts)

```typescript
// 针对不同命令的路径提取
export const PATH_EXTRACTORS = {
  cd: args => args.length === 0 ? [homedir()] : [args.join(' ')],
  ls: args => filterOutFlags(args),
  find: args => { /* 复杂逻辑 */ },
  rm: filterOutFlags,  // 特殊处理--选项终止符
  // ...
}
```

### Layer 5: 权限规则匹配 (bashPermissions.ts)

```typescript
// 规则类型
type PermissionRule = 
  | { type: 'exact', command: string }   // 精确匹配
  | { type: 'prefix', prefix: string }   // 前缀匹配
  | { type: 'wildcard', pattern: string } // 通配符

// Safe Wrapper剥离
const SAFE_WRAPPER_PATTERNS = [
  /^timeout[ \t]+/,
  /^time[ \t]+/,
  /^nice(?:[ \t]+-n[ \t]+-?\d+)?/,
  /^stdbuf(?:[ \t]+-[ioe][LN0-9]+)+/,
  /^nohup[ \t]+/,
]
```

## 五、插件系统架构

### 5.1 插件来源优先级

```
1. Session插件 (--plugin-dir)     ← 最高优先级
2. Marketplace插件 (plugin@marketplace)
3. 内置插件 (builtin)              ← 最低优先级
```

### 5.2 插件目录结构

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # 清单
├── commands/                # 斜杠命令
├── agents/                 # 自定义代理
├── skills/                 # 技能
├── hooks/                  # Hook配置
└── output-styles/          # 输出样式
```

### 5.3 插件清单 Schema

```typescript
type PluginManifest = {
  hooks?: HooksSettings
  commands?: string[] | Record<string, string>
  agents?: string[]
  skills?: string[]
  outputStyles?: string[]
  mcpServers?: Record<string, McpServerConfig>
  lspServers?: Record<string, LspServerConfig>
  userConfig?: PluginUserConfigOption[]
  channels?: ChannelConfig[]
}
```

### 5.4 技能Frontmatter字段

```yaml
---
name: Custom Name
description: ...
allowed-tools: [Read, Edit, Bash]
argument-hint: [file]
when_to_use: ...
model: sonnet
disable-model-invocation: false
user-invocable: true
context: fork
agent: agent-name
effort: medium
---
# Markdown内容...
```

## 六、多Agent协调模式 (Coordinator)

### 6.1 协调流程

```
Coordinator
    ├── Phase 1: Research    → 并行启动多个Worker调查
    ├── Phase 2: Synthesis   → 整合结果，编写实施规范
    ├── Phase 3: Implementation → Worker执行代码修改
    └── Phase 4: Verification → Worker测试验证
```

### 6.2 XML通知格式

```xml
<task-notification>
  <task-id>{agentId}</task-id>
  <status>completed|failed|killed</status>
  <summary>...</summary>
  <result>...</result>
  <usage>...</usage>
</task-notification>
```

## 七、状态管理模式

### 7.1 Bootstrap State (state.ts)

```typescript
// 全局单例
export const STATE = {
  sessionId: '',
  parentSessionId: undefined,
  modelUsage: { inputTokens: 0, outputTokens: 0 },
  totalCostUSD: 0,
  isRemoteMode: false,
  invokedSkills: [],
  // ...50+字段
}

// 访问模式
export function getSessionId(): SessionId { return STATE.sessionId }
export function switchSession(sessionId, projectDir): void { ... }
```

### 7.2 AppState Store (store.ts)

```typescript
// React风格订阅式存储
export function createStore<T>(initialState: T, onChange?) {
  let state = initialState
  const listeners = new Set<Listener>()
  return {
    getState: () => state,
    setState: (updater) => { /* immutable update */ },
    subscribe: (listener) => { /* pub/sub */ }
  }
}
```

## 八、MCP协议实现

### 8.1 传输类型

```typescript
type TransportType = 'stdio' | 'sse' | 'sse-ide' | 'http' | 'ws' | 'sdk' | 'claudeai-proxy'
```

### 8.2 连接管理

```typescript
// 缓存连接，自动重连
const connection = await ensureConnectedClient(mcpClientId);

// 调用工具
const result = await callTool('tool-name', { arg1: 'value' });
```

## 九、关键设计模式

### 9.1 死代码消除 (DCE)

```typescript
// 条件导入用于DCE
const REPLTool = process.env.USER_TYPE === 'ant'
  ? require('./tools/REPLTool/REPLTool.js').REPLTool
  : null;

// Feature flag门控
...(process.env.USER_TYPE === 'ant' ? [REPLTool] : []);
```

### 9.2 延迟Schema加载

```typescript
const inputSchema = lazySchema(() => z.object({
  command: z.string(),
  timeout: semanticNumber(z.number().optional()),
}));

// 根据feature flag动态调整
const fullInputSchema = lazySchema(() => {
  return feature('KAIROS') ? fullSchema() : fullSchema().omit({ cwd: true });
});
```

### 9.3 Memoization

```typescript
// 插件加载memoize
export const loadAllPlugins = memoize(async (): Promise<PluginLoadResult> => {
  // 完整加载逻辑
});

// 缓存模式
export const loadAllPluginsCacheOnly = memoize(async (): Promise<PluginLoadResult> => {
  // 只读缓存
});
```

## 十、关键文件索引

| 功能 | 文件路径 | 大小 |
|------|----------|------|
| CLI入口 | main.tsx | 4683行 |
| 工具注册 | tools/tools.ts | |
| AgentTool | tools/AgentTool/AgentTool.tsx | 233KB |
| BashTool | tools/BashTool/BashTool.tsx | 160KB |
| Bash AST解析 | utils/bash/ast.ts | 112KB |
| Bash Parser | utils/bash/bashParser.ts | 130KB |
| Bash安全检查 | tools/BashTool/bashSecurity.ts | 102KB |
| 权限系统 | utils/permissions/permissions.ts | 52KB |
| 插件加载 | utils/plugins/pluginLoader.ts | 110KB |
| 市场管理 | utils/plugins/marketplaceManager.ts | 93KB |
| 权限Schema | utils/permissions/schemas.ts | 59KB |
| MCP客户端 | services/mcp/client.ts | 3348行 |
| 状态存储 | state/store.ts | 34行 |
| Coordinator | coordinator/coordinatorMode.ts | 369行 |

## 十一、核心学习点

1. **纵深防御**: Bash安全5层防护，每层都不知道上一层是否失败
2. **FAIL-CLOSED**: 不确定的结构 → 要求用户确认
3. **渲染分离**: 工具逻辑与UI完全分离
4. **状态分层**: Bootstrap State(单例) + AppState(pubsub)
5. **版本化缓存**: 插件按版本缓存，支持回滚
6. **声明式清单**: 清单驱动，自动检测目录结构

---

## 十二、逐行学习详细笔记

### 12.1 main.tsx (803KB, 4683行) - CLI核心入口

**启动预加载 (L1-20)**
```typescript
profileCheckpoint('main_tsx_entry');           // 性能分析入口标记
startMdmRawRead();                              // MDM子进程预读取(plutil/reg)
startKeychainPrefetch();                        // macOS keychain预读取OAuth凭证
```

**条件导入 (L68-81)** - 避免循环依赖
```typescript
const getTeammateUtils = () => require('./utils/teammate.js');
const coordinatorModeModule = feature('COORDINATOR_MODE') ? require(...) : null;
```

**迁移系统 (L325-352)**
```typescript
const CURRENT_MIGRATION_VERSION = 11;
// 同步迁移: migrateAutoUpdatesToSettings, migrateBypassPermissionsAcceptedToSettings等
// 异步迁移: migrateChangelogFromConfig
```

**延迟预取 (L388-431)** - 不阻塞首屏渲染
```typescript
export function startDeferredPrefetches(): void {
  void initUser();
  void getUserContext();
  void countFilesRoundedRg(getCwd(), AbortSignal.timeout(3000), []);
  void initializeAnalyticsGates();
  void settingsChangeDetector.initialize();
}
```

**CLI子命令结构**
```
mcp serve|add|remove|list|get|add-json|add-from-claude-desktop|reset-project-choices
server (DIRECT_CONNECT)
ssh (SSH_REMOTE)
auth login|status|logout
plugin validate|list|install|uninstall|enable|disable|update
marketplace add|list|remove|update
doctor, update, install, setup-token
```

### 12.2 store.ts (34行) - 极简状态管理

```typescript
type Listener = () => void
type OnChange<T> = (args: { newState: T; oldState: T }) => void

export function createStore<T>(initialState: T, onChange?: OnChange<T>): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()  // Set自动去重

  return {
    getState: () => state,
    setState: (updater) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return  // 优化：状态未变跳过
      state = next
      onChange?.({ newState: next, oldState: prev })
      for (const listener of listeners) listener()
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)  // 返回取消订阅函数
    }
  }
}
```

**React集成**: 通过`useSyncExternalStore` + Context传递store实例

### 12.3 Tool.ts (792行) - 工具基类

**buildTool工厂函数 (L783-792)**
```typescript
export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,           // 填充默认值
    userFacingName: () => def.name,
    ...def,
  } as BuiltTool<D>
}

// TOOL_DEFAULTS (L757-769)
const TOOL_DEFAULTS = {
  isEnabled: () => true,
  isConcurrencySafe: () => false,
  isReadOnly: () => false,
  isDestructive: () => false,
  checkPermissions: () => ({ behavior: 'allow' }),
  toAutoClassifierInput: () => '',
  userFacingName: () => def.name,
}
```

**ToolProgressData泛型**
```typescript
export type ToolProgress<P extends ToolProgressData> = {
  toolUseID: string
  data: P
}
```

### 12.4 Bash AST安全分析 (ast.ts, 2679行)

**FAIL-CLOSED核心原则 (L1-19)**
> "We never interpret structure we don't understand. If tree-sitter produces a node we haven't explicitly allowlisted, we refuse to extract argv"

**Pre-check防护 (L408-437)** - tree-sitter之前运行
```typescript
CONTROL_CHAR_RE.test(cmd)        // \x00-\x08, \x0B-\x1F
UNICODE_WHITESPACE_RE.test(cmd)   // NBSP, zero-width spaces
BACKSLASH_WHITESPACE_RE.test(cmd) // \ 空白
ZSH_TILDE_BRACKET_RE.test(cmd)    // ~[动态目录]
```

**DANGEROUS_TYPES (L186-218)**
```typescript
const DANGEROUS_TYPES = new Set([
  'command_substitution',     // $(...)
  'process_substitution',    // <() >
  'expansion',              // ${}
  'simple_expansion',       // $VAR
  'brace_expression',       // {a,b}
  'subshell',              // (...)
  'for_statement',         // for循环
  'if_statement',          // if条件
  // ...
])
```

**变量追踪机制 (L467-476)**
```typescript
const varScope = new Map<string, string>()
// 字面值: './etc'
// 占位符: __TRACKED_VAR__, __CMDSUB_OUTPUT__
```

**作用域隔离 (L504-564)**
```typescript
// ||, |, |&, & 分隔符使用snapshot重置
const snapshot = needsSnapshot ? new Map(varScope) : null
// 分支使用scope副本，体内赋值不泄漏
```

### 12.5 权限系统 (permissions.ts, 1486行)

**hasPermissionsToUseTool完整流程**

阶段A - 基础检查 (L1158-1319):
```
1a. getDenyRuleForTool() → 直接deny
1b. getAskRuleForTool() → 直接ask
1c. tool.checkPermissions() → 工具特定检查
1d-1g. 安全检查(git/.claude/.vscode等)
2a. bypassPermissions模式 → allow
2b. alwaysAllow规则 → allow
```

阶段B - Auto模式决策:
```
ask时:
├── mode === 'dontAsk' → deny
├── mode === 'auto' → classifyYoloAction()
│   ├── shouldBlock=true → denial tracking → 超限退prompt
│   └── shouldBlock=false → allow
└── 否则 → 普通prompt
```

**Denial Tracking**
```typescript
DENIAL_LIMITS = {
  maxConsecutive: 3,  // 3次连续拒绝
  maxTotal: 20,       // 总共20次拒绝
}
```

### 12.6 BashTool.tsx (160KB) - Shell命令执行

**call方法流程 (L624-820)**
```typescript
async call(input, toolUseContext, canUseTool, assistantMessage, onProgress) {
  // 1. 模拟sed编辑
  if (input._simulatedSedEdit) return applySimulatedSedEdit(input);

  // 2. runShellCommand异步生成器
  const commandGenerator = runShellCommand({
    input, abortController, setAppState, setToolJSX,
    preventCwdChanges, isMainThread, toolUseId, agentId
  });

  // 3. 消费生成器，onProgress显示进度
  for await (const progress of commandGenerator) {
    onProgress?.(progress);
  }

  // 4. 后处理
  // - 语义解释
  // - Git index.lock检测
  // - 大输出持久化
  // - Claude hints提取
}
```

**runShellCommand异步生成器 (L826-1143)**
```typescript
while (true) {
  const progressSignal = createProgressSignal();
  const result = await Promise.race([resultPromise, progressSignal]);

  if (result !== null) return result;  // 完成或后台化
  yield progress_update;  // 报告进度
}
```

**命令分类**
```typescript
SEARCH: find, grep, rg, ag      // UI折叠
READ: cat, head, tail, less     // UI折叠
LIST: ls, tree, du              // "Listed N directories"
SILENT: mv, cp, rm, mkdir        // "Done"而非"No output"
```

### 12.7 AgentTool.tsx (233KB) - Agent委托

**subagent_type路由**
```
有 team_name + name → spawnTeammate() [团队成员]
subagent_type 有值 → findAgentByType(effectiveType)
subagent_type 无值 → fork实验启用? FORK_AGENT : GENERAL_PURPOSE_AGENT
```

**forkSubagent实验**
```typescript
isForkSubagentEnabled()  // FORK_SUBAGENT特性门
FORK_AGENT: { tools: ['*'], model: 'inherit' }
buildForkedMessages()   // placeholder保证prompt cache命中
```

**Coordinator交互**
```typescript
isCoordinatorMode() && !modelParam
  → 强制异步执行，忽略model参数
  → getCoordinatorSystemPrompt() 提供worker管理指南
```

### 12.8 Coordinator Mode (coordinatorMode.ts)

**四阶段流程**
```
Phase 1: Research  → Workers并行调研
Phase 2: Synthesis → Coordinator汇总+编写规格
Phase 3: Implementation → Workers按规格实施
Phase 4: Verification → Workers独立验证
```

**Worker生命周期工具**
```typescript
INTERNAL_WORKER_TOOLS = {
  TEAM_CREATE_TOOL_NAME,    // 创建团队
  TEAM_DELETE_TOOL_NAME,    // 删除团队
  SEND_MESSAGE_TOOL_NAME,   // 发消息
  SYNTHESIS_OUTPUT_TOOL_NAME, // 合成输出
}
```

**XML通知格式**
```xml
<task-notification>
<task-id>{agentId}</task-id>
<status>completed|failed|killed</status>
<summary>...</summary>
<result>...</result>
<usage><total_tokens>N</total_tokens></usage>
</task-notification>
```

### 12.9 插件系统 (pluginLoader.ts, 110KB)

**加载优先级**
```
1. Session插件 (--plugin-dir)     ← 最高
2. Marketplace插件 (plugin@marketplace)
3. 内置插件 (builtin)             ← 最低
```

**版本化缓存**
```
~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/
```

**技能Frontmatter**
```yaml
---
name: Custom Name
description: ...
allowed-tools: [Read, Edit, Bash]
model: sonnet
user-invocable: true
context: fork
agent: agent-name
---
# Markdown内容...
```

---

## 十三、深入学习详细笔记

### 13.1 bashParser.ts (130KB, 4436行) - 纯TS递归下降Parser

**核心设计**: 纯TypeScript实现tree-sitter-bash兼容输出，无需WASM

**Lexer核心机制**
```typescript
// 双索引机制
type Lexer = {
  i: number           // JS字符串索引
  b: number           // UTF-8字节偏移
  heredocs: HeredocPending[]  // 未扫描heredoc定界符
}

// 上下文敏感词法分析
nextToken(L, ctx)  // ctx: 'cmd' | 'arg'
```

**Token类型**
```typescript
type TokenType =
  | 'WORD' | 'NUMBER' | 'OP' | 'NEWLINE' | 'COMMENT'
  | 'DQUOTE' | 'SQUOTE' | 'ANSI_C'         // $'...'
  | 'DOLLAR' | 'DOLLAR_PAREN' | 'DOLLAR_BRACE' | 'DOLLAR_DPAREN'
  | 'BACKTICK' | 'LT_PAREN' | 'GT_PAREN'   // <() >()
  | 'EOF'
```

**Parser层次结构**
```
parseProgram
  └── parseStatements (循环 until EOF)
        └── parseAndOr (&&, ||)
              └── parsePipeline (|, |&)
                    └── parseCommand
                          ├── parseSimpleCommand
                          │     ├── tryParseAssignment
                          │     └── tryParseRedirect
                          ├── parseIf/parseFor/parseWhile/parseCase
                          ├── parseFunction
                          └── parseSubshell (( ... ))
```

**安全特性**
```typescript
MAX_NODES = 50_000     // 防止OOM
PARSE_TIMEOUT_MS = 50  // 超时保护
```

### 13.2 bashSecurity.ts (102KB, 2592行) - 23种安全检查器

**Parser Differential防御核心**: 防止shell-quote与bash的解析差异被攻击利用

**23种检查器ID映射**
```typescript
const BASH_SECURITY_CHECK_IDS = {
  INCOMPLETE_COMMANDS: 1,      // tab/-
  JQ_SYSTEM_FUNCTION: 2,         // jq system()
  OBFUSCATED_FLAGS: 4,          // 混淆flags
  SHELL_METACHARACTERS: 5,     // 引号内元字符
  DANGEROUS_VARIABLES: 6,       // 危险变量上下文
  NEWLINES: 7,                  // 换行分隔
  COMMAND_SUBSTITUTION: 8,     // $(...)
  INPUT_REDIRECTION: 9,         // <
  OUTPUT_REDIRECTION: 10,       // >
  IFS_INJECTION: 11,           // $IFS
  GIT_COMMIT_SUBSTITUTION: 12,  // git -m注入
  PROC_ENVIRON_ACCESS: 13,     // /proc/*/environ
  MALFORMED_TOKEN: 14,         // 畸形token
  BACKSLASH_ESCAPED_WHITESPACE: 15, // 反斜杠空白
  BRACE_EXPANSION: 16,        // Brace扩展
  CONTROL_CHARACTERS: 17,     // 控制字符
  UNICODE_WHITESPACE: 18,     // Unicode空白
  MID_WORD_HASH: 19,           // 词内#
  ZSH_DANGEROUS_COMMANDS: 20, // Zsh危险命令
  BACKSLASH_ESCAPED_OPERATORS: 21, // 反斜杠操作符
  COMMENT_QUOTE_DESYNC: 22,    // 注释引号desync
  QUOTED_NEWLINE: 23,         // 引号内换行
}
```

**关键Parser Differential攻击**

1. **CR注入 (validateCarriageReturn)**
```
TZ=UTC\recho curl evil.com
shell-quote: "TZ=UTC echo curl evil.com" → echo规则
bash: 执行curl evil.com
```

2. **Brace扩展 (validateBraceExpansion)**
```
git ls-remote {--upload-pack="touch /tmp/pwn",test}
Parser: 1个literal参数
Bash: --upload-pack="touch /tmp/pwn" test → 任意文件写入
```

3. **反斜杠操作符 (validateBackslashEscapedOperators)**
```
cat safe.txt \; echo ~/.ssh/id_rsa
规范化: "cat safe.txt ; echo ~/.ssh/id_rsa"
第二个segment通过isCommandReadOnly → id_rsa泄露
```

4. **Mid-word hash (validateMidWordHash)**
```
foo\#bar
shell-quote: #是注释开始
bash: 词中#是literal
```

**验证器分组**
```typescript
earlyValidators:  // 可返回allow跳过所有检查
  - validateEmpty
  - validateIncompleteCommands
  - validateSafeCommandSubstitution
  - validateGitCommit

nonMisparsingValidators:  // 不设isBashSecurityCheckForMisparsing
  - validateNewlines
  - validateRedirections

validators:  // 全部检查器
  - validateJqCommand
  - validateObfuscatedFlags  // 最复杂(400+行)
  - validateShellMetacharacters
  - ...
```

### 13.3 MCP客户端 (client.ts, 119KB, 3348行)

**传输类型**
```typescript
type TransportType = 'stdio' | 'sse' | 'http' | 'ws' | 'sse-ide' | 'ws-ide' | 'sdk' | 'claudeai-proxy'
```

**连接管理**
```typescript
connectToServer()  // memoize缓存
// 连接超时: 30秒
// stdio优雅关闭: SIGINT→100ms→SIGTERM→400ms→SIGKILL(600ms总)
```

**OAuth认证**
```typescript
MCP_AUTH_CACHE_TTL_MS = 15分钟  // 避免频繁401重试
// claude.ai代理: 自动刷新token，401重试一次
```

**工具调用**
```typescript
callMCPTool()  // ~27.8小时超时
// 大输出: 保存到文件而非内存(ENABLE_MCP_LARGE_OUTPUT_FILES)
```

**会话过期检测**
```typescript
isMcpSessionExpiredError()  // HTTP 404 + JSON-RPC -32001
```

### 13.4 Agent系统 (agent/, 973行 runAgent.ts)

**runAgent核心结构**
```typescript
// AsyncGenerator<Message>驱动
for await (const message of query({...})) {
  // 1. 转发API指标(ttftMs)
  // 2. 处理附件消息(max_turns_reached等)
  // 3. 记录可记录消息并yield
}
```

**消息过滤**
```typescript
isRecordableMessage():
  ✅ assistant/user/progress/system compact_boundary
  ❌ stream_event/tool_use/tool_result
```

**工具解析**
```typescript
resolveAgentTools():
  1. 过滤禁用工具(ALL_AGENT_DISALLOWED_TOOLS)
  2. wildcard: tools:['*'] → 所有可用工具
  3. 去重合并(uniqBy name)
```

**后台代理清理**
```typescript
finally {
  // 清理MCP服务器
  // 清理session hooks
  // 清理prompt cache tracking
  // 释放readFileState缓存
  // Kill bash任务(killShellTasksForAgent)
}
```

### 13.5 AsyncGenerator模式

**双路径执行**
```
同步(前台): runAgent → for await → Promise.race([消息, 后台信号])
异步(后台): runAsyncAgentLifecycle → onCacheSafeParams → enqueueAgentNotification
```

**自动后台化**
```typescript
// Assistant模式: 15秒无输出自动后台
// 命令超时: 超时后自动后台
```

### 13.6 MCP OAuth认证流程

```typescript
// 1. 认证缓存TTL: 15分钟
// 2. checkAndRefreshOAuthTokenIfNeeded()
// 3. 401时handleOAuth401Error()重试
// 4. McpAuthError: 令牌过期
// 5. McpSessionExpiredError: 会话过期(404+-32001)
```

---

## 十四、更多核心模块深入学习

### 14.1 双层状态系统

**Bootstrap State** (`bootstrap/state.ts`, 1758行)
```typescript
// 模块化单例状态机，60+字段
type State = {
  sessionId, parentSessionId           // 会话追踪
  totalCostUSD, totalAPIDuration       // 性能追踪
  mainLoopModelOverride                 // CLI模型覆盖
  meter, sessionCounter, costCounter   // 遥测
  agentColorMap                        // Agent颜色映射
  invokedSkills                        // 跨compact保留
}
```

**AppState Store** (`state/store.ts`, 34行)
```typescript
// React风格订阅式存储
export function createStore<T>(initialState: T, onChange?): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()

  return {
    getState: () => state,
    setState: (updater) => {
      const next = updater(state)
      if (Object.is(next, state)) return  // 优化：状态未变跳过
      state = next
      onChange?.({ newState: next, oldState: prev })
      for (const listener of listeners) listener()
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    }
  }
}
```

**状态传播枢纽** (`onChangeAppState.ts`)
```typescript
// 单一变更点，所有setState触发onChange
onChangeAppState({ newState, oldState }) {
  // permission_mode → CCR/SDK同步
  // mainLoopModel → 持久化+bootstrap同步
  // settings → 清除认证缓存
}
```

### 14.2 Prompt构建系统

**System Prompt两阶段构建** (`prompts.ts`)
```typescript
// 静态部分(可缓存) - 在动态边界之前
[
  getSimpleIntroSection(),
  getSimpleSystemSection(),
  getSimpleDoingTasksSection(),
  getActionsSection(),
  getUsingYourToolsSection(enabledTools),
  getSimpleToneAndStyleSection(),
  getOutputEfficiencySection(),
  SYSTEM_PROMPT_DYNAMIC_BOUNDARY,  // 边界标记
  // 动态部分(会话特定)
  ...resolvedDynamicSections,
]
```

**动态Section注册** (`systemPromptSections.ts`)
```typescript
systemPromptSection('session_guidance', () => getSessionSpecificGuidanceSection(...))
systemPromptSection('memory', () => loadMemoryPrompt())
systemPromptSection('language', () => getLanguageSection(...))
systemPromptSection('output_style', () => getOutputStyleSection(...))
DANGEROUS_uncachedSystemPromptSection('mcp_instructions', ...)  // 每轮重算
```

### 14.3 Compact/Summarization系统

**两种压缩模式**
```
Full Compact:  全部消息摘要，保留最近对话
Partial Compact: 选择性摘要，支持from和up_to方向
```

**压缩流程** (`compactConversation()`)
```typescript
// 1. 执行pre-compact hooks
// 2. streamCompactSummary()生成对话摘要
// 3. 创建compact boundary marker + summary messages
// 4. 生成post-compact attachments
// 5. 执行post-compact hooks
```

**摘要提示词格式** (`prompt.ts`)
```xml
<analysis>  内部推理过程（最终被移除）
<summary>
  Primary Request and Intent
  Key Technical Concepts
  Files and Code Sections
  Errors and fixes
  Problem Solving
  All user messages
  Pending Tasks
  Current Work
  Optional Next Step
</summary>
```

**触发条件**
```typescript
// 自动压缩
shouldAutoCompact() → true when:
  tokenCount >= autoCompactThreshold (contextWindow - 18000)

// Microcompact (微压缩)
Time-based: 最后assistant消息后超过gapThresholdMinutes(默认60min)
Cached MC: 使用API的cache_edits机制
```

### 14.4 沙箱系统

**SandboxManager核心** (`sandbox-adapter.ts`)
```typescript
export const SandboxManager: ISandboxManager = {
  initialize,                       // 异步初始化
  isSandboxingEnabled,             // 检查是否启用
  isAutoAllowBashIfSandboxedEnabled, // auto-allow bash
  areUnsandboxedCommandsAllowed,   // 是否允许非沙箱命令
  wrapWithSandbox,                 // 用沙箱包装命令
  // ...转发给BaseSandboxManager
}
```

**决策逻辑** (`shouldUseSandbox.ts`)
```typescript
export function shouldUseSandbox(input): boolean {
  if (!SandboxManager.isSandboxingEnabled()) return false
  if (input.dangerouslyDisableSandbox &&
      SandboxManager.areUnsandboxedCommandsAllowed()) return false
  if (containsExcludedCommand(input.command)) return false
  return true
}
```

**文件系统隔离配置**
```typescript
filesystem: {
  denyRead,     // 拒绝读取的路径
  allowRead,    // 允许读取的路径
  allowWrite,   // 允许写入的路径
  denyWrite,    // 拒绝写入的路径
}
// 始终拒绝写入settings.json
// 阻止写入.claude/skills目录
```

### 14.5 Bridge/远程会话

**两种Bridge模式**

**v1环境基础模式** (`initBridgeCore`)
```
注册Environment → 创建Session → Poll循环 → WebSocket连接 → Teardown
```

**v2无环境模式** (`initEnvLessBridgeCore`)
```
创建Session → POST /bridge获取worker_jwt → SSE+CCRClient连接
```

**传输类型**
```
WebSocketTransport:  WS读取 + WS写入
SSETransport:         SSE读取 + HTTP POST写入
HybridTransport:      WS读取 + HTTP POST批量写入
```

**CCRClient v2协议**
```
初始化: PUT /sessions/{id}/worker
心跳: POST /sessions/{id}/worker/heartbeat (20s间隔)
事件: POST /sessions/{id}/worker/events (批量)
```

### 14.6 流式处理架构

**三层传输策略** (`transportUtils.ts`)
```typescript
CLAUDE_CODE_USE_CCR_V2=true  →  SSETransport
CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2 → HybridTransport
default                          →  WebSocketTransport
```

**SSE消息解析流程**
```typescript
// parseSSEFrames()
// 1. 双换行符分隔帧
// 2. 冒号分隔字段名和值
// 3. 支持event:, id:, data:字段
// 4. 多行data:用\n连接
// 5. 跳过注释行
```

**重连机制**
```typescript
RECONNECT_BASE_DELAY_MS = 1000
RECONNECT_MAX_DELAY_MS = 30_000
RECONNECT_GIVE_UP_MS = 600_000  // 10分钟后放弃
// 指数退避 + 25%抖动
```

### 14.7 流式消息处理

**消息类型**
```typescript
type StreamClientEvent = {
  event_id: string
  sequence_num: number
  event_type: string
  source: string
  payload: Record<string, unknown>
  created_at: string
}
```

**去重机制**
```typescript
seenSequenceNums: Set<number>
// 超过1000个时清理低于 lastSequenceNum - 200 的旧序号
// 重复帧记录warn级别日志
```

**文本delta合并**
```typescript
// stream_event消息100ms缓冲
// 多个text_delta合并为"截至目前的完整快照"
// 每个flush只输出一个事件，保留首个delta的UUID
```

---

## 十五、更多核心模块深入学习

### 15.1 工具注册和发现系统

**注册机制** (`tools.ts`)
```typescript
// 直接导入 + 加入 getAllBaseTools() 数组
export function getAllBaseTools(): Tools {
  return [
    AgentTool,
    TaskOutputTool,
    BashTool,
    ...(hasEmbeddedSearchTools() ? [] : [GlobTool, GrepTool]),
    ...(process.env.USER_TYPE === 'ant' ? [ConfigTool] : []),
    ...(isTodoV2Enabled() ? [TaskCreateTool, ...] : []),
  ]
}
```

**发现流程** (`getTools()`)
```
Simple Mode检查 → 特殊工具过滤 → 权限规则过滤 → isEnabled()检查
```

**工具池组装** (`assembleToolPool()`)
```typescript
// 内置工具优先，uniqBy保留首次出现的工具名
// 按名称排序保证缓存稳定性
```

### 15.2 Settings系统

**5个来源优先级** (低→高)
```
userSettings → projectSettings → localSettings → flagSettings → policySettings
```

**变更检测** (`changeDetector.ts`)
```
文件变化 → executeConfigChangeHooks → fanOut() → resetSettingsCache()
```

**Keychain存储** (macOS)
```
读取: security find-generic-password -a "<username>" -w -s "<serviceName>"
写入: security add-generic-password -U -a "<username>" -s "<serviceName>" -X "<hexData>"
```

### 15.3 MCP协议处理

**工具名称格式**: `mcp__<serverName>__<toolName>`

**8种传输类型**
```
stdio | sse | http | ws | sse-ide | ws-ide | sdk | claudeai-proxy
```

**生命周期清理** (stdio)
```
SIGINT → 100ms → SIGTERM → 400ms → SIGKILL (600ms总)
```

### 15.4 会话管理和历史记录

**会话消息持久化** (`sessionStorage.ts`)
```typescript
// 延迟物化: Session文件在第一个真实消息时才创建
// 写入缓冲: 100ms间隔批量写入
// Chain追踪: isChainParticipant()区分parentUuid关系
```

**Compact压缩类型**
```
Full Compact: 全部消息摘要
Partial Compact: 选择性摘要
Microcompact: 时间触发/缓存编辑
Session Memory: 会话级摘要替代传统压缩
```

### 15.5 日志和遥测系统

**三层日志架构**
```
Debug日志 (debug.ts) → Analytics事件 → Error日志
```

**敏感数据脱敏**
```typescript
// MCP工具名脱敏: mcp__slack__read_channel → mcp_tool
// 工具输入截断: 512字符→128字符, 4KB JSON, 20项, 2层深度
```

**隐私级别**
```
default → no-telemetry → essential-traffic
```

### 15.6 Memory系统

**四类记忆**
```
user: 用户角色、目标、职责
feedback: 用户指导
project: 项目状态、目标、bug
reference: 外部系统指针
```

**存储路径**
```
~/.claude/projects/<sanitized-git-root>/memory/
├── MEMORY.md (索引，最多200行)
├── user_role.md
├── feedback_xxx.md
├── project_xxx.md
└── reference_xxx.md
```

### 15.7 FileEditTool

**核心验证流程**
```
权限检查 → 文件大小检查(1GB) → TOCTOU检查 → 字符串匹配
```

**撤销机制**: `fileHistoryTrackEdit()` 备份编辑前内容

**引号规范化**: 弯引号转直引号，但保留文件中的弯引号风格

### 15.8 SearchTool

**Ripgrep三重模式**
```
System ripgrep → Embedded ripgrep (Bun) → Bundled ripgrep
```

**EAGAIN重试**: 自动切换单线程模式 `-j 1`

**超时处理**
```
WSL: 60秒 (3-5x性能惩罚)
其他: 20秒
```

### 15.9 Worktree系统

**存储结构**
```
仓库根目录/.claude/worktrees/<slug>
// 扁平化命名: user/feature → user+feature
```

**创建流程**
```
validateWorktreeSlug → hasWorktreeCreateHook?
  ├─ 有Hook → executeWorktreeCreateHook
  └─ 无Hook → git fetch → git worktree add → sparse-checkout → symlink
```

**安全保护**: 删除前检测未提交变更，防止数据丢失

### 15.10 Swarm/Team多Agent

**Mailbox系统** (文件-based)
```
.claude/teams/{team_name}/inboxes/{agent_name}.json
```

**消息格式**
```xml
<teammate-message teammate_id="agent-name" color="red" summary="brief">
  message content
</teammate-message>
```

**隔离机制**: worktree隔离 / 远程隔离 / 进程隔离

### 15.11 Todo vs Task

| | Todo | Task |
|---|---|---|
| 存储 | 内存 (appState.todos) | 文件系统 |
| ID管理 | 无，纯数组索引 | 自增ID + 高水位 |
| 依赖管理 | 无 | blocks/blockedBy |
| 持久化 | 会话级 | 跨会话 |

### 15.12 Speculation预测执行

**Overlay文件系统** (Copy-on-Write)
```
/tmp/claude/speculation/{pid}/{id}/
写入文件时先复制原文件到overlay目录，再修改overlay版本
```

**工具限制**
```
允许: 只读工具(Read, Glob, Grep)
拒绝: 写工具(Edit, Write)除非权限模式允许
边界停止: bash命令, edit操作
```

**状态类型**
```
idle → active → (complete | bash | edit | denied_tool)
```

### 15.13 FileHistory和锁文件

**FileHistory核心**
```typescript
// 三阶段追踪
fileHistoryTrackEdit()  // 编辑前保存当前状态
fileHistoryMakeSnapshot()  // 每用户消息后创建快照
fileHistoryRewind()  // 回滚到指定消息时的状态
```

**防竞态设计**
```typescript
// 确定性hash命名 {hash}@v1 避免重复备份
// 但真正写入时通过竞态检查保护
```

**锁文件机制** (`consolidationLock.ts`)
```
用于autoDream并发控制
锁文件路径: {autoMemPath}/.consolidate-lock
锁文件内容: holder的PID
锁的mtime: 上次整合时间
```

### 15.14 REPL交互界面

**REPL模式控制**
```typescript
// 仅CLI启用，隐藏直接工具访问
isReplModeEnabled() → CLAUDE_CODE_REPL / USER_TYPE=ant
```

**QueryGuard模式**
```typescript
// 同步状态机替代双状态模式
// 防止isLoading和isQueryRunning不同步
```

**历史管理** (`history.ts`)
```
MAX_HISTORY_ITEMS = 100
存储在 ~/.claude/history.jsonl
按项目隔离，当前会话优先
```

### 15.15 核心设计模式总结

**1. 纵深防御 (Defense in Depth)**
```
Bash安全5层: bashParser → ast → bashSecurity → pathValidation → bashPermissions
每层不知道上一层是否失败，FAIL-CLOSED策略
```

**2. 状态管理模式**
```
Bootstrap State (单例) → AppState Store (pubsub) → onChange传播枢纽
React集成: useSyncExternalStore + selector模式
```

**3. 工具系统架构**
```
buildTool工厂 → 统一接口 → UI.tsx独立渲染
注册: 直接导入 + getAllBaseTools()数组
发现: getTools() → 权限过滤 → isEnabled()检查
```

**4. AsyncGenerator驱动**
```
runAgent: for await → yield消息
BashTool: runShellCommand生成器 → 进度回调
Stream处理: 生成器 + yield实现流式输出
```

**5. Prompt缓存边界**
```
__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__
分离静态(可缓存)和动态(会话特定)内容
```

**6. 延迟物化模式**
```
Session文件在第一个真实消息时才创建
Settings文件在第一次写入时才物化
```

**7. Memoization策略**
```
connectToServer() - 连接缓存
loadAllPlugins() - 插件加载缓存
createStore() - 状态变化时比较Object.is()
```

**8. Feature DCE (死代码消除)**
```
process.env.USER_TYPE === 'ant' 条件导入
feature('FEATURE_NAME') 运行时检查
```

**9. Copy-on-Write隔离**
```
Speculation: /tmp/claude/speculation/{pid}/{id}/
写入文件时先复制原文件到overlay目录
```

**10. 版本化缓存**
```
插件缓存: ~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/
Keychain: 30秒TTL，stale-while-error
```
7. **Memoization**: 避免重复加载和计算

## 十六、Session和对话管理系统

### 16.1 核心数据结构

**SessionHandle** (`bridge/types.ts`)
```typescript
type SessionHandle = {
  sessionId: string
  done: Promise<SessionDoneStatus>
  activities: SessionActivity[]  // ring buffer of recent activities
  currentActivity: SessionActivity | null
  accessToken: string
  lastStderr: string[]
  writeStdin(data: string): void
  updateAccessToken(token: string): void
  kill(): void
  forceKill(): void
}
```

**Session状态管理** (`utils/sessionState.ts`)
```typescript
type SessionState = 'idle' | 'running' | 'requires_action'
```

### 16.2 对话历史存储

**文件格式**: JSONL (每行一个JSON对象)
**路径**: `~/.claude/projects/{sanitized_cwd}/{sessionId}.jsonl`

**轻量级元数据提取** (`sessionStoragePortable.ts`)
```typescript
// 不解析完整JSONL，只读head(64KB)+tail(64KB)
readHeadAndTail(filePath, fileSize, buf)
extractFirstPromptFromHead(head)
```

### 16.3 多会话管理

**并发会话追踪** (`concurrentSessions.ts`)
```typescript
registerSession()  // 写 ~/.claude/sessions/{pid}.json
countConcurrentSessions()
```

### 16.4 Session Memory自动摘要

**触发阈值** (`services/SessionMemory/sessionMemory.ts`)
```typescript
minimumMessageTokensToInit: number    // 默认10000
minimumTokensBetweenUpdate: number     // 默认5000
toolCallsBetweenUpdates: number        // 默认3
```

**隔离子Agent提取模式**
```typescript
// 使用runForkedAgent创建独立上下文
// 只允许修改特定memory文件
await runForkedAgent({
  promptMessages: [createUserMessage({ content: userPrompt })],
  canUseTool: createMemoryFileCanUseTool(memoryPath),
})
```

## 十七、AsyncGenerator流式处理和Agent循环

### 17.1 query主循环 (`query.ts:307-1728`)

```typescript
// while(true)主循环
while (true) {
  // 1. 预处理：snip、microcompact、autocompact
  // 2. 调用模型进行流式处理
  for await (const message of deps.callModel({...})) {
    yield message  // 实时 yield 流式事件
    // 处理工具块...
    if (streamingToolExecutor) {
      streamingToolExecutor.addTool(toolBlock, message)
    }
  }
  // 3. 工具执行
  for await (const update of toolUpdates) {
    if (update.message) yield update.message
  }
  // 4. 继续下一轮或返回终止
  state = next; continue
}
```

### 17.2 状态不可变更新

```typescript
const next: State = {
  ...state,
  messages: newMessages,
  turnCount: nextTurnCount,
  transition: { reason: 'next_turn' },
}
state = next; continue  // 关键：继续循环
```

### 17.3 依赖注入模式 (`query/deps.ts`)

```typescript
export type QueryDeps = {
  callModel: typeof queryModelWithStreaming
  microcompact: typeof microcompactMessages
  autocompact: typeof autoCompactIfNeeded
  uuid: () => string
}
```

### 17.4 终止原因 (Terminal)

| Reason | 含义 |
|--------|------|
| `completed` | 正常完成 |
| `max_turns` | 达到最大轮数 |
| `prompt_too_long` | 提示过长 |
| `stop_hook_prevented` | Stop hook阻止 |

## 十八、StreamingToolExecutor并行执行

### 18.1 核心机制

**并发安全判断**
```typescript
const isConcurrencySafe = parsedInput?.success
  ? toolDefinition.isConcurrencySafe(parsedInput.data)
  : false
```

**执行条件**
```typescript
canExecuteTool(isConcurrencySafe): boolean {
  const executingTools = this.tools.filter(t => t.status === 'executing')
  return (
    executingTools.length === 0 ||
    (isConcurrencySafe && executingTools.every(t => t.isConcurrencySafe))
  )
}
```

### 18.2 队列处理

**并行规则**:
- `isConcurrencySafe=true` → 可互相并行
- `isConcurrencySafe=false` → 必须独占执行

### 18.3 进度消息即时yield

```typescript
// 进度消息 → 立即加入pendingProgress并唤醒消费者
if (update.message.type === 'progress') {
  tool.pendingProgress.push(update.message)
  this.progressAvailableResolve?.()
}
```

### 18.4 错误级联取消

```typescript
// 只有Bash错误取消同级的工具
if (tool.block.name === BASH_TOOL_NAME) {
  this.hasErrored = true
  this.siblingAbortController.abort('sibling_error')
}
```

## 十九、MCP协议处理和工具转换

### 19.1 工具命名策略

**格式**: `mcp__serverName__toolName`

```typescript
buildMcpToolName(client.name, tool.name)
mcpInfoFromString(toolName)  // 解析
```

### 19.2 工具注解转换

```typescript
// 从MCP annotations读取工具特性
isConcurrencySafe() { return tool.annotations?.readOnlyHint ?? false }
isDestructive() { return tool.annotations?.destructiveHint ?? false }
isOpenWorld() { return tool.annotations?.openWorldHint ?? false }
```

### 19.3 LRU缓存模式

```typescript
export const fetchToolsForClient = memoizeWithLRU(
  async (client) => { /* ... */ },
  (client) => client.name,  // 按服务器名缓存
  MCP_FETCH_CACHE_SIZE  // 20
)
```

### 19.4 资源处理

```typescript
// MCP资源包装
type ServerResource = Resource & { server: string }

// 仅在首个支持资源的服务器连接时添加工具
if (supportsResources && !resourceToolsAdded) {
  resourceToolsAdded = true
  resourceTools.push(ListMcpResourcesTool, ReadMcpResourceTool)
}
```

## 二十、核心设计模式总结（补充）

### 11. Ring Buffer模式
```typescript
const MAX_ACTIVITIES = 10
if (activities.length >= MAX_ACTIVITIES) {
  activities.shift()
}
activities.push(activity)
```

### 12. Post-Sampling Hook模式
```typescript
// 在采样完成后异步执行，不阻塞主对话
registerPostSamplingHook(extractSessionMemory)
```

### 13. Two-Phase Commit模式
```typescript
// 1. 创建session获取ID
// 2. 启动子进程
// 3. 通过stdin/stdout通信
```

### 14. 轻量级元数据提取模式
```typescript
// 不解析完整JSONL，只读head+tail
// 通过正则提取关键字段
```

### 15. 隔离子Agent模式
```typescript
// 使用runForkedAgent创建独立上下文
// 只允许修改特定文件
```

### 16. AsyncGenerator级联
```typescript
// yield* 语法将内层yield直接传递出去
const terminal = yield* queryLoop(params, consumedCommandUuids)
```

### 17. 状态不可变更新
```typescript
// 每次状态转换创建新对象而非修改
const next = { ...state, messages: newMessages }
state = next; continue
```

### 18. 并行安全判断模式
```typescript
// 在执行时而非添加时判断并发安全性
const isConcurrencySafe = toolDefinition.isConcurrencySafe(input)
```

### 19. 进度消息即时yield模式
```typescript
// 进度消息不等待工具完成，立即返回
if (update.message.type === 'progress') {
  pendingProgress.push(update.message)
  progressAvailableResolve?.()
}
```

### 20. 错误级联取消模式
```typescript
// 一个工具错误取消所有同级工具
if (errorTool.name === BASH_TOOL_NAME) {
  siblingAbortController.abort('sibling_error')
}
```
