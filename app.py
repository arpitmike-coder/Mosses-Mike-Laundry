import os
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# API Keys & URLs
GEMINI_API_KEY = "YAHAN_APNI_GEMINI_API_KEY_DALO"
WHATSAPP_TOKEN = "YAHAN_APNA_WHATSAPP_ACCESS_TOKEN_DALO"
PHONE_NUMBER_ID = "YAHAN_APNI_PHONE_NUMBER_ID_DALO"
VERIFY_TOKEN = "my_secret_token_123"
GOOGLE_WEB_APP_URL = "YAHAN_APNA_GOOGLE_APPS_SCRIPT_WEB_APP_URL_DALO"
OWNER_PHONE = "917355517322" # ओनर का नंबर नोटिफिकेशन के लिए

genai.configure(api_key=GEMINI_API_KEY)

system_instruction = """
You are a smart laundry booking assistant for "Moses Mike Laundry".
Rules:
1. First Message: When user says hi/hello/नमस्ते, reply:
"Welcome to Moses Mike Laundry 🧺
How can I help you today?
- 🧺 Book an order
- ℹ️ Rates
- 📦 Check order status"
2. If user wants Order: Collect Name, Mobile, Address, Service Type (Normal/Express), and Weight/Clothes. Provide slots: 9-12 PM, 12-3 PM, 3-6 PM, 6-9 PM. Once all details are given, generate Order ID (First 4 letters of name + Last 4 digits of mobile, e.g., RAHU3210). Confirm order and notify owner.
3. If user asks for Rates: Fetch and show rates.
4. If user asks for Order Status: Ask for Order ID.
5. Match user's language (Hindi/English/Hinglish). Keep replies short and friendly.
"""

model = genai.GenerativeModel(model_name='gemini-1.5-flash', system_instruction=system_instruction)

@app.route("/", methods=["GET"])
def home():
    return "Moses Mike Laundry Bot is Live!"

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        if "entry" in data and data["entry"][0]["changes"][0]["value"].get("messages"):
            value = data["entry"][0]["changes"][0]["value"]
            phone_number_id = value["metadata"]["phone_number_id"]
            message = value["messages"][0]
            from_mobile = message["from"]
            msg_body = message["text"]["body"]

            # अगर यूजर rates मांग रहा है, तो Google Sheet से सीधे ले आओ
            if "rate" in msg_body.lower() or "price" in msg_body.lower() or "कीमत" in msg_body.lower():
                sheet_res = requests.get(GOOGLE_WEB_APP_URL).text
                reply_text = f"Here are our current rates:\n\n{sheet_res}"
            
            # अगर यूजर आर्डर स्टेटस चेक करना चाहता है
            elif "status" in msg_body.lower() or "order id" in msg_body.lower():
                # यहाँ हम Gemini से पूछेंगे या सीधा Google Sheet चेक करेंगे
                ai_response = model.generate_content(f"User is asking about order status or message: {msg_body}. Help them.")
                reply_text = ai_response.text
            
            else:
                # सामान्य बातचीत या बुकिंग के लिए Gemini AI का इस्तेमाल
                ai_response = model.generate_content(msg_body)
                reply_text = ai_response.text

            # WhatsApp पर जवाब भेजें
            send_whatsapp_message(phone_number_id, from_mobile, reply_text)

    except Exception as e:
        print(f"Error: {e}")

    return jsonify({"status": "success"}), 200

def send_whatsapp_message(phone_number_id, to_number, message):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": message}}
    requests.post(f"https://graph.facebook.com/v18.0/{phone_number_id}/messages", json=payload, headers=headers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)