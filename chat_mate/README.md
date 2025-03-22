# ChatMate - AI-Powered Community Management

ChatMate is a comprehensive AI-powered social media management platform that helps you build, monitor, and grow thriving communities across multiple platforms.

## 🌟 Key Features

### Unified Community Dashboard
- **Cross-platform analytics** - Track metrics from Twitter, Facebook, Reddit, LinkedIn, Instagram, and StockTwits in one place
- **Community health monitoring** - Analyze engagement, sentiment, and growth trends
- **Top member identification** - Identify and nurture influential community advocates

### Advanced Community Building Tools
- **Data-driven insights** - Get actionable recommendations tailored to your community
- **Strategic planning** - Create and manage comprehensive community building plans
- **Visualization tools** - Visual representation of community metrics for better decision making

### Content & Engagement Management
- **Prompt library** - Access a growing collection of effective prompts for community engagement
- **Multi-platform posting** - Create and schedule content across all your platforms
- **Sentiment analysis** - Monitor community sentiment and adapt your strategy accordingly

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- PyQt5
- NLTK (optional, for enhanced sentiment analysis)

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/chat_mate.git
cd chat_mate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up environment variables for social media APIs
```bash
# Twitter
export TWITTER_API_KEY="your_api_key"
export TWITTER_API_SECRET="your_api_secret"
export TWITTER_ACCESS_TOKEN="your_access_token"
export TWITTER_ACCESS_SECRET="your_access_secret"

# Facebook
export FACEBOOK_PAGE_ID="your_page_id"
export FACEBOOK_ACCESS_TOKEN="your_access_token"

# Reddit
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
export REDDIT_USERNAME="your_username"
export REDDIT_PASSWORD="your_password"

# Add other platform credentials as needed
```

4. Run the application
```bash
python main.py
```

## 📊 Using the Community Dashboard

The Community Dashboard provides real-time insights into your social media communities:

1. **Overview Tab** - View community health score, strengths, weaknesses, and opportunities
2. **Insights Tab** - Get actionable recommendations and content insights
3. **Planning Tab** - Access your community building plan with daily activities

### Filtering Data
Use the platform selector at the top of the dashboard to filter data for specific platforms.

### Generating Fresh Insights
Click the "Generate Insights" button to create new recommendations based on the latest data.

## 🧩 Creating Custom Prompts

ChatMate includes a prompt manager for creating and using effective community engagement prompts:

1. Navigate to the "Prompt Manager" tab
2. Select the "Custom" category and click "Add New"
3. Enter details for your custom prompt
4. Click "Save Changes" to save your prompt
5. Click "Use This Prompt" to send it to the execution tab

## 📱 Social Media Integration

ChatMate currently supports these platforms:
- Twitter
- Facebook
- Reddit
- LinkedIn
- Instagram
- StockTwits

To add your social accounts:
1. Set up the required environment variables
2. Restart the application
3. The platform will be automatically added to your dashboard

## 🔧 Advanced Configuration

### Custom Sentiment Analysis
- Create a JSON lexicon file in `utils/lexicons/custom_lexicon.json`
- Format: `{"word": score}` where score ranges from -1.0 to 1.0

### Data Storage
- Metrics are stored in `social/data/unified_community_metrics.json`
- Community members data is in `social/data/unified_community_members.json`
- Insights are saved in `social/data/community_insights.json`

## 📈 Future Enhancements
- AI-driven content generation
- Competitive community analysis
- Advanced member segmentation
- Automated engagement workflows

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.

## Environment Variables

This project requires certain environment variables to be set in a `.env` file in the root directory:

```
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_PUBLIC_KEY=your_public_key
DISCORD_GUILD_ID=your_guild_id
```

**Important:** Never commit the `.env` file to the repository. It is already included in `.gitignore`.

## Setup

1. Clone the repository
2. Install dependencies
3. Create a `.env` file with the required variables
4. Run the application 