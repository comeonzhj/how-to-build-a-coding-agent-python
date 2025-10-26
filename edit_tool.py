#!/usr/bin/env python3
"""
文件编辑助手 - 添加文件编辑功能
这是构建编程助手的第五个版本
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools = {}
    
    def register(self, name: str, description: str, input_schema: Dict, function):
        """注册工具"""
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
    """读取文件内容"""
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
    """列出文件和目录"""
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
    """执行 shell 命令"""
    try:
        # 安全检查 - 禁止某些危险命令
        dangerous_commands = [
            "rm -rf /", "sudo", "mkfs", "fdisk", "dd if=", 
            ":(){ :|:& };:", "wget", "curl"
        ]
        
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return {
                    "success": False,
                    "error": f"检测到潜在危险命令: {dangerous}",
                    "stdout": "",
                    "stderr": "命令被拒绝执行",
                    "exit_code": 1
                }
        
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        # 构建响应
        response = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "command": command
        }
        
        return response
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"命令执行超时（{timeout}秒）",
            "stdout": "",
            "stderr": "命令执行超时",
            "exit_code": 1
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"执行命令时出错: {str(e)}",
            "stdout": "",
            "stderr": str(e),
            "exit_code": 1
        }


def edit_file(path: str, content: str, create_if_not_exists: bool = True) -> Dict[str, Any]:
    """编辑或创建文件"""
    try:
        file_path = Path(path)
        
        # 检查文件是否存在
        if not file_path.exists():
            if not create_if_not_exists:
                return {
                    "success": False,
                    "error": f"文件不存在且不允许创建: {path}"
                }
            
            # 创建文件（包括必要的目录）
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.verbose:
                print(f"[日志] 创建新文件: {path}")
        
        # 检查是否是文件（不是目录）
        if file_path.exists() and not file_path.is_file():
            return {
                "success": False,
                "error": f"路径不是文件: {path}"
            }
        
        # 写入文件内容
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 获取文件统计信息
            file_stats = file_path.stat()
            
            return {
                "success": True,
                "path": str(file_path.absolute()),
                "size": file_stats.st_size,
                "created": not file_path.exists() if create_if_not_exists else False,
                "message": "文件已成功保存"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"写入文件时出错: {str(e)}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"编辑文件时出错: {str(e)}"
        }


def str_replace_file(path: str, old: str, new: str, replace_all: bool = False) -> Dict[str, Any]:
    """在文件中替换字符串"""
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
        except UnicodeDecodeError:
            # 如果 UTF-8 失败，尝试其他编码
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # 执行替换
        if replace_all:
            new_content = content.replace(old, new)
            replacements = content.count(old)
        else:
            new_content = content.replace(old, new, 1)
            replacements = 1 if old in content else 0
        
        if replacements == 0:
            return {
                "success": False,
                "error": f"未找到要替换的字符串: '{old}'",
                "replacements": 0
            }
        
        # 写回文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "path": str(file_path.absolute()),
                "replacements": replacements,
                "old_length": len(old),
                "new_length": len(new),
                "message": f"成功替换 {replacements} 处"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"写入文件时出错: {str(e)}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"替换字符串时出错: {str(e)}"
        }


class EditToolAgent:
    """文件编辑助手"""
    
    def __init__(self, verbose: bool = False):
        """初始化助手"""
        self.verbose = verbose
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.conversation = []
        self.registry = ToolRegistry()
        
        # 注册工具
        self._register_tools()
        
        if self.verbose:
            print("[日志] 文件编辑助手已初始化")
    
    def _register_tools(self):
        """注册所有工具"""
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
        
        # 注册 bash 工具
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
                        "default": 30
                    }
                },
                "required": ["command"]
            },
            function=bash
        )
        
        # 注册 edit_file 工具
        self.registry.register(
            name="edit_file",
            description="编辑或创建文件",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要编辑的文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "新的文件内容"
                    },
                    "create_if_not_exists": {
                        "type": "boolean",
                        "description": "如果文件不存在是否创建",
                        "default": True
                    }
                },
                "required": ["path", "content"]
            },
            function=edit_file
        )
        
        # 注册 str_replace_file 工具
        self.registry.register(
            name="str_replace_file",
            description="在文件中替换字符串",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要编辑的文件路径"
                    },
                    "old": {
                        "type": "string",
                        "description": "要替换的字符串"
                    },
                    "new": {
                        "type": "string",
                        "description": "新字符串"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "是否替换所有匹配项",
                        "default": False
                    }
                },
                "required": ["path", "old", "new"]
            },
            function=str_replace_file
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
        """执行工具"""
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
        """处理工具调用"""
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
            
            # 显示结果摘要
            if result.get("success"):
                if tool_name == "edit_file":
                    path = result.get("path", "")
                    size = result.get("size", 0)
                    created = result.get("created", False)
                    message = result.get("message", "")
                    
                    print(f"✅ 文件编辑成功")
                    print(f"📁 文件路径: {path}")
                    print(f"📊 文件大小: {size} 字节")
                    if created:
                        print("🆕 创建了新文件")
                    print(f"💬 {message}")
                    
                elif tool_name == "str_replace_file":
                    path = result.get("path", "")
                    replacements = result.get("replacements", 0)
                    message = result.get("message", "")
                    
                    print(f"✅ 字符串替换成功")
                    print(f"📁 文件路径: {path}")
                    print(f"🔢 替换次数: {replacements}")
                    print(f"💬 {message}")
                    
                elif tool_name == "bash":
                    exit_code = result.get("exit_code", 0)
                    print(f"✅ 命令执行完成，退出码: {exit_code}")
                    
                elif tool_name == "list_files":
                    items = result.get("items", [])
                    print(f"✅ 找到 {len(items)} 个项目")
                    
                elif tool_name == "read_file":
                    content = result.get("content", "")
                    print(f"✅ 读取文件成功，内容长度: {len(content)} 字符")
                    
            else:
                print(f"❌ 工具执行失败: {result.get('error', '未知错误')}")
        
        return results
    
    def run(self):
        """运行聊天循环"""
        print("🤖 文件编辑助手 (使用 Ctrl+C 退出)")
        print("💡 提示：你可以说'创建文件 xxx'、'编辑文件 xxx'或'替换文件中的 xxx'")
        print("-" * 50)
        
        if self.verbose:
            print("[日志] 开始聊天会话")
        
        try:
            while True:
                # 获取用户输入
                user_input = self.get_user_input()
                
                # 处理空输入或退出
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
                    
                    # 如果有工具调用，执行它们
                    if tool_calls:
                        # 先显示文本消息（如果有）
                        if assistant_message:
                            print(f"🤖 Claude: {assistant_message}")
                            print()
                        
                        # 执行工具调用
                        tool_results = self.handle_tool_calls(tool_calls)
                        
                        # 将工具结果发送回 Claude
                        self.conversation.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        
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
                        
                        # 显示最终响应
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
    parser = argparse.ArgumentParser(description="文件编辑助手")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="启用详细日志记录")
    
    args = parser.parse_args()
    
    # 检查 API 密钥
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY 环境变量")
        print("请运行: export ANTHROPIC_API_KEY='你的-api-密钥'")
        sys.exit(1)
    
    # 创建并运行助手
    agent = EditToolAgent(verbose=args.verbose)
    agent.run()


if __name__ == "__main__":
    main()