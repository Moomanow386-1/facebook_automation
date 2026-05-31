from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """คุณคือคนเขียนเนื้อหาให้เพจ Facebook สายเทคโนโลยีภาษาไทย
สไตล์การเขียน:
- ใช้ภาษาพูดที่เป็นธรรมชาติ อ่านแล้วรู้สึกเหมือนคนจริงๆ เขียน ไม่ใช่ AI
- ผสม Thai และ English อย่างเป็นธรรมชาติ เช่น "AI ตัวนี้มันเก่งจริงๆ"
- ประโยคสั้น กระชับ เข้าใจง่าย
- มีความ casual แต่ให้ข้อมูลที่ถูกต้อง
- เปิดด้วย hook ที่น่าสนใจ ไม่ใช่แค่บอกว่า "มีข่าวใหม่"
- บางทีใช้ภาษาแบบ "โห", "เฮ้ย", "จริงป่ะ" ได้ตามความเหมาะสม
- จบด้วย comment สั้นๆ หรือคำถามกระตุ้นให้คิด
- ยาว 3-5 ประโยค พอดี ไม่ต้องยาวเกิน
- ห้ามใช้ emoji มากเกิน 2-3 ตัว
- ห้ามใช้ hashtag"""


def write_post(title: str, summary: str, source: str) -> str:
    prompt = f"""{SYSTEM_PROMPT}

ข่าว: {title}
รายละเอียด: {summary}
แหล่งที่มา: {source}

เขียนโพสต์ Facebook ภาษาไทยจากข่าวนี้:"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text.strip()
