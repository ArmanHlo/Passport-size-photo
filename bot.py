import os
import requests
import numpy as np
from PIL import Image
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from io import BytesIO
from flask import Flask
import threading
from apscheduler.schedulers.background import BackgroundScheduler

# Constants for conversation steps
CHOOSING_FORMAT = 1

# Use environment variables for sensitive information
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN', '7872145894:AAHXeYeq5WNqco63GdOoB0RDuNy7QJfDWcg')
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY', 'jvbpsiXdN3uPkWTxYCDg2WsK')


# Flask app for port binding
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# Keep-alive ping function
def ping_self():
    url = "https://passport-size-photo.onrender.com/"  # Replace with your Render app's URL
    try:
        requests.get(url)
        print(f"Pinged {url} to keep the app alive.")
    except Exception as e:
        print(f"Failed to ping the app: {e}")

# Remove background function
def remove_background(image_path):
    url = 'https://api.remove.bg/v1.0/removebg'
    headers = {'X-Api-Key': REMOVE_BG_API_KEY}

    with open(image_path, 'rb') as image_file:
        response = requests.post(
            url,
            files={'image_file': image_file},
            data={'size': 'auto'},
            headers=headers
        )
    if response.status_code == 200:
        return response.content
    else:
        raise Exception("Failed to remove background: " + response.text)

# Handle format choice
async def choose_format(update, context):
    await update.message.reply_text("Which format would you like? Reply with 'PNG' or 'JPEG'.")
    return CHOOSING_FORMAT

# Handle format selection from user
async def format_choice(update, context):
    user_choice = update.message.text.upper()
    if user_choice not in ["PNG", "JPEG"]:
        await update.message.reply_text("Please choose either 'PNG' or 'JPEG'.")
        return CHOOSING_FORMAT

    context.user_data['format_choice'] = user_choice
    await update.message.reply_text(f"Got it! You chose {user_choice}. Now send me an image to process.")
    return ConversationHandler.END

# Handle incoming images
async def handle_image(update, context):
    if 'format_choice' not in context.user_data:
        await update.message.reply_text("Please start the process by choosing a format using /start.")
        return

    photo_file = await update.message.photo[-1].get_file()
    image_path = f"temp_{update.message.from_user.id}.jpg"
    await photo_file.download_to_drive(image_path)

    format_choice = context.user_data['format_choice']
    output_path = f"bg_removed_{update.message.from_user.id}.{format_choice.lower()}"

    try:
        await update.message.reply_text("Processing your image...")

        # Step 1: Remove background
        await context.bot.send_message(chat_id=update.message.chat.id, text="Removing background... 100%")
        bg_removed = remove_background(image_path)
        bg_removed_image = Image.open(BytesIO(bg_removed))

        if format_choice == 'JPEG':
            bg_removed_image = bg_removed_image.convert("RGB")

        bg_removed_image.save(output_path, format=format_choice, quality=95)
        await context.bot.send_photo(chat_id=update.message.chat.id, photo=open(output_path, 'rb'))

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

    finally:
        if os.path.exists(image_path):
            os.remove(image_path)
        if os.path.exists(output_path):
            os.remove(output_path)

# Start command handler
async def start(update, context):
    await update.message.reply_text("Hello! First, choose your preferred format (PNG or JPEG) for the images.")
    return await choose_format(update, context)

# Run the Telegram bot
def run_telegram_bot():
    application = Application.builder().token(API_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={CHOOSING_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, format_choice)]},
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    application.run_polling()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': port}).start()

    # Start pinging every 1 minute
    scheduler = BackgroundScheduler()
    scheduler.add_job(ping_self, 'interval', minutes=1)
    scheduler.start()

    # Run the Telegram bot
    run_telegram_bot()
