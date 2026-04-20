import telebot
import time
import os
import json
import threading
import logging
from datetime import datetime
import requests
from keep_alive import keep_alive

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
PORT = int(os.environ.get('PORT', 8080))

# OpenRouter AI Configuration
AI_CONFIG = {
    "api_key": "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",
    "base_url": "https://openrouter.ai/api/v1",
    "model": "deepseek/deepseek-chat-v3-0324:free",
    "language": "English"
}

bot = telebot.TeleBot(BOT_TOKEN)

# Data storage
DATA_DIR = "bot_data"
os.makedirs(DATA_DIR, exist_ok=True)

PREMIUM_USERS = {}
OWNERS = []
BOT_START_TIME = time.time()
GROUP_IDS = set()
USER_CONVERSATIONS = {}  # Store conversation history for AI

def load_data():
    """Load all data from JSON files"""
    global PREMIUM_USERS, OWNERS, GROUP_IDS
    try:
        with open(f"{DATA_DIR}/premium.json", "r") as f:
            PREMIUM_USERS = json.load(f)
        logger.info(f"Loaded {len(PREMIUM_USERS)} premium users")
    except:
        PREMIUM_USERS = {}
    
    try:
        with open(f"{DATA_DIR}/owners.json", "r") as f:
            OWNERS = json.load(f)
        logger.info(f"Loaded {len(OWNERS)} owners")
    except:
        OWNERS = []
    
    try:
        with open(f"{DATA_DIR}/groups.json", "r") as f:
            GROUP_IDS = set(json.load(f))
        logger.info(f"Loaded {len(GROUP_IDS)} groups")
    except:
        GROUP_IDS = set()

def save_data():
    """Save all data to JSON files"""
    with open(f"{DATA_DIR}/premium.json", "w") as f:
        json.dump(PREMIUM_USERS, f)
    with open(f"{DATA_DIR}/owners.json", "w") as f:
        json.dump(OWNERS, f)
    with open(f"{DATA_DIR}/groups.json", "w") as f:
        json.dump(list(GROUP_IDS), f)

def is_owner(user_id):
    return str(user_id) in OWNERS

def is_premium(user_id):
    return str(user_id) in PREMIUM_USERS

def ai_chat(messages, user_id):
    """Send request to OpenRouter AI API"""
    try:
        headers = {
            "Authorization": f"Bearer {AI_CONFIG['api_key']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/AlurbBot",  # Required for OpenRouter
            "X-Title": "Alurb Telegram Bot"  # Your bot name
        }
        
        payload = {
            "model": AI_CONFIG["model"],
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            f"{AI_CONFIG['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            logger.error(f"AI API Error: {response.status_code} - {response.text}")
            return "❌ AI service temporarily unavailable. Please try again later."
            
    except Exception as e:
        logger.error(f"AI Request Error: {e}")
        return "❌ Error connecting to AI service."

# Load initial data
load_data()

# Keep-alive server for Render
keep_alive()

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    welcome_text = f"""
╔══════════════════════╗
     🤖 WELCOME TO ALURB BOT 🤖
╚══════════════════════╝

👋 Hello {username}!

🔰 Bot Features:
• 24/7 Online Status
• AI Assistant (DeepSeek V3)
• Premium Management  
• Owner Management
• Group Management
• And much more!

📌 Use /help to see all commands
🏠 Bot Status: Active 24/7 ✅

🤖 AI Model: DeepSeek Chat V3
💡 Try /ask <your question>

━━━━━━━━━━━━━━━━━━━━━━
© dev_nappier 😂🫡
Powered by Alurb Bot System
    """
    bot.reply_to(message, welcome_text)
    
    if message.chat.type in ['group', 'supergroup']:
        GROUP_IDS.add(str(message.chat.id))
        save_data()

@bot.message_handler(commands=['pair'])
def pair_command(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ You don't have permission to use this command!")
        return
    
    try:
        token = message.text.split(' ', 1)[1]
        bot.reply_to(message, f"✅ Pairing bot with token: {token[:10]}...\n⚠️ Note: This is a simulated pairing system.")
        logger.info(f"Pair attempt by user {user_id}")
    except:
        bot.reply_to(message, "❌ Usage: /pair <bot_token>")

@bot.message_handler(commands=['addprem'])
def add_premium(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        target_id = message.text.split(' ', 1)[1]
        PREMIUM_USERS[target_id] = {
            "added_by": user_id,
            "date": str(datetime.now()),
            "expires": None
        }
        save_data()
        bot.reply_to(message, f"✅ User {target_id} added to premium list!")
        logger.info(f"User {target_id} added to premium by {user_id}")
    except:
        bot.reply_to(message, "❌ Usage: /addprem <user_id>")

@bot.message_handler(commands=['delprem'])
def del_premium(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        target_id = message.text.split(' ', 1)[1]
        if target_id in PREMIUM_USERS:
            del PREMIUM_USERS[target_id]
            save_data()
            bot.reply_to(message, f"✅ User {target_id} removed from premium list!")
        else:
            bot.reply_to(message, f"❌ User {target_id} not found in premium list!")
    except:
        bot.reply_to(message, "❌ Usage: /delprem <user_id>")

@bot.message_handler(commands=['addowner'])
def add_owner(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id) and len(OWNERS) > 0:
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        target_id = message.text.split(' ', 1)[1]
        if target_id not in OWNERS:
            OWNERS.append(target_id)
            save_data()
            bot.reply_to(message, f"✅ User {target_id} added as owner!")
            logger.info(f"New owner added: {target_id}")
        else:
            bot.reply_to(message, f"⚠️ User {target_id} is already an owner!")
    except:
        bot.reply_to(message, "❌ Usage: /addowner <user_id>")

@bot.message_handler(commands=['delowner'])
def del_owner(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        target_id = message.text.split(' ', 1)[1]
        if target_id in OWNERS:
            OWNERS.remove(target_id)
            save_data()
            bot.reply_to(message, f"✅ User {target_id} removed from owners!")
        else:
            bot.reply_to(message, f"❌ User {target_id} not found in owners list!")
    except:
        bot.reply_to(message, "❌ Usage: /delowner <user_id>")

@bot.message_handler(commands=['listprem'])
def list_premium(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    if PREMIUM_USERS:
        text = "📋 PREMIUM USERS LIST:\n\n"
        for idx, (uid, data) in enumerate(PREMIUM_USERS.items(), 1):
            text += f"{idx}. ID: `{uid}`\n   Added: {data['date']}\n\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    else:
        bot.reply_to(message, "📋 No premium users found!")

@bot.message_handler(commands=['cekidgrup'])
def check_group(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id) and not is_premium(user_id):
        bot.reply_to(message, "❌ Premium or Owner only command!")
        return
    
    chat_id = message.chat.id
    chat_type = message.chat.type
    
    if chat_type in ['group', 'supergroup']:
        bot.reply_to(message, f"📱 Current Group ID: `{chat_id}`\n📝 Group Type: {chat_type}", parse_mode="Markdown")
        GROUP_IDS.add(str(chat_id))
        save_data()
    else:
        bot.reply_to(message, f"💬 This is a private chat!\nYour Chat ID: `{chat_id}`", parse_mode="Markdown")

@bot.message_handler(commands=['listidgrup'])
def list_groups(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    if GROUP_IDS:
        text = "📋 ALL GROUP IDs:\n\n"
        for idx, gid in enumerate(GROUP_IDS, 1):
            text += f"{idx}. `{gid}`\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    else:
        bot.reply_to(message, "📋 No groups recorded yet!")

@bot.message_handler(commands=['silencer'])
def silencer_attack(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id) and not is_premium(user_id):
        bot.reply_to(message, "❌ Premium or Owner only command!")
        return
    
    try:
        number = int(message.text.split(' ', 1)[1])
        
        msg = bot.reply_to(message, f"🔇 Starting silencer attack with {number} threads...")
        
        def cpu_stress():
            while True:
                _ = [x**2 for x in range(10000)]
        
        threads = []
        for _ in range(min(number, 10)):
            t = threading.Thread(target=cpu_stress)
            t.daemon = True
            t.start()
            threads.append(t)
        
        bot.edit_message_text(f"✅ Silencer attack active!\nThreads: {len(threads)}\nTarget: Device CPU", 
                            message.chat.id, msg.message_id)
        logger.info(f"Silencer attack initiated by {user_id} with {number} threads")
    except:
        bot.reply_to(message, "❌ Usage: /silencer <number>")

@bot.message_handler(commands=['crash'])
def crash_attack(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        number = int(message.text.split(' ', 1)[1])
        bot.reply_to(message, f"💥 Initiating crash attack...\nForce: {number}")
        
        def memory_eater():
            data = []
            while True:
                data.append("X" * 1024 * 1024)
                
        for _ in range(min(number, 5)):
            t = threading.Thread(target=memory_eater)
            t.daemon = True
            t.start()
            
        bot.reply_to(message, f"✅ Crash attack initiated with {number} threads!")
    except:
        bot.reply_to(message, "❌ Usage: /crash <number>")

@bot.message_handler(commands=['xdelay'])
def xdelay_attack(message):
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id) and not is_premium(user_id):
        bot.reply_to(message, "❌ Premium or Owner only command!")
        return
    
    try:
        delay_time = int(message.text.split(' ', 1)[1])
        
        msg = bot.reply_to(message, f"⏱ Applying heavy delay of {delay_time}ms...")
        
        time.sleep(delay_time / 1000)
        
        bot.edit_message_text(f"✅ Delay completed!\nDuration: {delay_time}ms", 
                            message.chat.id, msg.message_id)
    except:
        bot.reply_to(message, "❌ Usage: /xdelay <milliseconds>")

@bot.message_handler(commands=['ask'])
def ask_ai(message):
    user_id = str(message.from_user.id)
    
    try:
        query = message.text.split(' ', 1)[1]
        
        # Send typing indicator
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Initialize conversation for user if not exists
        if user_id not in USER_CONVERSATIONS:
            USER_CONVERSATIONS[user_id] = [
                {"role": "system", "content": f"You are a helpful AI assistant for Alurb Telegram Bot. Respond in {AI_CONFIG['language']}. Be concise and friendly. © dev_nappier"}
            ]
        
        # Add user message to conversation
        USER_CONVERSATIONS[user_id].append({"role": "user", "content": query})
        
        # Keep conversation history limited (last 10 messages)
        if len(USER_CONVERSATIONS[user_id]) > 11:
            USER_CONVERSATIONS[user_id] = [USER_CONVERSATIONS[user_id][0]] + USER_CONVERSATIONS[user_id][-10:]
        
        # Get AI response
        ai_response = ai_chat(USER_CONVERSATIONS[user_id], user_id)
        
        # Add AI response to conversation
        USER_CONVERSATIONS[user_id].append({"role": "assistant", "content": ai_response})
        
        # Send response
        response_text = f"""
🤖 **AI Assistant Response**

💭 **Question:** _{query}_

📝 **Answer:**
{ai_response}

━━━━━━━━━━━━━━━━━━━━━━
🤖 Model: DeepSeek Chat V3
💡 Ask anything! I'm here 24/7
© dev_nappier 😂🫡
        """
        
        bot.reply_to(message, response_text, parse_mode="Markdown")
        logger.info(f"AI query from {user_id}: {query[:50]}...")
        
    except IndexError:
        bot.reply_to(message, "❌ Usage: /ask <your question>")
    except Exception as e:
        logger.error(f"AI command error: {e}")
        bot.reply_to(message, "❌ Error processing your request. Please try again.")

@bot.message_handler(commands=['clearai'])
def clear_ai_history(message):
    """Clear AI conversation history"""
    user_id = str(message.from_user.id)
    
    if user_id in USER_CONVERSATIONS:
        del USER_CONVERSATIONS[user_id]
        bot.reply_to(message, "✅ AI conversation history cleared!")
    else:
        bot.reply_to(message, "ℹ️ No conversation history found.")

@bot.message_handler(commands=['status'])
def bot_status(message):
    user_id = str(message.from_user.id)
    
    uptime = time.time() - BOT_START_TIME
    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    
    status_text = f"""
╔══════════════════════╗
       🤖 BOT STATUS 🤖
╚══════════════════════╝

📊 Current Statistics:
━━━━━━━━━━━━━━━━━━━━━━
✅ Bot Status: 24/7 Active
⏰ Uptime: {days}d {hours}h {minutes}m
👑 Total Owners: {len(OWNERS)}
💎 Premium Users: {len(PREMIUM_USERS)}
📱 Groups Joined: {len(GROUP_IDS)}
💬 Active AI Chats: {len(USER_CONVERSATIONS)}
👤 Your Status: {'👑 Owner' if is_owner(user_id) else '💎 Premium' if is_premium(user_id) else '👤 User'}

🛠 System Info:
━━━━━━━━━━━━━━━━━━━━━━
🤖 AI Model: DeepSeek Chat V3
🌐 Language: {AI_CONFIG['language']}
🔧 Python Telebot v{telebot.__version__}
📡 Response Time: Optimal
🔄 Auto-Restart: Enabled

━━━━━━━━━━━━━━━━━━━━━━
Powered by Alurb Bot System
© dev_nappier 😂🫡
    """
    bot.reply_to(message, status_text)

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = str(message.from_user.id)
    
    help_text = f"""
╔══════════════════════╗
     📚 COMMAND MENU 📚
╚══════════════════════╝

𖤊───⪩ OWNER MENU ⪨───𖤊
✦ /pair <token> - Add bot
✦ /addprem <id> - Add premium
✦ /delprem <id> - Remove premium
✦ /addowner <id> - Add owner
✦ /delowner <id> - Remove owner
✦ /listprem - Premium list
✦ /cekidgrup - Group ID
✦ /listidgrup - All groups

𖤊───⪩ BUG MENU ⪨───𖤊
✦ /silencer <num> - Crash Dvc
✦ /crash <num> - System crash
✦ /xdelay <num> - Heavy delay

𖤊───⪩ AI MENU ⪨───𖤊
✦ /ask <query> - Ask AI (DeepSeek V3)
✦ /clearai - Clear AI history
✦ /status - Bot status

━━━━━━━━━━━━━━━━━━━━━━
🤖 AI Model: DeepSeek Chat V3
🌐 Language: {AI_CONFIG['language']}
👤 Your Level: {'👑 Owner' if is_owner(user_id) else '💎 Premium' if is_premium(user_id) else '👤 User'}
🔄 Bot runs 24/7 with auto-restart
© dev_nappier 😂🫡
    """
    bot.reply_to(message, help_text)

@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def track_groups(message):
    GROUP_IDS.add(str(message.chat.id))
    if len(GROUP_IDS) % 10 == 0:
        save_data()

# ==================== MAIN RUNNER ====================

def run_bot():
    """Run bot with automatic restart on failure"""
    logger.info("🚀 Starting Alurb Bot - 24/7 Mode with DeepSeek AI")
    logger.info(f"🤖 AI Model: {AI_CONFIG['model']}")
    logger.info(f"📊 Loaded {len(OWNERS)} owners, {len(PREMIUM_USERS)} premium users")
    
    if len(OWNERS) == 0:
        logger.warning("⚠️ No owners set! First user to run /addowner will become owner.")
    
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Network connection error: {e}")
            time.sleep(10)
        except requests.exceptions.ReadTimeout as e:
            logger.error(f"Read timeout error: {e}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Bot crashed with error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
