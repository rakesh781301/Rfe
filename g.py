from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import logging
import datetime

# === Bot Configuration ===
BOT_TOKEN = "8181730975:AAE6mw1FNybVlkEy7tM4CBSisSCHVLtUwJU"
CHANNEL_USERNAME = "@earnmoneyonlineheist"
BOT_USERNAME = "earnmoneyonlineheist_bot"

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === In-Memory Data ===
users_data = {}
REFERRAL_BONUS = 15
DAILY_BONUS = 5
WITHDRAWAL_LIMIT = 100

# === Channel Membership Check ===
async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# === /start Command with Referral Logic ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    joined = await check_membership(user_id, context)
    if not joined:
        keyboard = [
            [InlineKeyboardButton("🔗 Join Channel", url="https://t.me/earnmoneyonlineheist")],
            [InlineKeyboardButton("✅ Joined", callback_data='check_join')]
        ]
        await update.message.reply_text(
            "To continue, please join our official channel below:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Initialize user data if not present
    if user_id not in users_data:
        referred_by = None
        if context.args:
            referrer_id = int(context.args[0])
            if referrer_id != user_id and referrer_id in users_data:
                referred_by = referrer_id
                # Reward referrer only once
                if user_id not in users_data:
                    users_data[referrer_id]["balance"] += REFERRAL_BONUS
                    users_data[referrer_id]["referrals"].append(user_id)
                    # Notify referrer
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 Congratulations! You've earned ₹{REFERRAL_BONUS} for referring {user.first_name}!"
                    )

        users_data[user_id] = {
            "balance": 0,
            "referrals": [],
            "referred_by": referred_by,
            "last_bonus": None,
            "joined": True
        }

    else:
        # Check again if user has left the channel
        if not await check_membership(user_id, context):
            await update.message.reply_text("❌ You have left the channel. Please rejoin to continue.")
            return

    await send_main_menu(update, context)

# === Handler When Clicking "Joined" Button ===
async def check_joined_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    joined = await check_membership(user_id, context)
    if joined:
        await query.edit_message_text("✅ You're verified! Proceeding to the main menu...")
        await send_main_menu(update, context)
    else:
        await query.edit_message_text("❌ You haven't joined yet. Please join the channel and click again.")

# === Main Menu ===
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data='balance')],
        [InlineKeyboardButton("👥 My Referral Link", callback_data='referral')],
        [InlineKeyboardButton("🏦 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data='bonus')],
        [InlineKeyboardButton("📊 My Stats", callback_data='stats')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')],
    ]
    text = (
        f"Welcome {user.first_name}!\n\n"
        f"Earn ₹{REFERRAL_BONUS} per referral and ₹{DAILY_BONUS} daily bonus!\n"
        f"Minimum withdrawal: ₹{WITHDRAWAL_LIMIT}"
    )
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

# === Button Handling ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_data = users_data.get(user_id)

    if query.data == 'check_join':
        await check_joined_button(update, context)
        return

    if not user_data:
        await query.edit_message_text("Please start the bot using /start.")
        return

    # Check membership on every action
    if not await check_membership(user_id, context):
        await query.edit_message_text("❌ You have left the channel. Please rejoin to use the bot.")
        return

    if query.data == "balance":
        await query.edit_message_text(f"💰 Your Balance: ₹{user_data['balance']}")
    elif query.data == "referral":
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        await query.edit_message_text(f"👥 Your referral link:\n{link}")
    elif query.data == "withdraw":
        if user_data["balance"] >= WITHDRAWAL_LIMIT:
            user_data["balance"] -= WITHDRAWAL_LIMIT
            await query.edit_message_text(f"🏦 Withdrawal of ₹{WITHDRAWAL_LIMIT} successful!")
        else:
            await query.edit_message_text(f"🏦 You need ₹{WITHDRAWAL_LIMIT} to withdraw.")
    elif query.data == "bonus":
        today = datetime.date.today()
        if user_data["last_bonus"] != today:
            user_data["balance"] += DAILY_BONUS
            user_data["last_bonus"] = today
            await query.edit_message_text(f"🎁 Bonus claimed! ₹{DAILY_BONUS} added.")
        else:
            await query.edit_message_text("🎁 You've already claimed today's bonus.")
    elif query.data == "stats":
        await query.edit_message_text(
            f"📊 Stats:\nBalance: ₹{user_data['balance']}\nReferrals: {len(user_data['referrals'])}"
        )
    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ *How to Earn:*\n\n"
            f"• ₹{REFERRAL_BONUS} per referral\n"
            f"• ₹{DAILY_BONUS} daily bonus\n"
            f"• Minimum ₹{WITHDRAWAL_LIMIT} to withdraw\n\n"
            "Promote your referral link and earn!",
            parse_mode="Markdown"
        )

# === Main Entry ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
