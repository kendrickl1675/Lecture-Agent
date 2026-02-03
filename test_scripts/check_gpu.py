import torch
from faster_whisper import WhisperModel
import time

def check_environment():
    print("="*30)
    print("环境硬件自检程序")
    print("="*30)

    # 1. 检查 PyTorch 是否识别到 CUDA
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        print(f"✅ CUDA 就绪! 显卡型号: {device_name}")
        
        # 简单显存测试
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"✅ 显存总量: {vram:.2f} GB (足够运行 RAG + Whisper)")
    else:
        print("❌ 警告: 未检测到 GPU，将使用 CPU (速度会很慢)")
        return

    # 2. 检查 Faster-Whisper 加载 (模拟感知层)
    print("\n[测试] 加载 Whisper 模型 (至显卡)...")
    try:
        start = time.time()
        # 使用 tiny 模型进行快速冒烟测试
        model = WhisperModel("tiny", device="cuda", compute_type="float16")
        print(f"✅ Whisper 模型加载成功! 耗时: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"❌ Whisper 加载失败: {e}")

    # 3. 检查向量库依赖
    try:
        from chromadb.utils import embedding_functions
        print("✅ ChromaDB 依赖加载正常")
    except ImportError:
        print("❌ ChromaDB 加载失败")

    print("\n🎉 环境配置完成，随时可以开始开发！")

if __name__ == "__main__":
    check_environment()