import torch
import torchvision
import huggingface_hub
import transformers
from langchain_huggingface import HuggingFaceEmbeddings

print("="*40)
print("🔍 最终环境核查")
print("="*40)

print(f"✅ PyTorch 版本: {torch.__version__}")
print(f"✅ Vision 版本:  {torchvision.__version__}")
print(f"✅ CUDA 可用性:  {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"   - 显卡: {torch.cuda.get_device_name(0)}")

print(f"✅ Hub 版本:     {huggingface_hub.__version__} (预期: >=1.3.5)")
print(f"✅ Transformers: {transformers.__version__}")

print("\n[测试] 尝试加载 Embeddings 模型...")
try:
    # 使用一个小模型快速验证接口兼容性
    emb = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cuda'} # 确保能调用显卡
    )
    vec = emb.embed_query("FinTech Test")
    print(f"🎉 成功! 生成向量维度: {len(vec)}")
except Exception as e:
    print(f"❌ 失败: {e}")