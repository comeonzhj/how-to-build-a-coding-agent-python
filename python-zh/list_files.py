#!/usr/bin/env python3
"""
文件浏览助手 - 添加文件列表功能
这是构建编程助手的第三个版本

这个程序在前一版本的基础上添加了文件浏览功能。
现在 Claude 不仅可以读取文件内容，还可以查看目录结构，
了解文件系统的组织方式。

新增功能：
- 列出目录中的文件和子目录
- 支持递归列出（查看子目录内容）
- 显示文件类型、大小等信息
- 按类型和名称排序

工具系统增强：
- 现在有多个工具：read_file 和 list_files
- Claude 可以根据需要选择合适的工具
- 工具之间可以协同工作（先列出文件，再读取具体内容）

为什么要添加文件浏览功能？
- 帮助用户了解目录结构
- 找到需要的文件
- 验证文件是否存在
- 了解项目组织结构

使用场景示例：
- "列出当前目录的所有文件"
- "查看项目结构"
- "找到所有的 Python 文件"
- "这个文件夹里有什么？"
"""

# 导入必要的库
import argparse  # 命令行参数解析
import json      # JSON 数据处理
import os        # 操作系统功能
import sys       # 系统相关操作
from pathlib import Path  # 现代文件路径处理
from typing import List, Dict, Any, Optional  # 类型提示
from anthropic import Anthropic  # Anthropic API 客户端
from dotenv import load_dotenv   # 环境变量加载

# 加载环境变量
load_dotenv()

class ToolRegistry:
    """工具注册表类
    
    与前一版本相同，管理所有可用工具。
    这个类提供了工具的标准化管理方式。
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
    """读取文件内容（与前一版本相同）
    
    这个工具保持不变，因为文件读取功能已经很好用了。
    """
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
    """列出文件和目录的工具函数
    
    这是新添加的工具，用于浏览文件系统。
    它可以列出指定目录中的所有文件和子目录。
    
    参数:
        path: 要列出的目录路径，默认为当前目录 "."
        recursive: 是否递归列出子目录内容，默认为 False
        
    返回:
        字典，包含以下字段：
        - success: 是否成功
        - items: 文件和目录列表（每个元素包含名称、类型、大小等信息）
        - path: 目录的绝对路径
        - total_count: 总项目数
        - directory_count: 子目录数量
        - file_count: 文件数量
        - error: 错误信息（如果失败）
    
    功能特点：
    - 支持绝对路径和相对路径
    - 自动排序（目录在前，文件在后；按名称排序）
    - 显示文件大小（字节）
    - 提供绝对路径信息
    - 递归和非递归两种模式
    """
    try:
        # 解析路径（支持相对路径和绝对路径）
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
            # 递归模式：列出所有子目录的内容
            # rglob("*") 会递归地匹配所有文件和目录
            for item in target_path.rglob("*"):
                # 计算相对路径（相对于目标目录）
                relative_path = str(item.relative_to(target_path))
                
                # 收集项目信息
                items.append({
                    "name": relative_path,  # 相对路径名称
                    "type": "directory" if item.is_dir() else "file",  # 类型
                    "size": item.stat().st_size if item.is_file() else 0,  # 文件大小
                    "absolute_path": str(item.absolute())  # 绝对路径
                })
        else:
            # 非递归模式：只列出当前目录
            # iterdir() 只列出直接子项
            for item in target_path.iterdir():
                items.append({
                    "name": item.name,  # 名称（不包含路径）
                    "type": "directory" if item.is_dir() else "file",  # 类型
                    "size": item.stat().st_size if item.is_file() else 0,  # 大小
                    "absolute_path": str(item.absolute())  # 绝对路径
                })
        
        # 按类型和名称排序
        # 这样目录会排在文件前面，同类项目按名称排序
        items.sort(key=lambda x: (x["type"], x["name"]))
        
        # 计算统计信息
        directory_count = sum(1 for item in items if item["type"] == "directory")
        file_count = sum(1 for item in items if item["type"] == "file")
        
        # 返回完整结果
        return {
            "success": True,
            "items": items,  # 项目列表
            "path": str(target_path.absolute()),  # 目录绝对路径
            "total_count": len(items),  # 总数量
            "directory_count": directory_count,  # 目录数量
            "file_count": file_count  # 文件数量
        }
        
    except Exception as e:
        # 错误处理
        return {
            "success": False,
            "error": f"列出文件时出错: {str(e)}"
        }


class FileExplorerAgent:
    """文件浏览助手类
    
    这是主要的助手类，现在支持两种工具：
    1. read_file - 读取文件内容
    2. list_files - 列出目录内容
    
    Claude 可以根据用户的问题选择合适的工具，
    或者组合使用多个工具来完成复杂任务。
    """
    
    def __init__(self, verbose: bool = False):
        """初始化文件浏览助手"""
        self.verbose = verbose
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.conversation = []
        self.registry = ToolRegistry()
        
        # 注册所有工具
        self._register_tools()
        
        if self.verbose:
            print("[日志] 文件浏览助手已初始化")
    
    def _register_tools(self):
        """注册所有可用工具"""
        
        # 注册 read_file 工具（已存在）
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
        
        # 注册 list_files 工具（新增）
        self.registry.register(
            name="list_files",
            description="列出目录中的文件和子目录",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要列出的目录路径（默认为当前目录）",
                        "default": "."  # 默认值是当前目录
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归列出子目录内容",
                        "default": False  # 默认不递归
                    }
                }
            },
            function=list_files
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
        
        这个方法现在需要处理两种不同类型的工具：
        1. list_files - 列出文件和目录
        2. read_file - 读取文件内容
        
        根据工具类型，显示不同的结果摘要。
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
                if tool_name == "list_files":
                    # 显示文件列表的摘要信息
                    items = result.get("items", [])
                    print(f"✅ 找到 {len(items)} 个项目")
                    print(f"📁 目录: {result.get('directory_count', 0)}")
                    print(f"📄 文件: {result.get('file_count', 0)}")
                    
                    # 显示前几个项目作为预览
                    if items:
                        print("前几个项目:")
                        for item in items[:5]:
                            # 根据类型选择图标
                            icon = "📁" if item["type"] == "directory" else "📄"
                            print(f"  {icon} {item['name']}")
                        
                        # 如果还有更多项目，显示省略信息
                        if len(items) > 5:
                            print(f"  ... 还有 {len(items) - 5} 个项目")
                    
                elif tool_name == "read_file":
                    # 显示文件读取的摘要信息
                    content = result.get("content", "")
                    print(f"✅ 读取文件成功，内容长度: {len(content)} 字符")
                    
            else:
                # 工具执行失败
                print(f"❌ 工具执行失败: {result.get('error', '未知错误')}")
        
        return results
    
    def run(self):
        """运行聊天循环
        
        主要的聊天循环，支持多工具调用。
        """
        # 显示欢迎信息和提示
        print("🤖 文件浏览助手 (使用 Ctrl+C 退出)")
        print("💡 提示：你可以说'列出文件'或'读取文件 xxx'来浏览文件系统")
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
    parser = argparse.ArgumentParser(description="文件浏览助手")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="启用详细日志记录")
    
    args = parser.parse_args()
    
    # 检查 API 密钥
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY 环境变量")
        print("请运行: export ANTHROPIC_API_KEY='你的-api-密钥'")
        sys.exit(1)
    
    # 创建并运行助手
    agent = FileExplorerAgent(verbose=args.verbose)
    agent.run()


if __name__ == "__main__":
    main()