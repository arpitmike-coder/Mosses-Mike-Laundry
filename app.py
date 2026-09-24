import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ================= CONFIGURATIONS =================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mosses191218")
GOOGLE_WEB_APP_URL = os.environ.get("GOOGLE_WEB_APP_URL", "")
OWNER_PHONE = "917355517322"

system_instruction = """
You are a strict and professional laundry booking assistant for "Moses Mike Laundry".

CRITICAL RULE (Strict Boundary):
- DO NOT use your general knowledge, internet data, or external assumptions.
- You must ONLY and STRICTLY answer based on the provided instructions, Pricing sheet, and FAQ sheet.
- If a user asks a question whose answer is NOT present in your instructions, Pricing, or FAQs, you must strictly reply:
  "Maaf kijiye, mujhe iski jankari nahi hai. Kripya humare owner se is number par sampark karein: +91 7355517322"

Rules:
1. First Message: When user sends hi/hello/namaste, reply:
"Welcome to Moses Mike Laundry
How can I help you today?
- Book an order
- Rates
- Check order status"

2. If user wants Order Booking: Collect Name, Mobile, Address, Service Type (Normal/Express), and Weight/Clothes. Provide slots: 9-12 PM, 12-3 PM, 3-6 PM, 6-9 PM. Once all details are given, generate Order ID (First 4 letters of name + Last 4 digits of mobile, e.g., RAHU3210). Confirm order.

3. Match the user's language (Hindi/English/Hinglish). Keep replies short, polite, and strictly to the point.
"""

@app.route("/", methods=["GET"])
def home():
    return "Moses Mike Laundry Bot with ChatGPT is Live!"

# ================= WEBHOOK =================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        actual_verify_token = os.environ.get("VERIFY_TOKEN", "mosses191218")

        if mode and token:
            if mode == "subscribe" and token == actual_verify_token:
                print("WEBHOOK_VERIFIED")
                return challenge, 200
            else:
                return "Verification failed: Token mismatch", 403
        return "Webhook endpoint is active", 200

    elif request.method == "POST":
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

                reply_text = "Welcome to Moses Mike Laundry!"

                # Pricing check
                if any(word in msg_body.lower() for word in ["rate", "price", "kimat", "rates"]):
                    try:
                        sheet_res = requests.get(f"{GOOGLE_WEB_APP_URL}?type=pricing").text
                        reply_text = sheet_res
                    except Exception as e:
                        print(f"Error fetching pricing: {e}")
                        reply_text = "Sorry, unable to fetch rates right now."
                
                # FAQ & OpenAI ChatGPT check
                else:
                    faq_data = "No FAQ data available."
                    try:
                        faq_data = requests.get(f"{GOOGLE_WEB_APP_URL}?type=faq").text
                    except Exception as e:
                        print(f"Error fetching FAQ: {e}")

                    # OpenAI API Request Setup
                    headers = {
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": f"Here is the official FAQ list and database from our store:\n{faq_data}\n\nUser's message: '{msg_body}'"}
                        ],
                        "temperature": 0.0
                    }

                    try:
                        openai_res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                        res_json = openai_res.json()
                        
                        if "choices" in res_json:
                            reply_text = res_json["choices"][0]["message"]["content"]
                        else:
                            print("OpenAI Error Response:", res_json)
                            reply_text = f"Technical Error: {res_json.get('error', {}).get('message', 'Unknown error')}"
                    except Exception as ai_err:
                        print(f"OpenAI Request Exception: {ai_err}")
                        reply_text = f"Technical Error: {str(ai_err)}"

                # Send response to customer
                send_whatsapp_message(phone_number_id, from_mobile, reply_text)

                # Send notification to owner if order confirmed
                if "order id" in reply_text.lower() or "confirmed" in reply_text.lower():
                    owner_notification = f"New Order Alert!\n\nCustomer: {from_mobile}\nDetails/Reply: {reply_text}"
                    send_whatsapp_message(phone_number_id, OWNER_PHONE, owner_notification)

        except Exception as e:
            print(f"Error processing message: {e}")

        return jsonify({"status": "success"}), 200

def send_whatsapp_message(phone_number_id, to_number, message):
    current_token = os.environ.get("WHATSAPP_TOKEN", WHATSAPP_TOKEN)
    headers = {
        "Authorization": f"Bearer {current_token}",
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
