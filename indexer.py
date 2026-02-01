import os
import glob
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import time

# --- 配置 ---
SOURCE_DIR = "./test_notes"  # 指向你的笔记目录
PERSIST_DIR = "./chroma_db"  # 向量库存储位置
EMBEDDING_MODEL = "BAAI/bge-m3"  # 目前最强的开源中英双语模型


def load_and_chunk_markdown(path):
    """
    两阶段切分策略：
    1. 语义层级切分：按 H1/H2/H3 标题切分，保留层级元数据。
    2. 字符长度切分：如果某个章节内容过长，再按字符强制截断。
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"❌ 读取失败 {path}: {e}")
        return []

    # 1. 结构化切分 (保留上下文)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(text)

    # 2. 长度控制 (防止某个章节写了5000字，超过模型窗口)
    # chunk_size=1000 tokens 大约对应 BGE-M3 的最佳窗口
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    final_splits = text_splitter.split_documents(md_header_splits)

    # 注入源文件路径元数据
    for doc in final_splits:
        doc.metadata["source"] = path

    return final_splits


def main():
    # 1. 初始化 Embedding 模型 (关键：使用 CUDA)
    print(f"🔄 正在加载模型 {EMBEDDING_MODEL} 到 GPU (RTX 4070 Ti)...")
    start_time = time.time()

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cuda'},  # 显式指定 CUDA
        encode_kwargs={'normalize_embeddings': True}  # 归一化有助于余弦相似度计算
    )
    print(f"✅ 模型加载完成，耗时: {time.time() - start_time:.2f}s")

    # 2. 读取并切分文件
    md_files = glob.glob(os.path.join(SOURCE_DIR, "**/*.md"), recursive=True)
    all_splits = []

    print(f"📂 发现 {len(md_files)} 个 Markdown 文件，开始处理...")

    for file_path in md_files:
        splits = load_and_chunk_markdown(file_path)
        all_splits.extend(splits)
        print(f"  - {os.path.basename(file_path)} -> 切分为 {len(splits)} 个块")

    if not all_splits:
        print("⚠️ 没有数据可供索引。")
        return

    # 3. 存入 ChromaDB
    print(f"💾 正在将 {len(all_splits)} 个向量块写入数据库...")

    # 如果数据库已存在，直接追加；否则创建
    vectorstore = Chroma.from_documents(
        documents=all_splits,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name="fintech_knowledge"
    )

    print(f"🎉 索引构建成功！数据已持久化至 {PERSIST_DIR}")
    print(f"✅ 显存占用提示: 请观察任务管理器，BGE-M3 应该占用约 1-2GB VRAM。")


if __name__ == "__main__":
    main()