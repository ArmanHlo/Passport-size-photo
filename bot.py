import os
import cv2
import requests
import numpy as np
from PIL import Image, ImageEnhance
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from io import BytesIO
from flask import Flask
import threading

# Use environment variables for sensitive information
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN', '7872145894:AAHXeYeq5WNqco63GdOoB0RDuNy7QJfDWcg')
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY', 'jvbpsiXdN3uPkWTxYCDg2WsK')


# Image dimensions for passport size (pixels)
PASSPORT_WIDTH = 413
PASSPORT_HEIGHT = 531

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

def crop_to_passport(image):
    ''' Crops the image to passport size after detecting full body '''
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Load the body cascade classifier
    body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    
    # Detect bodies in the image
    bodies = body_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3)

    if len(bodies) == 0:
        raise Exception("No body detected!")

    # Get the largest body detected
    x, y, w, h = max(bodies, key=lambda b: b[2] * b[3])

    # Adjust cropping dimensions to include shoulders, head, and hair
    shoulder_padding = int(h * 0.2)  # Adjust this value as needed for shoulder space
    head_padding = int(h * 0.3)  # Space above head for hair
    cropped_image = image.crop((x - int(w * 0.1), y - head_padding, x + w + int(w * 0.1), y + h + shoulder_padding))

    # Resize to passport size
    cropped_image = cropped_image.resize((PASSPORT_WIDTH, PASSPORT_HEIGHT), Image.LANCZOS)

    # Enhance image quality
    enhancer = ImageEnhance.Contrast(cropped_image)
    cropped_image = enhancer.enhance(1.2)  # Increase contrast

    enhancer = ImageEnhance.Brightness(cropped_image)
    cropped_image = enhancer.enhance(1.1)  # Slightly increase brightness

    return cropped_image

async def handle_image(update, context):
    ''' Handle images sent by users '''
    photo_file = await update.message.photo[-1].get_file()
    image_path = f"temp_{update.message.from_user.id}.jpg"
    await photo_file.download_to_drive(image_path)

    output_path = f"passport_{update.message.from_user.id}.jpg"  # Output path

    try:
        # Notify the user that processing has started
        await update.message.reply_text("Processing your image...")

        # Step 1: Remove background
        await context.bot.send_message(chat_id=update.message.chat.id, text="Removing background... 50%")
        bg_removed = remove_background(image_path)
        bg_removed_image = Image.open(BytesIO(bg_removed))

        # Step 2: Crop to passport size
        await context.bot.send_message(chat_id=update.message.chat.id, text="Cropping image to passport size... 100%")
        passport_image = crop_to_passport(bg_removed_image)

        # Convert the image to RGB before saving as JPEG
        passport_image = passport_image.convert("RGB")
        
        # Save the processed image as JPEG
        passport_image.save(output_path, format='JPEG', quality=95)

        # Send the processed image
        with open(output_path, 'rb') as f:
            await context.bot.send_photo(chat_id=update.message.chat.id, photo=f)

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
    await update.message.reply_text("Hello! Send me an image, and I'll remove the background and crop it to passport size.")

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
    run_telegram_bot()  # Run without asyncio.run() to avoid issues

