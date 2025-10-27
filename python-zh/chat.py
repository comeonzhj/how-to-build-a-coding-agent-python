#!/usr/bin/env python3
"""
基础聊天机器人 - 与 Claude 对话
这是构建编程助手的第一个版本

这个程序实现了一个简单的 AI 聊天机器人，可以与 Claude 进行对话。
它展示了如何使用 Anthropic API 进行基本的对话交互。

主要功能：
- 与 Claude API 建立连接
- 处理用户输入和 AI 响应
- 维护对话历史
- 支持详细日志模式

使用方法：
1. 设置环境变量：export ANTHROPIC_API_KEY='你的-api-密钥'
2. 运行程序：python chat.py
3. 输入消息与 Claude 对话
4. 输入 'exit'、'quit' 或 '退出' 结束对话

添加 --verbose 参数可以查看详细的运行日志：
python chat.py --verbose
"""

# 导入必要的库
# argparse: 用于解析命令行参数
import argparse
# os: 用于访问环境变量和操作系统功能
import os
# sys: 用于系统相关的操作，如退出程序
import sys
# typing: 提供类型提示，让代码更清晰
from typing import List, Dict, Any
# Anthropic: Anthropic 官方 API 客户端库
from anthropic import Anthropic
# dotenv: 用于加载 .env 文件中的环境变量
from dotenv import load_dotenv

# 加载环境变量
# 这会自动加载当前目录下的 .env 文件（如果存在）
# 让你可以在文件中设置环境变量，而不必每次都导出
load_dotenv()

class ChatAgent:
    """基础聊天助手类
    
    这个类封装了与 Claude 对话的所有功能。
    它处理了 API 连接、消息发送和接收、对话历史维护等。
    """
    
    def __init__(self, verbose: bool = False):
        """初始化聊天助手
        
        参数:
            verbose (bool): 是否启用详细日志模式。如果为 True，
                          会输出更多调试信息，帮助了解程序运行状态
        """
        self.verbose = verbose  # 保存详细模式设置
        
        # 创建 Anthropic 客户端
        # 从环境变量中获取 API 密钥
        # 如果密钥不存在，os.getenv() 会返回 None
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # 初始化对话历史列表
        # 这个列表会保存整个对话过程中的所有消息
        # 每个消息是一个字典，包含 role（角色）和 content（内容）
        self.conversation = []
        
        # 如果启用了详细模式，输出初始化信息
        if self.verbose:
            print("[日志] 聊天助手已初始化")
            # 检查 API 密钥是否设置，但不显示密钥本身（安全考虑）
            print(f"[日志] API密钥: {'已设置' if os.getenv('ANTHROPIC_API_KEY') else '未设置'}")
    
    def get_user_input(self) -> str:
        """获取用户输入
        
        从命令行读取用户输入。处理 Ctrl+C 和 Ctrl+D 等中断信号。
        
        返回:
            str: 用户输入的文本。如果用户中断输入，返回空字符串
        """
        try:
            # 显示提示符并等待用户输入
            return input("你: ")
        except (EOFError, KeyboardInterrupt):
            # 处理输入结束（Ctrl+D）或键盘中断（Ctrl+C）
            return ""
    
    def run_inference(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行推理，调用 Claude API
        
        这个方法负责与 Claude API 进行通信。
        它发送对话历史并获取 AI 的响应。
        
        参数:
            conversation: 对话历史列表，每个元素是一个消息字典
            
        返回:
            Dict[str, Any]: API 响应对象
            
        异常:
            如果 API 调用失败，会抛出异常
        """
        # 如果启用了详细模式，输出调用信息
        if self.verbose:
            print(f"[日志] 正在调用 Claude API，对话长度: {len(conversation)}")
        
        try:
            # 调用 Claude API
            # model: 使用的具体模型版本
            # max_tokens: 响应的最大令牌数（控制响应长度）
            # messages: 对话历史
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",  # Claude 3 Sonnet 模型
                max_tokens=1024,  # 最多生成 1024 个令牌
                messages=conversation  # 发送整个对话历史
            )
            
            # 如果启用了详细模式，输出成功信息
            if self.verbose:
                print(f"[日志] API 调用成功，收到响应")
            
            return response
            
        except Exception as e:
            # 如果 API 调用失败，输出错误信息
            if self.verbose:
                print(f"[日志] API 调用失败: {str(e)}")
            # 重新抛出异常，让上层处理
            raise e
    
    def run(self):
        """运行聊天循环
        
        这是主要的聊天循环方法。
        它持续获取用户输入，调用 API，显示响应，直到用户选择退出。
        """
        # 显示欢迎信息
        print("🤖 与 Claude 聊天 (使用 Ctrl+C 退出)")
        print("-" * 50)
        
        if self.verbose:
            print("[日志] 开始聊天会话")
        
        try:
            # 主循环
            while True:
                # 获取用户输入
                user_input = self.get_user_input()
                
                # 处理空输入或退出命令
                # 如果用户直接按回车，或输入退出命令，就结束循环
                if not user_input or user_input.lower() in ['exit', 'quit', '退出']:
                    if self.verbose:
                        print("[日志] 用户请求退出")
                    break
                
                # 输出用户输入（用于调试）
                if self.verbose:
                    # 只显示前50个字符，避免日志太长
                    print(f"[日志] 收到用户输入: {user_input[:50]}...")
                
                # 将用户消息添加到对话历史
                # role="user" 表示这是用户发送的消息
                self.conversation.append({
                    "role": "user",
                    "content": user_input
                })
                
                try:
                    # 调用 Claude API 获取响应
                    response = self.run_inference(self.conversation)
                    
                    # 从响应中提取文本内容
                    # Claude 的响应可能包含多种类型的内容（文本、工具调用等）
                    assistant_message = ""
                    for content in response.content:
                        if content.type == "text":
                            # 找到第一个文本类型的内容
                            assistant_message = content.text
                            break
                    
                    # 显示 AI 响应
                    print(f"🤖 Claude: {assistant_message}")
                    print()  # 空行，让输出更清晰
                    
                    # 将 AI 响应添加到对话历史
                    # role="assistant" 表示这是 AI 助手的回复
                    self.conversation.append({
                        "role": "assistant",
                        "content": assistant_message
                    })
                    
                except Exception as e:
                    # 处理 API 调用错误
                    print(f"❌ 错误: {str(e)}")
                    if self.verbose:
                        # 如果启用了详细模式，打印完整的错误堆栈
                        import traceback
                        traceback.print_exc()
                    
        except KeyboardInterrupt:
            # 处理 Ctrl+C 中断
            print("\n👋 再见！")
        finally:
            # 无论正常退出还是异常退出，都会执行这里
            if self.verbose:
                print("[日志] 聊天会话结束")


def main():
    """主函数
    
    程序的入口点。
    负责解析命令行参数，创建聊天助手实例，并启动聊天循环。
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="基础聊天机器人")
    
    # 添加 --verbose 参数
    # action="store_true" 表示如果指定了这个参数，值为 True，否则为 False
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="启用详细日志记录")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 检查 API 密钥是否设置
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY 环境变量")
        print("请运行: export ANTHROPIC_API_KEY='你的-api-密钥'")
        # 退出程序，返回错误码 1
        sys.exit(1)
    
    # 创建聊天助手实例
    agent = ChatAgent(verbose=args.verbose)
    
    # 启动聊天循环
    agent.run()


# 这个判断确保只有在直接运行这个文件时才会执行 main()
# 如果文件被其他程序导入，不会自动执行
if __name__ == "__main__":
    main()