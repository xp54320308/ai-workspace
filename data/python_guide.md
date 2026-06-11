# Python 编程语言指南

## 简介

Python 是一种高级、解释型、通用编程语言，由 Guido van Rossum 于 1991 年首次发布。
Python 的设计哲学强调代码的可读性和简洁性，使用缩进来定义代码块。

## 核心特性

### 1. 简洁易读
Python 语法简洁清晰，接近自然语言，学习曲线较低。

### 2. 动态类型
变量无需声明类型，运行时自动推断。
```python
x = 10        # 整数
x = "hello"   # 字符串
```

### 3. 丰富的标准库
Python 内置了大量模块：`os`, `sys`, `json`, `re`, `datetime`, `collections` 等。

### 4. 跨平台
Windows、macOS、Linux 均可运行。

## 常用框架

| 框架 | 用途 |
|------|------|
| Django | 全栈 Web 框架 |
| Flask | 轻量级 Web 框架 |
| FastAPI | 高性能 API 框架 |
| TensorFlow | 机器学习框架 |
| PyTorch | 深度学习框架 |
| LangChain | LLM 应用开发框架 |
| Pandas | 数据分析 |

## 虚拟环境

Python 使用虚拟环境隔离项目依赖：
```bash
python -m venv myenv
source myenv/bin/activate   # Linux/macOS
myenv\Scripts\activate      # Windows
pip install <package>
```

## 最佳实践

1. **使用 type hints** 提高代码可读性
2. **遵循 PEP 8** 编码规范
3. **使用虚拟环境** 隔离依赖
4. **编写单元测试** 保证代码质量
5. **使用 `requirements.txt`** 管理依赖版本
