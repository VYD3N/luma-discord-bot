import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from services.luma_service import LumaService
import requests
import asyncio

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True

# Add this near the top of the file with other constants
CAMERA_MOTION_CHOICES = [
    app_commands.Choice(name="None", value=""),
    app_commands.Choice(name="Orbit Left", value="camera orbit left, "),
    app_commands.Choice(name="Orbit Right", value="camera orbit right, "),
    app_commands.Choice(name="Zoom In", value="camera zoom in, "),
    app_commands.Choice(name="Zoom Out", value="camera zoom out, "),
    app_commands.Choice(name="Pan Left", value="camera pan left, "),
    app_commands.Choice(name="Pan Right", value="camera pan right, "),
    app_commands.Choice(name="Pan Up", value="camera pan up, "),
    app_commands.Choice(name="Pan Down", value="camera pan down, "),
    app_commands.Choice(name="Dolly In", value="camera dolly in, "),
    app_commands.Choice(name="Dolly Out", value="camera dolly out, "),
]

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)
        
    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

bot = Bot()

# Service instances
luma = LumaService()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Print all registered commands
    commands = [cmd.name for cmd in bot.tree.get_commands()]
    print(f'Registered commands: {commands}')

@bot.tree.command(name="luma")
@app_commands.describe(
    aspect="Choose the aspect ratio for your image",
    model="Choose the model to use",
    prompt="What would you like to generate?"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="square", value="1:1"),
    app_commands.Choice(name="portrait", value="3:4"),
    app_commands.Choice(name="landscape", value="4:3"),
    app_commands.Choice(name="wide", value="16:9"),
])
@app_commands.choices(model=[
    app_commands.Choice(name="photon-1 (default, higher quality)", value="photon-1"),
    app_commands.Choice(name="photon-flash-1 (faster)", value="photon-flash-1"),
])
async def luma_generate(interaction: discord.Interaction, aspect: str, model: str, prompt: str):
    """Generate an image using Luma Dream Machine"""
    try:
        await interaction.response.send_message(f"🎨 Generating {aspect} image using {model} with prompt: {prompt}")
        
        # Start the generation
        result = await luma.create_capture("image", prompt, aspect, model)
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Generation started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"Aspect: {aspect}\n"
            f"Model: {model}\n\n"
            f"Please wait while your image is being generated..."
        )
        
        while True:
            final_result = await luma.wait_for_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Generation failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still generating... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("image_url"):
                await interaction.followup.send(
                    f"✅ Generation complete! ({elapsed_time} seconds)\n"
                    f"🖼️ Image: {final_result['image_url']}"
                )
                break
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_status")
@app_commands.describe(generation_id="The ID of the generation to check")
async def luma_status(interaction: discord.Interaction, generation_id: str):
    """Check Luma generation status"""
    try:
        result = await luma.get_capture_status(generation_id)
        
        if not result.get("success"):
            await interaction.response.send_message(
                f"❌ Error checking status: {result.get('error', 'Unknown error')}"
            )
            return
            
        # Build status message
        status = result.get('status', 'unknown')
        emoji = result.get('emoji', '❓')
        image_url = result.get('image_url')
        
        status_message = f"{emoji} Generation `{generation_id}`:\nStatus: {status}"
        
        if image_url:
            status_message += f"\n🖼️ Image: {image_url}"
        
        await interaction.response.send_message(status_message)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error checking status: {str(e)}")

@bot.tree.command(name="luma_ref")
@app_commands.describe(
    aspect="Choose the aspect ratio for your image",
    model="Choose the model to use",
    prompt="What would you like to generate",
    image_url1="First reference image URL (required)",
    weight1="Weight for first image (0.1 to 1.0, default: 0.85)",
    image_url2="Second reference image URL (optional)",
    weight2="Weight for second image (0.1 to 1.0, default: 0.85)",
    image_url3="Third reference image URL (optional)",
    weight3="Weight for third image (0.1 to 1.0, default: 0.85)",
    image_url4="Fourth reference image URL (optional)",
    weight4="Weight for fourth image (0.1 to 1.0, default: 0.85)"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="square", value="1:1"),
    app_commands.Choice(name="portrait", value="3:4"),
    app_commands.Choice(name="landscape", value="4:3"),
    app_commands.Choice(name="wide", value="16:9"),
])
@app_commands.choices(model=[
    app_commands.Choice(name="photon-1 (default, higher quality)", value="photon-1"),
    app_commands.Choice(name="photon-flash-1 (faster)", value="photon-flash-1"),
])
async def luma_ref(
    interaction: discord.Interaction, 
    aspect: str, 
    model: str, 
    prompt: str,
    image_url1: str,
    weight1: float = 0.85,
    image_url2: str = None,
    weight2: float = 0.85,
    image_url3: str = None,
    weight3: float = 0.85,
    image_url4: str = None,
    weight4: float = 0.85
):
    """Generate an image using up to 4 reference images"""
    try:
        # Validate weights
        for weight in [weight1, weight2, weight3, weight4]:
            if weight and not 0.1 <= weight <= 1.0:
                await interaction.response.send_message("❌ All weights must be between 0.1 and 1.0")
                return
        
        # Build image references list
        image_refs = [{"url": image_url1, "weight": weight1}]
        
        if image_url2:
            image_refs.append({"url": image_url2, "weight": weight2})
        if image_url3:
            image_refs.append({"url": image_url3, "weight": weight3})
        if image_url4:
            image_refs.append({"url": image_url4, "weight": weight4})
            
        # Build reference images preview
        ref_preview = "\n".join([
            f"�� Reference {i+1}: {ref['url']} (Weight: {ref['weight']})"
            for i, ref in enumerate(image_refs)
        ])
            
        await interaction.response.send_message(
            f"🎨 Generating {aspect} image using {model}\n"
            f"✏️ Prompt: {prompt}\n\n"
            f"Reference Images:\n{ref_preview}"
        )
        
        # Start the generation with references
        result = await luma.create_capture_with_ref(
            prompt=prompt,
            aspect_ratio=aspect,
            model=model,
            image_refs=image_refs
        )
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Generation started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"Aspect: {aspect}\n"
            f"Model: {model}\n\n"
            f"Please wait while your image is being generated..."
        )
        
        while True:
            final_result = await luma.wait_for_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Generation failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still generating... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("image_url"):
                await interaction.followup.send(
                    f"✅ Generation complete! ({elapsed_time} seconds)\n"
                    f"🖼️ Image: {final_result['image_url']}"
                )
                break
            
    except Exception as e:
        print(f"Error in luma_ref: {str(e)}")  # Debug log
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_style")
@app_commands.describe(
    aspect="Choose the aspect ratio for your image",
    model="Choose the model to use",
    prompt="What would you like to generate",
    style_url="Style reference image URL",
    weight="Style influence (0.1 to 1.0, default: 0.85)"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="square", value="1:1"),
    app_commands.Choice(name="portrait", value="3:4"),
    app_commands.Choice(name="landscape", value="4:3"),
    app_commands.Choice(name="wide", value="16:9"),
])
@app_commands.choices(model=[
    app_commands.Choice(name="photon-1 (default, higher quality)", value="photon-1"),
    app_commands.Choice(name="photon-flash-1 (faster)", value="photon-flash-1"),
])
async def luma_style(
    interaction: discord.Interaction, 
    aspect: str, 
    model: str, 
    prompt: str,
    style_url: str,
    weight: float = 0.85
):
    """Generate an image using a style reference image"""
    try:
        # Validate weight
        if not 0.1 <= weight <= 1.0:
            await interaction.response.send_message("❌ Weight must be between 0.1 and 1.0")
            return
        
        # Build style reference
        style_ref = [{"url": style_url, "weight": weight}]
            
        await interaction.response.send_message(
            f"🎨 Generating {aspect} image using {model}\n"
            f"✏️ Prompt: {prompt}\n"
            f"🎨 Style: {style_url}\n"
            f"⚖️ Weight: {weight}"
        )
        
        # Start the generation with style reference
        result = await luma.create_capture_with_style(
            prompt=prompt,
            aspect_ratio=aspect,
            model=model,
            style_refs=style_ref
        )
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Generation started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"Aspect: {aspect}\n"
            f"Model: {model}\n\n"
            f"Please wait while your image is being generated..."
        )
        
        while True:
            final_result = await luma.wait_for_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Generation failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still generating... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("image_url"):
                await interaction.followup.send(
                    f"✅ Generation complete! ({elapsed_time} seconds)\n"
                    f"🖼️ Image: {final_result['image_url']}"
                )
                break
            
    except Exception as e:
        print(f"Error in luma_style: {str(e)}")  # Debug log
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_char")
@app_commands.describe(
    aspect="Choose the aspect ratio for your image",
    model="Choose the model to use",
    prompt="What would you like to generate",
    image_url1="First character reference image (required)",
    image_url2="Second character reference image (optional)",
    image_url3="Third character reference image (optional)",
    image_url4="Fourth character reference image (optional)"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="square", value="1:1"),
    app_commands.Choice(name="portrait", value="3:4"),
    app_commands.Choice(name="landscape", value="4:3"),
    app_commands.Choice(name="wide", value="16:9"),
])
@app_commands.choices(model=[
    app_commands.Choice(name="photon-1 (default, higher quality)", value="photon-1"),
    app_commands.Choice(name="photon-flash-1 (faster)", value="photon-flash-1"),
])
async def luma_char(
    interaction: discord.Interaction, 
    aspect: str, 
    model: str, 
    prompt: str,
    image_url1: str,
    image_url2: str = None,
    image_url3: str = None,
    image_url4: str = None
):
    """Generate an image using character reference images"""
    try:
        # Build character references list
        char_images = [image_url1]
        if image_url2:
            char_images.append(image_url2)
        if image_url3:
            char_images.append(image_url3)
        if image_url4:
            char_images.append(image_url4)
            
        # Build character preview
        char_preview = "\n".join([
            f"👤 Reference {i+1}: {url}"
            for i, url in enumerate(char_images)
        ])
            
        await interaction.response.send_message(
            f"🎨 Generating {aspect} image using {model}\n"
            f"✏️ Prompt: {prompt}\n\n"
            f"Character References:\n{char_preview}"
        )
        
        # Start the generation with character reference
        result = await luma.create_capture_with_char(
            prompt=prompt,
            aspect_ratio=aspect,
            model=model,
            char_images=char_images
        )
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Generation started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"Aspect: {aspect}\n"
            f"Model: {model}\n\n"
            f"Please wait while your image is being generated..."
        )
        
        while True:
            final_result = await luma.wait_for_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Generation failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still generating... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("image_url"):
                await interaction.followup.send(
                    f"✅ Generation complete! ({elapsed_time} seconds)\n"
                    f"🖼️ Image: {final_result['image_url']}"
                )
                break
            
    except Exception as e:
        print(f"Error in luma_char: {str(e)}")  # Debug log
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_mod")
@app_commands.describe(
    model="Choose the model to use",
    prompt="Describe the changes you want to make",
    image_url="URL of the image to modify",
    weight="Image influence (0.1 to 1.0, default: 0.45, use 0.1 or less for color changes)"
)
@app_commands.choices(model=[
    app_commands.Choice(name="photon-1 (default, higher quality)", value="photon-1"),
    app_commands.Choice(name="photon-flash-1 (faster)", value="photon-flash-1"),
])
async def luma_mod(
    interaction: discord.Interaction,
    model: str,
    prompt: str,
    image_url: str,
    weight: float = 0.45
):
    """Modify an existing image using AI"""
    try:
        # Validate weight
        if not 0.0 <= weight <= 1.0:
            await interaction.response.send_message("❌ Weight must be between 0.0 and 1.0")
            return
            
        await interaction.response.send_message(
            f"🎨 Modifying image using {model}\n"
            f"✏️ Changes: {prompt}\n"
            f"🖼️ Image: {image_url}\n"
            f"⚖️ Weight: {weight}\n\n"
            f"💡 Tip: For color changes, use weight of 0.1 or less"
        )
        
        # Start the modification
        result = await luma.create_capture_with_mod(
            prompt=prompt,
            model=model,
            image_url=image_url,
            weight=weight
        )
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Modification failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Modification started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"Model: {model}\n\n"
            f"Please wait while your image is being modified..."
        )
        
        while True:
            final_result = await luma.wait_for_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Modification failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still modifying... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("image_url"):
                await interaction.followup.send(
                    f"✅ Modification complete! ({elapsed_time} seconds)\n"
                    f"🖼️ Image: {final_result['image_url']}"
                )
                break
            
    except Exception as e:
        print(f"Error in luma_mod: {str(e)}")  # Debug log
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_t2v")
@app_commands.describe(
    prompt="What video would you like to generate",
    aspect="Choose the aspect ratio for your video",
    loop="Should the video loop seamlessly?",
    camera="Add camera motion to your video"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="square", value="1:1"),
    app_commands.Choice(name="portrait", value="3:4"),
    app_commands.Choice(name="landscape", value="4:3"),
    app_commands.Choice(name="wide", value="16:9"),
])
@app_commands.choices(loop=[
    app_commands.Choice(name="yes", value=1),
    app_commands.Choice(name="no", value=0),
])
@app_commands.choices(camera=CAMERA_MOTION_CHOICES)
async def luma_t2v(
    interaction: discord.Interaction,
    prompt: str,
    aspect: str = "16:9",
    loop: int = 0,
    camera: str = ""
):
    """Generate a video from text using AI"""
    try:
        # Combine camera motion with prompt
        full_prompt = camera + prompt
        
        await interaction.response.send_message(
            f"🎬 Generating {aspect} video\n"
            f"✏️ Prompt: {full_prompt}\n"
            f"🔄 Loop: {'Yes' if loop else 'No'}"
        )
        
        result = await luma.create_video(
            prompt=full_prompt,
            aspect_ratio=aspect,
            loop=bool(loop)
        )
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Video generation started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"Aspect: {aspect}\n"
            f"This might take several minutes..."
        )
        
        while True:
            final_result = await luma.wait_for_video_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Generation failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still generating... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("video_url"):
                await interaction.followup.send(
                    f"✅ Video generation complete! ({elapsed_time} seconds)\n"
                    f"🎥 Video: {final_result['video_url']}"
                )
                break
            
    except Exception as e:
        print(f"Error in luma_t2v: {str(e)}")  # Debug log
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_i2v")
@app_commands.describe(
    prompt="What video would you like to generate",
    image_url1="First image URL (required)",
    frame_type1="Frame type for first image",
    image_url2="Second image URL (optional)",
    frame_type2="Frame type for second image (if using two images)",
    aspect="Choose the aspect ratio for your video",
    loop="Should the video loop seamlessly?",
    camera="Add camera motion to your video"
)
@app_commands.choices(aspect=[
    app_commands.Choice(name="square", value="1:1"),
    app_commands.Choice(name="portrait", value="3:4"),
    app_commands.Choice(name="landscape", value="4:3"),
    app_commands.Choice(name="wide", value="16:9"),
])
@app_commands.choices(frame_type1=[
    app_commands.Choice(name="start frame", value="frame0"),
])
@app_commands.choices(frame_type2=[
    app_commands.Choice(name="end frame", value="frame1"),
])
@app_commands.choices(loop=[
    app_commands.Choice(name="yes", value=1),
    app_commands.Choice(name="no", value=0),
])
@app_commands.choices(camera=CAMERA_MOTION_CHOICES)
async def luma_i2v(
    interaction: discord.Interaction,
    prompt: str,
    image_url1: str,
    frame_type1: str,
    image_url2: str = None,
    frame_type2: str = None,
    aspect: str = "16:9",
    loop: int = 0,
    camera: str = ""
):
    """Generate a video from one or two images using AI"""
    try:
        # Combine camera motion with prompt
        full_prompt = camera + prompt
        
        # Build preview message based on number of images
        if image_url2:
            preview = (
                f"🎬 Generating {aspect} video with start and end frames\n"
                f"✏️ Prompt: {full_prompt}\n"
                f"🖼️ Start Frame: {image_url1}\n"
                f"🖼️ End Frame: {image_url2}\n"
                f"🔄 Loop: {'Yes' if loop else 'No'}"
            )
        else:
            preview = (
                f"🎬 Generating {aspect} video with start frame\n"
                f"✏️ Prompt: {full_prompt}\n"
                f"🖼️ Frame: {image_url1}\n"
                f"🔄 Loop: {'Yes' if loop else 'No'}"
            )
            
        await interaction.response.send_message(preview)
        
        # Start the generation
        result = await luma.create_image_video(
            prompt=full_prompt,
            image_url1=image_url1,
            frame_type1=frame_type1,
            image_url2=image_url2,
            frame_type2=frame_type2,
            aspect_ratio=aspect,
            loop=bool(loop),
            camera_motion=camera
        )
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Video generation started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"Aspect: {aspect}\n"
            f"This might take several minutes..."
        )
        
        while True:
            final_result = await luma.wait_for_video_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Generation failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still generating... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("video_url"):
                await interaction.followup.send(
                    f"✅ Video generation complete! ({elapsed_time} seconds)\n"
                    f"🎥 Video: {final_result['video_url']}"
                )
                break
            
    except Exception as e:
        print(f"Error in luma_i2v: {str(e)}")  # Debug log
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_xtnd")
@app_commands.describe(
    mode="Choose how to extend the video",
    prompt="What should happen in the extended video",
    video_id1="ID of the video to extend (from previous generation)",
    video_id2="Second video ID (only needed for interpolation mode)",
    image_url="Image URL (only needed for modes with frame images)",
    camera="Add camera motion to your video"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="Forward Extension", value="extend"),
    app_commands.Choice(name="Reverse Extension", value="reverse"),
    app_commands.Choice(name="Extend with End Frame", value="extend_end"),
    app_commands.Choice(name="Reverse with Start Frame", value="reverse_start"),
    app_commands.Choice(name="Interpolate Between Videos", value="interpolate")
])
@app_commands.choices(camera=CAMERA_MOTION_CHOICES)
async def luma_xtnd(
    interaction: discord.Interaction,
    mode: str,
    prompt: str,
    video_id1: str,
    video_id2: str = None,
    image_url: str = None,
    camera: str = ""
):
    """Extend a previously generated video"""
    try:
        # Combine camera motion with prompt
        full_prompt = camera + prompt
        
        # Validate parameters based on mode
        if mode == "interpolate" and not video_id2:
            await interaction.response.send_message("❌ Interpolation requires two video IDs!")
            return
            
        if mode in ["extend_end", "reverse_start"] and not image_url:
            await interaction.response.send_message("❌ This mode requires an image URL!")
            return
            
        # Build preview message based on mode
        preview = f"🎬 Extending video with {mode} mode\n✏️ Prompt: {full_prompt}\n"
        
        if mode == "extend":
            preview += f"📝 Extending forward from video: `{video_id1}`"
        elif mode == "reverse":
            preview += f"📝 Extending backward from video: `{video_id1}`"
        elif mode == "extend_end":
            preview += f"📝 Extending video `{video_id1}` to end frame\n🖼️ End frame: {image_url}"
        elif mode == "reverse_start":
            preview += f"📝 Extending backward from video `{video_id1}` with start frame\n🖼️ Start frame: {image_url}"
        else:  # interpolate
            preview += f"📝 Interpolating between videos:\n💫 Start: `{video_id1}`\n💫 End: `{video_id2}`"
            
        await interaction.response.send_message(
            f"{preview}\n\n⚠️ Checking video status..."
        )
        
        # Check if video(s) are completed
        status = await luma.get_video_status(video_id1)
        if not status.get("success") or status.get("status") != "completed":
            await interaction.followup.send(
                "❌ First video must be completed before extending!\n"
                f"Current status: {status.get('status', 'unknown')}\n"
                "💡 Use `/luma_status {video_id1}` to check status"
            )
            return
            
        if video_id2:
            status2 = await luma.get_video_status(video_id2)
            if not status2.get("success") or status2.get("status") != "completed":
                await interaction.followup.send(
                    "❌ Second video must be completed before interpolating!\n"
                    f"Current status: {status2.get('status', 'unknown')}\n"
                    "💡 Use `/luma_status {video_id2}` to check status"
                )
                return
        
        # Start the extension
        result = await luma.extend_video(
            prompt=full_prompt,
            mode=mode,
            video_id1=video_id1,
            video_id2=video_id2,
            image_url=image_url,
            camera_motion=camera
        )
        
        if not result.get("success"):
            await interaction.followup.send(f"❌ Extension failed: {result.get('error', 'Unknown error')}")
            return
            
        generation_id = result.get("id")
        elapsed_time = 0
        
        # Send initial status message
        await interaction.followup.send(
            f"⏳ Video extension started (ID: `{generation_id}`)\n"
            f"Status: {result.get('state', 'queued')}\n"
            f"This might take several minutes..."
        )
        
        while True:
            final_result = await luma.wait_for_video_generation(generation_id)
            
            if not final_result.get("success"):
                await interaction.followup.send(
                    f"❌ Extension failed: {final_result.get('error', 'Unknown error')}\n"
                    f"You can check status manually with `/luma_status {generation_id}`"
                )
                break
                
            if final_result.get("progress_update"):
                elapsed_time = final_result.get("elapsed_time", 0)
                await interaction.followup.send(
                    f"⏳ Still extending... ({elapsed_time} seconds elapsed)\n"
                    f"Status: {final_result.get('status', 'processing')}"
                )
                continue
                
            if final_result.get("video_url"):
                await interaction.followup.send(
                    f"✅ Video extension complete! ({elapsed_time} seconds)\n"
                    f"🎥 Video: {final_result['video_url']}\n"
                    f"📝 Generation ID: `{generation_id}`\n"
                    f"💡 Use this ID with /luma_xtnd to extend this video further!"
                )
                break
            
    except Exception as e:
        print(f"Error in luma_xtnd: {str(e)}")  # Debug log
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="luma_help")
@app_commands.describe(
    section="Choose a specific section of help (optional)"
)
@app_commands.choices(section=[
    app_commands.Choice(name="Image Generation", value="image"),
    app_commands.Choice(name="Video Generation", value="video"),
    app_commands.Choice(name="Video Extension", value="extend"),
    app_commands.Choice(name="General Info", value="info")
])
async def luma_help(
    interaction: discord.Interaction,
    section: str = None
):
    """Get detailed help and instructions for all Luma AI commands"""
    
    # General Info Section
    general_info = """
🤖 **Luma AI Discord Bot Help**
This bot provides access to Luma AI's image and video generation capabilities.

**Quick Start:**
• Use `/luma_gen` for basic image generation
• Use `/luma_t2v` for basic video generation
• All generation commands will provide a Generation ID
• Generation IDs are needed for status checks and video extensions

**Tips:**
• Higher weights in image references mean closer to reference image
• For color changes in image modification, use weights of 0.1 or less
• Camera Motions can be selected from drop down, or manually inserted in the prompt for user control
• Videos must be in 'completed' state before extending
"""

    # Image Commands Section
    image_commands = """
🖼️ **Image Generation Commands**

**/luma_gen**
• Basic image generation from text
• Choose aspect ratio and model
• Example: `/luma_gen prompt:a beautiful sunset aspect:wide`

**/luma_ref**
• Generate with up to 4 reference images
• Each reference can have its own weight (0.1-1.0)
• Example: `/luma_ref prompt:similar style image_url1:url weight1:0.7`

**/luma_style**
• Generate with a single style reference
• Great for matching specific artistic styles
• Example: `/luma_style prompt:in this style image_url:url weight:0.8`

**/luma_char**
• Generate with character references (up to 4 images)
• All images should be of the same person/character
• Example: `/luma_char prompt:same person in different pose image_url1:url`

**/luma_mod**
• Modify existing images
• Default weight: 0.45
• Use weight ≤ 0.1 for color changes
• Example: `/luma_mod prompt:make background blue image_url:url weight:0.05`
"""

    # Video Commands Section
    video_commands = """
🎥 **Video Generation Commands**

**/luma_t2v**
• Text to video generation
• Choose aspect ratio and loop options
• Optional camera motions
• Example: `/luma_t2v prompt:flying through clouds camera:Dolly In`

**/luma_i2v**
• Image to video generation
• Use 1-2 images as keyframes
• Supports start frame, end frame, or both
• Example: `/luma_i2v prompt:animate this image_url1:url`
"""

    # Video Extension Section
    video_extension = """
📽️ **Video Extension Commands**

**/luma_xtnd**
Five extension modes available:
1. **Forward Extension**
   • Continues the video forward
   • Needs one video ID

2. **Reverse Extension**
   • Adds content before the video
   • Needs one video ID

3. **Extend with End Frame**
   • Extends to match an end image
   • Needs video ID and image

4. **Reverse with Start Frame**
   • Extends backward from video to match start image
   • Needs video ID and image

5. **Interpolate**
   • Creates transition between two videos
   • Needs two video IDs

Example: `/luma_xtnd mode:Forward Extension prompt:continue the action video_id1:your-id`

**Important Notes:**
• Videos must be in 'completed' state before extending
• Generation IDs are shown in previous generation results
• Camera motions can be added to any extension
"""

    try:
        if section == "image":
            await interaction.response.send_message(image_commands)
        elif section == "video":
            await interaction.response.send_message(video_commands)
        elif section == "extend":
            await interaction.response.send_message(video_extension)
        elif section == "info":
            await interaction.response.send_message(general_info)
        else:
            # Send all sections with a small delay between each
            await interaction.response.send_message(general_info)
            await asyncio.sleep(1)
            await interaction.followup.send(image_commands)
            await asyncio.sleep(1)
            await interaction.followup.send(video_commands)
            await asyncio.sleep(1)
            await interaction.followup.send(video_extension)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error displaying help: {str(e)}")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN) 