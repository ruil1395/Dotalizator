import os
import requests
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

STRATZ_API_TOKEN = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJTdWJqZWN0IjoiZDRhNDY1NDAtOWU1OS00ZTYxLWE3ZTktNzRhYzJiOWE2YzIxIiwiU3RlYW1JZCI6IjE0Mzc3MjkzNyIsIkFQSVVzZXIiOiJ0cnVlIiwibmJmIjoxNzcwODAzNDI3LCJleHAiOjE4MDIzMzk0MjcsImlhdCI6MTc3MDgwMzQyNywiaXNzIjoiaHR0cHM6Ly9hcGkuc3RyYXR6LmNvbSJ9.WjKRKSsWmOsAkZnLQx3Kz2Apc_Cq1Xiw5sRuu31UnFo")
TELEGRAM_BOT_TOKEN = os.getenv("8577747626:AAELNZ_QI7c6Cns8EDSKiFUihAUdO4muwaE")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fetch_match_data(match_id: int) -> str:
    if not STRATZ_API_TOKEN:
        return "Ошибка: API токен для Stratz не был указан в переменных окружения."

    headers = {"Authorization": f"Bearer {STRATZ_API_TOKEN}"}
    query = """
    query GetMatchDetails($matchId: Long!) {
      match(id: $matchId) {
        durationSeconds
        radiantKills
        direKills
        players {
          steamAccount { name }
          hero { shortName }
          isRadiant
          kills
          deaths
          assists
          goldPerMinute
        }
      }
    }
    """
    variables = {"matchId": match_id}
    
    try:
        response = requests.post("https://api.stratz.com/graphql", headers=headers, json={"query": query, "variables": variables})
        response.raise_for_status()
        data = response.json()

        if 'errors' in data or not data.get('data', {}).get('match'):
            return f"Не удалось найти информацию по матчу с ID {match_id}."

        match_data = data['data']['match']
        duration_seconds = match_data['durationSeconds']
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        
        output_lines = [
            f"📊 *Информация по матчу ID: {match_id}*",
            f"⏳ *Продолжительность:* {minutes} мин {seconds} сек",
            f"⚔️ *Итоговый счет:* Radiant {sum(match_data['radiantKills'])} - {sum(match_data['direKills'])} Dire\n" + ("-" * 20),
        ]
        
        radiant_players = [p for p in match_data['players'] if p['isRadiant']]
        dire_players = [p for p in match_data['players'] if not p['isRadiant']]

        output_lines.append("\n🌞 *Команда Radiant:*")
        for p in radiant_players:
            name = p.get('steamAccount', {}).get('name') or "Аноним"
            output_lines.append(f"  - *{name}* на *{p['hero']['shortName']}* | KDA: {p['kills']}/{p['deaths']}/{p['assists']} | GPM: {p['goldPerMinute']}")

        output_lines.append("\n" + ("-" * 20) + "\n\n🌚 *Команда Dire:*")
        for p in dire_players:
            name = p.get('steamAccount', {}).get('name') or "Аноним"
            output_lines.append(f"  - *{name}* на *{p['hero']['shortName']}* | KDA: {p['kills']}/{p['deaths']}/{p['assists']} | GPM: {p['goldPerMinute']}")
            
        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка: {e}")
        return "Произошла внутренняя ошибка. Проверьте логи."

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй команду `/match <ID матча>` для получения статистики.")

async def match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        match_id = int(context.args[0])
        await update.message.reply_text("🔎 Ищу информацию...")
        result_text = fetch_match_data(match_id)
        await update.message.reply_text(result_text, parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("Неверный формат. Используйте: `/match <ID матча>`")
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при обработке.")

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_BOT_TOKEN не найден!")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("match", match_command))

    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
