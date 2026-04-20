from flask import Flask, jsonify
from threading import Thread
import logging
import time

app = Flask(__name__)
logger = logging.getLogger(__name__)
start_time = time.time()

@app.route('/')
def home():
    return """
    <html>
    <head>
        <title>Alurb Bot - 24/7 Active</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 10px;
                max-width: 600px;
                margin: 0 auto;
            }
            h1 { font-size: 3em; margin: 0; }
            .status { color: #4ade80; font-weight: bold; }
            .footer { margin-top: 30px; opacity: 0.8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Alurb Bot</h1>
            <p class="status">✅ 24/7 Active & Online</p>
            <p>Telegram Godfather Bot with DeepSeek AI</p>
            <div class="footer">
                <p>© dev_nappier 😂🫡</p>
                <p>Powered by OpenRouter AI</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    uptime = time.time() - start_time
    return jsonify({
        "status": "healthy",
        "bot": "Alurb Telegram Bot",
        "uptime_seconds": int(uptime),
        "ai_model": "DeepSeek Chat V3",
        "copyright": "dev_nappier 😂🫡"
    })

@app.route('/ping')
def ping():
    return "pong", 200

def run():
    """Run Flask server"""
    try:
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Keep-alive server error: {e}")

def keep_alive():
    """Start keep-alive server in thread"""
    t = Thread(target=run)
    t.daemon = True
    t.start()
    logger.info(f"🌐 Keep-alive server started on port {os.environ.get('PORT', 8080)}")

# Import here to avoid circular import
import os
