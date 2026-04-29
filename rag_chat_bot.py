import os
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from config import load_config, get_legacy_config
from skill_manager import SkillManager


# ====================================================================
#  加载配置
# ====================================================================
_config = load_config()
CONFIG = get_legacy_config(_config)

SKILLS_DIR = _config["paths"]["skills_dir"]
SKILL_LEARNING_ENABLED = _config["skill_learning"]["enabled"]
SKILL_MIN_RATING = _config["skill_learning"]["min_rating"]
SKILL_AUTO_SAVE = _config["skill_learning"]["auto_save"]

# 自定义系统提示
_custom_prompt = _config["chat"].get("system_prompt", "")
SYSTEM_PROMPT = _custom_prompt if _custom_prompt else """你是一个专业的知识库助手。你的职责是根据提供的【参考上下文】准确回答用户问题。

## 规则
1. **优先使用上下文**：如果上下文中有相关信息，必须基于上下文回答。
2. **诚实回应**：如果上下文中没有答案，请明确说"根据现有知识库，我无法回答这个问题"，不要编造。
3. **引用来源**：在回答末尾标注信息来源文件名。
4. **使用中文**：始终使用中文回答。
5. **简洁清晰**：回答要结构化、有条理，使用列表或分点。
"""


# ====================================================================
#  核心函数
# ====================================================================
def load_vectorstore(config):
    """加载向量库"""
    embeddings = OllamaEmbeddings(model=config["embedding_model"])
    vectorstore = Chroma(
        persist_directory=config["persist_dir"],
        embedding_function=embeddings,
    )
    return vectorstore


def format_docs_with_sources(docs):
    """格式化文档块，附带来源标注"""
    formatted = []
    sources = set()
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source_file", "未知来源")
        sources.add(source)
        formatted.append(f"[来源: {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted), list(sources)


def build_chain(vectorstore, config):
    """构建带记忆的 RAG 链"""
    llm = ChatOllama(
        model=config["chat_model"],
        temperature=config["temperature"],
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", """
【参考上下文】:
{context}

【用户问题】:
{question}

请根据以上上下文和规则回答。在末尾标注来源文件。
        """),
    ])

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": config["retrieval_k"]}
    )

    def rag_chain(question, chat_history):
        # 1. 检索相关文档
        docs = retriever.invoke(question)
        context, sources = format_docs_with_sources(docs)

        # 2. 构建消息
        messages = prompt.format_messages(
            chat_history=chat_history,
            context=context,
            question=question,
        )

        # 3. 调用 LLM
        response = llm.invoke(messages)

        return response.content, sources, docs

    return rag_chain


# ====================================================================
#  交互循环
# ====================================================================
def run_rag_chatbot():
    config = CONFIG

    print("\n" + "=" * 60)
    print("🤖 RAG 智能助手 v3.0")
    print("=" * 60)
    print(f"📂 知识库路径: {config['persist_dir']}")
    print(f"🧠 嵌入模型:   {config['embedding_model']}")
    print(f"💬 Chat 模型:  {config['chat_model']}")
    print(f"🔍 检索数量:   k={config['retrieval_k']}")
    print(f"📜 记忆轮数:   {config['max_history']} 轮")
    if SKILL_LEARNING_ENABLED:
        print(f"🧠 闭环学习:   ✅ 已启用 (最低评分: {SKILL_MIN_RATING})")
    print("=" * 60)

    # 加载向量库
    print("\n⏳ 正在加载向量库...")
    if not os.path.exists(config["persist_dir"]):
        print(f"❌ 错误: 找不到数据库目录 {config['persist_dir']}")
        print("💡 请先运行: python run_rag.py build")
        return

    try:
        vectorstore = load_vectorstore(config)
        print("✅ 知识库加载成功！")
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return

    # 构建链
    rag_chain = build_chain(vectorstore, config)

    # Skill 管理器
    skill_mgr = SkillManager(skills_dir=SKILLS_DIR) if SKILL_LEARNING_ENABLED else None

    # 对话历史
    chat_history = []

    print("\n✨ 您可以开始提问了！")
    print("   输入 'exit' 或 '退出' → 退出")
    print("   输入 'clear' 或 '清空' → 清空对话记忆")
    print("   输入 'sources' 或 '来源' → 显示上轮来源")
    if SKILL_LEARNING_ENABLED:
        print("   输入 'save' 或 '保存' → 将上轮问答保存为 Skill")
    print("-" * 60 + "\n")

    last_sources = []
    last_question = ""
    last_answer = ""

    while True:
        user_query = input("👤 你: ").strip()

        if not user_query:
            continue

        # 退出
        if user_query.lower() in ["exit", "quit", "退出"]:
            print("\n👋 再见！下次再聊！")
            break

        # 清空记忆
        if user_query.lower() in ["clear", "清空", "reset"]:
            chat_history = []
            print("🧹 对话记忆已清空！\n")
            continue

        # 显示来源
        if user_query.lower() in ["sources", "来源"]:
            if last_sources:
                print(f"\n📄 上轮回答来源: {', '.join(last_sources)}")
            else:
                print("\n📄 暂无来源信息")
            print()
            continue

        # 保存为 Skill
        if user_query.lower() in ["save", "保存"]:
            if skill_mgr and last_question and last_answer:
                try:
                    rating_input = input("⭐ 评分 (1-5, 默认5): ").strip()
                    rating = int(rating_input) if rating_input.isdigit() else 5
                    rating = max(1, min(5, rating))
                except (ValueError, EOFError):
                    rating = 5

                skill_mgr.save_skill(
                    question=last_question,
                    answer=last_answer,
                    sources=last_sources,
                    rating=rating,
                )
                print(f"✅ 已保存为 Skill (评分: {rating}⭐)\n")
            else:
                print("⚠️ 没有可保存的问答（需要先提问）\n")
            continue

        # --- 主查询流程 ---
        print("🔍 正在检索知识库...")
        try:
            response, sources, docs = rag_chain(user_query, chat_history)

            # 更新对话历史
            chat_history.append(HumanMessage(content=user_query))
            chat_history.append(AIMessage(content=response))

            # 控制历史长度
            if len(chat_history) > config["max_history"] * 2:
                chat_history = chat_history[-(config["max_history"] * 2):]

            last_sources = sources
            last_question = user_query
            last_answer = response

            # 显示回答
            print(f"\n🤖 助手: {response}")

            # 显示来源摘要
            if sources:
                print(f"\n📄 来源: {', '.join(sources)}")

            # 显示检索块数
            print(f"🔍 参考了 {len(docs)} 个知识片段")

            # 闭环学习：自动保存（如果启用）
            if skill_mgr and SKILL_AUTO_SAVE:
                skill_mgr.save_skill(
                    question=user_query,
                    answer=response,
                    sources=sources,
                    rating=5,  # 自动保存默认 5 星
                    tags=["auto-save"],
                )
                print("🧠 [自动保存为 Skill]")

            print("\n" + "-" * 40 + "\n")

        except Exception as e:
            print(f"❌ 发生错误: {e}\n")


if __name__ == "__main__":
    run_rag_chatbot()
