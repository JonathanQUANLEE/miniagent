# ============================================================
# step24_rag.py — RAG 全链路：让 Agent 开卷考试
# ------------------------------------------------------------
# 五步流水线：
#   ① 切片 chunk   — 长文档切成小块（重叠 50 字符防句子被拦腰切断）
#   ② 向量化 embed — 文字 → 向量（优先真实 Embedding API，失败降级本地哈希向量）
#   ③ 入库 index   — 本项目用普通列表存（300 篇文档内无需向量数据库）
#   ④ 检索 search  — 问题也向量化，余弦相似度取 Top-K
#   ⑤ 生成 answer  — 检索到的原文 + 问题一起交给模型，要求标注引用
#
# 设计说明：
#   * 本文件自包含、可直接运行；函数全部在模块层定义（带 __main__ 护栏），
#     所以 tests/ 可以 import 它做单元测试。
#   * embed() 是 Fallback 家族血统（step14）：API 好用就走 API，
#     API 挂了自动降级本地向量——检索照样能跑，只是精度略降。
# ============================================================
import os
import sys
import glob
import math
import zlib

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

# ---------- 可调参数 ----------
DIM        = 256   # 本地向量维度
CHUNK_SIZE = 300   # 每个切片的目标字符数
OVERLAP    = 50    # 相邻切片的重叠字符数
TOP_K      = 2     # 检索召回条数
# ------------------------------

_EMBED_FALLBACK_NOTED = False   # 只提示一次降级，别刷屏
_EMBED_CLIENT = None            # 懒加载：import 本模块时不建连接


# ------------------------------------------------------------
# ① 切片：固定窗口 + 重叠
# ------------------------------------------------------------
def chunk_text(text):
    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [text] if text else []
    chunks = []
    step = CHUNK_SIZE - OVERLAP
    for i in range(0, len(text), step):
        piece = text[i:i + CHUNK_SIZE].strip()
        if piece:
            chunks.append(piece)
        if i + CHUNK_SIZE >= len(text):
            break
    return chunks


# ------------------------------------------------------------
# ② 向量化（本地兜底版）：字符 n-gram 哈希词袋
#    crc32 是稳定哈希——同一句话今天算和明天算结果一样，
#    （内置 hash() 每次开进程会换盐，不能用于检索！）
# ------------------------------------------------------------
def embed_local(text):
    vec = [0.0] * DIM
    t = text.lower()
    for i in range(len(t)):
        vec[zlib.crc32(t[i].encode()) % DIM] += 1.0          # 单字
        if i + 1 < len(t):
            vec[zlib.crc32(t[i:i + 2].encode()) % DIM] += 1.0  # 二字组合
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]          # L2 归一化 → 余弦=点积


# ------------------------------------------------------------
# ② 向量化（主路径）：OpenAI 兼容 /embeddings 接口
#    .env 里配 EMBEDD_MODEL 即启用（如 SiliconFlow 的 bge-m3）
# ------------------------------------------------------------
def embed_api(text):
    global _EMBED_CLIENT
    if _EMBED_CLIENT is None:
        from openai import OpenAI
        import httpx
        proxy = os.environ.get("HTTP_PROXY", "").strip()
        http_client = httpx.Client(proxy=proxy, timeout=60) if proxy else httpx.Client(timeout=60)
        _EMBED_CLIENT = OpenAI(
            api_key=os.environ.get("EMBEDD_API_KEY") or os.environ.get("API_KEY") or "unset",
            base_url=os.environ.get("EMBEDD_BASE_URL") or os.environ.get("BASE_URL", "https://openrouter.ai/api/v1"),
            http_client=http_client,
        )
    r = _EMBED_CLIENT.embeddings.create(
        model=os.environ["EMBEDD_MODEL"],
        input=[text],
    )
    return r.data[0].embedding


def embed(text):
    # Fallback 家族：API 优先，挂了自动降级，只提示一次
    global _EMBED_FALLBACK_NOTED
    if os.environ.get("EMBEDD_MODEL"):
        try:
            return embed_api(text)
        except Exception as e:
            if not _EMBED_FALLBACK_NOTED:
                print(f"[fallback] Embedding API 不可用（{type(e).__name__}），降级本地哈希向量")
                _EMBED_FALLBACK_NOTED = True
    return embed_local(text)


# ------------------------------------------------------------
# ④ 检索：余弦相似度 Top-K
#    向量已 L2 归一化，点积 = 余弦，不用再除长度
# ------------------------------------------------------------
def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


def search(index, query_vec, k=TOP_K):
    scored = [(cosine(item["vec"], query_vec), item) for item in index]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:k]


# ------------------------------------------------------------
# ③ 入库：读知识库目录 → 切片 → 向量化 → 存列表
# ------------------------------------------------------------
def build_index(docs_dir="docs/knowledge"):
    index = []
    for path in sorted(glob.glob(os.path.join(docs_dir, "*.md"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for chunk in chunk_text(text):
            index.append({"source": os.path.basename(path), "text": chunk, "vec": embed(chunk)})
    return index


# ------------------------------------------------------------
# ⑤ 生成：检索结果 + 问题 → 带引用的回答
# ------------------------------------------------------------
def build_prompt(question, hits):
    blocks = [f"资料{i+1}（来自 {item['source']}）：\n{item['text']}"
              for i, (_, item) in enumerate(hits)]
    return ("请只根据下面的资料回答问题，回答末尾标注用了第几条资料；"
            "资料里没有的就说不知道，不要编。\n\n"
            + "\n\n".join(blocks)
            + f"\n\n问题：{question}")


def main():
    from openai import OpenAI
    import httpx
    proxy = os.environ.get("HTTP_PROXY", "").strip()
    http_client = httpx.Client(proxy=proxy, timeout=60) if proxy else httpx.Client(timeout=60)
    llm = OpenAI(
        api_key=os.environ.get("API_KEY") or "unset",
        base_url=os.environ.get("BASE_URL", "https://openrouter.ai/api/v1"),
        http_client=http_client,
    )
    model = os.environ.get("MODEL", "inclusionai/ling-3.0-flash-sante:free")

    # 全链路跑一遍，每一站都打印出实物（检索明细是重点观察对象）
    question = "什么是 Agent？它和直接调用 LLM 有什么区别？MCP 解决什么问题？"
    print(f"【问题】{question}\n")

    index = build_index()
    print(f"【入库】知识库切片共 {len(index)} 块")

    qvec = embed(question)
    hits = search(index, qvec)
    print("【检索明细】（余弦相似度 Top-%d）" % len(hits))
    for score, item in hits:
        print(f"  {score:.4f}  {item['source']}  ← {item['text'][:40]}...")

    prompt = build_prompt(question, hits)
    print(f"\n【提示词厚度】{len(prompt)} 字符")
    r = llm.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一个严谨的问答助手，只依据资料作答。"},
            {"role": "user", "content": prompt},
        ],
    )
    print(f"\n【Agent 回答】\n{r.choices[0].message.content}")
    print(f"\n【账单】prompt={r.usage.prompt_tokens} completion={r.usage.completion_tokens} total={r.usage.total_tokens}")


if __name__ == "__main__":
    main()
