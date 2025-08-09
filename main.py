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
    """يرسل رسالة نصية لقناة الديسكورد عبر الويب هوك ويطبع حالة الاستجابة."""
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": text}, timeout=15)
        print("Discord status:", r.status_code, r.text[:200])
        return r.status_code
    except Exception as e:
        print("❌ Discord error:", e)
        return None

def get_deals():
    """يجلب قائمة العروض من IsThereAnyDeal ويعيدها كقائمة (قد تكون فاضية)."""
    url = "https://api.isthereanydeal.com/v01/deals/list/"
    params = {
        "key": ITAD_API_KEY,
        "region": "us",
        "country": "US",
        "sort": "cut:desc",
        "cut": MIN_DISCOUNT,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    # البنية الشائعة: {"data": {"list": [...]}}
    return data.get("data", {}).get("list", [])

def format_msg(d):
    title = d.get("title") or d.get("game", {}).get("title", "Unknown")
    price = d.get("price", {})
    cut = price.get("cut")
    amount = price.get("amount")
    curr = price.get("currency")
    shop = d.get("shop", {}).get("name")
    url = d.get("urls", {}).get("buy") or d.get("urls", {}).get("game") or ""
    return f"🎮 **{title}**\n📉 خصم: {cut}%\n🏪 المتجر: {shop}\n💰 السعر: {amount} {curr}\n🔗 {url}"

def main():
    # رسالة تشغيل
    send_discord(f"🚀 البوت اشتغل ويتابع الخصومات (≥{MIN_DISCOUNT}%).")

    seen = set()
    while True:
        try:
            deals = get_deals()
            print(f"Got {len(deals)} deals")
            for d in deals:
                price_cut = d.get("price", {}).get("cut")
                if price_cut is None or price_cut < MIN_DISCOUNT:
                    continue
                deal_id = d.get("plain") or f"{d.get('title')}-{d.get('shop',{}).get('name')}-{price_cut}"
                if deal_id in seen:
                    continue
                msg = format_msg(d)
                send_discord(msg)
                seen.add(deal_id)
        except requests.HTTPError as e:
            # أخطاء HTTP من API
            print("HTTP error:", e, getattr(e, "response", None) and getattr(e.response, "text", "")[:200])
            send_discord(f"⚠️ خطأ من API: {e}")
        except Exception as e:
            print("Unhandled error:", e)
            traceback.print_exc()
            send_discord(f"⚠️ صار خطأ غير متوقع: {e}")
        # افحص كل 15 دقيقة
        time.sleep(900)

if __name__ == "__main__":
    main()

