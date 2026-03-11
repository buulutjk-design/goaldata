# bot.py
import os
import logging
import threading
import json
import time
import redis
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

from analysis import evaluate_match

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("banko-bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL, decode_responses=True)
bot = Bot(TELEGRAM_TOKEN)

def is_admin(user_id):
    return int(user_id) == ADMIN_ID

def set_paused(val: bool):
    r.set("bot:paused", "1" if val else "0")

def is_paused():
    return r.get("bot:paused") == "1"

def build_action_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔄 Tekrar Analiz", callback_data="repeat_analysis")],
        [InlineKeyboardButton("🚨 Botu Kapat", callback_data="stop_bot")]
    ]
    return InlineKeyboardMarkup(keyboard)

def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not is_admin(uid):
        update.message.reply_text("Bu bot yalnızca admin tarafından kullanılmaktadır.")
        return
    update.message.reply_text("⚽️: Otomatik /banko Maç Analizi. Komutlar: /banko, /dur")

def safe_pop_batch(batch_size=2000):
    items = []
    for _ in range(batch_size):
        raw = r.rpop("requests_queue")
        if not raw:
            break
        try:
            items.append(json.loads(raw))
        except Exception:
            continue
    return items

def run_analysis_and_edit(chat_id, message_id):
    try:
        total_processed = 0
        best_candidate = None
        while True:
            if is_paused():
                logger.info("Bot paused during analysis")
                break
            batch = safe_pop_batch(batch_size=2000)
            if not batch:
                break
            total_processed += len(batch)
            for item in batch:
                res = evaluate_match(item, n_sim=5000)
                if not res:
                    continue
                if not best_candidate or res["confidence"] > best_candidate["confidence"]:
                    best_candidate = res
            if best_candidate and best_candidate["p"] >= 0.90:
                break
        if not best_candidate:
            text = "MAÇ ANALİZİ BANKO 🔥\n\nHiç uygun aday bulunamadı."
        else:
            text = (
                "MAÇ ANALİZİ BANKO 🔥\n\n"
                f"Lig: {best_candidate['lig']}\n"
                f"🏳️ Ev Sahibi Takımı: {best_candidate['home']}\n"
                f"🚩 Deplasman Takımı: {best_candidate['away']}\n\n"
                f"2.5 ALT ÜST % {int(best_candidate['p']*100)} [ {best_candidate['label']} ] 🍀\n\n"
                f"Beklenen goller: Ev {best_candidate['exp_home']:.2f} — Dep {best_candidate['exp_away']:.2f}\n\n"
                "🔄: Tekrar Analiz /banko\n"
                "🚨: Botu Kapat /dur\n"
            )
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_action_keyboard())
        except Exception:
            bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=build_action_keyboard())
        r.rpush("analysis_logs", json.dumps({"time": datetime.utcnow().isoformat(), "processed": total_processed, "result": best_candidate}))
    except Exception:
        logger.exception("run_analysis_and_edit failed")
        try:
            bot.send_message(ADMIN_ID, "Analiz sırasında hata oluştu. Logları kontrol edin.")
        except Exception:
            pass

def banko_cmd(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    if is_paused():
        update.message.reply_text("Bot şu an kapalı. Önce /dur komutuyla açın.")
        return
    sent = update.message.reply_text("🛜 Bültendeki maçlar analiz ediliyor…")
    threading.Thread(target=run_analysis_and_edit, args=(sent.chat_id, sent.message_id), daemon=True).start()
    update.message.reply_text("Analiz başlatıldı; sonuç hazır olduğunda mesaj düzenlenecek.")

def dur_cmd(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not is_admin(uid):
        return
    set_paused(True)
    update.message.reply_text("Bot durduruldu. API çekimleri kapatıldı.")

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    if not is_admin(uid):
        query.answer()
        return
    if data == "repeat_analysis":
        query.answer("Tekrar analiz başlatılıyor...")
        try:
            query.edit_message_text("🛜 Bültendeki maçlar analiz ediliyor…")
        except Exception:
            pass
        threading.Thread(target=run_analysis_and_edit, args=(query.message.chat_id, query.message.message_id), daemon=True).start()
    elif data == "stop_bot":
        query.answer("Bot kapatılıyor...")
        set_paused(True)
        try:
            query.edit_message_text("Bot kapatıldı. API çekimleri durduruldu.")
        except Exception:
            pass

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("banko", banko_cmd))
    dp.add_handler(CommandHandler("dur", dur_cmd))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    while True:
        try:
            updater.start_polling(poll_interval=1.0, timeout=20)
            updater.idle()
            break
        except Exception:
            logger.exception("Updater crashed, restarting in 5s")
            time.sleep(5)

if __name__ == "__main__":
    main()
