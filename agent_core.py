import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()


class LectureAgentCore:
    def __init__(self):
        # 打印当前使用的模型名称，方便调试确认
        print(f"🧠 初始化 Agent (Engine: {os.getenv('MODEL_NAME')})...")

        # 1. 初始化向量数据库 (RAG 记忆模块)
        # 使用 BAAI/bge-m3 模型将文本转换为向量，支持中英文混合
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={'device': 'cuda'}  # 强制使用 GPU 加速
        )
        # 加载本地持久化的数据库
        self.vector_db = Chroma(
            persist_directory="./chroma_db",
            embedding_function=self.embeddings,
            collection_name="fintech_knowledge"
        )

        # 2. LLM 初始化 (大脑)
        # 温度设为 0.1 以保证学术输出的严谨性和一致性
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv("MODEL_NAME", "gemini-3-flash-preview"),  # 建议在 .env 中管理版本
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.1,
        )

        # 3. System Prompt (核心指令集)
        # 包含：角色定义、RAG上下文注入、任务指令、防御机制、格式约束
        self.system_prompt = """
        You are a strict academic research assistant in Quantitative Finance.

        [CONTEXT FROM LOCAL DATABASE]
        (This provides specific lecture details. It might be empty if no prior notes exist.)
        {context}

        [TASK]
        Refine the [USER INPUT] into rigorous **Academic English** Markdown based on TWO sources: 
        1. The [CONTEXT] provided above.
        2. Your own **Internal Expert Knowledge** of Finance/Math/Coding.

        [GATEKEEPING RULES]
        - **CASE A (Chat/Nonsense):** If the input is purely conversational or lacks technical substance, output EXACTLY: "SKIP_PROCESSING".
        - **CASE B (Valid Content):** If input contains recognizable concepts, process it even if context is empty.

        [CRITICAL RULES]
        1. **PROTECTED TOKENS**: You will see placeholders like `__IMG_0__` or `__LINK_1__`. **DO NOT CHANGE, DELETE, OR MOVE THEM.**
        2. **TERM ANALYSIS (CONSTRAINTS)**:
                   - **Quantity Limit**: TOP 3-5 critical terms only.
                   - **Expansion Logic**: Strictly relevant to current context.
                   - **Location**: Place "Key Term Analysis" at the very END.

                   **Format:**
                   ### 🏆Key Term Analysis
                   * **[Term Name]**
                       * **Origin**: ...
                       * **Application**: ...
                       * **Expansion**: ...
        3. **OBSIDIAN CALLOUT PRESERVATION**: 
           - Reconstruct Callouts (`> [!NOTE]`) exactly.
           - Academic text must be inside blockquote (`> ` prefix).
        4. **Math**: Use LaTeX ($...$).
        5. **Regulations**: Prioritize AMCM/PBOC/HKMA.

        [USER INPUT]
        {input_text}
        """

        self.prompt = ChatPromptTemplate.from_template(self.system_prompt)
        self.chain = self.prompt | self.llm | StrOutputParser()

    def generate_note(self, raw_text):
        # 1. 输入预检查：太短的文本直接忽略，节省 API 调用
        if not raw_text or len(raw_text.strip()) < 3:
            return raw_text

        # 2. RAG 检索流程
        try:
            # 检查数据库是否为空，防止冷启动报错
            if self.vector_db._collection.count() == 0:
                context_str = "No local context available (Database is empty)."
            else:
                # 使用带阈值的检索，过滤掉相关性低的内容
                retriever = self.vector_db.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={"score_threshold": 0.6, "k": 2}
                )
                docs = retriever.invoke(raw_text)
                if docs:
                    context_str = "\n".join([f"- {d.page_content}" for d in docs])
                else:
                    context_str = "No relevant context found in local database."

        except Exception as e:
            # 检索失败不应阻断主流程，降级为无 RAG 模式
            context_str = f"Context retrieval skipped: {str(e)}"

        # 3. LLM 生成流程
        try:
            response = self.chain.invoke({
                "context": context_str,
                "input_text": raw_text
            })

            # 4. 鲁棒性检查：如果模型判断为闲聊，则原样返回
            if "SKIP_PROCESSING" in response:
                print(f"⏭️  Skipped: {raw_text[:30]}... (Chat/Nonsense)")
                return raw_text

            return response

        except Exception as e:
            print(f"❌ Error: {e}")
            return raw_text