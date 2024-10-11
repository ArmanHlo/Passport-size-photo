import os
import requests
import numpy as np
from PIL import Image
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from io import BytesIO
from flask import Flask
import threading

# Use environment variables for sensitive information
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN', '7872145894:AAHXeYeq5WNqco63GdOoB0RDuNy7QJfDWcg')
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY', 'jvbpsiXdN3uPkWTxYCDg2WsK')

# Flask app for port binding
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

def remove_background(image_path):
    ''' Removes background using remove.bg API '''
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

async def handle_image(update, context):
    ''' Handle images sent by users '''
    photo_file = await update.message.photo[-1].get_file()
    image_path = f"temp_{update.message.from_user.id}.jpg"
    await photo_file.download_to_drive(image_path)

    output_path = f"bg_removed_{update.message.from_user.id}.jpg"  # Output path for background-removed image

    try:
        # Notify the user that processing has started
        await update.message.reply_text("Processing your image...")

        # Step 1: Remove background
        await context.bot.send_message(chat_id=update.message.chat.id, text="Removing background... 100%")
        bg_removed = remove_background(image_path)
        bg_removed_image = Image.open(BytesIO(bg_removed))

        # Convert the image to RGB before saving as JPEG
        bg_removed_image = bg_removed_image.convert("RGB")
        
        # Save the processed image as JPEG
        bg_removed_image.save(output_path, format='JPEG', quality=95)

        # Send the processed image
        await context.bot.send_photo(chat_id=update.message.chat.id, photo=open(output_path, 'rb'))

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

    finally:
        # Cleanup temporary files
        if os.path.exists(image_path):
            os.remove(image_path)
        if os.path.exists(output_path):
            os.remove(output_path)

async def start(update, context):
    ''' Send a welcome message '''
    await update.message.reply_text("Hello! Send me an image, and I'll remove the background.")

def run_telegram_bot():
    ''' Start the bot '''
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.run_polling()

if __name__ == '__main__':
    # Start the Flask server in a separate thread
    port = int(os.environ.get('PORT', 5000))  # Port for Flask
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': port}).start()

    # Run the Telegram bot
    run_telegram_bot()
