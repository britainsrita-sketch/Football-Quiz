import os
import random
import logging
import asyncio
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
        [InlineKeyboardButton("⚽ Jogar Quiz", callback_data="play_quiz")],
        [InlineKeyboardButton("📊 Minhas Estatísticas", callback_data="my_stats")],
    ])

    await update.message.reply_text(
        "👋 Bem-vindo ao *Quiz de Apelidos do Futebol*\\!\n\n"
        "Teste o quanto você conhece os apelidos dos clubes do mundo todo\\.\n\n"
        "10 perguntas por rodada\\. Quantas você consegue acertar\\? 🎯",
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
        f"*Pergunta {num}/{total}*\n\n"
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
            "Menu principal 👇",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚽ Jogar Quiz", callback_data="play_quiz")],
                [InlineKeyboardButton("📊 Minhas Estatísticas", callback_data="my_stats")],
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
        "🟢 Quiz iniciado\\! Boa sorte 🍀",
        parse_mode="MarkdownV2"
    )
    await send_question(update, context)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, chosen: str):
    state = get_user_state(context)

    if not state.get("active"):
        await update.callback_query.message.reply_text("Inicie um novo quiz primeiro — digite /start")
        return

    q = state["questions"][state["index"]]
    correct = q["answer"]
    is_correct = chosen == correct

    if is_correct:
        state["score"] += 1
        feedback = f"✅ *Correto\\!* {escape_md(correct)} é a resposta\\! \\+1 ponto"
    else:
        feedback = (
            f"❌ *Errado\\!*\n"
            f"Você escolheu: {escape_md(chosen)}\n"
            f"Resposta correta: *{escape_md(correct)}*"
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
        best_text = "🎉 Novo recorde pessoal\\!"
    else:
        best_text = f"Seu recorde: *{best}/{total}*"

    total_games = context.user_data.get("total_games", 0) + 1
    context.user_data["total_games"] = total_games

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Jogar Novamente", callback_data="play_again")],
        [InlineKeyboardButton("📊 Minhas Estatísticas", callback_data="my_stats")],
    ])

    await update.callback_query.message.reply_text(
        f"{emoji} *Quiz Finalizado\\!*\n\n"
        f"Você fez *{score}/{total}* pontos\n"
        f"{best_text}\n\n"
        f"Jogos realizados: {total_games}",
        parse_mode="MarkdownV2",
        reply_markup=keyboard,
    )


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    best = context.user_data.get("best_score", 0)
    total_games = context.user_data.get("total_games", 0)
    total_q = QUESTIONS_PER_ROUND

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ Jogar Quiz", callback_data="play_quiz")],
    ])

    await update.callback_query.message.reply_text(
        f"📊 *Suas Estatísticas*\n\n"
        f"🏆 Melhor pontuação: *{best}/{total_q}*\n"
        f"🎮 Jogos realizados: *{total_games}*",
        parse_mode="MarkdownV2",
        reply_markup=keyboard,
    )


# ── markdown escape ────────────────────────────────────────────────────────────

def escape_md(text: str) -> str:
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in text)


# ── main ───────────────────────────────────────────────────────────────────────

async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot está rodando...")
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
