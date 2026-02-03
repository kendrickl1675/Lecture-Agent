import time
import os
import re
import logging
from agent_core import LectureAgentCore

# --- 基础配置 ---
OBSIDIAN_PATH = r"./test_notes"  # ⚠️ Beta测试时请确认此路径指向你的克隆库
LOG_FILE = "agent_runtime.log"

# --- 触发标签配置 ---
START_TAG = "<ai>"
END_TAG = "</ai>"
# DOTALL 模式确保 . 能匹配换行符，捕获多行内容
PATTERN = re.compile(f"{re.escape(START_TAG)}(.*?){re.escape(END_TAG)}", re.DOTALL)

# --- 结构保护正则 ---
# 匹配图片 ![[...]]
REGEX_IMG = re.compile(r'(!\[\[.*?\]\])')
# 匹配双向链接 [[...]] (排除前面有!的情况)
REGEX_LINK = re.compile(r'(?<!\!)(\[\[.*?\]\])')
# 匹配 Callout 标题 (例如 > [!NOTE] Title)
REGEX_CALLOUT_HEADER = re.compile(r'^>\s*\[!.*?\](.*)$', re.MULTILINE)

# ==========================================
# ✅ 核心: 日志系统配置 (含降噪)
# ==========================================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    encoding='utf-8'
)

# 🔇 静音列表：屏蔽 HTTP 请求和 Google SDK 的内部啰嗦日志
silence_list = [
    "urllib3", "requests", "sentence_transformers", "huggingface_hub", "chromadb",
    "httpcore", "httpx",
    "google.generativeai",
    "google.ai.generativelanguage",
    "google.auth",
    "langchain_google_genai",
    "google_genai",  # 👈 针对 AFC 日志的关键屏蔽
]

for logger_name in silence_list:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# 控制台同步输出 (方便肉眼确认运行状态)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class ContentProtector:
    """
    内容保护器：在发给 LLM 之前，将图片和链接替换为占位符，
    处理完后再还原，防止 LLM 修改或删除关键链接。
    """

    def __init__(self):
        self.map = {}
        self.counter = 0

    def protect(self, text):
        self.map = {}
        self.counter = 0

        def replace_match(match, prefix):
            token = f"__{prefix}_{self.counter}__"
            self.map[token] = match.group(0)  # 存储原始内容
            self.counter += 1
            return token

        # 先保护图片，再保护链接
        text = REGEX_IMG.sub(lambda m: replace_match(m, "IMG"), text)
        text = REGEX_LINK.sub(lambda m: replace_match(m, "LINK"), text)
        return text

    def restore(self, text):
        # 将占位符还原为原始内容
        for token, original in self.map.items():
            text = text.replace(token, original)
        return text


def scan_and_process(agent):
    # 递归扫描目录下所有 .md 文件
    for root, dirs, files in os.walk(OBSIDIAN_PATH):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                process_segment(agent, file_path)


def process_segment(agent, file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 快速检查：如果文件里没标签，直接跳过，节省资源
        if START_TAG not in content:
            return

        matches = list(PATTERN.finditer(content))
        if not matches:
            return

        logging.info(f"📂 Detected {len(matches)} segments in: {os.path.basename(file_path)}")

        new_content = content

        # ⚠️ 关键：倒序处理 (Reversed)
        # 必须从文件末尾开始替换，否则前面的替换会改变字符串长度，导致后续索引失效
        for match in reversed(matches):
            raw_segment = match.group(1).strip()

            # --- Step 1: 结构识别 (Callout vs 普通文本) ---
            is_callout = False
            callout_header = ""
            processing_text = raw_segment

            header_match = REGEX_CALLOUT_HEADER.match(raw_segment)

            if header_match:
                is_callout = True
                raw_header = raw_segment.split('\n')[0].strip()
                # 规范化 Callout 格式 (确保 > 后有空格)
                if not raw_header.startswith("> "):
                    callout_header = raw_header.replace(">", "> ", 1)
                else:
                    callout_header = raw_header

                # 提取正文 (去除每一行开头的引用符 >)
                lines = raw_segment.split('\n')[1:]
                body_lines = [re.sub(r'^>\s?', '', line) for line in lines]
                processing_text = "\n".join(body_lines).strip()
                logging.info(f"  🔹 Callout identified: {callout_header}")

            elif raw_segment.strip().startswith(">"):
                # 处理普通引用块
                is_callout = True
                callout_header = ">"
                lines = raw_segment.split('\n')
                body_lines = [re.sub(r'^>\s?', '', line) for line in lines]
                processing_text = "\n".join(body_lines).strip()

            # --- Step 2: 内容保护 (加密) ---
            protector = ContentProtector()
            masked_text = protector.protect(processing_text)

            # --- Step 3: Agent 处理 (调用 LLM) ---
            processed_text = agent.generate_note(masked_text)

            # --- Step 4: 还原与重组 (解密 & 格式化) ---
            if processed_text and "SKIP_PROCESSING" not in processed_text:
                # 4.1 还原图片和链接
                restored_text = protector.restore(processed_text)
                final_replacement = ""

                if is_callout:
                    # 4.2 智能拆分：将 Term Analysis 移出 Callout
                    split_marker = None
                    # 兼容带 emoji 和不带 emoji 的标题
                    if "### Key Term Analysis" in restored_text:
                        split_marker = "### Key Term Analysis"
                    elif "### 🏆Key Term Analysis" in restored_text:
                        split_marker = "### 🏆Key Term Analysis"

                    if split_marker:
                        parts = restored_text.split(split_marker)
                        academic_body = parts[0].strip()
                        term_analysis = split_marker + parts[1]  # 拼接回去
                    else:
                        academic_body = restored_text
                        term_analysis = ""

                    # 4.3 重建引用块 (只给学术正文加 >)
                    reconstructed_body = "\n".join([f"> {line}" for line in academic_body.split('\n')])

                    # 4.4 最终拼接：Header + 引用正文 + 外部的 Term Analysis
                    final_replacement = f"{callout_header}\n{reconstructed_body}\n\n{term_analysis}\n"
                else:
                    final_replacement = f"{restored_text}\n"

                # 4.5 替换原文 (包含销毁 <ai> 标签)
                start_idx, end_idx = match.span()
                new_content = new_content[:start_idx] + final_replacement + new_content[end_idx:]
                logging.info("  ✅ Segment updated successfully")
            else:
                logging.info("  ⏭️  Agent skipped processing")

        # 写入文件
        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logging.info(f"💾 File saved: {os.path.basename(file_path)}")

    except Exception as e:
        logging.error(f"❌ Error processing {file_path}: {e}")


def main():
    print("==================================================")
    print("   👁️ Lecture Note Daemon (Gemini 3 Preview)       ")
    print("==================================================")
    logging.info("Watcher started.")

    try:
        agent = LectureAgentCore()
        logging.info("Agent initialized.")
    except Exception as e:
        logging.critical(f"Failed to initialize Agent: {e}")
        return

    try:
        while True:
            scan_and_process(agent)
            time.sleep(2)
    except KeyboardInterrupt:
        logging.info("Watcher stopped.")


if __name__ == "__main__":
    main()