import os
import threading
import logging
import openai  # Import OpenAI
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv  # Import to load .env file

# Load environment variables from .env file
load_dotenv()

# Set the OpenAI API key from the environment
openai.api_key = os.getenv('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')

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot and Flask Server are running!"

# Start command for the bot
async def start(update: Update, context):
    await update.message.reply_text('Welcome! Send me a description and I will create an image out of it.')

# Function to generate an image from a text description using OpenAI
def generate_image_from_text(description):
    try:
        # Send the text description to the OpenAI API
        response = openai.Image.create(
            prompt=description,
            n=1,  # Generate one image
            size="512x512"  # Image size
        )
        image_url = response['data'][0]['url']  # Get the image URL from the response
        return image_url
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None

# Handle incoming text messages
async def handle_message(update: Update, context):
    text = update.message.text
    image_url = generate_image_from_text(text)

    if image_url:
        # Send the generated image URL
        await update.message.reply_photo(photo=image_url)
    else:
        await update.message.reply_text('Sorry, I couldn\'t generate an image from that description.')

# Function to run the Telegram bot
def run_telegram_bot():
    # Replace 'YOUR_BOT_TOKEN' with your bot's token
    application = ApplicationBuilder().token('7872145894:AAHXeYeq5WNqco63GdOoB0RDuNy7QJfDWcg').build()

    # Add command and message handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    # Start the Flask server in a separate thread
    port = int(os.environ.get('PORT', 5000))  # Port for Flask
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': port}).start()

    # Run the Telegram bot
    run_telegram_bot()
