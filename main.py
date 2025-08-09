import os
import sys
import time
import traceback
import requests

print(">>> booting", flush=True)
print(">>> imports ok", flush=True)

# قراءة القيم من المتغيرات البيئية
ITAD_API_KEY = os.environ.get("ITAD_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
MIN_DISCOUNT = 15  # أقل نسبة خصم

# إرسال رسالة إلى الديسكورد
def send_discord(content):
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=15)
        print(f"Discord status: {r.status_code} {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"❌ Discord send failed: {e}", flush=True)

# جلب العروض
def get_deals_auto():
    url = f"https://api.isthereanydeal.com/v01/deals/list/"
    params = {
        "key": ITAD_API_KEY,
        "region": "us",
        "country": "US",
        "sort": "cut:desc",
        "cut": MIN_DISCOUNT
    }
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("data", {}).get("list", [])
    else:
        print(f"❌ HTTP error: {resp.status_code} - {resp.text[:200]}", flush=True)
        return []

def main():
    print(">>> entered main()", flush=True)
    
    # Ping عند بدء التشغيل
    try:
        send_discord(f"✅ البوت بدأ التشغيل — سيعرض الخصومات {MIN_DISCOUNT}%+")
    except Exception as e:
        print("❌ فشل إرسال Ping:", e, flush=True)

    seen = set()

    while True:
        try:
            deals = get_deals_auto()
            print(f"Got {len(deals)} deals", flush=True)

            for d in deals:
                if d["cut"] is None or d["cut"] < MIN_DISCOUNT or not d["urls"]["buy"]:
                    continue
                if d["id"] in seen:
                    continue

                msg = f"🎮 **{d['title']}**\nخصم: {d['cut']}%\nالمتجر: {d['shop']['name']}\n💰 السعر: {d['price']['amount']} {d['price']['currency']}\n🔗 {d['urls']['buy']}"
                send_discord(msg)
                seen.add(d["id"])

        except Exception as e:
            print(f"⚠ Fetch error: {e}", flush=True)
            traceback.print_exc()
            send_discord(f"⚠ خطأ أثناء جلب العروض: {e}")

        time.sleep(300)  # 5 دقائق

if __name__ == "__main__":
    print(">>> calling main()", flush=True)
    main()
