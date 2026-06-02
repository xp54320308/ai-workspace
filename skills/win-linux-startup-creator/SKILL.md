---
name: win-linux-startup-creator
category: software-development
description: |
  在 WSL2 中运行的程序创建 Windows 批处理启动器 (桌面快捷启动程序) 的完整指南

---

## 📋 场景
在 WSL2 中运行的程序（如 hermes、Python 等）需要创建 Windows 批处理启动器 `*.bat` 放在桌面快速启动。

## 🎯 关键经验

### 1. 路径转换规则
| Linux 路径 | Windows 路径 |
|-------------|---------------|
| `/home/user/.local/bin/hermes` | `C:\Users\user\.local\bin\hermes` |
| `/mnt/c/Users/user/Desktop/` | `C:\Users\user\Desktop\` |
| `/mnt/c/Users/user/` | `C:\Users\user\` |

### 2. 编码要求
```bat
@echo off
chcp 65001 >nul  ; 强制 UTF-8 编码，防止中文乱码
```

### 3. 可靠运行方式对比

#### ✅ 推荐：直接调用 hermes 可执行文件
```bat
@echo off
chcp 65001 >nul
"C:\Users\user\.local\bin\hermes" gateway run --replace
echo Gateway started
pause
```

#### ⚠️ 备选：使用 wsl (可能显示 wsl 不是命令)
```bat
wsl.exe -e hermes gateway run --replace
```

#### ⚠️ 备选：PowerShell 包装
```bat
powershell -Command "wsl -e hermes gateway run --replace"
```

## 📝 推荐模板

### 最小启动器 (5 行) ✅ 推荐
```bat
@echo off
chcp 65001 >nul
"C:\Users\user\.local\bin\hermes" gateway run --replace
echo Gateway running
pause
```

### 无限循环重启
```bat
@echo off
chcp 65001 >nul
:START
"C:\Users\user\.local\bin\hermes" gateway run --replace
goto START
```

### 带清理的启动器
```bat
@echo off
chcp 65001 >nul
echo Killing old instances...
pkill -f hermes 2>nul 2>&1
echo Starting fresh...
"C:\Users\user\.local\bin\hermes" gateway run --replace
pause
```

## 🔧 故障排查

### 问题 1: 双击无法启动
- 右键 → 属性 → 取消勾选"只读"
- 右键 → 以管理员身份运行
- 检查文件是否有占用进程

### 问题 2: 显示乱码
- 确保文件包含 `chcp 65001`
- Windows 11 一般自动处理 UTF-8
- 用记事本重新打开时选择"Save as"→ 编码选 UTF-8

### 问题 3: "不是内部或外部命令"
- 确保使用完整路径（不要依赖 `%PATH%`）
- 检查 hermes 是否存在：`file:///home/user/.local/bin/hermes`
- 确认 `wsl` 已启动：`wsl --list --verbose`

## 🛠️ 创建流程

### 使用 write_file 工具（推荐）
```python
content = """@echo off
chcp 65001 >nul
"C:\\Users\\user\\.local\\bin\\hermes" gateway run --replace
echo Started
pause
"""
write_file(content, "/mnt/c/Users/user/Desktop/start.bat")
```

### 重要提示
1. 必须包含 `\r\n` 行尾
2. 使用 `write_file` 而非 `echo` 或 `cat`
3. 路径用 `/mnt/c/` 或 `C:\` 均可
4. 转义路径中的反斜杠

## ✅ 验证步骤
```bash
# 1. 检查文件存在
ls -la "/mnt/c/Users/user/Desktop/start.bat"

# 2. 查看内容
cat "/mnt/c/Users/user/Desktop/start.bat"

# 3. 确认可读性
file "/mnt/c/Users/user/Desktop/start.bat"
```

## 💡 最佳实践

1. **始终使用完整路径** - 避免 `%PATH%` 环境变量问题
2. **添加 `chcp 65001`** - 强制 UTF-8 防止中文乱码
3. **禁用提示输出** - 用 `>nul` 抑制不必要的显示
4. **添加 `pause`** - 方便调试查看错误信息
5. **先测试再清理** - 删除测试/失败版本文件
6. **保持简单** - 避免复杂脚本，出错难排查

## ⚠️ 注意事项

- Windows 批处理需要 CRLF 行尾 (`\r\n`)
- WSL 中创建 `.bat` 文件需要正确处理行尾
- 某些工具可能截断换行符
- 在 Windows 上直接编辑更可靠
- 建议先用简单版本测试

## 📂 常用文件位置

| 用途 | Linux 路径 | Windows 路径 |
|------|------------|--------------|
| hermes | `/home/user/.local/bin/hermes` | `C:\Users\user\.local\bin\hermes` |
| 桌面 | `/mnt/c/Users/user/Desktop/` | `C:\Users\user\Desktop\` |
| hermes 配置 | `/home/user/.hermes/` | `C:\Users\user\.hermes\` |
| 网关启动脚本 | `/home/user/.hermes/hermes-agent/venv/bin/hermes` | - |

## 🎓 经验总结

从多次尝试中发现：
- 复杂的多行脚本容易出错
- 简单 5-6 行文件最可靠
- 直接用 hermes 路径最稳定
- `chcp 65001` 是必须的
- Windows 11 对 UTF-8 支持良好