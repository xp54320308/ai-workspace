import os

# ---------------------------------------------------------------------------
# 文件格式加载器映射
# ---------------------------------------------------------------------------
def _text_loader_mapping():
    # Other formats can be used without importing the PDF/directory backend.
    from langchain_community.document_loaders import TextLoader, PyPDFLoader
    return {
        ".txt": {"loader_cls": TextLoader, "loader_kwargs": {"encoding": "utf-8"}},
        ".pdf": {"loader_cls": PyPDFLoader, "loader_kwargs": {}},
        ".md": {"loader_cls": TextLoader, "loader_kwargs": {"encoding": "utf-8"}},
    }


def load_docx(file_path: str):
    """按正文顺序提取段落及表格，避免遗漏表格中的知识。"""
    from workspace_tools.docx import extract_docx, render_blocks
    text = render_blocks(extract_docx(file_path))
    from langchain_core.documents import Document as LCDocument
    return [LCDocument(page_content=text, metadata={"source": file_path})]


def load_xlsx(file_path: str):
    """使用 openpyxl 加载 .xlsx 文件，所有Sheet转为文本"""
    from openpyxl import load_workbook
    wb = load_workbook(file_path, read_only=True, data_only=True)
    from langchain_core.documents import Document as LCDocument
    docs = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            # 跳过全空行
            if all(cell is None for cell in row):
                continue
            # 将每个单元格转为字符串，用制表符连接
            line = "\t".join(str(cell) if cell is not None else "" for cell in row)
            rows.append(line)
        if rows:
            text = f"【工作表: {sheet_name}】\n" + "\n".join(rows)
            docs.append(LCDocument(page_content=text, metadata={"source": file_path, "sheet": sheet_name}))
    wb.close()
    return docs


def load_documents(data_dir: str = "data"):
    """
    从 data_dir 加载所有支持格式的文档。
    支持格式: .txt, .pdf, .md, .docx, .xlsx
    """
    all_docs = []

    if not os.path.exists(data_dir):
        print(f"❌ Error: {data_dir} directory not found.")
        return []

    print(f"📂 Scanning directory: {os.path.abspath(data_dir)}")

    from langchain_community.document_loaders import DirectoryLoader

    # 1. 加载 .txt, .pdf, .md 文件 (使用 DirectoryLoader)
    for ext, config in _text_loader_mapping().items():
        try:
            loader = DirectoryLoader(
                data_dir,
                glob=f"**/*{ext}",
                loader_cls=config["loader_cls"],
                loader_kwargs=config["loader_kwargs"],
                show_progress=True,
            )
            docs = loader.load()
            if docs:
                all_docs.extend(docs)
                print(f"  ✅ {ext}: 加载 {len(docs)} 个文档")
        except Exception as e:
            print(f"  ⚠️ {ext} 加载失败: {e}")

    # 2. 加载 .docx 文件 (使用 python-docx)
    docx_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".docx"):
                docx_files.append(os.path.join(root, file))

    for docx_path in docx_files:
        try:
            docs = load_docx(docx_path)
            all_docs.extend(docs)
            print(f"  ✅ .docx: 加载 {docx_path}")
        except Exception as e:
            print(f"  ⚠️ .docx 加载失败 {docx_path}: {e}")

    # 3. 加载 .xlsx 文件 (使用 openpyxl)
    xlsx_files = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".xlsx"):
                xlsx_files.append(os.path.join(root, file))

    for xlsx_path in xlsx_files:
        try:
            docs = load_xlsx(xlsx_path)
            all_docs.extend(docs)
            print(f"  ✅ .xlsx: 加载 {xlsx_path} ({len(docs)}个工作表)")
        except Exception as e:
            print(f"  ⚠️ .xlsx 加载失败 {xlsx_path}: {e}")

    return all_docs


def split_documents(docs, chunk_size=800, chunk_overlap=100):
    """将文档切分为文本块"""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n\n", "\n\n", "\n", "。", ".", " ", ""],
    )
    chunks = text_splitter.split_documents(docs)

    # 为每个 chunk 添加来源文件名
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        chunk.metadata["source_file"] = os.path.basename(source)

    return chunks


def main():
    data_dir = "data"

    print("=" * 50)
    print("🚀 文档摄入管道 (多格式支持)")
    print("=" * 50)

    # 1. 加载文档
    docs = load_documents(data_dir)
    if not docs:
        print("⚠️ 未找到任何文档。")
        return

    print(f"\n✅ 共加载 {len(docs)} 个文档")

    # 2. 切片
    print("✂️  正在切片...")
    chunks = split_documents(docs)
    print(f"✅ 共生成 {len(chunks)} 个文本块")

    # 3. 预览
    if chunks:
        print("\n--- 首个文本块预览 ---")
        print(f"📄 来源: {chunks[0].metadata.get('source_file', 'unknown')}")
        print(f"📝 内容: {chunks[0].page_content[:200]}...")
        print("----------------------\n")

    print(f"🎉 文档摄入完成！共 {len(chunks)} 个文本块待向量化")
    print(f"💡 下一步: 运行 python vectorstore_setup.py 进行向量化")


if __name__ == "__main__":
    main()
