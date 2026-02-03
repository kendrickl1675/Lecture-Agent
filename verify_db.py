import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- 配置 (必须与 indexer_pro.py 一致) ---
DB_DIR = "./chroma_db"
COLLECTION_NAME = "fintech_knowledge"
MODEL_NAME = "BAAI/bge-m3"

# Mac Intel 强制 CPU
DEVICE = "cpu"


def verify_retrieval(query_text: str):
    print(f"\n🔍 Testing Query: '{query_text}'")
    print("-" * 50)

    try:
        # 1. 初始化 Embedding (CPU模式)
        print("⚙️ Loading Embeddings (this may take a moment)...")
        embeddings = HuggingFaceEmbeddings(
            model_name=MODEL_NAME,
            model_kwargs={'device': DEVICE}
        )

        # 2. 连接数据库
        print(f"📂 Connecting to ChromaDB at {DB_DIR}...")
        vector_db = Chroma(
            persist_directory=DB_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )

        # 3. 检查库里有多少条数据
        count = vector_db._collection.count()
        print(f"📊 Total Documents in DB: {count}")

        if count == 0:
            print("❌ Database is empty! Please run indexer_pro.py first.")
            return

        # 4. 执行检索 (Top 3)
        # similarity_search_with_score 返回 (Document, score)
        # Chroma 默认距离通常是 L2 (欧氏距离)，分数越低越相似。
        results = vector_db.similarity_search_with_score(query_text, k=3)

        print(f"\n✅ Found {len(results)} relevant chunks:\n")

        for i, (doc, score) in enumerate(results):
            source = doc.metadata.get('source', 'Unknown')
            type_ = doc.metadata.get('type', 'Unknown')
            content_preview = doc.page_content[:150].replace('\n', ' ')

            print(f"📄 [Result {i + 1}] (Score: {score:.4f})")
            print(f"   Ref: {source} ({type_})")
            print(f"   Excerpt: \"{content_preview}...\"")
            print("-" * 30)

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # 请在这里修改为你课件里包含的具体概念，例如 "CAPM", "Smart Contracts", "Option Pricing"
    # 输入一个你确定在 PDF/PPT 里有的词
    TEST_QUERY = input("请输入通过 indexer 导入的一个核心概念 (例如: Smart Contracts): ")
    verify_retrieval(TEST_QUERY)