#!/usr/bin/env python3
"""
文件读取助手 - 添加文件读取功能
这是构建编程助手的第二个版本

这个程序在基础聊天功能上添加了文件读取能力。
它引入了"工具"的概念，让 Claude 能够读取用户电脑上的文件内容。

主要功能：
- 与 Claude API 进行对话
- 注册和使用工具（文件读取）
- 处理工具调用和结果返回
- 支持错误处理和安全检查

新的概念：
- 工具注册表（ToolRegistry）：管理和注册各种工具
- 工具调用：Claude 可以请求使用特定的工具
- 工具结果：将工具执行的结果返回给 Claude

使用方法：
1. 设置 API 密钥：export ANTHROPIC_API_KEY='你的-api-密钥'
2. 运行程序：python read_file.py
3. 尝试说："读取文件 fizzbuzz.js" 或 "查看 riddle.txt 的内容"

工具系统的工作原理：
1. 用户发送消息
2. Claude 分析问题，决定是否需要使用工具
3. 如果需要工具，Claude 会发送工具调用请求
4. 程序执行相应的工具函数
5. 工具结果返回给 Claude
6. Claude 根据工具结果给出最终回答
"""

# 导入必要的库
import argparse  # 命令行参数解析
import json      # JSON 数据处理，用于工具结果的序列化
import os        # 操作系统功能，如环境变量
import sys       # 系统相关操作
from pathlib import Path  # 现代文件路径处理
from typing import List, Dict, Any, Optional  # 类型提示
from anthropic import Anthropic  # Anthropic API 客户端
from dotenv import load_dotenv   # 环境变量加载

# 加载环境变量（.env 文件）
load_dotenv()

class ToolRegistry:
    """工具注册表类
    
    这个类负责管理所有可用的工具。
    工具是可以被 Claude 调用的函数，用于执行特定的任务。
    
    为什么要使用工具注册表？
    - 统一管理所有工具
    - 方便添加新工具
    - 提供工具的标准化接口
    - 便于工具的分类和查找
    """
    
    def __init__(self):
        """初始化工具注册表
        
        创建一个空字典来存储工具。
        字典的键是工具名称，值是工具的定义信息。
        """
        # 工具字典：{工具名称: 工具定义}
        self.tools = {}
    
    def register(self, name: str, description: str, input_schema: Dict, function):
        """注册新工具
        
        参数:
            name: 工具名称（必须是唯一的）
            description: 工具的描述，帮助 Claude 理解工具的用途
            input_schema: 输入参数的模式定义（JSON Schema）
            function: 实际执行工具功能的函数
        
        工具定义包含：
        - name: 工具名称
        - description: 工具描述
        - input_schema: 参数模式（告诉 Claude 如何调用这个工具）
        - function: 执行函数
        """
        self.tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "function": function
        }
    
    def get(self, name: str):
        """获取指定名称的工具
        
        参数:
            name: 工具名称
            
        返回:
            工具定义字典，如果工具不存在返回 None
        """
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Dict]:
        """获取所有工具的定义（用于 API 调用）
        
        Anthropic API 需要知道有哪些工具可用。
        这个方法返回所有工具的定义，但不包括实际的执行函数
        （因为函数不能序列化为 JSON）。
        
        返回:
            工具定义列表，每个元素包含 name、description 和 input_schema
        """
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            for tool in self.tools.values()
        ]


def read_file(path: str) -> Dict[str, Any]:
    """读取文件内容的工具函数
    
    这是实际的文件读取工具实现。
    它接收文件路径作为参数，返回文件内容或错误信息。
    
    参数:
        path: 要读取的文件路径
        
    返回:
        字典，包含以下字段：
        - success: 是否成功读取
        - content: 文件内容（如果成功）
        - path: 文件的绝对路径（如果成功）
        - error: 错误信息（如果失败）
        - warning: 警告信息（如果有）
    
    错误处理：
    - 文件不存在
    - 路径不是文件（可能是目录）
    - 文件读取权限问题
    - 编码问题（自动尝试不同编码）
    """
    try:
        # 使用 Path 对象处理文件路径
        # Path 是 Python 3.4+ 引入的现代路径处理类
        file_path = Path(path)
        
        # 检查文件是否存在
        if not file_path.exists():
            # 如果文件不存在，返回错误信息
            return {
                "success": False,
                "error": f"文件不存在: {path}"
            }
        
        # 检查路径是否是文件（而不是目录）
        if not file_path.is_file():
            return {
                "success": False,
                "error": f"路径不是文件: {path}"
            }
        
        # 尝试读取文件内容
        try:
            # 首先尝试使用 UTF-8 编码读取
            # UTF-8 是现代文本文件的标准编码
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 成功读取，返回内容和文件信息
            return {
                "success": True,
                "content": content,  # 文件内容
                "path": str(file_path.absolute())  # 绝对路径
            }
            
        except UnicodeDecodeError:
            # 如果 UTF-8 解码失败，可能是其他编码
            # 尝试使用 latin-1 编码（可以解码任何字节序列）
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            
            # 返回内容，并添加编码警告
            return {
                "success": True,
                "content": content,
                "path": str(file_path.absolute()),
                "warning": "使用 latin-1 编码读取文件"
            }
            
    except Exception as e:
        # 捕获所有其他异常
        return {
            "success": False,
            "error": f"读取文件时出错: {str(e)}"
        }


class FileReadAgent:
    """文件读取助手类
    
    这是主要的助手类，负责协调对话和工具使用。
    它比基础聊天机器人多了一个文件读取工具。
    """
    
    def __init__(self, verbose: bool = False):
        """初始化文件读取助手
        
        参数:
            verbose: 是否启用详细日志模式
        """
        self.verbose = verbose  # 详细模式设置
        
        # 创建 Anthropic API 客户端
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # 初始化对话历史
        self.conversation = []
        
        # 创建工具注册表
        self.registry = ToolRegistry()
        
        # 注册所有可用的工具
        self._register_tools()
        
        if self.verbose:
            print("[日志] 文件读取助手已初始化")
    
    def _register_tools(self):
        """注册所有工具
        
        这个方法定义了助手可以使用的所有工具。
        每个工具都有名称、描述、输入模式和执行函数。
        """
        # 注册 read_file 工具
        self.registry.register(
            name="read_file",  # 工具名称（Claude 会用到这个名称）
            description="读取文件内容",  # 工具描述
            input_schema={
                "type": "object",  # JSON Schema 类型
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径"
                    }
                },
                "required": ["path"]  # 必需的参数
            },
            function=read_file  # 实际执行的函数
        )
        
        if self.verbose:
            # 输出已注册的工具数量
            print(f"[日志] 已注册 {len(self.registry.tools)} 个工具")
    
    def get_user_input(self) -> str:
        """获取用户输入
        
        与基础版本相同，从命令行读取用户输入。
        """
        try:
            return input("你: ")
        except (EOFError, KeyboardInterrupt):
            return ""
    
    def execute_tool(self, tool_name: str, tool_input: Dict) -> Dict[str, Any]:
        """执行指定的工具
        
        参数:
            tool_name: 要执行的工具名称
            tool_input: 工具的输入参数
            
        返回:
            工具执行的结果
        """
        # 从注册表中获取工具定义
        tool = self.registry.get(tool_name)
        if not tool:
            # 工具不存在，返回错误
            return {
                "success": False,
                "error": f"未知工具: {tool_name}"
            }
        
        try:
            # 如果启用了详细模式，输出执行信息
            if self.verbose:
                print(f"[日志] 执行工具: {tool_name}, 输入: {tool_input}")
            
            # 调用工具函数，传入参数
            # **tool_input 将字典解包为关键字参数
            result = tool["function"](**tool_input)
            
            # 如果启用了详细模式，输出成功信息
            if self.verbose:
                print(f"[日志] 工具执行成功: {tool_name}")
            
            return result
            
        except Exception as e:
            # 工具执行出错
            error_msg = f"工具执行失败: {str(e)}"
            if self.verbose:
                print(f"[日志] {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def run_inference(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行推理，调用 Claude API
        
        这个方法与基础版本类似，但增加了一个重要参数：tools。
        通过提供可用工具列表，Claude 可以决定何时使用工具。
        
        参数:
            conversation: 对话历史
            
        返回:
            API 响应对象
        """
        if self.verbose:
            print(f"[日志] 正在调用 Claude API，对话长度: {len(conversation)}")
        
        try:
            # 调用 Claude API，包含工具定义
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=conversation,
                tools=self.registry.get_all_tools()  # 提供可用工具列表
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
        
        当 Claude 决定使用工具时，会发送工具调用请求。
        这个方法负责执行所有请求的工具，并返回结果。
        
        参数:
            tool_calls: Claude 请求的工具调用列表
            
        返回:
            工具结果列表，用于发送回 Claude
        """
        results = []
        
        # 遍历所有工具调用请求
        for tool_call in tool_calls:
            tool_name = tool_call.name  # 工具名称
            tool_input = tool_call.input  # 工具输入参数
            
            # 显示正在使用的工具
            print(f"🔧 使用工具: {tool_name}")
            
            # 执行工具
            result = self.execute_tool(tool_name, tool_input)
            
            # 构建工具结果
            # 每个工具结果需要包含 tool_call_id 和 content
            tool_result = {
                "tool_call_id": tool_call.id,  # 工具调用的唯一 ID
                "content": json.dumps(result)  # 将结果转为 JSON 字符串
            }
            
            results.append(tool_result)
            
            # 显示结果摘要（用户友好的输出）
            if result.get("success"):
                # 如果成功，显示内容预览
                if "content" in result:
                    # 只显示前100个字符，避免输出太长
                    content_preview = result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                    print(f"✅ 工具执行成功，内容预览: {content_preview}")
            else:
                # 如果失败，显示错误信息
                print(f"❌ 工具执行失败: {result.get('error', '未知错误')}")
        
        return results
    
    def run(self):
        """运行聊天循环
        
        主要的聊天循环，处理用户输入、API 调用和工具使用。
        与基础版本相比，这个版本需要处理工具调用的额外复杂性。
        """
        # 显示欢迎信息和提示
        print("🤖 文件读取助手 (使用 Ctrl+C 退出)")
        print("💡 提示：你可以说'读取文件 xxx'来读取文件")
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
                    assistant_message = ""  # AI 的文本回复
                    tool_calls = []  # 工具调用请求
                    
                    # Claude 的响应可能包含多种内容类型
                    for content in response.content:
                        if content.type == "text":
                            # 文本类型的响应
                            assistant_message = content.text
                        elif content.type == "tool_use":
                            # 工具调用请求
                            tool_calls.append(content)
                    
                    # 如果有工具调用，需要特殊处理
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
                        # 注意：这里使用特殊的格式发送工具结果
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
                        
                        # 获取 Claude 对工具结果的最终响应
                        final_response = self.run_inference(self.conversation)
                        
                        # 提取最终消息
                        final_message = ""
                        for content in final_response.content:
                            if content.type == "text":
                                final_message = content.text
                                break
                        
                        # 显示最终响应
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
    """主函数
    
    程序的入口点，处理命令行参数并启动助手。
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="文件读取助手")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="启用详细日志记录")
    
    args = parser.parse_args()
    
    # 检查 API 密钥
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY 环境变量")
        print("请运行: export ANTHROPIC_API_KEY='你的-api-密钥'")
        sys.exit(1)
    
    # 创建并运行助手
    agent = FileReadAgent(verbose=args.verbose)
    agent.run()


if __name__ == "__main__":
    main()