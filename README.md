# Football-Quiz
# Football Nickname Quiz Bot 🏆

A Telegram bot that quizzes users on football club nicknames from around the world.

## Features
- 30 questions in the pool, 10 random per round
- 4 multiple choice options per question (shuffled each time)
- Score tracking with personal best
- Play again without restarting

## Project Structure
```
nickname_quiz_bot/
├── bot.py           # Main bot logic
├── questions.py     # Question bank (30 questions)
├── requirements.txt
├── render.yaml      # Render deployment config
└── README.md
```

---

## Local Setup

1. Clone the repo
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file:
   ```
   BOT_TOKEN=your_token_here
   ```
5. Run:
   ```bash
   export BOT_TOKEN=your_token_here
   python bot.py
   ```

---

## Deploy to Render (Background Worker)

### Step 1 — Create your bot
1. Open Telegram → message `@BotFather`
2. Send `/newbot` → follow the steps
3. Copy the token BotFather gives you

### Step 2 — Push to GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 3 — Deploy on Render
1. Go to [render.com](https://render.com) → New → **Background Worker**
2. Connect your GitHub repo
3. Render auto-detects `render.yaml` — confirm settings:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python bot.py`
4. Under **Environment Variables**, add:
   - Key: `BOT_TOKEN`
   - Value: your BotFather token
5. Click **Deploy**

### Done ✅
Bot goes live in ~2 minutes. Test it by sending `/start` in Telegram.

---

## Adding More Questions
Open `questions.py` and add entries following this format:
```python
{
    "question": "Which club is called 'The Bees'?",
    "options": ["Brentford", "Watford", "Burnley", "QPR"],
    "answer": "Brentford"
},
```
Make sure every question has exactly 4 options and the answer matches one of them exactly.
