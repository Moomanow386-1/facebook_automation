import math
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

EMBED_MODEL = "text-embedding-004"
GENERATE_MODEL = "gemini-3.5-flash"
GENERATE_MODEL_FALLBACKS = ["gemini-3.1-flash", "gemini-3.1-flash-lite"]
UTIL_MODEL = "gemini-3.1-flash-lite"
_RETRY_DELAYS = [30, 60, 120, 180, 300, 300, 300, 300]


def _with_retry(fn):
    for delay in _RETRY_DELAYS:
        try:
            return fn()
        except ServerError as exc:
            print(f"[retry] ServerError: {exc}, retrying in {delay}s…")
            time.sleep(delay)
    return fn()


SIM_HARD_REJECT = 0.92  # nearly identical text → hard block
SIM_LLM_CHECK   = 0.65  # ambiguous zone → let LLM decide


def _get_embedding(text: str) -> list[float] | None:
    try:
        result = client.models.embed_content(model=EMBED_MODEL, contents=text[:2000])
        return result.embeddings[0].values
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag = math.sqrt(sum(x**2 for x in a)) * math.sqrt(sum(x**2 for x in b))
    return dot / mag if mag else 0.0


def _max_similarity(embedding: list[float], posted_history: list[dict]) -> float:
    best = 0.0
    for item in posted_history:
        stored = item.get("embedding")
        if stored:
            best = max(best, _cosine(embedding, stored))
    return best

PROMPT = """ค้นหาข่าว tech หรือ AI ที่น่าสนใจที่สุดในช่วงนี้ แล้วเขียนโพสต์ Facebook ภาษาไทย 1 โพสต์

หัวข้อที่สนใจ (เรียงตามความสำคัญ):
1. AI agents และ agentic workflows — เช่น multi-agent systems, MCP (Model Context Protocol), AI ที่ทำงานแทนคน, tool use, computer use, agent orchestration, autonomous coding agents
2. Claude ecosystem — MCP servers เจ๋งๆ, plugins, skills, integrations ใหม่; แอป เว็บ หรือ product ที่สร้างด้วย Claude Code หรือ Claude API; use cases จริงที่คนเอา Claude ไปทำอะไรได้น่าทึ่ง
3. AI model ใหม่และ benchmark — Claude, Gemini, GPT, Llama, Mistral และโมเดลอื่นๆ ความสามารถใหม่, context window, reasoning, multimodal
4. AI ในการทำงานจริง — coding agents, AI สำหรับธุรกิจ, workflow automation, AI engineer tools, enterprise AI adoption
5. เทคโนโลยีใหม่ — robot, semiconductor, quantum computing, space, NASA, SpaceX
6. ข่าวหุ้น tech (ถ้าไม่มีข่าวอื่นที่น่าสนใจกว่า): NVDA, AMD, TSMC, Apple, Microsoft — เช่น ผลประกอบการ, demand chip, AI chip cycle

ถ้าเจอข่าวจาก official source ของบริษัท AI โดยตรง (เช่น blog ของ Anthropic, OpenAI, Google DeepMind, Meta AI) ให้ prefer มากกว่าสื่อที่รายงานซ้ำ

ลดความสำคัญ: ข่าว fundraising, valuation, IPO, การระดมทุน — เลือกเฉพาะเมื่อไม่มีข่าวเทคนิคหรือ product ที่น่าสนใจกว่า

สไตล์การเขียน:
- ภาษาพูด casual เหมือนคนในวงการ tech คุยกัน
- ผสม Thai และ English อย่างเป็นธรรมชาติ
- ประโยคสั้น กระชับ อ่านง่าย
- เปิดด้วยเนื้อหาตรงๆ เช่น fact, ตัวเลข, หรือ statement เกี่ยวกับข่าวนั้นเลย ไม่ต้อง intro ว่า "มีข่าวมาก" หรือ "มาดูกัน"
- จบแบบหลากหลาย บางทีเป็นความคิดเห็นสั้นๆ บางทีเป็น statement ที่ทิ้งให้คิด — ห้ามจบด้วยคำถาม
- ความยาวหลากหลาย บางโพสต์สั้น 2-3 ประโยค บางโพสต์ยาว 5-7 ประโยค และบางโพสต์ที่เนื้อหาน่าสนใจมากๆ สามารถเขียนยาว 30-50 ประโยคได้เลย แต่ไม่ต้องทุกโพสต์
- ใช้ย่อหน้าแบ่งเนื้อหา ไม่ต้องเขียนต่อกันยาวๆ เป็นก้อนเดียว แต่ขึ้นย่อหน้าใหม่เฉพาะเมื่อเปลี่ยนประเด็นหรือ idea ใหม่จริงๆ เท่านั้น — ห้ามขึ้นย่อหน้าใหม่กลางความคิดเดียวกัน หรือเมื่อประโยคถัดไปยังเชื่อมกับประโยคก่อนหน้าโดยตรง แต่ละย่อหน้าไม่ควรยาวเกิน 3-4 ประโยค ถ้ายาวกว่านั้นให้หาจุดแบ่ง idea ที่เหมาะสม
- ท้ายโพสต์ใส่ hashtag ที่เกี่ยวข้อง 4-6 อัน ทั้ง Thai และ English

ห้าม:
- ห้ามขึ้นต้นประโยคแรกด้วย "ช่วงนี้" ทุกกรณี ไม่ว่าจะตามด้วยอะไรก็ตาม
- ห้ามขึ้นต้นด้วย meta-intro เช่น "วงการ AI ช่วงนี้...", "มาดูกันว่า...", "มีอะไรน่าสนใจ...", "ข่าว AI ล่าสุด..." — เริ่มด้วย fact หรือ event ตรงๆ เช่น "[ชื่อบริษัท] เพิ่งปล่อย...", "[ตัวเลข] คือ...", "[ชื่อ product] ทำได้..."
- ห้ามใช้คำอุทานเกินจริง เช่น "นะเนี่ย!" "เลยนะ!" "ของจริง!"
- ห้ามใช้ ! เลย ไม่แม้แต่ครั้งเดียว
- ห้ามใส่จุด (.) ท้ายประโยคสุดท้ายหรือท้ายโพสต์
- ห้ามจบด้วยคำถาม เช่น "คุณคิดว่า...ไหม" "แล้วคุณล่ะ..." — จบด้วย statement เท่านั้น
- ห้ามใช้ emoji มากเกิน 1 ตัว
- ห้ามพูดถึง link ในโพสต์

ห้ามใส่ URL หรือ SOURCE_URL ในโพสต์"""


def _build_avoid_block(posted_history: list[dict]) -> str:
    lines = []
    for item in posted_history:
        topic = item.get("topic", "")
        url = item.get("url", "")
        if topic and url:
            lines.append(f"- {topic} ({url})")
        elif topic:
            lines.append(f"- {topic}")
    if not lines:
        return ""
    avoid = "\n".join(lines)
    return (
        f"\n\nข่าวที่โพสต์ไปแล้ว (ห้ามเลือกเรื่องที่มีเนื้อหาเหตุการณ์เดียวกัน แม้จะมาจากแหล่งข่าวอื่นหรือชื่อหัวข้อต่างกัน):\n{avoid}"
        "\n\nให้เปรียบว่า 'เหตุการณ์ที่เกิดขึ้น' เหมือนกันมั้ย ไม่ใช่แค่ดูชื่อ"
        "\n(ยกเว้น: product เดิมแต่ version ใหม่กว่า = ไม่ซ้ำ)"
    )


def _is_duplicate(post: str, posted_history: list[dict]) -> bool:
    if not posted_history:
        return False
    summaries = "\n".join(
        f"- {item['topic']}" for item in posted_history if item.get("topic")
    )
    check_prompt = f"""โพสต์ใหม่:
{post[:600]}

เหตุการณ์ที่โพสต์ไปแล้ว:
{summaries}

โพสต์ใหม่นี้รายงานเหตุการณ์เดียวกันกับรายการใดรายการหนึ่งข้างบนมั้ย?
ตอบแค่ YES หรือ NO (product เดิมแต่ version ใหม่กว่า = NO)"""
    try:
        res = _with_retry(lambda: client.models.generate_content(
            model=UTIL_MODEL,
            contents=check_prompt,
        ))
        answer = res.text.strip().upper()
        return answer.startswith("YES")
    except Exception:
        return False


def _generate_post(prompt: str) -> tuple[str, str]:
    last_exc = None
    for model in [GENERATE_MODEL] + GENERATE_MODEL_FALLBACKS:
        try:
            response = _with_retry(lambda m=model: client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                ),
            ))
            if model != GENERATE_MODEL:
                print(f"[fallback] used {model} after {GENERATE_MODEL} unavailable")
            break
        except ServerError as exc:
            print(f"[fallback] {model} exhausted retries: {exc}")
            last_exc = exc
    else:
        raise last_exc
    post = response.text.strip()
    url = ""
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks
        for chunk in chunks:
            if hasattr(chunk, "web") and chunk.web.uri:
                url = chunk.web.uri
                break
    except Exception:
        pass
    return post, url


def _extract_topic_label(post: str) -> str:
    try:
        res = _with_retry(lambda: client.models.generate_content(
            model=UTIL_MODEL,
            contents=(
                f"สรุปเหตุการณ์หลักของโพสต์นี้เป็น 1 ประโยคสั้นๆ ภาษาอังกฤษ (max 15 words) "
                f"เช่น 'Claude Opus 4.8 release - agentic workflows' หรือ 'Google I/O 2026 - Gemini becomes OS'\n\n"
                f"โพสต์:\n{post[:800]}"
            ),
        ))
        return res.text.strip()[:120]
    except Exception:
        return post[:80]


def generate_overlay_text(post: str) -> tuple[str, str]:
    """Return (headline, subtitle) Thai strings for the image overlay."""
    try:
        res = _with_retry(lambda: client.models.generate_content(
            model=UTIL_MODEL,
            contents=(
                "จากโพสต์นี้ ให้สร้างข้อความ 2 บรรทัดสำหรับใส่บนรูปภาพ:\n"
                "บรรทัด 1 (HEADLINE): ประโยคสั้นๆ ภาษาไทยผสม English ได้ ไม่เกิน 40 ตัวอักษร กระชับ น่าสนใจ\n"
                "บรรทัด 2 (SUBTITLE): อธิบายเพิ่มเติม 1 ประโยค ไม่เกิน 60 ตัวอักษร\n\n"
                "ตอบแค่ 2 บรรทัด ไม่ต้องมี label หรือ prefix\n\n"
                f"โพสต์:\n{post[:800]}"
            ),
        ))
        lines = [l.strip() for l in res.text.strip().splitlines() if l.strip()]
        headline = lines[0][:80] if lines else post[:40]
        subtitle = lines[1][:100] if len(lines) > 1 else ""
        return headline, subtitle
    except Exception:
        return post[:40], ""


def write_post_with_search(posted_history: list[dict] | None = None) -> tuple[str, str, str]:
    history = posted_history or []
    avoid_block = _build_avoid_block(history)
    base_prompt = PROMPT + avoid_block

    for attempt in range(3):
        extra = f"\n\n(พยายามครั้งที่ {attempt + 1}: ข่าวก่อนหน้าซ้ำ เลือกเรื่องใหม่ที่ต่างออกไปเลย)" if attempt > 0 else ""
        post, url = _generate_post(base_prompt + extra)

        embedding = _get_embedding(post)
        if embedding and history:
            sim = _max_similarity(embedding, history)
            if sim >= SIM_HARD_REJECT:
                print(f"[dedup] attempt {attempt + 1} hard reject (similarity={sim:.3f}), retrying...")
                continue
            if sim >= SIM_LLM_CHECK:
                if _is_duplicate(post, history):
                    print(f"[dedup] attempt {attempt + 1} LLM reject (similarity={sim:.3f}), retrying...")
                    continue
        elif history:
            if _is_duplicate(post, history):
                print(f"[dedup] attempt {attempt + 1} LLM reject, retrying...")
                continue

        topic_label = _extract_topic_label(post)
        return post, url, topic_label

    print("[dedup] all retries exhausted, using last attempt")
    topic_label = _extract_topic_label(post)
    return post, url, topic_label
