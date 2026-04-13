import os
import io
import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from rembg import remove, new_session

# --- 1. Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BG_Remover_Bot')

# --- 2. Load Environment Variables ---
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    logger.critical("DISCORD_BOT_TOKEN not found in environment variables. Exiting.")
    exit(1)

# --- 3. Define the Bot Class ---
class BackgroundBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.add_cog(BackgroundRemoverCog(self))
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} command(s).")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        logger.info(f"✅ Bot is online and ready! Logged in as {self.user} (ID: {self.user.id})")

# --- 4. Define the Command Logic (Cog) ---
class BackgroundRemoverCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Helper function to run the AI process
    def process_image(self, image_bytes: bytes, model_name: str) -> bytes:
        # new_session loads the specific AI model chosen by the user
        session = new_session(model_name)
        return remove(image_bytes, session=session)

    @app_commands.command(name="removebg", description="Removes the background from an uploaded image.")
    @app_commands.describe(
        image="The image you want to remove the background from",
        subject_type="What is in the image? (Helps pick the best AI model)"
    )
    # This creates the drop-down menu in Discord!
    @app_commands.choices(subject_type=[
        app_commands.Choice(name="👤 Person / Complex", value="u2net"),
        app_commands.Choice(name="📦 Object / Simple", value="u2netp"),
        app_commands.Choice(name="🎨 Anime / Illustration", value="isnet-anime")
    ])
    async def remove_background(
        self, 
        interaction: discord.Interaction, 
        image: discord.Attachment, 
        subject_type: app_commands.Choice[str]
    ):
        
        # Validate that the file is actually an image
        if not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message("⚠️ Please provide a valid image file (PNG, JPG, etc.).", ephemeral=True)
            return

        # Defer response to prevent timeout
        await interaction.response.defer(thinking=True)

        try:
            # Check which model the user selected from the dropdown
            selected_model = subject_type.value
            logger.info(f"Processing image with model '{selected_model}' for {interaction.user}")
            
            image_bytes = await image.read()

            # Pass the image and the chosen model name to the background thread
            output_bytes = await asyncio.to_thread(self.process_image, image_bytes, selected_model)

            with io.BytesIO(output_bytes) as image_file:
                discord_file = discord.File(fp=image_file, filename=f"nobg_{image.filename}.png")
                
                await interaction.followup.send(
                    content=f"✨ Background removed using the **{subject_type.name}** model, {interaction.user.mention}!", 
                    file=discord_file
                )
            
        except Exception as e:
            logger.error(f"Error processing image for {interaction.user}: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while processing your image.", ephemeral=True)

# --- 5. Run the Bot ---
if __name__ == "__main__":
    bot = BackgroundBot()
    bot.run(TOKEN, log_handler=None)
    
