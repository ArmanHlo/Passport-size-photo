import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from transformers import pipeline

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Bot and Flask Server are running!"

# Load Hugging Face model for text generation
hugging_face_pipeline = pipeline("text-generation", model="distilgpt2")

# Start command for the bot
async def start(update: Update, context):
    await update.message.reply_text('Welcome! Ask me anything!')

# Function to get answers from the Hugging Face model
def get_answer_from_huggingface(question):
    try:
        # Generate text using Hugging Face's distilGPT2
        result = hugging_face_pipeline(question, max_length=100, num_return_sequences=1)
        return result[0]['generated_text']
    except Exception as e:
        logger.error(f"Error generating text with Hugging Face: {e}")
        return "Sorry, I couldn't process your question."

# Handle incoming text messages
async def handle_message(update: Update, context):
    text = update.message.text
    answer = get_answer_from_huggingface(text)
    await update.message.reply_text(answer)

# Function to run the Telegram bot
def run_telegram_bot():
    # Build the Telegram bot application with the token from environment variables
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

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
