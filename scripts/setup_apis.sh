#!/bin/bash

# ZeroCrash API Setup Guide Script

echo "🔧 ZeroCrash API Setup Guide"
echo "============================"
echo ""

echo "This script will help you set up the required API keys for ZeroCrash."
echo ""

# Function to get user input
get_api_key() {
    local service_name=$1
    local env_var_name=$2
    local instructions=$3
    
    echo "📋 Setting up $service_name"
    echo "Instructions: $instructions"
    echo ""
    
    read -p "Enter your $service_name API key (or press Enter to skip): " api_key
    
    if [ ! -z "$api_key" ]; then
        # Update .env file
        if [ -f ".env" ]; then
            # Check if the line exists and replace it, otherwise append
            if grep -q "^$env_var_name=" .env; then
                # Replace existing line (works on both macOS and Linux)
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s/^$env_var_name=.*/$env_var_name=$api_key/" .env
                else
                    sed -i "s/^$env_var_name=.*/$env_var_name=$api_key/" .env
                fi
            else
                echo "$env_var_name=$api_key" >> .env
            fi
            echo "✅ $service_name API key saved to .env file"
        else
            echo "$env_var_name=$api_key" > .env
            echo "✅ Created .env file with $service_name API key"
        fi
    else
        echo "⏭️  Skipped $service_name setup (you can add it later in .env file)"
    fi
    echo ""
}

# Check if .env exists, create from template if not
if [ ! -f ".env" ]; then
    if [ -f "../.env.example" ]; then
        cp ../.env.example .env
        echo "📄 Created .env file from template"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        echo "📄 Created .env file from template"
    else
        echo "📄 Creating new .env file"
        cat > .env << EOF
# ZeroCrash Backend Configuration
MOCK_MODE=true
DEBUG=true
CACHE_TTL=3600
RATE_LIMIT_PER_MINUTE=60
DATABASE_URL=sqlite:///./zerocrash.db
HOST=0.0.0.0
PORT=8000
EOF
    fi
fi

echo "🔑 API Key Setup"
echo "=================="
echo ""

# Google News API (GNews.io)
get_api_key "Google News (GNews.io)" "GNEWS_API_KEY" "Get your free API key from https://gnews.io/"

# YouTube Data API v3
get_api_key "YouTube Data API v3" "YOUTUBE_API_KEY" "Create a project at https://console.cloud.google.com and enable YouTube Data API v3"

# Reddit API
echo "📋 Setting up Reddit API"
echo "Instructions: Create an app at https://www.reddit.com/prefs/apps"
echo ""

read -p "Enter your Reddit Client ID: " reddit_client_id
read -p "Enter your Reddit Client Secret: " reddit_client_secret

if [ ! -z "$reddit_client_id" ] && [ ! -z "$reddit_client_secret" ]; then
    # Update .env file for Reddit
    if grep -q "^REDDIT_CLIENT_ID=" .env; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^REDDIT_CLIENT_ID=.*/REDDIT_CLIENT_ID=$reddit_client_id/" .env
            sed -i '' "s/^REDDIT_CLIENT_SECRET=.*/REDDIT_CLIENT_SECRET=$reddit_client_secret/" .env
        else
            sed -i "s/^REDDIT_CLIENT_ID=.*/REDDIT_CLIENT_ID=$reddit_client_id/" .env
            sed -i "s/^REDDIT_CLIENT_SECRET=.*/REDDIT_CLIENT_SECRET=$reddit_client_secret/" .env
        fi
    else
        echo "REDDIT_CLIENT_ID=$reddit_client_id" >> .env
        echo "REDDIT_CLIENT_SECRET=$reddit_client_secret" >> .env
    fi
    echo "✅ Reddit API credentials saved"
else
    echo "⏭️  Skipped Reddit API setup"
fi

echo ""
echo "🎯 Setup Complete!"
echo "=================="
echo ""

# Check current configuration
echo "📊 Current Configuration:"
echo "-------------------------"

if grep -q "GNEWS_API_KEY=your-gnews-api-key" .env; then
    echo "❌ Google News API: Not configured"
else
    echo "✅ Google News API: Configured"
fi

if grep -q "YOUTUBE_API_KEY=your-youtube-api-key" .env; then
    echo "❌ YouTube API: Not configured"  
else
    echo "✅ YouTube API: Configured"
fi

if grep -q "REDDIT_CLIENT_ID=your-reddit-client-id" .env; then
    echo "❌ Reddit API: Not configured"
else
    echo "✅ Reddit API: Configured"
fi

echo ""
echo "💡 Next Steps:"
echo "1. Run './scripts/start_backend.sh' to start the server"
echo "2. Visit http://localhost:8000/docs to see the API documentation"  
echo "3. Test your APIs at http://localhost:8000/api/connections/test"
echo "4. Set MOCK_MODE=false in .env when you're ready to use real APIs"
echo ""

echo "📝 Note: The application will work in MOCK_MODE even without API keys."
echo "This is perfect for development and testing!"