import os

def simple_rag_demo():
    print("\n" + "="*40)
    print("🚀 欢迎来到 RAG 演示实验室！")
    print("="*40)
    
    # 1. 模拟知识库
    knowledge_base = [
        "Python 是一种强大的编程语言。",
        "RAG 技术（检索增强生成）可以提高 AI 的准确性。",
        "今天的天气非常适合写代码。",
        "AI 技术正在改变世界。"
    ]
    
    # 2. 用户问题
    user_query = "RAG 技术有什么作用？"
    print(f"🔍 用户提问: {user_query}")
    
    # 3. 模拟检索过程
    print("🔍 正在检索知识库...")
    retrieved = [line for line in knowledge_base if "RAG" in line]
    
    if not retrieved:
        print("❌ 未找到相关信息。")
        return

    # 4. 模拟生成回答
    print(f"✅ 检索成功！找到内容: {retrieved}")
    print("🤖 AI 正在思考并回答...")
    
    print(f"\n📢 AI 最终回答: 基于检索到的信息，RAG 技术可以提高 AI 的准确性。")
    print("="*40 + "\n")

if __name__ == "__main__":
    simple_rag_demo()
