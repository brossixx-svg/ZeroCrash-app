# ZeroCrash.app - Complete AI-Powered IT Content Platform

ZeroCrash is a comprehensive platform that aggregates IT content from multiple sources (Google News, YouTube, Reddit) and provides AI-powered SEO optimization suggestions. The platform features a modern web interface with a complete FastAPI backend.

## 🌟 Features

### Frontend (Web UI)
- **Responsive Design**: Modern UI with Tailwind CSS
- **Advanced Search**: Multi-source content search with filters
- **Dashboard**: Real-time trending content and analytics
- **SEO Generator**: AI-powered SEO suggestions and content optimization
- **Category Management**: Hierarchical IT taxonomy
- **Settings**: API configuration and customization

### Backend (FastAPI)
- **Multi-API Integration**: Google News, YouTube Data API v3, Reddit API
- **Intelligent Caching**: TTL-based caching with Redis support
- **SEO Intelligence**: Advanced SEO analysis and recommendations
- **Rate Limiting**: Built-in API rate limiting
- **Mock Mode**: Full functionality without API keys for development
- **Database**: SQLite with automatic schema setup
- **Testing**: Comprehensive test suite with pytest

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ (for frontend development)
- Git

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd zerocrash-app
   ```

2. **Navigate to backend directory**
   ```bash
   cd backend
   ```

3. **Run the setup script**
   ```bash
   chmod +x scripts/*.sh
   ./scripts/setup_apis.sh
   ```

4. **Start the backend server**
   ```bash
   ./scripts/start_backend.sh
   ```

The backend will be available at:
- **API Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd ../  # Go to root directory
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Build CSS**
   ```bash
   npm run build:css
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

The frontend will be available at http://localhost:3000 (or your configured port).

## 📋 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search` | Search content across multiple sources |
| POST | `/api/suggest-article` | Generate SEO-optimized content suggestions |
| GET | `/api/taxonomy` | Get IT categories hierarchy |
| GET | `/api/connections/test` | Test external API connections |
| GET | `/health` | Health check and system status |

### Search API Example

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "artificial intelligence",
    "sources": ["google_news", "youtube", "reddit"],
    "category": "ai-ml",
    "max_results": 20
  }'
```

### SEO Suggestion API Example

```bash
curl -X POST "http://localhost:8000/api/suggest-article" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Artificial intelligence is transforming the IT industry...",
    "target_keywords": ["AI", "machine learning", "technology"],
    "language": "it"
  }'
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# API Keys
GNEWS_API_KEY=your-gnews-api-key
YOUTUBE_API_KEY=your-youtube-api-key  
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret

# Application Settings
MOCK_MODE=false
DEBUG=false
CACHE_TTL=3600
RATE_LIMIT_PER_MINUTE=60

# Database
DATABASE_URL=sqlite:///./zerocrash.db

# Server
HOST=0.0.0.0
PORT=8000
```

### API Setup Instructions

#### Google News (GNews.io)
1. Visit https://gnews.io/
2. Sign up for a free account
3. Get your API key from the dashboard
4. Add to `.env` as `GNEWS_API_KEY`

#### YouTube Data API v3
1. Go to Google Cloud Console
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create credentials (API key)
5. Add to `.env` as `YOUTUBE_API_KEY`

#### Reddit API
1. Visit https://www.reddit.com/prefs/apps
2. Create a new application (script type)
3. Note the client ID and secret
4. Add to `.env` as `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`

## 🧪 Testing

### Run Backend Tests
```bash
cd backend
./scripts/run_tests.sh
```

### Test Categories
- **Unit Tests**: API endpoints, data processing, validation
- **Integration Tests**: Complete workflows, database operations
- **Performance Tests**: Response times, load handling
- **Mock Tests**: Functionality without external APIs

### Test API Connections
```bash
curl http://localhost:8000/api/connections/test
```

## 🏗️ Architecture

### Backend Stack
- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database with automatic setup  
- **httpx**: Async HTTP client for API requests
- **Pydantic**: Data validation and serialization
- **Cachetools**: In-memory caching with TTL
- **pytest**: Comprehensive testing framework

### Frontend Stack
- **HTML5**: Semantic markup structure
- **Tailwind CSS**: Utility-first CSS framework
- **Vanilla JavaScript**: Modern ES6+ features
- **Responsive Design**: Mobile-first approach

### Data Flow
1. **Content Ingestion**: Multi-source API aggregation
2. **Processing**: Normalization and categorization
3. **Storage**: SQLite database with caching
4. **Analysis**: SEO optimization and recommendations
5. **Delivery**: RESTful API with rate limiting

## 📊 Features Deep Dive

### Content Aggregation
- **Google News**: Latest IT news and articles
- **YouTube**: Technical videos and tutorials
- **Reddit**: Community discussions and insights
- **Smart Filtering**: Category-based content filtering
- **Deduplication**: Intelligent duplicate detection

### SEO Intelligence
- **Title Optimization**: SEO-friendly title generation
- **Meta Descriptions**: Optimized meta descriptions
- **Content Structure**: Hierarchical outline suggestions
- **Keyword Analysis**: Competitive keyword research
- **Performance Scoring**: Content optimization scoring

### Caching Strategy
- **Memory Cache**: Fast in-memory TTL cache
- **Database Cache**: Persistent search result storage
- **API Rate Management**: Intelligent request caching
- **Cache Invalidation**: Smart cache refresh policies

## 🔒 Security Features

- **Rate Limiting**: Per-endpoint request limiting
- **Input Validation**: Comprehensive data validation
- **Error Handling**: Secure error responses
- **CORS Configuration**: Cross-origin request handling
- **API Key Management**: Secure credential handling

## 📈 Monitoring & Health

### Health Checks
- Database connectivity
- External API status
- Cache system status
- Overall system health

### Performance Monitoring
- Response time tracking
- API success rates
- Cache hit ratios
- System resource usage

## 🚀 Deployment

### Production Setup

1. **Update Environment**
   ```bash
   # Set production values
   MOCK_MODE=false
   DEBUG=false
   ENVIRONMENT=production
   ```

2. **Use Production Server**
   ```bash
   # Install production server
   pip install gunicorn
   
   # Start with Gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UnicornWorker
   ```

3. **Setup Reverse Proxy** (nginx example)
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY .env .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📚 API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Workflow
```bash
# Setup development environment
./scripts/setup_apis.sh

# Start development server
./scripts/start_backend.sh

# Run tests
./scripts/run_tests.sh

# Code formatting
black backend/
isort backend/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Troubleshooting

**Common Issues:**

1. **API Keys Not Working**
   - Verify keys in `.env` file
   - Check API quotas and limits
   - Test with `/api/connections/test`

2. **Database Issues**
   - Delete `zerocrash.db` and restart
   - Check file permissions
   - Verify SQLite installation

3. **Performance Issues**
   - Enable caching with Redis
   - Adjust `CACHE_TTL` setting
   - Monitor with `/health` endpoint

**Getting Help:**
- Check the logs for detailed error messages
- Use MOCK_MODE=true for testing without APIs
- Review the test suite for usage examples

### Performance Tips
- Use Redis for production caching
- Enable API key rotation
- Monitor rate limits
- Implement request batching
- Use CDN for static content

---

**Built with ❤️ for the IT community**

*ZeroCrash.app - Transforming how you discover and create IT content*