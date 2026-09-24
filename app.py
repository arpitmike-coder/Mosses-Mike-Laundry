import os
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# ================= CONFIGURATIONS =================
# Yahan apni asli API keys ya to direct dalen ya Render ke environment variables se uthayein
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YAHAN_APNI_GEMINI_API_KEY_DALO")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "YAHAN_APNA_WHATSAPP_ACCESS_TOKEN_DALO")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "YAHAN_APNI_PHONE_NUMBER_ID_DALO")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "my_secret_token_123")
GOOGLE_WEB_APP_URL = os.environ.get("GOOGLE_WEB_APP_URL", "YAHAN_APNA_GOOGLE_APPS_SCRIPT_WEB_APP_URL_DALO")
OWNER_PHONE = "917355517322"

# Gemini API configure karen
genai.configure(api_key=GEMINI_API_KEY)

# Temperature 0.0 taaki AI apni taraf se internet ki koi extra baat na soche (Strict Boundary Rule)
generation_config = {
    "temperature": 0.0,
}

system_instruction = """
You are a strict and professional laundry booking assistant for "Moses Mike Laundry".

CRITICAL RULE (Strict Boundary):
- DO NOT use your general knowledge, internet data, or external assumptions.
- You must ONLY and STRICTLY answer based on the provided instructions, Pricing sheet, and FAQ sheet.
- If a user asks a question whose answer is NOT present in your instructions, Pricing, or FAQs, you must strictly reply:
  "Maaf kijiye, mujhe iski jankari nahi hai 🙏 Kripya humare owner se is number par sampark karein: +91 7355517322"

Rules:
1. First Message: When user sends hi/hello/नमस्ते, reply:
"Welcome to Moses Mike Laundry 🧺
How can I help you today?
- 🧺 Book an order
- ℹ️ Rates
- 📦 Check order status"

2. If user wants Order Booking: Collect Name, Mobile, Address, Service Type (Normal/Express), and Weight/Clothes. Provide slots: 9-12 PM, 12-3 PM, 3-6 PM, 6-9 PM. Once all details are given, generate Order ID (First 4 letters of name + Last 4 digits of mobile, e.g., RAHU3210). Confirm order.

3. Match the user's language (Hindi/English/Hinglish). Keep replies short, polite, and strictly to the point.
"""

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=system_instruction,
    generation_config=generation_config
)

@app.route("/", methods=["GET"])
def home():
    return "Moses Mike Laundry Bot is Live!"

# Meta Webhook Verification
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return "Verification failed", 403
    return "Hello World", 200

# Incoming WhatsApp Messages Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Incoming Data:", data)

    try:
        if "entry" in data and \
           data["entry"][0]["changes"] and \
           "messages" in data["entry"][0]["changes"][0]["value"]:
            
            value = data["entry"][0]["changes"][0]["value"]
            phone_number_id = value["metadata"]["phone_number_id"]
            
            message = value["messages"][0]
            from_mobile = message["from"]
            msg_body = message["text"]["body"]
            
            print(f"Message received from {from_mobile}: {msg_body}")

            # 1. Agar user rates ya price maange toh direct Google Sheet (Pricing tab) se laayein
            if any(word in msg_body.lower() for word in ["rate", "price", "कीमत", "रेट", "rates"]):
                try:
                    sheet_res = requests.get(f"{GOOGLE_WEB_APP_URL}?type=pricing").text
                    reply_text = sheet_res
                except Exception as e:
                    reply_text = "Sorry, unable to fetch rates right now."
            
            # 2. Baki sabhi messages ke liye FAQ data fetch karke Gemini ko dein
            else:
                try:
                    faq_data = requests.get(f"{GOOGLE_WEB_APP_URL}?type=faq").text
                except Exception as e:
                    faq_data = "No FAQ data available."

                prompt = f"""
                Here is the official FAQ list and database from our store:
                {faq_data}

                User's message: "{msg_body}"
                
                Instructions: Answer the user's question accurately based ONLY on the FAQ data or system instructions above. If it's a greeting, reply with the welcome menu.
                """
                ai_response = model.generate_content(prompt)
                reply_text = ai_response.text

            # WhatsApp par response bhejen
            send_whatsapp_message(phone_number_id, from_mobile, reply_text)

    except Exception as e:
        print(f"Error: {e}")

    return jsonify({"status": "success"}), 200

def send_whatsapp_message(phone_number_id, to_number, message):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message},
    }
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
    response = requests.post(url, json=payload, headers=headers)
    print("WhatsApp Send Response:", response.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)