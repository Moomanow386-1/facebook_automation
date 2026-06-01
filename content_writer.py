import math
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

EMBED_MODEL = "text-embedding-004"
_RETRY_DELAYS = [30, 60]


def _with_retry(fn):
    for delay in _RETRY_DELAYS:
        try:
            return fn()
        except ServerError as exc:
            print(f"[retry] ServerError: {exc}, retrying in {delay}s…")
            time.sleep(delay)
    return fn()


SIM_HARD_REJECT = 0.95  # nearly identical text → hard block
SIM_LLM_CHECK   = 0.80  # ambiguous zone → let LLM decide


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

PROMPT = """ค้นหาข่าว tech, AI, หรือหุ้นเทคที่น่าสนใจที่สุดในช่วงนี้ แล้วเขียนโพสต์ Facebook ภาษาไทย 1 โพสต์

หัวข้อที่สนใจ: AI, ChatGPT, Claude, Gemini, OpenAI, Anthropic, Google, Meta AI, space, NASA, SpaceX, robot, semiconductor, quantum computing, หรือเทคโนโลยีใหม่ๆ

หรือข่าวหุ้น tech เช่น: NVDA (Nvidia), AMD, Intel, TSMC, Apple (AAPL), Microsoft (MSFT), Broadcom, ASML, Arm Holdings — เช่น ผลประกอบการ, guidance, ราคาหุ้น, demand chip, AI chip cycle, data center capex, analyst upgrade/downgrade

สไตล์การเขียน:
- ภาษาพูด casual เหมือนคนในวงการ tech คุยกัน
- ผสม Thai และ English อย่างเป็นธรรมชาติ
- ประโยคสั้น กระชับ อ่านง่าย
- เปิดด้วยเนื้อหาตรงๆ เช่น fact, ตัวเลข, หรือ statement เกี่ยวกับข่าวนั้นเลย ไม่ต้อง intro ว่า "มีข่าวมาก" หรือ "มาดูกัน"
- จบแบบหลากหลาย บางทีเป็นความคิดเห็นสั้นๆ บางทีเป็น statement ที่ทิ้งให้คิด บางทีเป็นคำถามก็ได้ แต่ไม่ต้องถามทุกโพสต์
- ความยาวหลากหลาย บางโพสต์สั้น 2-3 ประโยค บางโพสต์ยาว 5-7 ประโยค และบางโพสต์ที่เนื้อหาน่าสนใจมากๆ สามารถเขียนยาว 30-50 ประโยคได้เลย แต่ไม่ต้องทุกโพสต์
- ใช้ย่อหน้าแบ่งเนื้อหา ไม่ต้องเขียนต่อกันยาวๆ เป็นก้อนเดียว
- ท้ายโพสต์ใส่ hashtag ที่เกี่ยวข้อง 4-6 อัน ทั้ง Thai และ English

ห้าม:
- ห้ามขึ้นต้นด้วย meta-intro เช่น "ช่วงนี้มีข่าว..." "มาดูกันว่า..." "มีอะไรน่าสนใจเพียบ" — เริ่มด้วยเรื่องตรงๆ เลย
- ห้ามใช้คำอุทานเกินจริง เช่น "นะเนี่ย!" "เลยนะ!" "ของจริง!"
- ห้ามใช้ ! เลย ไม่แม้แต่ครั้งเดียว
- ห้ามใส่จุด (.) ท้ายประโยคสุดท้ายหรือท้ายโพสต์
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
            model="gemini-2.5-flash",
            contents=check_prompt,
        ))
        answer = res.text.strip().upper()
        return answer.startswith("YES")
    except Exception:
        return False


def _generate_post(prompt: str) -> tuple[str, str]:
    response = _with_retry(lambda: client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        ),
    ))
    post = response.text.strip()
    url = ""
    try:
        chunks = response.candidates[0].grounding_metadata.grounding_chunks
        for chunk in chunks:
            if hasattr(chunk, "web") and chunk.web.uri:
                uri = chunk.web.uri
                if "vertexaisearch" not in uri and "grounding-api-redirect" not in uri:
                    url = uri
                    break
        if not url and chunks:
            url = chunks[0].web.uri if hasattr(chunks[0], "web") else ""
    except Exception:
        pass
    return post, url


def write_post_with_search(posted_history: list[dict] | None = None) -> tuple[str, str]:
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
            # sim < SIM_LLM_CHECK → clearly different, skip LLM verify
        elif history:
            # no embedding available, fall back to LLM verify
            if _is_duplicate(post, history):
                print(f"[dedup] attempt {attempt + 1} LLM reject, retrying...")
                continue

        return post, url

    print("[dedup] all retries exhausted, using last attempt")
    return post, url
