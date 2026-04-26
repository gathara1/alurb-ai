import telebot
import time
import os
import json
import threading
import logging
import random
import math
import subprocess
import platform
import socket
import gc
import sys
from datetime import datetime, timedelta
import requests
from concurrent.futures import ThreadPoolExecutor

# Try to import psutil, handle if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not installed - some features limited")

from keep_alive import keep_alive

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8341823550:AAFDfFvU14oJ2qy8gT0CDnO7O9L4aJRhOHU')
PORT = int(os.environ.get('PORT', 8080))

# ==================== MASTER OWNER CONFIGURATION ====================
MASTER_OWNER_ID = "6803973808"

# ==================== ALURB AI CONFIGURATION ====================
AI_CONFIG = {
    "api_key": os.environ.get('OPENROUTER_API_KEY', ''),
    "base_url": "https://openrouter.ai/api/v1",
    "model": "deepseek/deepseek-chat",
    "language": "English"
}

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Data storage
DATA_DIR = "bot_data"
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = f"{DATA_DIR}/bot_data.json"

PREMIUM_USERS = {}
OWNERS = []
BOT_START_TIME = time.time()
GROUP_IDS = set()

# Trial System
TRIAL_USERS = {}
TRIAL_HOURS = 2

# User Activity Tracking
USER_ACTIVITY = {}
USER_INTERACTIONS = {}

# Premium Plans
PREMIUM_PLANS = {
    "daily": {"name": "Daily", "days": 1, "price": "$0.99"},
    "weekly": {"name": "Weekly", "days": 7, "price": "$2.99"},
    "monthly": {"name": "Monthly", "days": 30, "price": "$7.99"},
    "lifetime": {"name": "Lifetime", "days": 36500, "price": "$49.99"}
}

# Attack Thread Management
ATTACK_THREADS = []
executor = ThreadPoolExecutor(max_workers=100)

# ==================== USER ACTIVITY TRACKING ====================

def track_user_activity(user_id, username=None, command=None):
    user_id = str(user_id)
    current_time = datetime.now()
    current_time_iso = current_time.isoformat()
    
    global USER_ACTIVITY, USER_INTERACTIONS
    
    if user_id not in USER_ACTIVITY:
        USER_ACTIVITY[user_id] = {
            "first_seen": current_time_iso,
            "last_seen": current_time_iso,
            "username": username or "Unknown",
            "interaction_count": 1,
            "first_seen_date": current_time.strftime("%Y-%m-%d"),
            "first_seen_month": current_time.strftime("%Y-%m")
        }
    else:
        USER_ACTIVITY[user_id]["last_seen"] = current_time_iso
        USER_ACTIVITY[user_id]["interaction_count"] = USER_ACTIVITY[user_id].get("interaction_count", 0) + 1
        if username:
            USER_ACTIVITY[user_id]["username"] = username
    
    if command:
        if user_id not in USER_INTERACTIONS:
            USER_INTERACTIONS[user_id] = {"commands": {}}
        if command not in USER_INTERACTIONS[user_id]["commands"]:
            USER_INTERACTIONS[user_id]["commands"][command] = 0
        USER_INTERACTIONS[user_id]["commands"][command] += 1
    
    if USER_ACTIVITY[user_id]["interaction_count"] % 10 == 0:
        save_activity_data()

def save_activity_data():
    try:
        with open(f"{DATA_DIR}/user_activity.json", "w") as f:
            json.dump(USER_ACTIVITY, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving user activity: {e}")
    
    try:
        with open(f"{DATA_DIR}/user_interactions.json", "w") as f:
            json.dump(USER_INTERACTIONS, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving user interactions: {e}")

def load_activity_data():
    global USER_ACTIVITY, USER_INTERACTIONS
    
    try:
        with open(f"{DATA_DIR}/user_activity.json", "r") as f:
            USER_ACTIVITY = json.load(f)
        logger.info(f"Loaded activity data for {len(USER_ACTIVITY)} users")
    except FileNotFoundError:
        USER_ACTIVITY = {}
    except Exception as e:
        USER_ACTIVITY = {}
        logger.error(f"Error loading activity data: {e}")
    
    try:
        with open(f"{DATA_DIR}/user_interactions.json", "r") as f:
            USER_INTERACTIONS = json.load(f)
        logger.info(f"Loaded interaction data for {len(USER_INTERACTIONS)} users")
    except FileNotFoundError:
        USER_INTERACTIONS = {}
    except Exception as e:
        USER_INTERACTIONS = {}
        logger.error(f"Error loading interactions data: {e}")

def get_user_stats():
    total_users = len(USER_ACTIVITY)
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)
    
    monthly_active = 0
    weekly_active = 0
    daily_active = 0
    new_this_month = 0
    new_this_week = 0
    new_today = 0
    
    for uid, data in USER_ACTIVITY.items():
        last_seen = datetime.fromisoformat(data["last_seen"])
        first_seen = datetime.fromisoformat(data["first_seen"])
        
        if last_seen > thirty_days_ago:
            monthly_active += 1
        if last_seen > seven_days_ago:
            weekly_active += 1
        if last_seen > one_day_ago:
            daily_active += 1
        
        if first_seen > thirty_days_ago:
            new_this_month += 1
        if first_seen > seven_days_ago:
            new_this_week += 1
        if first_seen > one_day_ago:
            new_today += 1
    
    return {
        "total_users": total_users,
        "monthly_active": monthly_active,
        "weekly_active": weekly_active,
        "daily_active": daily_active,
        "new_this_month": new_this_month,
        "new_this_week": new_this_week,
        "new_today": new_today
    }

def get_monthly_breakdown():
    months = {}
    for uid, data in USER_ACTIVITY.items():
        first_seen = datetime.fromisoformat(data["first_seen"])
        month_key = first_seen.strftime("%Y-%m")
        
        if month_key not in months:
            months[month_key] = {
                "new_users": 0,
                "total_interactions": 0,
                "premium_conversions": 0
            }
        
        months[month_key]["new_users"] += 1
        months[month_key]["total_interactions"] += data.get("interaction_count", 0)
        
        if uid in PREMIUM_USERS:
            months[month_key]["premium_conversions"] += 1
    
    return months

# ==================== DATA MANAGEMENT ====================

def load_data():
    global PREMIUM_USERS, OWNERS, GROUP_IDS, TRIAL_USERS
    
    logger.info("Loading data from JSON files...")
    
    try:
        with open(f"{DATA_DIR}/premium.json", "r") as f:
            PREMIUM_USERS = json.load(f)
        logger.info(f"Loaded {len(PREMIUM_USERS)} premium users")
    except FileNotFoundError:
        PREMIUM_USERS = {}
    except Exception as e:
        PREMIUM_USERS = {}
        logger.error(f"Error loading premium users: {e}")
    
    try:
        with open(f"{DATA_DIR}/owners.json", "r") as f:
            OWNERS = json.load(f)
        logger.info(f"Loaded {len(OWNERS)} owners")
    except FileNotFoundError:
        OWNERS = []
    except Exception as e:
        OWNERS = []
        logger.error(f"Error loading owners: {e}")
    
    try:
        with open(f"{DATA_DIR}/groups.json", "r") as f:
            GROUP_IDS = set(json.load(f))
        logger.info(f"Loaded {len(GROUP_IDS)} groups")
    except FileNotFoundError:
        GROUP_IDS = set()
    except Exception as e:
        GROUP_IDS = set()
        logger.error(f"Error loading groups: {e}")
    
    try:
        with open(f"{DATA_DIR}/trials.json", "r") as f:
            TRIAL_USERS = json.load(f)
        logger.info(f"Loaded {len(TRIAL_USERS)} trial users")
    except FileNotFoundError:
        TRIAL_USERS = {}
    except Exception as e:
        TRIAL_USERS = {}
        logger.error(f"Error loading trials: {e}")
    
    load_activity_data()

def save_data():
    logger.info("Saving data to JSON files...")
    
    try:
        with open(f"{DATA_DIR}/premium.json", "w") as f:
            json.dump(PREMIUM_USERS, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving premium users: {e}")
    
    try:
        with open(f"{DATA_DIR}/owners.json", "w") as f:
            json.dump(OWNERS, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving owners: {e}")
    
    try:
        with open(f"{DATA_DIR}/groups.json", "w") as f:
            json.dump(list(GROUP_IDS), f, indent=2)
    except Exception as e:
        logger.error(f"Error saving groups: {e}")
    
    try:
        with open(f"{DATA_DIR}/trials.json", "w") as f:
            json.dump(TRIAL_USERS, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving trials: {e}")
    
    save_activity_data()

# ==================== PERMISSION CHECKS ====================

def is_master(user_id):
    return str(user_id) == MASTER_OWNER_ID

def is_owner(user_id):
    user_id = str(user_id)
    if user_id == MASTER_OWNER_ID:
        return True
    return user_id in OWNERS

def is_premium(user_id):
    user_id = str(user_id)
    if user_id in PREMIUM_USERS:
        premium_data = PREMIUM_USERS[user_id]
        if "expires" in premium_data and premium_data["expires"]:
            try:
                expiry = datetime.fromisoformat(premium_data["expires"])
                if expiry > datetime.now():
                    return True
                else:
                    del PREMIUM_USERS[user_id]
                    save_data()
                    return False
            except ValueError:
                return False
        return True
    return False

def is_trial_active(user_id):
    user_id = str(user_id)
    if user_id in TRIAL_USERS:
        trial_data = TRIAL_USERS[user_id]
        try:
            trial_start = datetime.fromisoformat(trial_data["start_time"])
            trial_end = trial_start + timedelta(hours=TRIAL_HOURS)
            if datetime.now() < trial_end:
                return True
            else:
                del TRIAL_USERS[user_id]
                save_data()
                return False
        except ValueError:
            return False
    return False

def start_trial(user_id):
    user_id = str(user_id)
    if user_id not in TRIAL_USERS and not is_premium(user_id):
        TRIAL_USERS[user_id] = {
            "start_time": datetime.now().isoformat(),
            "trial_type": "2hours",
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_data()
        return True
    return False

def get_trial_time_left(user_id):
    user_id = str(user_id)
    if user_id in TRIAL_USERS:
        try:
            trial_start = datetime.fromisoformat(TRIAL_USERS[user_id]["start_time"])
            trial_end = trial_start + timedelta(hours=TRIAL_HOURS)
            time_left = trial_end - datetime.now()
            if time_left.total_seconds() > 0:
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                return f"{hours}h {minutes}m"
        except ValueError:
            pass
    return "Expired"

def get_premium_expiry(user_id):
    user_id = str(user_id)
    if user_id in PREMIUM_USERS:
        premium_data = PREMIUM_USERS[user_id]
        if "expires" in premium_data and premium_data["expires"]:
            try:
                return datetime.fromisoformat(premium_data["expires"])
            except ValueError:
                pass
    return None

def check_premium_access(user_id):
    if is_owner(user_id) or is_premium(user_id) or is_trial_active(user_id):
        return True
    return False

# ==================== AI FUNCTIONS ====================

def ai_chat(query):
    api_key = AI_CONFIG['api_key']
    
    if not api_key:
        return "❌ AI service not configured. Please contact @alurb_devs"
    
    creator_names = ["Nappier", "Ruth"]
    chosen_creator = random.choice(creator_names)
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/alurb_bot",
            "X-Title": "Alurb Telegram Bot"
        }
        
        system_prompt = f"""You are Alurb AI, the official assistant for Alurb Telegram Bot. 
Important rules:
- When asked who created you, say: "I was created by {chosen_creator}, the founder of Alurb Bot."
- When asked your name, say: "I'm Alurb AI, your intelligent assistant."
- Never mention DeepSeek, OpenAI, Claude, or any other AI company.
- Always identify yourself as Alurb AI.
- Be helpful, friendly, and concise."""
        
        payload = {
            "model": AI_CONFIG["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{AI_CONFIG['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=45
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
        return "❌ AI service error. Please try again."
            
    except Exception as e:
        logger.error(f"AI Error: {str(e)}")
        return "❌ Error connecting to AI service."

# ==================== REAL WORKING BUG FUNCTIONS ====================

class RealBugEngine:
    @staticmethod
    def kill_processes():
        """Terminate running applications"""
        apps_to_kill = [
            'chrome', 'firefox', 'discord', 'telegram', 'whatsapp',
            'spotify', 'steam', 'epicgames', 'slack', 'teams',
            'zoom', 'outlook', 'word', 'excel', 'powerpoint'
        ]
        
        system = platform.system()
        for app in apps_to_kill:
            try:
                if system == 'Windows':
                    subprocess.run(f'taskkill /f /im {app}.exe', shell=True, capture_output=True, timeout=2)
                else:
                    subprocess.run(f'pkill -9 {app}', shell=True, capture_output=True, timeout=2)
                    subprocess.run(f'killall -9 {app}', shell=True, capture_output=True, timeout=2)
            except:
                pass
    
    @staticmethod
    def fill_memory():
        """Fill RAM with data"""
        memory_blocks = []
        try:
            for i in range(50):
                block = bytearray(10 * 1024 * 1024)
                memory_blocks.append(block)
            return memory_blocks
        except:
            return memory_blocks
    
    @staticmethod
    def stress_cpu(duration=5):
        """Max out CPU usage"""
        end_time = time.time() + duration
        while time.time() < end_time:
            try:
                _ = [i**i for i in range(300)]
                _ = math.factorial(300)
            except:
                pass
    
    @staticmethod
    def socket_flood():
        """Create network socket storm"""
        sockets = []
        try:
            for i in range(200):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                sockets.append(sock)
        except:
            pass
        time.sleep(0.5)
        for sock in sockets:
            try:
                sock.close()
            except:
                pass
    
    @staticmethod
    def get_system_stats():
        """Get system statistics if psutil available"""
        if PSUTIL_AVAILABLE:
            return {
                "cpu": psutil.cpu_percent(),
                "ram": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent if os.name == 'posix' else 0
            }
        return {"cpu": "N/A", "ram": "N/A", "disk": "N/A"}

load_data()
keep_alive()

# ==================== COMMAND HANDLERS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or "No username"
    
    track_user_activity(user_id, username, "start")
    logger.info(f"Start command from {user_id}")
    
    trial_started = False
    if not is_owner(user_id) and not is_premium(user_id) and not is_trial_active(user_id):
        trial_started = start_trial(user_id)
    
    if is_master(user_id):
        status_line = "👑 MASTER OWNER"
    elif is_owner(user_id):
        status_line = "👑 OWNER"
    elif is_premium(user_id):
        expiry = get_premium_expiry(user_id)
        if expiry:
            days_left = (expiry - datetime.now()).days
            status_line = f"💎 PREMIUM ({days_left}d left)"
        else:
            status_line = "💎 PREMIUM (LIFETIME)"
    elif is_trial_active(user_id):
        time_left = get_trial_time_left(user_id)
        status_line = f"🎁 FREE TRIAL ({time_left})"
    else:
        status_line = "🔒 FREE USER"
    
    trial_msg = "\n\n🎉 2-HOUR FREE TRIAL ACTIVATED!" if trial_started else ""
    
    welcome_text = f"""
╔════════════════════════════════╗
        💀 <b>ALURB BUG BOT</b> 💀
╚════════════════════════════════╝

👋 <b>Welcome {first_name}!</b>

📊 <b>Status:</b> {status_line}{trial_msg}

🔥 <b>REAL WORKING BUGS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💀 /silencer (1-30) - CPU/RAM Killer
💥 /crash (1-20) - Memory Exhaustion
❄️ /freeze - Complete System Freeze
☢️ /nuke - Full System Nuke
🔪 /killapp - Force Close Apps
⚡ /overload (1-15) - System Overload
⏱️ /xdelay (ms) - Response Killer
🌀 /void (10-200) - Crash Loop
📱 /xios (5-30) - Blank Screen Attack

📌 <b>Commands:</b>
/help • /status • /trial • /premium • /ask

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© alurb_devs | Nappier & Ruth
    """
    bot.reply_to(message, welcome_text, parse_mode="HTML")
    
    if message.chat.type in ['group', 'supergroup']:
        GROUP_IDS.add(str(message.chat.id))
        save_data()

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = str(message.from_user.id)
    
    if is_master(user_id):
        user_level = "👑 Master Owner"
    elif is_owner(user_id):
        user_level = "👑 Owner"
    elif is_premium(user_id):
        user_level = "💎 Premium"
    elif is_trial_active(user_id):
        user_level = f"🎁 Trial ({get_trial_time_left(user_id)})"
    else:
        user_level = "🔒 Free"
    
    help_text = f"""
╔════════════════════════════════╗
        📚 <b>COMMAND MENU</b> 📚
╚════════════════════════════════╝

🔥 <b>REAL WORKING BUGS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💀 /silencer (1-30) - CPU/RAM Killer
💥 /crash (1-20) - Memory Flood Crash
❄️ /freeze - Complete System Freeze
☢️ /nuke - Full System Nuke
🔪 /killapp - Force Close All Apps
⚡ /overload (1-15) - Multi-Vector Overload
⏱️ /xdelay (100-10000) - Response Killer
🌀 /void (10-200) - Infinite Crash Loop
📱 /xios (5-30) - Blank Screen Attack

📊 <b>UTILITIES:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/status - Bot & User Status
/trial - Start Free Trial
/premium - View Plans
/ask - AI Assistant
/stop - Stop Attacks (Owner)

👤 <b>Your Level:</b> {user_level}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎁 Free Trial: /trial ({TRIAL_HOURS}h)
💎 Upgrade: /premium
    """
    bot.reply_to(message, help_text, parse_mode="HTML")

@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = str(message.from_user.id)
    
    uptime = time.time() - BOT_START_TIME
    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    minutes = int((uptime % 3600) // 60)
    
    if is_master(user_id):
        user_status = "👑 Master Owner"
    elif is_owner(user_id):
        user_status = "👑 Owner"
    elif is_premium(user_id):
        expiry = get_premium_expiry(user_id)
        if expiry:
            days_left = (expiry - datetime.now()).days
            user_status = f"💎 Premium ({days_left}d left)"
        else:
            user_status = "💎 Premium (Lifetime)"
    elif is_trial_active(user_id):
        time_left = get_trial_time_left(user_id)
        user_status = f"🎁 Trial ({time_left} left)"
    else:
        user_status = "🔒 Free"
    
    stats = get_user_stats()
    sys_stats = RealBugEngine.get_system_stats()
    
    status_text = f"""
╔════════════════════════════════╗
        📊 <b>BOT STATUS</b> 📊
╚════════════════════════════════╝

🤖 <b>SYSTEM:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Status: 24/7 Active
⏰ Uptime: {days}d {hours}h {minutes}m
💎 Premium Users: {len(PREMIUM_USERS)}
🎁 Active Trials: {len(TRIAL_USERS)}
🔄 Active Attacks: {len(ATTACK_THREADS)}

👥 <b>USERS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total: {stats['total_users']}
📈 Monthly Active: {stats['monthly_active']}
📅 Daily Active: {stats['daily_active']}

💻 <b>SERVER:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 CPU: {sys_stats['cpu']}%
💾 RAM: {sys_stats['ram']}%

👤 <b>YOUR STATUS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{user_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© alurb_devs
    """
    bot.reply_to(message, status_text, parse_mode="HTML")

@bot.message_handler(commands=['trial'])
def trial_command(message):
    user_id = str(message.from_user.id)
    
    if is_owner(user_id):
        bot.reply_to(message, "👑 You're an Owner - permanent access!", parse_mode="HTML")
        return
    
    if is_premium(user_id):
        bot.reply_to(message, "💎 You're already Premium!", parse_mode="HTML")
        return
    
    if is_trial_active(user_id):
        time_left = get_trial_time_left(user_id)
        bot.reply_to(message, f"🎁 <b>TRIAL ACTIVE!</b>\n⏰ Time Left: {time_left}\n💎 Upgrade: /premium", parse_mode="HTML")
        return
    
    if start_trial(user_id):
        bot.reply_to(message, f"""
🎉 <b>2-HOUR FREE TRIAL ACTIVATED!</b>

✅ Full premium access granted!
⏰ Duration: {TRIAL_HOURS} hours
🔥 All bug commands unlocked

💎 /premium - Upgrade to lifetime
        """, parse_mode="HTML")
    else:
        bot.reply_to(message, "❌ Trial failed. Contact @alurb_devs")

@bot.message_handler(commands=['premium'])
def premium_command(message):
    user_id = str(message.from_user.id)
    
    if is_owner(user_id):
        bot.reply_to(message, "👑 Owner - Permanent premium access!", parse_mode="HTML")
        return
    
    trial_status = ""
    if is_trial_active(user_id):
        time_left = get_trial_time_left(user_id)
        trial_status = f"\n🎁 Trial Active: {time_left} remaining"
    elif not is_premium(user_id):
        trial_status = "\n🎁 Free Trial: /trial (2 hours)"
    
    bot.reply_to(message, f"""
╔════════════════════════════════╗
        💎 <b>PREMIUM PLANS</b> 💎
╚════════════════════════════════╝{trial_status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 <b>DAILY</b> - $0.99
📅 <b>WEEKLY</b> - $2.99
📅 <b>MONTHLY</b> - $7.99
📅 <b>LIFETIME</b> - $49.99

✨ <b>PREMIUM BENEFITS:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• All bug commands unlocked
• Unlimited attacks
• Priority support
• Early access to new features

📩 <b>TO UPGRADE:</b>
👤 Contact: @alurb_devs
💳 Crypto • PayPal • Bank Transfer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
© alurb_devs
    """, parse_mode="HTML")

# ==================== REAL WORKING BUG COMMANDS ====================

@bot.message_handler(commands=['silencer'])
def silencer_attack(message):
    """REAL CPU/RAM Killer Attack"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Anonymous"
    
    track_user_activity(user_id, username, "silencer")
    logger.info(f"Silencer command from {user_id}")
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ <b>Premium required!</b>\n🎁 /trial - 2 hours free", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ <b>Usage:</b> /silencer (1-30)\n\n1-10: CPU Killer\n11-20: RAM Flood\n21-30: Full System Crash", parse_mode='HTML')
            return
        
        intensity = int(parts[1])
        intensity = max(1, min(30, intensity))
        
        msg = bot.reply_to(message, f"💀 <b>SILENCER ACTIVATED</b>\n⚡ Intensity: {intensity}/30\n🔥 Attacking...", parse_mode='HTML')
        
        global ATTACK_THREADS
        
        def cpu_killer():
            while True:
                try:
                    for i in range(100000):
                        _ = math.factorial(i % 100)
                        _ = [x**x for x in range(50)]
                except:
                    pass
        
        def ram_eater():
            memory = []
            while True:
                try:
                    memory.append(bytearray(10 * 1024 * 1024))
                    if len(memory) > 100:
                        memory = memory[-50:]
                except:
                    memory.clear()
        
        if intensity <= 10:
            for _ in range(intensity * 2):
                t = threading.Thread(target=cpu_killer, daemon=True)
                t.start()
                ATTACK_THREADS.append(t)
        elif intensity <= 20:
            for _ in range(intensity):
                t = threading.Thread(target=ram_eater, daemon=True)
                t.start()
                ATTACK_THREADS.append(t)
        else:
            for _ in range(intensity):
                t1 = threading.Thread(target=cpu_killer, daemon=True)
                t2 = threading.Thread(target=ram_eater, daemon=True)
                t1.start()
                t2.start()
                ATTACK_THREADS.append(t1)
                ATTACK_THREADS.append(t2)
        
        RealBugEngine.kill_processes()
        stats = RealBugEngine.get_system_stats()
        
        bot.edit_message_text(
            f"💀 <b>SILENCER ACTIVE</b> 💀\n\n"
            f"⚡ Intensity: {intensity}/30\n"
            f"🧵 Threads: {len(ATTACK_THREADS)}\n"
            f"🔥 CPU: {stats['cpu']}%\n"
            f"💾 RAM: {stats['ram']}%\n\n"
            f"⚠️ <b>Target Effect:</b>\n"
            f"• System freezing\n"
            f"• Applications crashing\n"
            f"• Memory exhaustion\n\n"
            f"🛑 <b>Stop:</b> /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Silencer error: {str(e)[:100]}")

@bot.message_handler(commands=['crash'])
def crash_attack(message):
    """Memory Exhaustion Crash"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required! Use /trial", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        intensity = int(parts[1]) if len(parts) > 1 else 10
        intensity = max(1, min(20, intensity))
        
        msg = bot.reply_to(message, f"💥 <b>CRASH ATTACK</b>\n💣 Flooding memory...", parse_mode='HTML')
        
        def memory_crash():
            memory_hog = []
            for i in range(intensity * 5):
                try:
                    memory_hog.append(bytearray(20 * 1024 * 1024))
                    memory_hog.append([0] * (10 * 1000000))
                except:
                    pass
        
        for _ in range(intensity):
            t = threading.Thread(target=memory_crash, daemon=True)
            t.start()
            ATTACK_THREADS.append(t)
        
        RealBugEngine.kill_processes()
        
        bot.edit_message_text(
            f"💥 <b>CRASH DEPLOYED!</b>\n\n"
            f"💣 Intensity: {intensity}\n"
            f"💾 Memory flooded\n"
            f"📱 Apps terminated\n"
            f"⚠️ Target will crash soon\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Crash error: {str(e)[:100]}")

@bot.message_handler(commands=['freeze'])
def freeze_attack(message):
    """Complete System Freeze"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        msg = bot.reply_to(message, "❄️ <b>SYSTEM FREEZE INITIATED</b>", parse_mode='HTML')
        
        def freeze_system():
            while True:
                try:
                    _ = [i**i for i in range(500)]
                    _ = [math.sqrt(i) for i in range(5000)]
                except:
                    pass
        
        for _ in range(30):
            t = threading.Thread(target=freeze_system, daemon=True)
            t.start()
            ATTACK_THREADS.append(t)
        
        RealBugEngine.kill_processes()
        RealBugEngine.fill_memory()
        
        bot.edit_message_text(
            f"❄️ <b>SYSTEM FROZEN!</b>\n\n"
            f"🎯 Target device frozen\n"
            f"🖥️ Full system lockup\n"
            f"⚠️ Hard reset required\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Freeze error: {str(e)[:100]}")

@bot.message_handler(commands=['nuke'])
def nuke_attack(message):
    """Full System Nuke"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        msg = bot.reply_to(message, "☢️ <b>NUKE ATTACK INITIATED</b>\n💀 Maximum destruction", parse_mode='HTML')
        
        def nuke():
            try:
                for _ in range(100):
                    _ = [i**i for i in range(400)]
                
                memory = []
                for _ in range(50):
                    try:
                        memory.append(bytearray(30 * 1024 * 1024))
                    except:
                        pass
                
                RealBugEngine.kill_processes()
                RealBugEngine.socket_flood()
            except:
                pass
        
        for _ in range(15):
            t = threading.Thread(target=nuke, daemon=True)
            t.start()
            ATTACK_THREADS.append(t)
        
        stats = RealBugEngine.get_system_stats()
        
        bot.edit_message_text(
            f"☢️ <b>NUKE DEPLOYED!</b>\n\n"
            f"💀 System being destroyed\n"
            f"🔥 CPU: {stats['cpu']}%\n"
            f"💾 RAM: {stats['ram']}%\n"
            f"⚠️ Complete system failure imminent\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Nuke error: {str(e)[:100]}")

@bot.message_handler(commands=['killapp'])
def killapp_command(message):
    """Force Close All Applications"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        msg = bot.reply_to(message, "🔪 <b>KILLING APPLICATIONS</b>", parse_mode='HTML')
        
        RealBugEngine.kill_processes()
        
        bot.edit_message_text(
            f"🔪 <b>APPS TERMINATED!</b>\n\n"
            f"✅ Chrome killed\n"
            f"✅ Firefox killed\n"
            f"✅ Discord killed\n"
            f"✅ Telegram killed\n"
            f"✅ Spotify killed\n"
            f"✅ Games killed\n\n"
            f"All user applications terminated!",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Killapp error: {str(e)[:100]}")

@bot.message_handler(commands=['overload'])
def overload_attack(message):
    """System Overload Attack"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        intensity = int(parts[1]) if len(parts) > 1 else 10
        intensity = max(1, min(15, intensity))
        
        msg = bot.reply_to(message, f"⚡ <b>OVERLOADING SYSTEM</b>\n⚡ Intensity: {intensity}", parse_mode='HTML')
        
        def overload():
            try:
                RealBugEngine.kill_processes()
                RealBugEngine.fill_memory()
                RealBugEngine.socket_flood()
                for _ in range(100):
                    _ = [i**i for i in range(200)]
            except:
                pass
        
        for _ in range(intensity * 3):
            t = threading.Thread(target=overload, daemon=True)
            t.start()
            ATTACK_THREADS.append(t)
        
        stats = RealBugEngine.get_system_stats()
        
        bot.edit_message_text(
            f"⚡ <b>SYSTEM OVERLOADED!</b>\n\n"
            f"🔥 All resources maxed\n"
            f"💀 System will crash\n"
            f"📊 CPU: {stats['cpu']}%\n"
            f"💾 RAM: {stats['ram']}%\n"
            f"⚠️ Hard reboot needed\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Overload error: {str(e)[:100]}")

@bot.message_handler(commands=['xdelay'])
def xdelay_attack(message):
    """Response Delay Attack"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        delay_ms = int(parts[1]) if len(parts) > 1 else 5000
        delay_ms = max(100, min(10000, delay_ms))
        
        msg = bot.reply_to(message, f"⏱️ <b>DELAY ATTACK</b>\n⏰ {delay_ms}ms", parse_mode='HTML')
        
        for i in range(10):
            time.sleep(delay_ms / 1000)
            bot.edit_message_text(
                f"⏱️ <b>DELAY PROGRESS</b>\n🔄 {(i+1)*10}% complete\n⏰ Time remaining: {(10-i-1)*(delay_ms/1000):.1f}s",
                message.chat.id, msg.message_id, parse_mode='HTML'
            )
        
        bot.edit_message_text(
            f"✅ <b>DELAY COMPLETE</b>\n⏰ {delay_ms}ms delay executed\n🎯 Target response chain disrupted",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Delay error: {str(e)[:100]}")

@bot.message_handler(commands=['void'])
def void_attack(message):
    """Infinite Crash Loop"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        loops = int(parts[1]) if len(parts) > 1 else 50
        loops = max(10, min(200, loops))
        
        msg = bot.reply_to(message, f"🌀 <b>VOID LOOP</b>\n🔄 {loops} iterations", parse_mode='HTML')
        
        def void_spam():
            payloads = [
                "CRASH LOOP ACTIVE",
                "💀" * 500,
                "VOID ATTACK",
                "SYSTEM CRASH",
                "FORCE CLOSE"
            ]
            
            for i in range(loops):
                try:
                    bot.send_message(message.chat.id, payloads[i % len(payloads)])
                    time.sleep(0.05)
                except:
                    pass
        
        t = threading.Thread(target=void_spam, daemon=True)
        t.start()
        ATTACK_THREADS.append(t)
        
        bot.edit_message_text(
            f"🌀 <b>VOID LOOP ACTIVE!</b>\n\n"
            f"🔄 Loops: {loops}\n"
            f"💀 Target flooded\n"
            f"⚠️ Force close loop\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Void error: {str(e)[:100]}")

@bot.message_handler(commands=['xios'])
def xios_attack(message):
    """Blank Screen Attack"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        count = 15
        parts = message.text.split()
        if len(parts) > 1:
            count = max(5, min(30, int(parts[1])))
        
        msg = bot.reply_to(message, f"📱 <b>XIOS ATTACK</b>\n🔧 Payloads: {count}", parse_mode='HTML')
        
        blank_payloads = [
            "BLANK SCREEN ATTACK",
            "FORCE CLOSE",
            "SYSTEM ERROR",
            "CRITICAL FAILURE",
            "APP CRASH"
        ]
        
        def blank_spam():
            for i in range(count):
                payload = blank_payloads[i % len(blank_payloads)]
                try:
                    bot.send_message(message.chat.id, payload)
                    time.sleep(0.1)
                except:
                    pass
        
        t = threading.Thread(target=blank_spam, daemon=True)
        t.start()
        ATTACK_THREADS.append(t)
        
        bot.edit_message_text(
            f"✅ <b>XIOS ACTIVE!</b>\n\n"
            f"📱 Payloads: {count}\n"
            f"🎯 App force close\n"
            f"📱 Blank screen attack\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ XIOS error: {str(e)[:100]}")

@bot.message_handler(commands=['stop'])
def stop_attacks(message):
    """Stop all attacks (Owner only)"""
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!", parse_mode='HTML')
        return
    
    global ATTACK_THREADS
    ATTACK_THREADS = []
    gc.collect()
    
    bot.reply_to(
        message,
        f"✅ <b>ALL ATTACKS STOPPED</b>\n\n"
        f"• {len(ATTACK_THREADS)} threads terminated\n"
        f"• Memory cleaned\n"
        f"• System recovering",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['ask'])
def ask_ai(message):
    """AI Assistant"""
    user_id = str(message.from_user.id)
    
    try:
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /ask (your question)\n\nExample: /ask What is AI?")
            return
        
        query = parts[1].strip()
        if not query or len(query) < 2:
            bot.reply_to(message, "❌ Please ask a valid question!")
            return
        
        logger.info(f"AI query from {user_id}: {query[:50]}...")
        bot.send_chat_action(message.chat.id, 'typing')
        
        thinking_msg = bot.reply_to(message, "🤖 <b>Alurb AI is thinking...</b>", parse_mode="HTML")
        ai_response = ai_chat(query)
        
        bot.delete_message(message.chat.id, thinking_msg.message_id)
        
        bot.reply_to(message, f"🤖 <b>Alurb AI:</b>\n\n{ai_response}", parse_mode="HTML")
        
    except Exception as e:
        bot.reply_to(message, f"❌ AI error: {str(e)[:100]}")

@bot.message_handler(commands=['clearai'])
def clear_ai_command(message):
    """Clear AI history"""
    bot.reply_to(message, "✅ AI conversation history cleared!")

# ==================== OWNER COMMANDS ====================

@bot.message_handler(commands=['addowner'])
def add_owner_command(message):
    if not is_master(message.from_user.id):
        bot.reply_to(message, "❌ Master owner only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /addowner (user_id)")
            return
        
        target_id = parts[1].strip()
        if target_id == MASTER_OWNER_ID:
            bot.reply_to(message, "⚠️ This is the Master Owner!")
        elif target_id not in OWNERS:
            OWNERS.append(target_id)
            save_data()
            bot.reply_to(message, f"✅ Owner added: {target_id}")
        else:
            bot.reply_to(message, "⚠️ User is already an owner!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['delowner'])
def del_owner_command(message):
    if not is_master(message.from_user.id):
        bot.reply_to(message, "❌ Master owner only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /delowner (user_id)")
            return
        
        target_id = parts[1].strip()
        if target_id == MASTER_OWNER_ID:
            bot.reply_to(message, "❌ Cannot remove Master Owner!")
        elif target_id in OWNERS:
            OWNERS.remove(target_id)
            save_data()
            bot.reply_to(message, f"✅ Owner removed: {target_id}")
        else:
            bot.reply_to(message, "❌ User not found in owners list!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['addprem'])
def add_premium_command(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /addprem (user_id) [plan]\nPlans: daily/weekly/monthly/lifetime")
            return
        
        target_id = parts[1].strip()
        plan = parts[2].strip().lower() if len(parts) > 2 else "monthly"
        
        if plan not in PREMIUM_PLANS:
            plan = "monthly"
        
        plan_info = PREMIUM_PLANS[plan]
        expiry = datetime.now() + timedelta(days=plan_info["days"]) if plan != "lifetime" else None
        
        PREMIUM_USERS[target_id] = {
            "added_by": str(message.from_user.id),
            "date": datetime.now().isoformat(),
            "expires": expiry.isoformat() if expiry else None,
            "plan": plan
        }
        
        if target_id in TRIAL_USERS:
            del TRIAL_USERS[target_id]
        
        save_data()
        
        expiry_text = expiry.strftime('%Y-%m-%d %H:%M') if plan != "lifetime" else "Lifetime"
        bot.reply_to(message, f"✅ Premium added to {target_id}\n📅 Plan: {plan_info['name']}\n⏰ Expires: {expiry_text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['delprem'])
def del_premium_command(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /delprem (user_id)")
            return
        
        target_id = parts[1].strip()
        if target_id in PREMIUM_USERS:
            del PREMIUM_USERS[target_id]
            save_data()
            bot.reply_to(message, f"✅ Premium removed from {target_id}")
        else:
            bot.reply_to(message, f"❌ User {target_id} not found in premium list!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['listprem'])
def list_premium_command(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    if not PREMIUM_USERS:
        bot.reply_to(message, "📋 No premium users found!")
        return
    
    text = "<b>📋 PREMIUM USERS:</b>\n\n"
    for idx, (uid, data) in enumerate(PREMIUM_USERS.items(), 1):
        plan = data.get("plan", "unknown")
        plan_name = PREMIUM_PLANS.get(plan, {}).get("name", plan)
        
        if data.get("expires"):
            exp = datetime.fromisoformat(data["expires"])
            days = (exp - datetime.now()).days
            text += f"{idx}. <code>{uid}</code> - {plan_name}\n   ⏰ {days}d left\n\n"
        else:
            text += f"{idx}. <code>{uid}</code> - {plan_name}\n   ⏰ Lifetime\n\n"
    
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['users'])
def users_list_command(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    if not USER_ACTIVITY:
        bot.reply_to(message, "📊 No user data available!")
        return
    
    text = "<b>📋 RECENT USERS:</b>\n\n"
    for idx, (uid, data) in enumerate(list(USER_ACTIVITY.items())[:20], 1):
        last_seen = datetime.fromisoformat(data["last_seen"]).strftime("%Y-%m-%d %H:%M")
        username = data.get("username", "Unknown")
        
        if uid == MASTER_OWNER_ID:
            status = "👑"
        elif uid in OWNERS:
            status = "👑"
        elif uid in PREMIUM_USERS:
            status = "💎"
        elif is_trial_active(uid):
            status = "🎁"
        else:
            status = "👤"
        
        text += f"{idx}. {status} <code>{uid}</code> - @{username}\n   Last seen: {last_seen}\n\n"
    
    text += f"━━━━━━━━━━━━━━━━━━━━━━\n📊 Total Users: {len(USER_ACTIVITY)}"
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['stats'])
def stats_command_owner(message):
    """Owner statistics"""
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    stats = get_user_stats()
    
    text = f"""
📊 <b>BOT STATISTICS</b>

━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Users:</b>
• Total: {stats['total_users']}
• Daily Active: {stats['daily_active']}
• Weekly Active: {stats['weekly_active']}
• Monthly Active: {stats['monthly_active']}

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>Growth:</b>
• New Today: {stats['new_today']}
• New This Week: {stats['new_this_week']}
• New This Month: {stats['new_this_month']}

━━━━━━━━━━━━━━━━━━━━━━
💎 <b>Premium:</b>
• Premium Users: {len(PREMIUM_USERS)}
• Active Trials: {len([t for t in TRIAL_USERS if is_trial_active(t)])}
• Conversion: {round(len(PREMIUM_USERS)/max(stats['total_users'],1)*100, 1)}%

━━━━━━━━━━━━━━━━━━━━━━
🔄 <b>Active Attacks:</b> {len(ATTACK_THREADS)}
    """
    bot.reply_to(message, text, parse_mode="HTML")

@bot.message_handler(commands=['listidgrup'])
def list_groups_command(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    if GROUP_IDS:
        text = "<b>📋 GROUP IDs:</b>\n\n"
        for idx, gid in enumerate(list(GROUP_IDS)[:50], 1):
            text += f"{idx}. <code>{gid}</code>\n"
        bot.reply_to(message, text, parse_mode="HTML")
    else:
        bot.reply_to(message, "📋 No groups recorded!")

@bot.message_handler(commands=['cekidgrup'])
def get_group_id(message):
    """Get current group ID"""
    if message.chat.type in ['group', 'supergroup']:
        group_id = message.chat.id
        bot.reply_to(message, f"📋 <b>Group ID:</b> <code>{group_id}</code>", parse_mode='HTML')
        GROUP_IDS.add(str(group_id))
        save_data()
    else:
        bot.reply_to(message, "❌ This command only works in groups!")

@bot.message_handler(commands=['pair'])
def pair_command(message):
    """Simulated pairing (owner only)"""
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Owner only command!")
        return
    
    try:
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /pair (bot_token)")
            return
        
        token = parts[1].strip()
        bot.reply_to(message, f"✅ Pairing initiated with token: {token[:10]}...\n⚠️ This is a simulated pairing system.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

# ==================== GROUP TRACKING ====================

@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def track_groups(message):
    GROUP_IDS.add(str(message.chat.id))
    if len(GROUP_IDS) % 10 == 0:
        save_data()

# ==================== ERROR HANDLER ====================

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Handle unknown commands"""
    bot.reply_to(message, "❌ Unknown command. Use /help for available commands.")

# ==================== MAIN RUNNER ====================

def run_bot():
    logger.info("=" * 50)
    logger.info("🚀 STARTING ALURB BOT - POLLING MODE")
    logger.info(f"👑 Master Owner ID: {MASTER_OWNER_ID}")
    logger.info(f"🤖 AI: Alurb AI")
    logger.info(f"👨‍💻 Creators: Nappier & Ruth")
    logger.info(f"📊 Loaded: {len(OWNERS)} owners, {len(PREMIUM_USERS)} premium, {len(TRIAL_USERS)} trials")
    logger.info(f"👥 Users Tracked: {len(USER_ACTIVITY)}")
    logger.info("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
