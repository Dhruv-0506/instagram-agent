from flask import Flask, request, jsonify
import logging
import requests
import os

app = Flask(__name__)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# You set this in your OnDemand environment variables or .env file
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "my_secret_token")

# --- 1. Webhook Verification (Meta Standard) ---
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    Meta calls this to verify your server exists.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
            logger.info("Meta Webhook Verified Successfully.")
            return challenge, 200
    
    logger.error("Webhook Verification Failed.")
    return 'Forbidden', 403

# --- 2. Webhook Listener (Read DMs & Comments) ---
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """
    Receives real-time updates from Instagram.
    Extracts the data so you can process it.
    """
    data = request.json
    
    # Simple check to ensure it's an Instagram event
    if data.get('object') != 'instagram':
        return jsonify({"status": "ignored"}), 200

    for entry in data.get('entry', []):
        page_id = entry.get('id')

        # --- Handle DMs ---
        if 'messaging' in entry:
            for event in entry['messaging']:
                sender_id = event.get('sender', {}).get('id')
                message_text = event.get('message', {}).get('text')
                
                if message_text:
                    logger.info(f"New DM received from {sender_id}: {message_text}")
                    
                    # TODO: CONNECT YOUR LOGIC HERE
                    # This is where you would send this data to your separate agent.
                    # Example: requests.post("YOUR_OTHER_AGENT_URL", json={...})

        # --- Handle Comments ---
        if 'changes' in entry:
            for change in entry['changes']:
                if change.get('field') == 'comments':
                    val = change.get('value', {})
                    comment_id = val.get('id')
                    text = val.get('text')
                    sender_id = val.get('from', {}).get('id')

                    if text:
                        logger.info(f"New Comment received from {sender_id}: {text}")
                        
                        # TODO: CONNECT YOUR LOGIC HERE
                        # Example: requests.post("YOUR_OTHER_AGENT_URL", json={...})

    return jsonify({"status": "processed"}), 200

# --- 3. Action: Reply to DM (Uses Header Auth) ---
@app.route("/reply-dm", methods=["POST"])
def reply_dm():
    """
    Sends a reply to an Instagram DM.
    Reads 'X-Instagram-Token' from headers.
    """
    # 1. Get Token from Header (User Input)
    token = request.headers.get("X-Instagram-Token")
    
    # 2. Get Message Data
    data = request.json
    recipient_id = data.get("recipient_id")
    message = data.get("message")

    # 3. Validation
    if not token:
        return jsonify({"error": "Missing Header: X-Instagram-Token"}), 401
    if not recipient_id or not message:
        return jsonify({"error": "Missing body fields: recipient_id or message"}), 400

    # 4. Call Meta API
    url = f"https://graph.facebook.com/v18.0/me/messages"
    params = {"access_token": token}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message}
    }

    try:
        res = requests.post(url, params=params, json=payload, timeout=10)
        res.raise_for_status() # Raise error for bad responses (4xx, 5xx)
        return jsonify(res.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Meta API Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- 4. Action: Reply to Comment (Uses Header Auth) ---
@app.route("/reply-comment", methods=["POST"])
def reply_comment():
    """
    Replies to a specific Instagram Comment.
    Reads 'X-Instagram-Token' from headers.
    """
    token = request.headers.get("X-Instagram-Token")
    
    data = request.json
    comment_id = data.get("comment_id")
    message = data.get("message")

    if not token:
        return jsonify({"error": "Missing Header: X-Instagram-Token"}), 401
    if not comment_id or not message:
        return jsonify({"error": "Missing body fields: comment_id or message"}), 400

    url = f"https://graph.facebook.com/v18.0/{comment_id}/replies"
    params = {"access_token": token}
    payload = {"message": message}

    try:
        res = requests.post(url, params=params, json=payload, timeout=10)
        res.raise_for_status()
        return jsonify(res.json())
    except requests.exceptions.RequestException as e:
        logger.error(f"Meta API Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
