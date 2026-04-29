#!/usr/bin/env python3
"""
RAG 管道一键管理脚本

用法:
  python run_rag.py ingest     # 导入文档
  python run_rag.py build      # 构建向量库 (先 ingest 再向量化)
  python run_rag.py chat       # 启动聊天机器人
  python run_rag.py rebuild    # 全量重建向量库 (清空旧数据)
  python run_rag.py test       # 运行管道测试
  python run_rag.py auto       # 启动自动监听 (自动检测新文件并重建向量库)
  python run_rag.py status     # 查看知识库状态
  python run_rag.py query "问题"  # 单次查询（非交互）
  python run_rag.py skills     # 列出所有已保存的 Skills
  python run_rag.py skill-stats # 查看 Skill 统计信息
"""

import sys
import os

# 确保项目根目录在 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _load_config():
    """加载配置（兼容旧代码）"""
    from config import load_config, get_legacy_config
    return load_config(), get_legacy_config()


def cmd_ingest():
    """导入文档"""
    config, _ = _load_config()
    from ingest_docs import load_documents, split_documents
    docs = load_documents(config["paths"]["data_dir"])
    if docs:
        cs = config["retrieval"]["chunk_size"]
        co = config["retrieval"]["chunk_overlap"]
        chunks = split_documents(docs, chunk_size=cs, chunk_overlap=co)
        print(f"\n✅ 导入完成: {len(docs)} 文档 → {len(chunks)} 文本块")
    else:
        print("⚠️ 未找到文档")


def cmd_build(clear_old=False):
    """构建向量库"""
    config, legacy = _load_config()
    from vectorstore_setup import setup_vectorstore
    setup_vectorstore(
        data_dir=config["paths"]["data_dir"],
        persist_dir=config["paths"]["persist_dir"],
        embedding_model=config["models"]["embedding"],
        chunk_size=config["retrieval"]["chunk_size"],
        chunk_overlap=config["retrieval"]["chunk_overlap"],
        clear_old=clear_old,
    )


def cmd_chat():
    """启动聊天机器人"""
    from rag_chat_bot import run_rag_chatbot
    run_rag_chatbot()


def cmd_test():
    """运行管道测试"""
    config, legacy = _load_config()
    from langchain_ollama import OllamaEmbeddings, ChatOllama
    from langchain_chroma import Chroma
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    persist_dir = config["paths"]["persist_dir"]
    if not os.path.exists(persist_dir):
        print("❌ 向量库不存在，请先运行: python run_rag.py build")
        return

    print("🧪 管道测试中...\n")
    embeddings = OllamaEmbeddings(model=config["models"]["embedding"])
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    llm = ChatOllama(model=config["models"]["chat"], temperature=config["models"]["temperature"])

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    template = "根据上下文回答问题:\n\n{context}\n\n问题: {question}\n\n回答:"
    prompt = ChatPromptTemplate.from_template(template)

    def format_docs(docs):
        return "\n\n".join(d.page_content for d in docs)

    chain = (
        {"context": retriever | format_docs, "question": lambda x: x}
        | prompt | llm | StrOutputParser()
    )

    test_q = "这个知识库包含什么内容？"
    response = chain.invoke(test_q)
    print(f"❓ {test_q}")
    print(f"🤖 {response}")
    print("\n✅ 测试通过！")


def cmd_status():
    """查看知识库状态"""
    config, _ = _load_config()
    persist_dir = config["paths"]["persist_dir"]
    data_dir = config["paths"]["data_dir"]
    skills_dir = config["paths"]["skills_dir"]

    print("\n📊 RAG 管道状态")
    print("=" * 50)

    # 数据文件
    supported = set(config["auto_ingest"]["supported_extensions"])
    if os.path.exists(data_dir):
        files = []
        for root, dirs, filenames in os.walk(data_dir):
            for f in filenames:
                ext = os.path.splitext(f)[1]
                if ext in supported:
                    files.append(f)
        print(f"📂 知识文件: {len(files)} 个")
        for f in files:
            print(f"   - {f}")
    else:
        print("📂 知识文件: 数据目录不存在")

    # 向量库
    if os.path.exists(persist_dir):
        from langchain_chroma import Chroma
        from langchain_ollama import OllamaEmbeddings
        try:
            embeddings = OllamaEmbeddings(model=config["models"]["embedding"])
            vs = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
            count = vs._collection.count()
            print(f"💾 向量库: {persist_dir}")
            print(f"📊 索引文档块: {count}")
        except Exception as e:
            print(f"💾 向量库: 存在但无法读取 ({e})")
    else:
        print("💾 向量库: 未创建")

    # Skills
    if os.path.exists(os.path.join(skills_dir, "index.json")):
        from skill_manager import SkillManager
        mgr = SkillManager(skills_dir=skills_dir)
        stats = mgr.get_stats()
        print(f"🧠 已保存 Skills: {stats['total_skills']} 个")
        print(f"📈 Skill 总命中: {stats['total_hits']} 次")
        print(f"⭐ 平均评分: {stats['avg_rating']}")
    else:
        print("🧠 Skills: 无")

    # 配置摘要
    print(f"\n⚙️ 配置:")
    print(f"   嵌入模型: {config['models']['embedding']}")
    print(f"   Chat 模型: {config['models']['chat']}")
    print(f"   检索数量: k={config['retrieval']['k']}")
    print(f"   记忆轮数: {config['chat']['max_history']}")

    print("=" * 50)


def cmd_query(question: str):
    """单次查询（非交互模式）"""
    config, legacy = _load_config()

    # 先搜索 Skills
    from skill_manager import SkillManager
    mgr = SkillManager(skills_dir=config["paths"]["skills_dir"])
    skill_matches = mgr.search_skills(question, min_rating=config["skill_learning"]["min_rating"])

    if skill_matches and skill_matches[0]["score"] > 0.3:
        best = skill_matches[0]
        skill = mgr.get_skill_answer(best["skill_id"])
        if skill:
            print(f"🧠 [Skill 匹配: {best['skill_id']} (score={best['score']})]")
            print(f"\n{skill['answer']}")
            if skill.get("sources"):
                print(f"\n📄 来源: {', '.join(skill['sources'])}")
            return

    # Skill 未命中，走 RAG
    from rag_chat_bot import load_vectorstore, build_chain
    vs = load_vectorstore(legacy)
    chain = build_chain(vs, legacy)

    print("🔍 检索知识库中...")
    answer, sources, docs = chain(question, [])

    print(f"\n🤖 {answer}")
    if sources:
        print(f"\n📄 来源: {', '.join(sources)}")
    print(f"🔍 参考了 {len(docs)} 个知识片段")


def cmd_skills():
    """列出所有 Skills"""
    config, _ = _load_config()
    from skill_manager import SkillManager
    mgr = SkillManager(skills_dir=config["paths"]["skills_dir"])

    skills = mgr.list_skills(sort_by="created")
    if not skills:
        print("🧠 暂无已保存的 Skills")
        return

    print(f"\n🧠 已保存的 Skills ({len(skills)} 个)")
    print("=" * 60)
    for i, s in enumerate(skills, 1):
        print(f"\n{i}. [{s['rating']}⭐] {s['question'][:60]}")
        print(f"   ID: {s['skill_id']}")
        print(f"   关键词: {', '.join(s.get('keywords', [])[:5])}")
        print(f"   来源: {', '.join(s.get('sources', []))}")
        print(f"   命中: {s.get('hits', 0)} 次")


def cmd_skill_stats():
    """查看 Skill 统计"""
    config, _ = _load_config()
    from skill_manager import SkillManager
    mgr = SkillManager(skills_dir=config["paths"]["skills_dir"])
    stats = mgr.get_stats()

    print("\n📊 Skill 统计")
    print("=" * 40)
    print(f"  总数: {stats['total_skills']}")
    print(f"  总命中: {stats['total_hits']}")
    print(f"  平均评分: {stats['avg_rating']}")
    print(f"  最后更新: {stats['last_updated'] or '无'}")
    print("=" * 40)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "ingest":
        cmd_ingest()
    elif cmd == "build":
        cmd_build(clear_old=False)
    elif cmd == "chat":
        cmd_chat()
    elif cmd == "rebuild":
        cmd_build(clear_old=True)
    elif cmd == "test":
        cmd_test()
    elif cmd == "status":
        cmd_status()
    elif cmd == "auto":
        from auto_ingest import main as auto_main
        auto_main()
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("用法: python run_rag.py query \"你的问题\"")
            return
        question = " ".join(sys.argv[2:])
        cmd_query(question)
    elif cmd == "skills":
        cmd_skills()
    elif cmd == "skill-stats":
        cmd_skill_stats()
    else:
        print(f"❌ 未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
