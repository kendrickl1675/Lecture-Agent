from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 初始化（必须与 indexer 配置一致）
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={'device': 'cuda'}
)

# 加载已存在的数据库
db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embedding_model,
    collection_name="fintech_knowledge"
)

# 测试查询
query = "Explain the assumptions of Black-Scholes"
print(f"\n🔍 Query: {query}")
print("-" * 30)

# 检索 Top 2 结果
docs = db.similarity_search(query, k=2)

for i, doc in enumerate(docs):
    print(f"📄 Result {i+1} (Source: {doc.metadata.get('source', 'Unknown')}):")
    # 打印对应的 Header 上下文
    headers = [doc.metadata.get(k) for k in ['Header 1', 'Header 2', 'Header 3'] if doc.metadata.get(k)]
    print(f"   Context: {' > '.join(headers)}")
    print(f"   Content: {doc.page_content[:150]}...\n")