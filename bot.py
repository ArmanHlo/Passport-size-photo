import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Start command
async def start(update: Update, context):
    await update.message.reply_text('Welcome! Send me some text and I will create an image out of it.')

# Generate image from text
def generate_image(text):
    # Create an image with white background
    img = Image.new('RGB', (500, 300), color = (255, 255, 255))

    # Load a font
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()

    # Get a drawing context
    d = ImageDraw.Draw(img)

    # Add text to image (centered)
    text_width, text_height = d.textsize(text, font=font)
    position = ((500-text_width)/2, (300-text_height)/2)
    d.text(position, text, fill=(0, 0, 0), font=font)

    # Save the image to a file
    img.save('output.png')

# Handle incoming text messages
async def handle_message(update: Update, context):
    text = update.message.text
    generate_image(text)

    # Send the generated image
    with open('output.png', 'rb') as image:
        await update.message.reply_photo(photo=image)

# Main function to run the bot
def main():
    # Replace 'YOUR_BOT_TOKEN' with your bot's token
    application = ApplicationBuilder().token('7872145894:AAHXeYeq5WNqco63GdOoB0RDuNy7QJfDWcg').build()

    # Add command and message handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
