from google import genai
from config import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """คุณคือคนเขียนเนื้อหาให้เพจ Facebook สายเทคโนโลยีภาษาไทย

สไตล์:
- ภาษาพูด casual แต่ให้ข้อมูลถูกต้อง เหมือนคนในวงการ tech คุยกัน
- ผสม Thai และ English อย่างเป็นธรรมชาติ
- ประโยคสั้น กระชับ อ่านง่าย
- เปิดด้วย hook ที่ชวนอ่านต่อ
- จบด้วยคำถามหรือ comment กระตุ้นให้คิด
- ยาว 3-5 ประโยค

ห้ามทำ:
- ห้ามใช้คำอุทานเกินจริง เช่น "นะเนี่ย!" "เลยนะ!" "ของจริง!" "โห!" "เฮ้ย!"
- ห้ามใช้เครื่องหมายอัศเจรีย์ (!) มากเกิน 1 ครั้งต่อโพสต์
- ห้ามใช้ emoji มากเกิน 1 ตัว
- ห้ามขึ้นต้นด้วย "มีข่าว" หรือ "ล่าสุด"
- ห้ามพูดถึง link หรือแหล่งที่มาในโพสต์

ท้ายโพสต์ใส่ hashtag ที่เกี่ยวข้อง 4-6 อัน ทั้งภาษาไทยและอังกฤษ เช่น #AI #เทคโนโลยี #ChatGPT #ปัญญาประดิษฐ์"""


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
