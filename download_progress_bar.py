import string

from huggingface_hub import snapshot_download
import os

# 指定下载目录，方便管理
# local_dir = "./models/faster-whisper-large-v3"
model_name = "faster-whisper-large-v3"
local_dir = "./models/" + model_name
os.makedirs(local_dir, exist_ok=True)

print(f"🚀 开始下载 {model_name}3 到 {local_dir} ...")
print("模型大小约 3GB，请保持网络通畅。")

try:
    path = snapshot_download(
        repo_id="Systran/" + model_name,
        local_dir=local_dir,
    )
    print(f"\n✅ 下载完成！模型路径: {path}")
except Exception as e:
    print(f"\n❌ 下载失败: {e}")
