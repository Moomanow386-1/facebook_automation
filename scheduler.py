import schedule
import time
from poster import post_text
from token_checker import check_token


def job_example():
    result = post_text("โพสต์อัตโนมัติ!")
    print(f"Posted: {result}")


# ตัวอย่าง: โพสต์ทุกวัน เวลา 09:00
schedule.every().day.at("09:00").do(job_example)

# เช็ก token ทุกวัน 08:00
schedule.every().day.at("08:00").do(check_token)

if __name__ == "__main__":
    print("Scheduler running...")
    check_token()
    while True:
        schedule.run_pending()
        time.sleep(60)
