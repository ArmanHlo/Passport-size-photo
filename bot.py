import os
import cv2
import numpy as np
from PIL import Image
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from io import BytesIO
from flask import Flask
import threading

# Use environment variables for sensitive information
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN', '7872145894:AAHXeYeq5WNqco63GdOoB0RDuNy7QJfDWcg')


# Flask app for port binding
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"


def cartoonize_image(image_path):
    ''' Convert an image to cartoon using OpenCV '''
    img = cv2.imread(image_path)

    # Step 1: Apply bilateral filter to smooth the image
    img_smoothed = cv2.bilateralFilter(img, 9, 75, 75)

    # Step 2: Convert to grayscale and apply median blur
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_blurred = cv2.medianBlur(gray, 5)

    # Step 3: Detect edges using adaptive thresholding
    edges = cv2.adaptiveThreshold(gray_blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY, 9, 9)

    # Step 4: Combine the edges and the smoothed image
    cartoon = cv2.bitwise_and(img_smoothed, img_smoothed, mask=edges)

    # Save the result
    cartoon_path = image_path.replace(".jpg", "_cartoon.jpg")
    cv2.imwrite(cartoon_path, cartoon)
    return cartoon_path

async def handle_image(update, context):
    ''' Handle images sent by users '''
    photo_file = await update.message.photo[-1].get_file()
    image_path = f"temp_{update.message.from_user.id}.jpg"
    await photo_file.download_to_drive(image_path)

    try:
        # Notify the user that processing has started
        await update.message.reply_text("Processing your image to convert it to cartoon...")

        # Step 1: Convert image to cartoon
        cartoon_path = cartoonize_image(image_path)

        # Step 2: Send the cartoonized image
        await context.bot.send_photo(chat_id=update.message.chat.id, photo=open(cartoon_path, 'rb'))

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

    finally:
        # Cleanup temporary files
        if os.path.exists(image_path):
            os.remove(image_path)
        if os.path.exists(cartoon_path):
            os.remove(cartoon_path)

async def start(update, context):
    ''' Send a welcome message '''
    await update.message.reply_text("Hello! Send me an image, and I'll convert it into a cartoon avatar.")

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
