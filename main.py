import os
import io
import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from rembg import remove

# --- 1. Setup Logging ---
# This logs errors and info to the console with timestamps, essential for debugging in production.
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
        # We don't need message content intent anymore since we use Slash Commands
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Add the background removal cog (module) to the bot
        await self.add_cog(BackgroundRemoverCog(self))
        
        # Sync slash commands with Discord globally
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

    # This defines the /removebg slash command
    @app_commands.command(name="removebg", description="Removes the background from an uploaded image.")
    @app_commands.describe(image="The image you want to remove the background from")
    async def remove_background(self, interaction: discord.Interaction, image: discord.Attachment):
        
        # Validate that the file is actually an image
        if not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message("⚠️ Please provide a valid image file (PNG, JPG, etc.).", ephemeral=True)
            return

        # Defer the response. This prevents the 3-second timeout error while the AI processes.
        # "thinking=True" shows "Bot is thinking..." in Discord.
        await interaction.response.defer(thinking=True)

        try:
            logger.info(f"Processing image from {interaction.user} in server {interaction.guild.name if interaction.guild else 'DMs'}")
            
            # Download the image bytes into memory
            image_bytes = await image.read()

            # Offload the heavy AI processing to a separate thread so the bot doesn't freeze
            output_bytes = await asyncio.to_thread(remove, image_bytes)

            # Convert the raw bytes back into a file object for Discord
            with io.BytesIO(output_bytes) as image_file:
                discord_file = discord.File(fp=image_file, filename=f"nobg_{image.filename}.png")
                
                # Send the final result as a follow-up to the deferred interaction
                await interaction.followup.send(
                    content=f"✨ Background removed successfully, {interaction.user.mention}!", 
                    file=discord_file
                )
            
            logger.info(f"Successfully processed and sent image for {interaction.user}")

        except Exception as e:
            logger.error(f"Error processing image for {interaction.user}: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while processing your image. It might be too large or complex.", ephemeral=True)

# --- 5. Run the Bot ---
if __name__ == "__main__":
    bot = BackgroundBot()
    bot.run(TOKEN, log_handler=None) # We set log_handler=None to use our custom logging setup above
