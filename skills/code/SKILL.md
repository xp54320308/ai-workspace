---
name: code
version: 2.0.0
description: 增强编码技能 - 基于 Claude Code 架构的多阶段任务系统。先规划、再执行、后验证。触发词：写代码、修复 bug、重构、代码审查、调试、创建项目。
triggers:
  - "写代码"
  - "修复 bug"
  - "重构"
  - "代码审查"
  - "调试"
  - "创建项目"
  - "实现功能"
  - "debug"
  - "写个脚本"
tags: [development, coding, refactoring, debugging]
allowed-tools:
  - terminal
  - read_file
  - write_file
  - edit_file
  - search_files
required_commands:
  - git
  - python3 / node / go
---

# Code Skill v2 — 基于 Claude Code 架构

## 核心改变

**v1 是工具集合，v2 是任务系统。**

Claude Code 的精髓不是某个算法，而是一套**任务状态机**：
- 每个任务有生命周期（规划 → 探索 → 实现 → 验证 → 完成）
- 每个阶段有明确的输入输出
- 状态机确保不会遗漏步骤

---

## 第一阶段：理解任务（Understanding）

### 1.1 分析请求

收到编码任务时，先问自己：

```
1. 这是什么类型的任务？
   - 新功能（new_feature）
   - Bug 修复（bug_fix）
   - 重构（refactor）
   - 代码审查（review）
   - 脚本/工具（script）

2. 涉及哪些文件？
   - 已知 → 直接读取
   - 未知 → 先搜索定位

3. 依赖什么环境？
   - 语言/框架
   - 外部服务
   - 配置文件
```

### 1.2 项目探索

```bash
# 找项目根目录
ls -la | grep -E "package.json|requirements.txt|Cargo.toml|go.mod|.git"

# 了解目录结构（跳过 node_modules 等）
tree -L 3 -I 'node_modules|__pycache__|.git|target|dist|build'

# 找入口文件
ls *.py *.js *.ts *.go 2>/dev/null

# 查依赖
cat requirements.txt 2>/dev/null || cat package.json 2>/dev/null || cat go.mod 2>/dev/null
```

### 1.3 理解代码

```bash
# 找相关文件
grep -r "关键词" --include="*.py" --include="*.js" -l

# 看关键函数的上下文
grep -n "function_name" -A 10 -B 2 file.py

# 了解接口/类
grep -n "class\|def\|interface\|type" file.py | head -30
```

---

## 第二阶段：规划（Planning）

### 2.1 任务分解

将任务拆成**有序步骤**：

```
Task: 实现用户登录功能

Step 1: 读取 auth.py 了解现有结构
Step 2: 在 UserService 添加 login 方法
Step 3: 添加数据库查询逻辑
Step 4: 处理密码验证
Step 5: 添加错误处理
Step 6: 写单元测试
Step 7: 验证功能
```

### 2.2 风险检查

```
⚠️ 需要确认的问题：
- 是否有现成的 auth 模块可以扩展？
- 密码加密用什么算法？
- session 怎么管理？
- 错误码规范是什么？
```

### 2.3 计划输出

在开始写代码之前，先输出计划：

```
## 实施计划

### Step 1: auth.py（第 N 行）
- 读取现有代码结构
- 找到 UserService 类

### Step 2: 添加 login 方法
- 输入：email, password
- 输出：User | Error
- 使用 bcrypt 验证密码

...（继续列出所有步骤）
```

---

## 第三阶段：实现（Implementation）

### 3.1 编码规范

**每个文件改动前先读取完整内容**，不要凭猜测写代码。

```python
# Python 模块模板
"""
模块描述。
"""

from typing import Optional


def function_name(param1: str, param2: int) -> Optional[dict]:
    """函数描述。
    
    Args:
        param1: 参数1描述
        param2: 参数2描述
    
    Returns:
        成功返回 dict，失败返回 None
    
    Raises:
        ValueError: 参数无效时
    """
    if not param1:
        raise ValueError("param1 is required")
    
    # 实现...
    return {"status": "ok"}
```

### 3.2 编辑策略

| 情况 | 策略 |
|------|------|
| 小改动（<5行） | `edit` 精确替换 |
| 中等改动（函数级） | 先读，再 `edit` 替换函数体 |
| 大改动（文件级） | `write` 新文件，再替换 |
| 多文件改动 | 按依赖顺序依次修改 |

### 3.3 Git 工作流

```bash
# 开始新任务前先看状态
git status

# 创建分支（如果涉及多步骤）
git checkout -b feature/my-feature

# 每完成一个步骤可以 commit
git add file.py
git commit -m "feat: add login method"

# 如果是很小的改动，可以直接 commit
```

---

## 第四阶段：验证（Verification）

### 4.1 语法检查

```bash
# Python
python -m py_compile file.py

# JavaScript/TypeScript
node --check file.js
npx tsc --noEmit file.ts

# Go
go build file.go

# Shell
bash -n script.sh
```

### 4.2 运行测试

```bash
# Python
pytest tests/ -v
pytest tests/ -k "test_name"

# Node
npm test
npm run test:watch

# Go
go test ./... -v
```

### 4.3 手动验证

```bash
# 运行脚本看输出
python script.py --arg value

# 启动服务测试
python app.py &
curl localhost:8080/health
```

### 4.4 回归检查

```
改完之后，确认：
□ 原有功能没坏（跑一下核心测试）
□ 语法无误（编译器检查）
□ 类型正确（如果有类型系统）
□ 没有引入明显的性能问题
```

---

## 第五阶段：完成（Completion）

### 5.1 整理输出

```
✅ 完成！

**改动摘要：**
- 新增：`auth.py` 添加 login() 方法
- 修改：`requirements.txt` 添加 bcrypt 依赖
- 新增：`tests/test_auth.py` 登录测试

**验证结果：**
- pytest tests/test_auth.py ✓
- 手动测试 curl localhost:8080/login ✓

**下一步（如需要）：**
- 添加注册功能
- 实现 token 刷新
- 添加登录日志
```

### 5.2 清理

```bash
# 确认 git 状态
git status

# 如果有临时文件，删除
rm -f *.pyc __pycache__/*
```

---

## 常见模式

### Pattern 1: Bug 修复

```
1. 复现 bug（读代码找到问题位置）
2. 理解预期行为 vs 实际行为
3. 修复（edit）
4. 验证修复有效
5. 确认没引入新 bug
```

### Pattern 2: 新功能

```
1. 找相关现有代码（避免重复造轮子）
2. 理解现有模式（命名/错误处理/返回格式）
3. 按现有模式实现
4. 写测试
5. 验证
```

### Pattern 3: 重构

```
1. 列出要改的点
2. 按依赖顺序改（先改被调用的，再改调用的）
3. 每改一个点，验证功能不变
4. 最后确认整体正常
```

### Pattern 4: 代码审查

```
1. 先跑测试，看是否通过
2. 读代码，找：
   - 逻辑错误
   - 边界情况漏掉
   - 安全问题（注入、密码明文等）
   - 性能问题（N+1 查询等）
   - 错误处理缺失
3. 输出审查报告
```

---

## 工具箱

### 文件读取优先级

```bash
# 优先读这些文件
README.md              # 项目概览
package.json           # JS 项目
requirements.txt       # Python 项目
go.mod                 # Go 项目
pyproject.toml         # 现代 Python

# 入口文件
app.py / main.py / index.js / main.go
```

### 搜索命令

```bash
# 找关键词
grep -rn "TODO\|FIXME\|BUG" --include="*.py" .

# 找函数定义
grep -n "def \|class " file.py

# 找 imports
grep -n "^import\|^from" file.py
```

### 测试命令速查

| 语言 | 测试 | 覆盖率 |
|------|------|--------|
| Python | `pytest` | `pytest --cov=src` |
| JavaScript | `npm test` | `npm run coverage` |
| Go | `go test ./...` | `go test -cover` |
| Rust | `cargo test` | `cargo test -- --cov` |

---

## 反合理化表（Anti-Rationalization）

Agent 常见偷懒借口 vs 现实：

| 借口 | 现实 |
|------|------|
| "这个太简单，不需要走流程" | 简单任务更容易漏边界情况，流程保证质量 |
| "我先写代码，测试以后补" | 没测试的代码 = 没完成。测试是验证，不是装饰 |
| "我大概知道问题在哪，直接改" | 猜测 ≠ 确认。先读代码，再动手 |
| "改动很小，不需要 git commit" | 小改动也需要可追溯性，出问题能回滚 |
| "这个 bug 我见过，直接修" | 每次都要重新确认上下文，环境可能变了 |
| "跑一下看看就行，不用写测试" | 手动验证不可重复，自动化测试才是真验证 |
| "重构不需要测试，逻辑没变" | 重构最需要测试保护，改错了都没发现 |
| "先让它跑起来，以后再优化" | 技术债利息很高，但至少要记录 TODO |

**铁律：如果发现自己在找理由跳过步骤，说明这个步骤更重要。**

---

## 验证清单（Verification）

每个编码任务完成前，必须通过以下检查：

### 必查项 ✅
- [ ] 代码已读取（不是凭猜测写的）
- [ ] 语法检查通过（`python -m py_compile` / `node --check` / `go build`）
- [ ] 测试通过（`pytest` / `npm test` / `go test`）
- [ ] 无硬编码密钥/API Key
- [ ] Git status 干净或有明确 commit message

### 按类型补充
- **新功能**: 有对应测试用例
- **Bug 修复**: 有复现测试 + 修复验证
- **重构**: 前后测试结果一致
- **API 变更**: 调用方已同步更新

### 退出条件
**只有全部 ✅ 才算完成。"看起来对"永远不够，要有证据。**

---

## 注意事项

1. **不要猜测** — 读文件先于写代码
2. **小步提交** — 避免一次性改几十个文件
3. **验证驱动** — 改完必须跑测试
4. **安全第一** — 密码/API Key 不写入代码
5. **向后兼容** — 改 API 要考虑调用方
