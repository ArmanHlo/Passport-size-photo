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
    ''' Crops the image to passport size after detecting face '''
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        raise Exception("No face detected!")

    # Get the largest face detected
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    # Expand the bounding box to include shoulders
    shoulder_margin = int(h * 0.5)  # Adjust this value to include more of the shoulders
    new_y = max(0, y - shoulder_margin)  # Ensure we don't go out of bounds
    new_height = h + shoulder_margin  # Expand the height to include shoulders

    # Adjust the cropping area to passport size while keeping the face in focus
    cropped_image = image.crop((x, new_y, x + w, new_y + new_height))
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
