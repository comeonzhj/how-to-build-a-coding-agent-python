#!/usr/bin/env python3
"""
基础聊天机器人 - 与 Claude 对话
这是构建编程助手的第一个版本
"""

import argparse
import os
import sys
from typing import List, Dict, Any
from anthropic import Anthropic
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class ChatAgent:
    """基础聊天助手"""
    
    def __init__(self, verbose: bool = False):
        """初始化聊天助手"""
        self.verbose = verbose
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.conversation = []
        
        if self.verbose:
            print("[日志] 聊天助手已初始化")
            print(f"[日志] API密钥: {'已设置' if os.getenv('ANTHROPIC_API_KEY') else '未设置'}")
    
    def get_user_input(self) -> str:
        """获取用户输入"""
        try:
            return input("你: ")
        except (EOFError, KeyboardInterrupt):
            return ""
    
    def run_inference(self, conversation: List[Dict[str, Any]]) -> Dict[str, Any]:
        """运行推理，调用 Claude API"""
        if self.verbose:
            print(f"[日志] 正在调用 Claude API，对话长度: {len(conversation)}")
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1024,
                messages=conversation
            )
            
            if self.verbose:
                print(f"[日志] API 调用成功，收到响应")
            
            return response
        except Exception as e:
            if self.verbose:
                print(f"[日志] API 调用失败: {str(e)}")
            raise e
    
    def run(self):
        """运行聊天循环"""
        print("🤖 与 Claude 聊天 (使用 Ctrl+C 退出)")
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
                    
                    # 提取响应内容
                    assistant_message = ""
                    for content in response.content:
                        if content.type == "text":
                            assistant_message = content.text
                            break
                    
                    # 显示响应
                    print(f"🤖 Claude: {assistant_message}")
                    print()
                    
                    # 添加到对话历史
                    self.conversation.append({
                        "role": "assistant",
                        "content": assistant_message
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
    parser = argparse.ArgumentParser(description="基础聊天机器人")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="启用详细日志记录")
    
    args = parser.parse_args()
    
    # 检查 API 密钥
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY 环境变量")
        print("请运行: export ANTHROPIC_API_KEY='你的-api-密钥'")
        sys.exit(1)
    
    # 创建并运行聊天助手
    agent = ChatAgent(verbose=args.verbose)
    agent.run()


if __name__ == "__main__":
    main()