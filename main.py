import os
import io
import logging
import asyncio
import gc
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from rembg import remove, new_session

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BG_Remover_Bot')

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if not TOKEN:
    logger.critical("DISCORD_BOT_TOKEN not found in environment variables. Exiting.")
    exit(1)

# Define the Bot Class
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

# Define the Command Logic
class BackgroundRemoverCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def process_image(self, image_bytes: bytes, model_name: str, smooth_edges: bool) -> bytes:
        gc.collect()
        
        session = new_session(model_name)
        
        if smooth_edges:
            output_bytes = remove(
                image_bytes, 
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10
            )
        else:
            output_bytes = remove(image_bytes, session=session)

        del session 

        gc.collect()
        
        return output_bytes

    @app_commands.command(name="removebg", description="Removes the background from an uploaded image.")
    @app_commands.describe(
        image="The image you want to remove the background from",
        subject_type="What is in the image? (Helps pick the best AI model)",
        smooth_edges="Enable Alpha Matting to smooth jagged edges? (Slightly slower)"
    )
    # The drop-down menu choices
    @app_commands.choices(subject_type=[
        app_commands.Choice(name="ℹ️ Person / Complex", value="u2net"),
        app_commands.Choice(name="ℹ️ Object / Simple", value="u2netp"),
        app_commands.Choice(name="ℹ️ Anime / Illustration", value="isnet-anime"),
    ])
    async def remove_background(
        self, 
        interaction: discord.Interaction, 
        image: discord.Attachment, 
        subject_type: app_commands.Choice[str],
        smooth_edges: bool = False
    ):
        
        if not image.content_type or not image.content_type.startswith('image/'):
            await interaction.response.send_message("⚠️ Please provide a valid image file (PNG, JPG, etc.).", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)

        try:
            selected_model = subject_type.value
            logger.info(f"Processing image with model '{selected_model}' | Smoothing: {smooth_edges} | User: {interaction.user}")
            
            image_bytes = await image.read()

            output_bytes = await asyncio.to_thread(self.process_image, image_bytes, selected_model, smooth_edges)

            with io.BytesIO(output_bytes) as image_file:
                discord_file = discord.File(fp=image_file, filename=f"nobg_{image.filename}.png")
                
                msg = f"☑️ Background removed using the **{subject_type.name}** model"
                if smooth_edges:
                    msg += " *(with edge smoothing)*"
                msg += f", {interaction.user.mention}!"

                await interaction.followup.send(content=msg, file=discord_file)
            
        except Exception as e:
            logger.error(f"Error processing image for {interaction.user}: {str(e)}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while processing your image. If the bot restarted, the image was too heavy for the server's RAM.", ephemeral=True)

# --- # Run the Bot
if __name__ == "__main__":
    bot = BackgroundBot()
    bot.run(TOKEN, log_handler=None)
    
