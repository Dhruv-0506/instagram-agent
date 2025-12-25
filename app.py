from flask import Flask, request, jsonify
import logging
import requests

app = Flask(__name__)

# Basic logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. VERIFICATION (The Handshake)
# ==============================================================================
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    User Input in Meta: 
    Callback URL: https://your-app.com/webhook?my_secret=12345
    Verify Token: 12345
    """
    # 1. Get the secret the USER embedded in the URL
    user_secret_in_url = request.args.get('my_secret')
    
    # 2. Get the token META is sending
    meta_token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # 3. Compare them.
    if user_secret_in_url and meta_token and challenge:
        if user_secret_in_url == meta_token:
            return challenge, 200
            
    return 'Forbidden', 403

# ==============================================================================
# 2. FORWARDING (The Blind Pipe)
# ==============================================================================
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """
    User Input in Meta:
    Callback URL: https://your-app.com/webhook?target_url=https://other-agent.com/api
    """
    # 1. Read the destination from the URL
    target_url = request.args.get('target_url')
    
    if not target_url:
        return jsonify({"status": "error", "message": "No target_url provided"}), 200

    # 2. Forward the data blindly.
    try:
        requests.post(
            target_url, 
            json=request.json, 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
    except Exception as e:
        logger.error(f"Failed to forward: {e}")

    # Always return 200 to Meta so they don't ban your webhook
    return jsonify({"status": "forwarded"}), 200

# ==============================================================================
# 3. ACTIONS (Reply via Header Auth)
# ==============================================================================
@app.route("/reply-dm", methods=["POST"])
def reply_dm():
    token = request.headers.get("X-Instagram-Token")
    data = request.json
    
    if not token: 
        return jsonify({"error": "Missing X-Instagram-Token header"}), 401

    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={token}"
    payload = {
        "recipient": {"id": data.get("recipient_id")},
        "message": {"text": data.get("message")}
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reply-comment", methods=["POST"])
def reply_comment():
    token = request.headers.get("X-Instagram-Token")
    data = request.json
    
    if not token: 
        return jsonify({"error": "Missing X-Instagram-Token header"}), 401

    url = f"https://graph.facebook.com/v18.0/{data.get('comment_id')}/replies?access_token={token}"
    payload = {"message": data.get("message")}
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
