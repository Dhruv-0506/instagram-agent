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
    Verifies the webhook connection with Meta.
    User Input in Meta: https://.../webhook?my_secret=123
    """
    user_secret = request.args.get('my_secret')
    meta_token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if user_secret and meta_token and challenge:
        if user_secret == meta_token:
            return challenge, 200
            
    return 'Forbidden', 403

# ==============================================================================
# 2. FORWARDING (The Blind Pipe)
# ==============================================================================
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    """
    Forwards incoming events blindly to the target_url defined in the Webhook URL.
    """
    target_url = request.args.get('target_url')
    
    if not target_url:
        return jsonify({"status": "error", "message": "No target_url provided"}), 200

    try:
        requests.post(
            target_url, 
            json=request.json, 
            headers={"Content-Type": "application/json"},
            timeout=10
        )
    except Exception as e:
        logger.error(f"Failed to forward: {e}")

    return jsonify({"status": "forwarded"}), 200

# ==============================================================================
# 3. ACTIONS (Strict / Standardized)
# ==============================================================================

@app.route("/reply-dm", methods=["POST"])
def reply_dm():
    """
    SAFE MODE DM:
    - Triggers a DM (or Private Reply).
    - CONTENT: Strictly reads 'X-Standard-DM-Message' header. 
    - Ignores any dynamic text input.
    """
    # 1. Get Headers
    token = request.headers.get("X-Instagram-Token")
    standard_message = request.headers.get("X-Standard-DM-Message")
    
    # 2. Validation
    if not token: 
        return jsonify({"error": "Missing Header: X-Instagram-Token"}), 401
    if not standard_message:
        return jsonify({"error": "Missing Header: X-Standard-DM-Message (Safe Mode Active)"}), 400
        
    data = request.json
    
    # 3. Determine Target (User ID vs Comment ID)
    if data.get("comment_id"):
        recipient_payload = {"comment_id": data.get("comment_id")}
    elif data.get("recipient_id"):
        recipient_payload = {"id": data.get("recipient_id")}
    else:
        return jsonify({"error": "Must provide 'recipient_id' or 'comment_id'"}), 400

    # 4. Send the STRICT message
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={token}"
    payload = {
        "recipient": recipient_payload,
        "message": {"text": standard_message} # Uses header variable only
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reply-comment", methods=["POST"])
def reply_comment():
    """
    SAFE MODE PUBLIC REPLY:
    - Posts a public comment.
    - CONTENT: Strictly reads 'X-Standard-Public-Message' header.
    """
    token = request.headers.get("X-Instagram-Token")
    standard_message = request.headers.get("X-Standard-Public-Message")
    data = request.json
    
    if not token: 
        return jsonify({"error": "Missing Header: X-Instagram-Token"}), 401
    if not standard_message:
        return jsonify({"error": "Missing Header: X-Standard-Public-Message"}), 400
    if not data.get("comment_id"):
        return jsonify({"error": "Missing 'comment_id'"}), 400

    url = f"https://graph.facebook.com/v18.0/{data.get('comment_id')}/replies?access_token={token}"
    payload = {"message": standard_message} # Uses header variable only
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
