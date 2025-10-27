# 🚀 Python 版本快速开始指南

欢迎使用 Python 版本的编程助手教程！这个指南将帮助你快速上手。

## 📋 前置要求

- Python 3.8 或更高版本
- Anthropic API 密钥

## ⚡ 快速安装

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **设置 API 密钥**
   ```bash
   export ANTHROPIC_API_KEY="你的-api-密钥-在这里"
   ```

## 🎯 开始体验

### 1. 基础聊天
```bash
python chat.py
```
试试说："你好！请介绍一下 Python 编程"

### 2. 文件读取
```bash
python read_file.py
```
试试说："读取 fizzbuzz.js 文件"

### 3. 文件浏览
```bash
python list_files.py
```
试试说："列出当前目录的所有文件"

### 4. 命令执行
```bash
python bash_tool.py
```
试试说："运行 pwd 命令"

### 5. 文件编辑
```bash
python edit_tool.py
```
试试说："创建一个 Python 的 hello world 程序"

### 6. 代码搜索（最终版本）
```bash
python code_search_tool.py
```
试试说："搜索所有 Python 文件中的函数定义"

## 💡 使用技巧

- **详细模式**：添加 `--verbose` 参数查看详细日志
  ```bash
  python chat.py --verbose
  ```

- **安全提示**：
  - 命令执行工具会阻止危险命令（如 `rm -rf /`）
  - 始终在受信任的环境中运行
  - 不要执行你不理解的命令

- **中文支持**：所有助手都支持中文对话

## 🔧 常见问题

### API 密钥问题
```bash
# 检查是否设置成功
echo $ANTHROPIC_API_KEY
```

### Python 版本问题
```bash
# 检查 Python 版本
python --version
# 或
python3 --version
```

### 依赖问题
```bash
# 重新安装依赖
pip install --force-reinstall -r requirements.txt
```

## 📚 学习路径

建议按以下顺序学习：

1. **chat.py** - 理解基本的 API 调用和对话管理
2. **read_file.py** - 学习如何添加工具和处理工具调用
3. **list_files.py** - 掌握多个工具的协同工作
4. **bash_tool.py** - 了解命令执行和安全考虑
5. **edit_tool.py** - 学习文件编辑和字符串操作
6. **code_search_tool.py** - 综合运用所有功能

## 🎉 恭喜！

你已经准备好开始构建自己的编程助手了。每个 Python 文件都是完整的工作示例，你可以：

- 直接运行体验功能
- 阅读代码学习实现原理
- 基于这些代码开发自己的工具

祝你学习愉快！🚀