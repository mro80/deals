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

HEADERS = {"Accept": "application/json"}

ENDPOINTS = [
    ("v01_list", "https://api.isthereanydeal.com/v01/deals/list/"),
    ("v02_list", "https://api.isthereanydeal.com/v02/deals/list/"),
    ("deals_v2", "https://api.isthereanydeal.com/deals/v2"),
    ("deals_v1", "https://api.isthereanydeal.com/deals/v1"),
]

def try_fetch(endpoint_key, url):
    params_common = {"key": ITAD_API_KEY, "country": "US"}
    if endpoint_key in ("v01_list", "v02_list"):
        params = {
            **params_common,
            "region": "us",
            "sort": "cut:desc",  # صيغة v0x القديمة
            "cut": MIN_DISCOUNT,
        }
    else:
        params = {
            **params_common,
            "limit": 50,
            "sort": "-cut",      # صيغة v2 الجديدة
            "nondeals": False,
            "mature": False,
        }
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    return r

def normalize_deals(endpoint_key, data):
    """تحويل النتائج لشكل موحّد: قائمة عناصر فيها title, price.cut, price.amount, price.currency, shop.name, url"""
    items = []
    if endpoint_key in ("v01_list", "v02_list"):
        # شكل v0x القديم: {"data":{"list":[{...}]}}
        for d in data.get("data", {}).get("list", []):
            items.append({
                "title": d.get("title"),
                "cut": d.get("price", {}).get("cut"),
                "amount": d.get("price", {}).get("amount"),
                "currency": d.get("price", {}).get("currency"),
                "shop": d.get("shop", {}).get("name"),
                "url": d.get("urls", {}).get("buy") or d.get("urls", {}).get("game"),
                "id": d.get("plain") or f"{d.get('title')}-{d.get('shop',{}).get('name')}",
            })
    else:
        # شكل v2/ v1 الجديد: {"list":[{"title":..., "deal":{ "price":{}, "shop":{}, "url":...}}]}
        for it in data.get("list", []):
            deal = it.get("deal", {}) or {}
            price = deal.get("price", {}) or {}
            items.append({
                "title": it.get("title"),
                "cut": price.get("cut"),
                "amount": price.get("amount"),
                "currency": price.get("currency"),
                "shop": (deal.get("shop") or {}).get("name"),
                "url": deal.get("url"),
                "id": it.get("id") or f"{it.get('title')}-{price.get('cut')}",
            })
    return items

def get_deals_auto():
    last_error = None
    for key, url in ENDPOINTS:
        try:
            r = try_fetch(key, url)
            print(f"Probe {key}: {r.status_code} → {r.url}")
            if r.status_code == 200:
                data = r.json()
                return key, normalize_deals(key, data)
            else:
                last_error = f"{key} -> {r.status_code}: {getattr(r, 'text', '')[:180]}"
        except Exception as e:
            last_error = f"{key} exception: {e}"
    raise RuntimeError(f"All endpoints failed. Last: {last_error}")

def main():
    send_discord(f"🚀 البوت اشتغل ويتابع الخصومات (≥{MIN_DISCOUNT}%).")
    seen = set()
    while True:
        try:
            endpoint_key, deals = get_deals_auto()
            print(f"Using endpoint: {endpoint_key} | Got {len(deals)}")
            for d in deals:
                if d["cut"] is None or d["cut"] < MIN_DISCOUNT or not d["url"]:
                    continue
                if d["id"] in seen: 
                    continue
                msg = f"🎮 **{d['title']}**\n📉 خصم: {d['cut']}%\n🏪 المتجر: {d['shop']}\n💰 السعر: {d['amount']} {d['currency']}\n🔗 {d['url']}"
                send_discord(msg)
                seen.add(d["id"])
        except Exception as e:
            print("Fetch error:", e)
            traceback.print_exc()
            send_discord(f"⚠️ خطأ أثناء جلب العروض: {e}")
        time.sleep(300)
