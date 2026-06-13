import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from questions import QUESTIONS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
QUESTIONS_PER_ROUND = 10


# ── helpers ────────────────────────────────────────────────────────────────────

def get_user_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    if "state" not in context.user_data:
        context.user_data["state"] = {
            "questions": [],
            "index": 0,
            "score": 0,
            "active": False,
        }
    return context.user_data["state"]


def build_answer_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    labels = ["A", "B", "C", "D"]
    buttons = [
        [InlineKeyboardButton(f"{labels[i]}. {opt}", callback_data=f"answer|{opt}")]
        for i, opt in enumerate(options)
    ]
    return InlineKeyboardMarkup(buttons)


def score_emoji(score: int, total: int) -> str:
    pct = score / total
    if pct == 1.0:
        return "🏆"
    if pct >= 0.8:
        return "🔥"
    if pct >= 0.5:
        return "⚽"
    return "📚"


# ── /start ─────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_user_state(context)
    state["active"] = False

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Play Quiz", callback_data="play_quiz")],
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
    ])

    await update.message.reply_text(
        "👋 Welcome to *Football Nickname Quiz*\\!\n\n"
        "Test how well you know club nicknames from around the world\\.\n\n"
        "10 questions per round\\. How many can you get right\\? 🎯",
        parse_mode="MarkdownV2",
        reply_markup=keyboard,
    )


# ── send a question ────────────────────────────────────────────────────────────

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_user_state(context)
    q = state["questions"][state["index"]]
    num = state["index"] + 1
    total = len(state["questions"])

    options = q["options"][:]
    random.shuffle(options)
    state["shuffled_options"] = options

    keyboard = build_answer_keyboard(options)

    text = (
        f"*Question {num}/{total}*\n\n"
        f"🏟️ {escape_md(q['question'])}"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text, parse_mode="MarkdownV2", reply_markup=keyboard
        )


# ── callbacks ──────────────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "play_quiz":
        await start_quiz(update, context)

    elif data == "my_stats":
        await show_stats(update, context)

    elif data.startswith("answer|"):
        await handle_answer(update, context, data.split("|", 1)[1])

    elif data == "play_again":
        await start_quiz(update, context)

    elif data == "main_menu":
        await query.message.reply_text(
            "Main menu 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚽ Play Quiz", callback_data="play_quiz")],
                [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
            ])
        )


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_user_state(context)
    pool = random.sample(QUESTIONS, min(QUESTIONS_PER_ROUND, len(QUESTIONS)))
    state.update({
        "questions": pool,
        "index": 0,
        "score": 0,
        "active": True,
        "shuffled_options": [],
    })

    await update.callback_query.message.reply_text(
        "🟢 Quiz started\\! Good luck 🍀",
        parse_mode="MarkdownV2"
    )
    await send_question(update, context)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, chosen: str):
    state = get_user_state(context)

    if not state.get("active"):
        await update.callback_query.message.reply_text("Start a new quiz first — tap /start")
        return

    q = state["questions"][state["index"]]
    correct = q["answer"]
    is_correct = chosen == correct

    if is_correct:
        state["score"] += 1
        feedback = f"✅ *Correct\\!* {escape_md(correct)} it is\\! \\+1 point"
    else:
        feedback = (
            f"❌ *Wrong\\!*\n"
            f"You picked: {escape_md(chosen)}\n"
            f"Correct answer: *{escape_md(correct)}*"
        )

    await update.callback_query.message.reply_text(feedback, parse_mode="MarkdownV2")

    state["index"] += 1

    if state["index"] < len(state["questions"]):
        await send_question(update, context)
    else:
        await show_final_score(update, context)


async def show_final_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_user_state(context)
    score = state["score"]
    total = len(state["questions"])
    emoji = score_emoji(score, total)
    state["active"] = False

    # Save all-time best
    best = context.user_data.get("best_score", 0)
    if score > best:
        context.user_data["best_score"] = score
        best_text = "🎉 New personal best\\!"
    else:
        best_text = f"Your best: *{best}/{total}*"

    total_games = context.user_data.get("total_games", 0) + 1
    context.user_data["total_games"] = total_games

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Play Again", callback_data="play_again")],
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
    ])

    await update.callback_query.message.reply_text(
        f"{emoji} *Quiz Over\\!*\n\n"
        f"You scored *{score}/{total}*\n"
        f"{best_text}\n\n"
        f"Games played: {total_games}",
        parse_mode="MarkdownV2",
        reply_markup=keyboard,
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    best = context.user_data.get("best_score", 0)
    total_games = context.user_data.get("total_games", 0)
    total_q = QUESTIONS_PER_ROUND

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Play Quiz", callback_data="play_quiz")],
    ])

    await update.callback_query.message.reply_text(
        f"📊 *Your Stats*\n\n"
        f"🏆 Best score: *{best}/{total_q}*\n"
        f"🎮 Games played: *{total_games}*",
        parse_mode="MarkdownV2",
        reply_markup=keyboard,
    )


# ── markdown escape ────────────────────────────────────────────────────────────

def escape_md(text: str) -> str:
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in text)


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
