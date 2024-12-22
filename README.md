# Luma AI Discord Bot
A Discord bot that interfaces with Luma AI's API to generate and manipulate images and videos. This bot provides a user-friendly interface for Luma's powerful AI generation capabilities directly in Discord.

## Features
### Image Generation
- `/luma_gen` - Basic image generation from text
- `/luma_ref` - Generate with reference images (up to 4)
- `/luma_style` - Generate with style reference
- `/luma_char` - Generate with character references
- `/luma_mod` - Modify existing images (adjustable influence)

### Video Generation
- `/luma_t2v` - Text to video generation
- `/luma_i2v` - Image to video generation (1-2 images)
- `/luma_xtnd` - Extend or interpolate videos
  - Forward extension
  - Reverse extension
  - Extension with end frame
  - Reverse with start frame
  - Video interpolation

### Additional Features
- Camera motion controls (dropdown or manual input)
- Multiple aspect ratio options
- Loop control for videos
- Comprehensive status checking
- Detailed help command

## Setup
### Prerequisites
- Python 3.8 or higher
- Discord Bot Token
- Luma AI API Key
- ImgBB API Key

### Installation
1. Clone the repository
```bash
git clone [repository-url]
cd luma-discord-bot
```

2. Install required packages
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   - Option 1: Copy and modify the example file
     ```bash
     cp .env.example .env
     ```
     Then edit `.env` with your actual API keys
   
   - Option 2: Create new `.env` file with:
     ```
     DISCORD_TOKEN=your_discord_token
     LUMA_API_KEY=your_luma_key
     IMGBB_API_KEY=your_imgbb_key
     ```

4. Run the bot
```bash
python lumadisc.py
```

5. Sync the commands (do this after any command changes)
```bash
python sync.py
```

## Command Usage

### Basic Commands
```
/luma_help - Display comprehensive help information
/luma_status <generation_id> - Check the status of any generation
```

### Image Generation Examples
```
/luma_gen aspect:wide model:photon-1 prompt:A serene mountain landscape at sunset
```
Expected response:
```
🎨 Generating wide image using photon-1
✏️ Prompt: A serene mountain landscape at sunset
⏳ Generation started (ID: `abc123`)...
```

### Video Generation Examples
```
/luma_t2v prompt:Flying through clouds camera:Dolly In aspect:wide loop:yes
```

### Video Extension Examples
1. Forward Extension
   ```
   /luma_xtnd mode:Forward Extension prompt:continue the action video_id1:abc123
   ```
2. Interpolation
   ```
   /luma_xtnd mode:interpolate prompt:smooth transition video_id1:abc123 video_id2:xyz789
   ```

## Troubleshooting

### Command Sync Issues
```bash
python sync.py
```
Expected output:
```
Logged in as [Bot Name]
Commands synced successfully!
Registered commands: ['luma_gen', 'luma_ref', ...]
```

### Common Error Messages
```
❌ Invalid API key - Check your .env configuration
❌ Rate limit exceeded - Wait before trying again
❌ Invalid image URL - Ensure URL is directly accessible
❌ Generation failed - Check prompt guidelines
```

## Best Practices

### Example Prompts
```
/luma_gen prompt:A majestic mountain landscape at golden hour, dramatic lighting, volumetric clouds, shot from below
```

```
/luma_t2v prompt:Camera slowly pans across a serene beach at sunset, gentle waves rolling in camera:Pan Right
```

### Weight Examples
```
/luma_ref prompt:similar pose but evening lighting image_url1:url weight1:0.7
/luma_mod prompt:change sky to purple image_url:url weight:0.1
```

## Getting API Keys

### Discord Bot Token
1. Visit [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the Bot section
4. Create a bot and copy the token
5. Enable necessary intents (Message Content Intent)
6. Use the OAuth2 URL Generator to invite the bot to your server
   - Required permissions: Send Messages, Use Slash Commands

### Luma AI API Key
1. Visit [Luma AI](https://lumalabs.ai/)
2. Sign up for an account
3. Obtain your API key from the dashboard

### ImgBB API Key
1. Visit [ImgBB](https://api.imgbb.com/)
2. Create an account
3. Get your API key from the dashboard

## Detailed Command Examples

### Image Generation Examples

**Basic Image Generation**
```
/luma_gen aspect:wide model:photon-1 prompt:A serene mountain landscape at sunset
```
Expected response:
```
🎨 Generating wide image using photon-1
✏️ Prompt: A serene mountain landscape at sunset
⏳ Generation started (ID: `abc123`)...
```

**Reference-Based Generation**
```
/luma_ref aspect:square model:photon-1 prompt:Similar style but with snow image_url1:https://example.com/image.jpg weight1:0.7
```

### Video Generation Examples

**Text to Video with Camera Motion**
```
/luma_t2v prompt:Flying through clouds camera:Dolly In aspect:wide loop:yes
```

**Video Extension Tips**
1. Forward Extension
   ```
   /luma_xtnd mode:Forward Extension prompt:continue the action video_id1:abc123
   ```
2. Interpolation Between Videos
   ```
   /luma_xtnd mode:interpolate prompt:smooth transition video_id1:abc123 video_id2:xyz789
   ```

### Command Sync Issues
1. **Commands not appearing in Discord**
   ```bash
   python sync.py
   ```
   Expected output:
   ```
   Logged in as [Bot Name] (ID: [Bot ID])
   ------
   Starting global command sync...
   Commands synced successfully!
   Registered commands: ['luma_gen', 'luma_ref', 'luma_style', 'luma_char', 'luma_mod', 'luma_status', 'luma_t2v', 'luma_i2v', 'luma_xtnd', 'luma_help']
   ```

## Advanced Troubleshooting

### Common Error Messages
```
❌ Invalid API key - Check your .env configuration
❌ Rate limit exceeded - Wait before trying again
❌ Invalid image URL - Ensure URL is directly accessible
❌ Generation failed - Check prompt guidelines
```

## Best Practices

### Prompting Tips
1. **Image Generation**
   - Be specific about style, lighting, and composition
   - Use artistic references: "in the style of..."
   - Mention camera angles: "shot from below..."

2. **Video Generation**
   - Describe motion clearly: "camera slowly pans across..."
   - Specify transitions: "gradually fading from day to night"
   - Use camera motion commands for precise control

3. **Weight Guidelines**
   - Style transfer: 0.6-0.8
   - Color modifications: 0.1-0.3
   - Character consistency: 0.7-0.9
   - General modifications: 0.4-0.6

## Contributing Guidelines

1. **Bug Reports**
   - Use the Issues tab
   - Include command used
   - Attach error messages
   - Describe expected vs actual behavior

2. **Feature Requests**
   - Explain the use case
   - Provide example commands
   - Suggest implementation approach

3. **Pull Requests**
   - Follow existing code style
   - Add comments for complex logic
   - Update README if adding features
   - Test commands before submitting

## Support Resources
- [Luma AI Documentation](https://lumalabs.ai/docs)
- [Discord.py Guide](https://discordpy.readthedocs.io/)
- [Project Issues](https://github.com/yourusername/luma-discord-bot/issues)

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support
If you encounter any issues or have questions:
1. Check the `/luma_help` command
2. Review error messages
3. Open an issue on GitHub

## Acknowledgments
- [Luma AI](https://lumalabs.ai/) for their powerful AI generation API
- [Discord.py](https://discordpy.readthedocs.io/) for the Discord bot framework
- [ImgBB](https://api.imgbb.com/) for image hosting services
