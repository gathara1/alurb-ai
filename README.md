# 🤖 Alurb AI Telegram Bot

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/gathara1/alurb-ai)

## Features

- ✅ 24/7 Online Status
- 🤖 AI Assistant (DeepSeek V3 via OpenRouter)
- 👑 Owner/Premium Management
- 📱 Group Management
- 🔒 Secure Authentication
- 🔄 Auto-Restart on Crash

## Commands

### Owner Menu
- `/pair <token>` - Add bot token
- `/addprem <id>` - Add premium user
- `/delprem <id>` - Remove premium
- `/addowner <id>` - Add owner
- `/delowner <id>` - Remove owner
- `/listprem` - Premium users list
- `/cekidgrup` - Get group ID
- `/listidgrup` - List all groups

### AI Menu
- `/ask <query>` - Ask AI Assistant
- `/clearai` - Clear AI history
- `/status` - Bot status

## Deployment

### One-Click Deploy to Render

1. Click the Deploy button above
2. Add your `BOT_TOKEN` environment variable
3. Deploy!

### Manual Deployment

```bash
git clone https://github.com/gathara1/alurb-ai.git
cd alurb-ai
pip install -r requirements.txt
python bot.py
