from google import genai
from google.genai import types
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

PROMPT = """ค้นหาข่าว tech หรือ AI ที่น่าสนใจที่สุดในช่วงนี้ แล้วเขียนโพสต์ Facebook ภาษาไทย 1 โพสต์

หัวข้อที่สนใจ: AI, ChatGPT, Claude, Gemini, OpenAI, Anthropic, Google, Meta AI, space, NASA, SpaceX, robot, semiconductor, quantum computing, หรือเทคโนโลยีใหม่ๆ

สไตล์การเขียน:
- ภาษาพูด casual เหมือนคนในวงการ tech คุยกัน
- ผสม Thai และ English อย่างเป็นธรรมชาติ
- ประโยคสั้น กระชับ อ่านง่าย
- เปิดด้วย hook ที่ชวนอ่านต่อ
- จบแบบหลากหลาย บางทีเป็นความคิดเห็นสั้นๆ บางทีเป็น statement ที่ทิ้งให้คิด บางทีเป็นคำถามก็ได้ แต่ไม่ต้องถามทุกโพสต์
- ยาว 3-5 ประโยค
- ท้ายโพสต์ใส่ hashtag ที่เกี่ยวข้อง 4-6 อัน ทั้ง Thai และ English

ห้าม:
- ห้ามใช้คำอุทานเกินจริง เช่น "นะเนี่ย!" "เลยนะ!" "ของจริง!"
- ห้ามใช้ ! มากเกิน 1 ครั้ง
- ห้ามใช้ emoji มากเกิน 1 ตัว
- ห้ามพูดถึง link ในโพสต์

ห้ามใส่ URL หรือ SOURCE_URL ในโพสต์"""


def write_post_with_search() -> tuple[str, str]:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        ),
    )
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
