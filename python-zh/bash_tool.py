#!/usr/bin/env python3
"""
命令执行助手 - 添加 shell 命令执行功能
这是构建编程助手的第四个版本

这个程序在前一版本的基础上添加了 shell 命令执行功能。
现在 Claude 不仅可以读取文件和浏览目录，还可以执行终端命令，
真正具备了与操作系统交互的能力。

新增功能：
- 执行 shell 命令
- 捕获命令输出（标准输出和错误输出）
- 命令超时控制
- 安全检查（阻止危险命令）
- 特殊命令处理（ls、pwd、git 等）

为什么要添加命令执行功能？
- 运行开发工具（git、npm、pip 等）
- 检查系统状态
- 执行构建和测试命令
- 自动化常见任务
- 验证代码更改

安全考虑：
- 阻止危险命令（rm -rf /、sudo 等）
- 命令超时防止挂起
- 在当前工作目录执行（限制范围）
- 不执行需要管理员权限的命令

使用场景示例：
- "运行 git status"
- "查看当前目录"
- "列出所有 Python 文件"
- "运行测试"
- "检查代码格式"
"""

# 导入必要的库
import argparse  # 命令行参数解析
import json      # JSON 数据处理
import os        # 操作系统功能
import subprocess  # 子进程管理（用于执行 shell 命令）
import sys       # 系统相关操作
from pathlib import Path  # 现代文件路径处理
from typing import List, Dict, Any, Optional  # 类型提示
from anthropic import Anthropic  # Anthropic API 客户端
from dotenv import load_dotenv   # 环境变量加载

# 加载环境变量
load_dotenv()

class ToolRegistry:
    """工具注册表类
    
    管理所有可用工具，包括文件操作和命令执行工具。
    """
    
    def __init__(self):
        """初始化工具注册表"""
        self.tools = {}
    
    def register(self, name: str, description: str, input_schema: Dict, function):
        """注册新工具"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "function": function
        }
    
    def get(self, name: str):
        """获取工具"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Dict]:
        """获取所有工具定义（用于 API 调用）"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            for tool in self.tools.values()
        ]


def read_file(path: str) -> Dict[str, Any]:
    """读取文件内容（与前一版本相同）"""
    try:
        file_path = Path(path)
        
        # 检查文件是否存在
        if not file_path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {path}"
            }
        
        # 检查是否是文件（不是目录）
        if not file_path.is_file():
            return {
                "success": False,
                "error": f"路径不是文件: {path}"
            }
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "path": str(file_path.absolute())
            }
        except UnicodeDecodeError:
            # 如果 UTF-8 失败，尝试其他编码
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "path": str(file_path.absolute()),
                "warning": "使用 latin-1 编码读取文件"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件时出错: {str(e)}"
        }


def list_files(path: str = ".", recursive: bool = False) -> Dict[str, Any]:
    """列出文件和目录（与前一版本相同）"""
    try:
        target_path = Path(path)
        
        # 检查路径是否存在
        if not target_path.exists():
            return {
                "success": False,
                "error": f"路径不存在: {path}"
            }
        
        # 获取文件和目录列表
        items = []
        
        if recursive:
            # 递归列出所有文件和目录
            for item in target_path.rglob("*"):
                relative_path = str(item.relative_to(target_path))
                items.append({
                    "name": relative_path,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "absolute_path": str(item.absolute())
                })
        else:
            # 只列出当前目录
            for item in target_path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "absolute_path": str(item.absolute())
                })
        
        # 按类型和名称排序
        items.sort(key=lambda x: (x["type"], x["name"]))
        
        return {
            "success": True,
            "items": items,
            "path": str(target_path.absolute()),
            "total_count": len(items),
            "directory_count": sum(1 for item in items if item["type"] == "directory"),
            "file_count": sum(1 for item in items if item["type"] == "file")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"列出文件时出错: {str(e)}"
        }


def bash(command: str, timeout: int = 30) -> Dict[str, Any]:
    """执行 shell 命令的工具函数
    
    这是新增的核心工具，允许 Claude 执行终端命令。
    
    参数:
        command: 要执行的 shell 命令字符串
        timeout: 命令超时时间（秒），默认为 30 秒
        
    返回:
        字典，包含以下字段：
        - success: 命令是否成功执行（退出码为 0）
        - stdout: 标准输出内容
        - stderr: 错误输出内容  
        - exit_code: 命令退出码
        - command: 实际执行的命令
        - error: 错误信息（如果有）
        - 其他附加信息（取决于命令类型）
    
    安全特性：
    - 危险命令检测和阻止
    - 超时控制防止命令挂起
    - 在当前工作目录执行（限制范围）
    - 不执行需要特权的命令
    
    特殊命令增强：
    - ls 命令：统计文件数量
    - pwd 命令：提供当前目录信息
    - git 分支命令：解析当前分支
    """
    try:
        # 安全检查 - 阻止危险命令
        # 这个列表包含可能有害的命令或命令片段
        dangerous_commands = [
            "rm -rf /",      # 删除根目录（危险！）
            "sudo",          # 需要管理员权限
            "mkfs",          # 格式化文件系统
            "fdisk",         # 磁盘分区工具
            "dd if=",        # 磁盘复制工具
            ":(){ :|:& };:", # fork 炸弹（会耗尽系统资源）
            "wget",          # 下载工具（可能下载恶意软件）
            "curl"           # 网络请求工具
        ]
        
        # 检查命令是否包含危险内容
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return {
                    "success": False,
                    "error": f"检测到潜在危险命令: {dangerous}",
                    "stdout": "",
                    "stderr": "命令被拒绝执行",
                    "exit_code": 1,
                    "command": command
                }
        
        # 执行命令
        # 使用 subprocess.run 执行 shell 命令
        result = subprocess.run(
            command,           # 命令字符串
            shell=True,        # 通过 shell 执行（支持管道、重定向等）
            capture_output=True,  # 捕获标准输出和错误输出
            text=True,         # 以文本模式返回输出（而不是字节）
            timeout=timeout,   # 超时时间
            cwd=os.getcwd()    # 在当前工作目录执行
        )
        
        # 构建响应
        response = {
            "success": result.returncode == 0,  # 退出码为 0 表示成功
            "stdout": result.stdout,            # 标准输出
            "stderr": result.stderr,            # 错误输出
            "exit_code": result.returncode,     # 退出码
            "command": command                  # 执行的命令
        }
        
        # 特殊命令增强处理
        if result.returncode == 0:
            # 对于某些命令，添加额外的有用信息
            
            if command.startswith("ls"):
                # ls 命令：统计文件数量
                lines = result.stdout.strip().split('\n')
                # 过滤掉空行
                file_count = len([line for line in lines if line.strip()])
                response["file_count"] = file_count
                
            elif command.startswith("pwd"):
                # pwd 命令：显示当前工作目录
                response["current_directory"] = result.stdout.strip()
                
            elif command.startswith("git") and "branch" in command:
                # git 分支命令：解析当前分支
                lines = result.stdout.strip().split('\n')
                current_branch = None
                # 查找以 * 开头的行（表示当前分支）
                for line in lines:
                    if line.startswith('*'):
                        current_branch = line[1:].strip()
                        break
                if current_branch:
                    response["current_branch"] = current_branch
        
        return response
        
    except subprocess.TimeoutExpired:
        # 命令执行超时
        return {
            "success": False,
            "error": f"命令执行超时（{timeout}秒）",
            "stdout": "",
            "stderr": "命令执行超时",
            "exit_code": 1,
            "command": command
        }
        
    except Exception as e:
        # 其他异常
        return {
            "success": False,
            "error": f"执行命令时出错: {str(e)}",
            "stdout": "",
            "stderr": str(e),
            "exit_code": 1,
            "command": command
        }


class BashAgent:
    """命令执行助手类
    
    现在支持三种主要工具：
    1. read_file - 读取文件内容
    2. list_files - 列出目录内容  
    3. bash - 执行 shell 命令
    
    这个助手具备了与操作系统完整交互的能力。
    """
    
    def __init__(self, verbose: bool = False):
        """初始化命令执行助手"""
        self.verbose = verbose
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.conversation = []
        self.registry = ToolRegistry()
        
        # 注册所有工具
        self._register_tools()
        
        if self.verbose:
            print("[日志] 命令执行助手已初始化")
    
    def _register_tools(self):
        """注册所有可用工具"""
        
        # 注册 read_file 工具
        self.registry.register(
            name="read_file",
            description="读取文件内容",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径"
                    }
                },
                "required": ["path"]
            },
            function=read_file
        )
        
        # 注册 list_files 工具
        self.registry.register(
            name="list_files",
            description="列出目录中的文件和子目录",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要列出的目录路径（默认为当前目录）",
                        "default": "."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归列出子目录内容",
                        "default": False
                    }
                }
            },
            function=list_files
        )
        
        # 注册 bash 工具（新增）
        self.registry.register(
            name="bash",
            description="执行 shell 命令",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 shell 命令"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "命令超时时间（秒）",
                        "default": 30  # 默认 30 秒超时
                    }
                },
                "required": ["command"]  # command 是必需参数
            },
            function=bash
        )
        
        if self.verbose:
            print(f"[日志] 已注册 {len(self.registry.tools)} 个工具")
    
    def get_user_input(self) -> str:
        """获取用户输入"""
        try:
            return input("你: ")
        except (EOFError, KeyboardInterrupt):
            return ""
    
    def execute_tool(self, tool_name: str, tool_input: Dict) -> Dict[str, Any]:
        """执行指定的工具"""
        tool = self.registry.get(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"未知工具: {tool_name}"
            }
        
        try:
            if self.verbose:
                print(f"[日志] 执行工具: {tool_name}, 输入: {tool_input}")
            
            result = tool["function"](**tool_input)
            
            if self.verbose:
                print(f"[日志] 工具执行成功: {tool_name}")
            
            return result
        except Exception as e:
            error_msg = f"工具执行失败: {str(e)}"
            if self.verbose:
                print(f"[日志] {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def run_inference(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行推理，调用 Claude API"""
        if self.verbose:
            print(f"[日志] 正在调用 Claude API，对话长度: {len(conversation)}")
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=conversation,
                tools=self.registry.get_all_tools()
            )
            
            if self.verbose:
                print(f"[日志] API 调用成功，收到响应")
            
            return response
        except Exception as e:
            if self.verbose:
                print(f"[日志] API 调用失败: {str(e)}")
            raise e
    
    def handle_tool_calls(self, tool_calls) -> List[Dict[str, Any]]:
        """处理工具调用
        
        现在需要处理三种不同类型的工具，每种工具的结果
        需要不同的显示方式。
        """
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_input = tool_call.input
            
            print(f"🔧 使用工具: {tool_name}")
            
            # 执行工具
            result = self.execute_tool(tool_name, tool_input)
            
            # 构建工具结果
            tool_result = {
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            }
            
            results.append(tool_result)
            
            # 显示结果摘要（根据工具类型显示不同信息）
            if result.get("success"):
                if tool_name == "bash":
                    # 显示命令执行结果
                    stdout = result.get("stdout", "").strip()
                    stderr = result.get("stderr", "").strip()
                    exit_code = result.get("exit_code", 0)
                    
                    print(f"✅ 命令执行完成，退出码: {exit_code}")
                    
                    # 显示标准输出（最多 10 行）
                    if stdout:
                        stdout_lines = stdout.split('\n')
                        if len(stdout_lines) <= 10:
                            print("输出:")
                            for line in stdout_lines:
                                print(f"  {line}")
                        else:
                            # 输出太长，只显示前 10 行
                            print("输出 (前10行):")
                            for line in stdout_lines[:10]:
                                print(f"  {line}")
                            print(f"  ... 还有 {len(stdout_lines) - 10} 行")
                    
                    # 显示错误输出（如果有）
                    if stderr:
                        print(f"错误输出: {stderr[:200]}")
                        
                elif tool_name == "list_files":
                    # 显示文件列表摘要
                    items = result.get("items", [])
                    print(f"✅ 找到 {len(items)} 个项目")
                    
                elif tool_name == "read_file":
                    # 显示文件读取摘要
                    content = result.get("content", "")
                    print(f"✅ 读取文件成功，内容长度: {len(content)} 字符")
                    
            else:
                # 工具执行失败
                print(f"❌ 工具执行失败: {result.get('error', '未知错误')}")
        
        return results
    
    def run(self):
        """运行聊天循环
        
        主要的聊天循环，现在支持命令执行。
        """
        # 显示欢迎信息和使用提示
        print("🤖 命令执行助手 (使用 Ctrl+C 退出)")
        print("💡 提示：你可以说'运行命令 xxx'或'执行 ls'等来执行 shell 命令")
        print("⚠️  注意：出于安全考虑，某些危险命令被禁止执行")
        print("-" * 50)
        
        if self.verbose:
            print("[日志] 开始聊天会话")
        
        try:
            while True:
                # 获取用户输入
                user_input = self.get_user_input()
                
                # 处理退出条件
                if not user_input or user_input.lower() in ['exit', 'quit', '退出']:
                    if self.verbose:
                        print("[日志] 用户请求退出")
                    break
                
                if self.verbose:
                    print(f"[日志] 收到用户输入: {user_input[:50]}...")
                
                # 添加到对话历史
                self.conversation.append({
                    "role": "user",
                    "content": user_input
                })
                
                try:
                    # 调用 Claude API
                    response = self.run_inference(self.conversation)
                    
                    # 处理响应
                    assistant_message = ""
                    tool_calls = []
                    
                    for content in response.content:
                        if content.type == "text":
                            assistant_message = content.text
                        elif content.type == "tool_use":
                            tool_calls.append(content)
                    
                    # 处理工具调用（如果有）
                    if tool_calls:
                        # 首先显示文本消息（如果有的话）
                        if assistant_message:
                            print(f"🤖 Claude: {assistant_message}")
                            print()
                        
                        # 执行工具调用
                        tool_results = self.handle_tool_calls(tool_calls)
                        
                        # 将 Claude 的响应添加到对话历史
                        self.conversation.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        
                        # 将工具结果发送回 Claude
                        self.conversation.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    **tool_result
                                }
                                for tool_result in tool_results
                            ]
                        })
                        
                        # 获取最终响应
                        final_response = self.run_inference(self.conversation)
                        
                        # 提取并显示最终消息
                        final_message = ""
                        for content in final_response.content:
                            if content.type == "text":
                                final_message = content.text
                                break
                        
                        print(f"🤖 Claude: {final_message}")
                        print()
                        
                        # 更新对话历史
                        self.conversation.append({
                            "role": "assistant",
                            "content": final_response.content
                        })
                        
                    else:
                        # 没有工具调用，直接显示响应
                        print(f"🤖 Claude: {assistant_message}")
                        print()
                        
                        # 添加到对话历史
                        self.conversation.append({
                            "role": "assistant",
                            "content": response.content
                        })
                    
                except Exception as e:
                    print(f"❌ 错误: {str(e)}")
                    if self.verbose:
                        import traceback
                        traceback.print_exc()
                    
        except KeyboardInterrupt:
            print("\n👋 再见！")
        finally:
            if self.verbose:
                print("[日志] 聊天会话结束")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="命令执行助手")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="启用详细日志记录")
    
    args = parser.parse_args()
    
    # 检查 API 密钥
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY 环境变量")
        print("请运行: export ANTHROPIC_API_KEY='你的-api-密钥'")
        sys.exit(1)
    
    # 创建并运行助手
    agent = BashAgent(verbose=args.verbose)
    agent.run()


if __name__ == "__main__":
    main()