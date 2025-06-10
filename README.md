# Treasure Hunter Telegram Bot

A specialized AI-powered Telegram bot for treasure hunting enthusiasts that analyzes images, signals, and provides expert guidance using OpenAI's GPT-4o.

## Features

### 🔍 Image Analysis
- Upload photos of finds, signals, or hunting sites
- AI-powered analysis of potential treasure indicators
- Identification of archaeological features and artifacts
- Soil composition and ground disturbance analysis
- Historical context and dating guidance

### 📊 Signal Analysis
- Describe metal detecting signals for expert interpretation
- Signal strength and consistency evaluation
- Target identification and confidence assessment
- Digging recommendations and approach strategies
- Equipment settings optimization

### ❓ Expert Q&A
- Ask any treasure hunting related questions
- Get expert advice on techniques and equipment
- Historical research and site analysis guidance
- Legal and ethical treasure hunting practices
- Safety protocols and best practices

### 💡 Knowledge Base
- General treasure hunting tips and techniques
- Equipment recommendations by experience level
- Legal and ethical guidelines
- Safety protocols for treasure hunters
- Common finds identification and analysis

## Available Commands

- `/start` - Welcome message and quick action buttons
- `/help` - Show all available commands
- `/analyze` - Instructions for image analysis
- `/ask [question]` - Ask treasure hunting questions
- `/signal [description]` - Analyze metal detecting signals
- `/tips` - Get general treasure hunting tips
- `/equipment` - Equipment recommendations
- `/legal` - Legal and ethical guidelines
- `/safety` - Safety guidelines

## How to Use

1. **Start the bot**: Send `/start` to get welcomed and see quick action buttons
2. **Upload images**: Send photos directly for AI analysis of potential finds
3. **Ask questions**: Use `/ask` followed by your question
4. **Analyze signals**: Use `/signal` followed by your signal description
5. **Get guidance**: Use specific commands for tips, equipment, legal, or safety info

## Examples

### Image Analysis
Simply upload a photo of your find, signal, or site. The AI will analyze:
- Potential treasure indicators
- Archaeological significance
- Historical context
- Recommendations for further investigation

### Signal Analysis
```
/signal Strong consistent tone at 6 inches, VDI shows 87, ground is moderately mineralized
```

### Questions
```
/ask What's the best metal detector for beach hunting?
/ask How deep can I expect to find colonial-era coins?
/ask What are the legal requirements for detecting in state parks?
```

## Bot Configuration

The bot uses:
- **OpenAI GPT-4o** for intelligent analysis and responses
- **Rate limiting** to prevent API abuse (10 requests per minute per user)
- **Image processing** with automatic resizing and format conversion
- **Multi-language support** for comprehensive responses
- **Error handling** with graceful fallbacks

## Technical Features

- Supports multiple image formats (JPG, PNG, GIF, BMP, WEBP)
- Automatic image compression and optimization
- Intelligent response chunking for long messages
- Inline keyboard navigation for better user experience
- Comprehensive error handling and logging
- Rate limiting protection

## Safety and Ethics

The bot emphasizes:
- Legal and ethical treasure hunting practices
- Proper permissions and landowner respect
- Historical preservation and reporting
- Environmental responsibility
- Safety protocols and risk management

## Support

The bot provides expert-level guidance on:
- Metal detecting techniques and equipment
- Historical research and site analysis
- Artifact identification and dating
- Legal compliance and permissions
- Safety protocols and best practices

---

Your Treasure Hunter Bot is now ready to assist treasure hunting enthusiasts with AI-powered analysis and expert guidance!