"""Entry point: initialise DB, start scheduler, start Telegram bot."""

import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import db
import scheduler as sched
from handlers import (
    DONE,
    WAITING_FOR_CITY,
    help_command,
    pause,
    receive_city,
    resume,
    start,
    stop,
)

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application(token: str):
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_FOR_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_city)
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("stop", stop),
            CommandHandler("pause", pause),
            CommandHandler("resume", resume),
            CommandHandler("help", help_command),
        ],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("help", help_command))

    return app


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]

    db.init_db()
    logger.info("Database initialised.")

    sched.scheduler.start()
    sched.scheduler.pause()  # pause during recovery
    logger.info("Scheduler started (paused for recovery).")

    app = build_application(token)

    active_users = db.get_all_active_users()
    logger.info("Recovering jobs for %d active user(s).", len(active_users))
    for user in active_users:
        sched.load_user_jobs(app.bot, user, db)

    sched.scheduler.resume()  # resume after all jobs are loaded
    logger.info("Scheduler resumed.")
    logger.info("Bot starting.")
    app.run_polling()


if __name__ == "__main__":
    main()
