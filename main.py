import os
import time
import requests
import feedparser
import re

# الإعدادات
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
MIN_DISCOUNT = 15  # أقل نسبة خصم

# رابط RSS من موقع IsThereAnyDeal (حدد الدولة لو حاب)
RSS_URL = "https://isthereanydeal.com/rss/?country=Sa"

def send_discord(message):
    """يرسل رسالة إلى قناة الديسكورد عبر Webhook"""
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        print(f"Discord status: {resp.status_code}")
    except Exception as e:
        print(f"❌ خطأ أثناء إرسال رسالة للديسكورد: {e}")

def parse_cut_from_title(title):
    """يحاول استخراج نسبة الخصم من العنوان"""
    m = re.search(r'(-?\d+)\s*%', title)
    if not m:
        return None
    try:
        return int(m.group(1))
    except:
        return None

def get_deals_auto():
    """يجلب العروض من RSS ويحولها لقائمة موحدة"""
    feed = feedparser.parse(RSS_URL)
    items = []
    for e in feed.entries:
        title = e.title
        link = e.link
        cut = parse_cut_from_title(title)
        deal_id = getattr(e, "id", None) or link or title
        items.append({
            "title": title,
            "cut": cut,
            "amount": None,
            "currency": "",
            "shop": "",
            "url": link,
            "id": deal_id
        })
    return "rss", items

def main():
    try:
        send_discord(f"✅ البوت تشتغل ويبلغ الخصومات (≥{MIN_DISCOUNT}%)")
        print("تم إرسال إشعار تشغيل البوت")
    except Exception as e:
        print("❌ خطأ أثناء إرسال إشعار التشغيل:", e)

    seen = set()
    while True:
        try:
            endpoint_key, deals = get_deals_auto()
            print(f"Using endpoint: {endpoint_key} | Got {len(deals)} deals")

            for d in deals:
                if d["cut"] is None or d["cut"] < MIN_DISCOUNT or not d["url"]:
                    continue
                if d["id"] in seen:
                    continue

                msg = (
                    f"🎮 **{d['title']}**\n"
                    f"📉 خصم: {d['cut']}%\n"
                    f"🔗 {d['url']}"
                )
                send_discord(msg)
                seen.add(d["id"])

        except Exception as e:
            print(f"⚠ Fetch error: {e}")
            send_discord(f"⚠ مشكلة أثناء جلب العروض: {e}")

        time.sleep(120)  # كل 5 دقائق

if __name__ == "__main__":
    print(">>> booting")
    main()
