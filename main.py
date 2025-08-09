import requests
import time
import os  # نضيف استيراد مكتبة os

# إعدادات - نقرأ من متغيرات البيئة
ITAD_API_KEY = os.environ["ITAD_API_KEY"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
MIN_DISCOUNT = 15  # أقل خصم للتنبيه

def get_deals():
    url = "https://api.isthereanydeal.com/v01/deals/list/"
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
        print("خطأ في الاتصال بالموقع:", resp.status_code)
        return []

def send_to_discord(deal):
    title = deal['title']
    discount = deal['price']['cut']
    shop = deal['shop']['name']
    price = deal['price']['amount']
    currency = deal['price']['currency']
    url = deal['urls']['buy']

    message = f"🎮 **{title}**\n💰 السعر: {price} {currency}\n📉 خصم: {discount}%\n🏪 المتجر: {shop}\n🔗 [رابط الشراء]({url})"
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})

def main():
    seen = set()
    while True:
        deals = get_deals()
        for deal in deals:
            deal_id = deal['plain']
            if deal_id not in seen:
                send_to_discord(deal)
                seen.add(deal_id)
        time.sleep(3600)  # كل ساعة يبحث عن خصومات جديدة

if __name__ == "__main__":
    main()
