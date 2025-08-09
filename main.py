import os
import sys
import time
import traceback
import requests

# ===== الإعدادات من متغيرات البيئة =====
ITAD_API_KEY = os.getenv("ITAD_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
MIN_DISCOUNT = 15  # أقل نسبة خصم للتنبيه

# فحص المتغيرات الأساسية
if not ITAD_API_KEY or not DISCORD_WEBHOOK_URL:
    print("❌ مفقود:", "ITAD_API_KEY" if not ITAD_API_KEY else "",
          "DISCORD_WEBHOOK_URL" if not DISCORD_WEBHOOK_URL else "")
    sys.exit(1)

def send_discord(text: str):
    """يرسل رسالة نصية لقناة الديسكورد ويطبع حالة الاستجابة."""
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": text}, timeout=15)
        print("Discord status:", r.status_code, r.text[:200])
        return r.status_code
    except Exception as e:
        print("❌ Discord error:", e)
        return None

def get_deals():
    """
    يجلب قائمة العروض من API الجديد:
    GET https://api.isthereanydeal.com/deals/v2
    أهم البراميترات:
      - key     : API key
      - country : رمز الدولة
      - limit   : عدد النتائج
      - sort    : -cut (أعلى خصم أولاً)
      - nondeals: لا تعرض العناصر اللي ما عليها خصم
    """
    url = "https://api.isthereanydeal.com/deals/v2"
    params = {
        "key": ITAD_API_KEY,
        "country": "US",
        "limit": 50,
        "sort": "-cut",      # أعلى خصم أولاً
        "nondeals": False,
        "mature": False
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    # البنية الجديدة: {"list":[{ "title":..., "deal": { "price":{...}, "shop":{...}, "url":... }, ...}], ...}
    return data.get("list", [])

def format_msg(item):
    deal = item.get("deal", {}) or {}
    title = item.get("title", "Unknown")
    shop = (deal.get("shop") or {}).get("name")
    price = deal.get("price") or {}
    cut = price.get("cut")
    amount = price.get("amount")
    curr = price.get("currency")
    url = deal.get("url") or ""
    return f"🎮 **{title}**\n📉 خصم: {cut}%\n🏪 المتجر: {shop}\n💰 السعر: {amount} {curr}\n🔗 {url}"

def main():
    # رسالة تشغيل
    send_discord(f"🚀 البوت اشتغل ويتابع الخصومات (≥{MIN_DISCOUNT}%).")

    seen = set()
    while True:
        try:
            deals = get_deals()
            print(f"Got {len(deals)} deals")
            for item in deals:
                # استخراج نسبة الخصم
                cut = ((item.get("deal") or {}).get("price") or {}).get("cut")
                if cut is None or cut < MIN_DISCOUNT:
                    continue

                # معرّف فريد للعرض لمنع التكرار
                deal_id = item.get("id") or f"{item.get('title')}-{cut}-{(item.get('deal') or {}).get('url','')}"

                if deal_id in seen:
                    continue

                msg = format_msg(item)
                send_discord(msg)
                seen.add(deal_id)

        except requests.HTTPError as e:
            # أخطاء HTTP من API
            body = ""
            try:
                body = e.response.text[:200]
            except Exception:
                pass
            print("HTTP error:", e, body)
            send_discord(f"⚠️ خطأ من API: {e}")
        except Exception as e:
            print("Unhandled error:", e)
            traceback.print_exc()
            send_discord(f"⚠️ صار خطأ غير متوقع: {e}")

        # افحص كل 15 دقيقة
        time.sleep(900)

if __name__ == "__main__":
    main()
