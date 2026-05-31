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
- จบด้วยคำถามหรือ comment กระตุ้นให้คิด
- ยาว 3-5 ประโยค
- ท้ายโพสต์ใส่ hashtag ที่เกี่ยวข้อง 4-6 อัน ทั้ง Thai และ English

ห้าม:
- ห้ามใช้คำอุทานเกินจริง เช่น "นะเนี่ย!" "เลยนะ!" "ของจริง!"
- ห้ามใช้ ! มากเกิน 1 ครั้ง
- ห้ามใช้ emoji มากเกิน 1 ตัว
- ห้ามพูดถึง link ในโพสต์

ท้ายสุด บรรทัดสุดท้าย ให้ใส่ SOURCE_URL: [url ของบทความ] เพื่อให้ระบบดึงไปใส่คอมเมนต์"""


def write_post_with_search() -> tuple[str, str]:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        ),
    )
    text = response.text.strip()

    url = ""
    lines = text.splitlines()
    post_lines = []
    for line in lines:
        if line.startswith("SOURCE_URL:"):
            url = line.replace("SOURCE_URL:", "").strip()
        else:
            post_lines.append(line)

    post = "\n".join(post_lines).strip()
    return post, url
