"""
ZeroCrash.app - Complete FastAPI Backend
AI-powered platform for IT content aggregation and SEO optimization
"""

import os
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel, Field
import redis.asyncio as redis
from cachetools import TTLCache
import sqlite3
from pathlib import Path

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    sources: List[str] = Field(default=["google_news", "youtube", "reddit"])
    category: Optional[str] = Field(default=None)
    date_range: str = Field(default="week")
    popularity_threshold: str = Field(default="medium")
    max_results: int = Field(default=50, ge=1, le=100)

class SearchResult(BaseModel):
    id: str
    title: str
    description: str
    url: str
    source: str
    author: Optional[str] = None
    published_at: datetime
    engagement: Dict[str, Any]
    category: Optional[str] = None
    tags: List[str] = []
    seo_score: Optional[float] = None

class SEOSuggestionRequest(BaseModel):
    content: str = Field(..., min_length=10)
    target_keywords: List[str] = Field(default=[])
    language: str = Field(default="it")
    content_type: str = Field(default="article")

class SEOSuggestion(BaseModel):
    title_suggestions: List[str]
    meta_descriptions: List[str]
    content_outline: List[Dict[str, str]]
    keyword_analysis: Dict[str, Any]
    seo_score: float
    recommendations: List[str]

class TaxonomyItem(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    subcategories: List['TaxonomyItem'] = []
    count: int = 0

class ConnectionTest(BaseModel):
    service: str
    status: str
    response_time_ms: float
    error: Optional[str] = None

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]
    cache_status: str

# Configuration
class Config:
    # API Keys
    GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "your-gnews-api-key")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "your-youtube-api-key") 
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "your-reddit-client-id")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "your-reddit-client-secret")
    
    # Mock mode
    MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
    
    # Cache settings
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./zerocrash.db")

config = Config()

# Initialize cache
memory_cache = TTLCache(maxsize=1000, ttl=config.CACHE_TTL)

# Database setup
def init_db():
    """Initialize SQLite database"""
    db_path = Path("zerocrash.db")
    conn = sqlite3.connect(str(db_path))
    
    # Create tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS search_results (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            source TEXT NOT NULL,
            author TEXT,
            published_at TIMESTAMP,
            engagement_data TEXT,
            category TEXT,
            tags TEXT,
            seo_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS seo_suggestions (
            id TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            suggestions_data TEXT NOT NULL,
            language TEXT DEFAULT 'it',
            content_type TEXT DEFAULT 'article',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id TEXT,
            description TEXT,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_search_query ON search_results(query);
        CREATE INDEX IF NOT EXISTS idx_search_source ON search_results(source);
        CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories(parent_id);
    """)
    
    # Insert default IT taxonomy
    categories = [
        ("ai-ml", "AI & Machine Learning", None, "Intelligenza artificiale e machine learning", "AI,machine learning,deep learning,neural networks"),
        ("cybersecurity", "Cybersecurity", None, "Sicurezza informatica", "security,cybersecurity,hacking,privacy"),
        ("cloud-computing", "Cloud Computing", None, "Cloud e infrastrutture", "cloud,AWS,Azure,GCP,serverless"),
        ("web-development", "Web Development", None, "Sviluppo web", "web,HTML,CSS,JavaScript,React,Vue"),
        ("mobile-development", "Mobile Development", None, "Sviluppo mobile", "mobile,Android,iOS,React Native,Flutter"),
        ("data-science", "Data Science", None, "Data science e analytics", "data,analytics,big data,visualization"),
        ("devops", "DevOps", None, "DevOps e infrastructure", "devops,docker,kubernetes,CI/CD"),
        ("blockchain", "Blockchain", None, "Blockchain e cryptocurrency", "blockchain,crypto,bitcoin,smart contracts"),
        ("iot", "Internet of Things", None, "Internet delle cose", "IoT,sensors,embedded,Arduino")
    ]
    
    for cat_id, name, parent_id, desc, keywords in categories:
        conn.execute(
            "INSERT OR IGNORE INTO categories (id, name, parent_id, description, keywords) VALUES (?, ?, ?, ?, ?)",
            (cat_id, name, parent_id, desc, keywords)
        )
    
    conn.commit()
    conn.close()

# API Clients
class GoogleNewsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://gnews.io/api/v4"
    
    async def search(self, query: str, category: str = None, days: int = 7) -> List[Dict]:
        """Search Google News via GNews.io API"""
        if config.MOCK_MODE:
            return self._get_mock_news_data(query)
        
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "token": self.api_key,
            "lang": "it",
            "country": "it",
            "max": 20,
            "from": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        if category:
            params["category"] = category
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("articles", [])
        except Exception as e:
            logger.error(f"Google News API error: {e}")
            return []
    
    def _get_mock_news_data(self, query: str) -> List[Dict]:
        """Mock Google News data for testing"""
        return [
            {
                "title": f"Intelligenza Artificiale: Nuove Scoperte nel {query}",
                "description": "Le ultime innovazioni nel campo dell'AI stanno trasformando il settore tecnologico italiano.",
                "content": "Contenuto completo dell'articolo...",
                "url": "https://techcrunch.it/ai-news-2025",
                "image": "https://example.com/ai-image.jpg",
                "publishedAt": "2025-01-18T10:00:00Z",
                "source": {
                    "name": "TechCrunch Italia",
                    "url": "https://techcrunch.it"
                }
            },
            {
                "title": f"Sicurezza Informatica: Guida Completa {query}",
                "description": "Proteggere i sistemi aziendali dalle nuove minacce cyber del 2025.",
                "content": "Contenuto dettagliato sulla cybersecurity...",
                "url": "https://cybersecurity.it/guide-2025",
                "image": "https://example.com/security-image.jpg",
                "publishedAt": "2025-01-18T08:30:00Z",
                "source": {
                    "name": "CyberSecurity Italia",
                    "url": "https://cybersecurity.it"
                }
            }
        ]

class YouTubeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    async def search(self, query: str, max_results: int = 20) -> List[Dict]:
        """Search YouTube via YouTube Data API v3"""
        if config.MOCK_MODE:
            return self._get_mock_youtube_data(query)
        
        url = f"{self.base_url}/search"
        params = {
            "part": "snippet",
            "q": query,
            "key": self.api_key,
            "type": "video",
            "maxResults": max_results,
            "relevanceLanguage": "it",
            "publishedAfter": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order": "relevance"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # Get additional video statistics
                video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
                stats = await self._get_video_statistics(video_ids)
                
                # Merge data
                for item in data.get("items", []):
                    video_id = item["id"]["videoId"]
                    item["statistics"] = stats.get(video_id, {})
                
                return data.get("items", [])
        except Exception as e:
            logger.error(f"YouTube API error: {e}")
            return []
    
    async def _get_video_statistics(self, video_ids: List[str]) -> Dict:
        """Get video statistics for given video IDs"""
        if not video_ids or config.MOCK_MODE:
            return {}
        
        url = f"{self.base_url}/videos"
        params = {
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                stats = {}
                for item in data.get("items", []):
                    stats[item["id"]] = item.get("statistics", {})
                
                return stats
        except Exception as e:
            logger.error(f"YouTube statistics API error: {e}")
            return {}
    
    def _get_mock_youtube_data(self, query: str) -> List[Dict]:
        """Mock YouTube data for testing"""
        return [
            {
                "id": {"videoId": "mock-video-1"},
                "snippet": {
                    "title": f"Machine Learning Spiegato Semplice: {query}",
                    "description": "In questo video esploriamo i concetti fondamentali del machine learning...",
                    "publishedAt": "2025-01-17T12:00:00Z",
                    "channelTitle": "AI Academy Italia",
                    "thumbnails": {
                        "default": {"url": "https://example.com/thumb1.jpg"}
                    }
                },
                "statistics": {
                    "viewCount": "45200",
                    "likeCount": "1240",
                    "commentCount": "89"
                }
            },
            {
                "id": {"videoId": "mock-video-2"},
                "snippet": {
                    "title": f"Sicurezza Informatica 2025: {query}",
                    "description": "Guida completa alla cybersecurity per le aziende italiane...",
                    "publishedAt": "2025-01-16T15:30:00Z",
                    "channelTitle": "CyberSec Italia",
                    "thumbnails": {
                        "default": {"url": "https://example.com/thumb2.jpg"}
                    }
                },
                "statistics": {
                    "viewCount": "28900",
                    "likeCount": "892",
                    "commentCount": "156"
                }
            }
        ]

class RedditClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://oauth.reddit.com"
        self.access_token = None
    
    async def search(self, query: str, subreddits: List[str] = None) -> List[Dict]:
        """Search Reddit posts"""
        if config.MOCK_MODE:
            return self._get_mock_reddit_data(query)
        
        if not self.access_token:
            await self._authenticate()
        
        if not subreddits:
            subreddits = ["programming", "MachineLearning", "cybersecurity", "webdev", "datascience"]
        
        all_posts = []
        for subreddit in subreddits:
            posts = await self._search_subreddit(query, subreddit)
            all_posts.extend(posts)
        
        return all_posts[:20]  # Limit results
    
    async def _authenticate(self):
        """Authenticate with Reddit API"""
        url = "https://www.reddit.com/api/v1/access_token"
        auth = httpx.BasicAuth(self.client_id, self.client_secret)
        data = {
            "grant_type": "client_credentials"
        }
        headers = {
            "User-Agent": "ZeroCrash/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, auth=auth, headers=headers, timeout=10.0)
                response.raise_for_status()
                token_data = response.json()
                self.access_token = token_data["access_token"]
        except Exception as e:
            logger.error(f"Reddit authentication error: {e}")
    
    async def _search_subreddit(self, query: str, subreddit: str) -> List[Dict]:
        """Search specific subreddit"""
        url = f"{self.base_url}/r/{subreddit}/search"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "ZeroCrash/1.0"
        }
        params = {
            "q": query,
            "sort": "relevance",
            "restrict_sr": "true",
            "limit": 10,
            "t": "week"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data.get("data", {}).get("children", [])
        except Exception as e:
            logger.error(f"Reddit search error: {e}")
            return []
    
    def _get_mock_reddit_data(self, query: str) -> List[Dict]:
        """Mock Reddit data for testing"""
        return [
            {
                "data": {
                    "title": f"[D] Quali sono le migliori librerie per {query}?",
                    "selftext": "Sto iniziando il mio percorso nel ML e vorrei sapere quali librerie Python consigliate...",
                    "url": "https://reddit.com/r/MachineLearning/mock-post-1",
                    "author": "AIResearcher_IT",
                    "subreddit": "MachineLearning",
                    "created_utc": 1705564800,
                    "score": 127,
                    "num_comments": 43,
                    "upvote_ratio": 0.95
                }
            },
            {
                "data": {
                    "title": f"Best practices per {query} in Python",
                    "selftext": "Condivido alcuni tips utili per ottimizzare le performance...",
                    "url": "https://reddit.com/r/programming/mock-post-2",
                    "author": "DevExpert_IT",
                    "subreddit": "programming",
                    "created_utc": 1705478400,
                    "score": 89,
                    "num_comments": 21,
                    "upvote_ratio": 0.91
                }
            }
        ]

# SEO Service
class SEOService:
    def __init__(self):
        self.italian_keywords = {
            "ai": ["intelligenza artificiale", "AI", "machine learning", "deep learning", "reti neurali"],
            "security": ["sicurezza informatica", "cybersecurity", "hacking", "privacy", "protezione dati"],
            "web": ["sviluppo web", "HTML", "CSS", "JavaScript", "React", "Vue"],
            "mobile": ["app mobile", "Android", "iOS", "React Native", "Flutter"],
            "cloud": ["cloud computing", "AWS", "Azure", "Google Cloud", "serverless"],
            "data": ["data science", "big data", "analytics", "visualizzazione dati"]
        }
    
    async def generate_suggestions(self, content: str, target_keywords: List[str] = None) -> SEOSuggestion:
        """Generate SEO suggestions for content"""
        if config.MOCK_MODE:
            return self._get_mock_seo_suggestions(content)
        
        # Analyze content
        content_lower = content.lower()
        detected_categories = []
        
        for category, keywords in self.italian_keywords.items():
            if any(keyword.lower() in content_lower for keyword in keywords):
                detected_categories.append(category)
        
        # Generate title suggestions
        titles = await self._generate_titles(content, target_keywords, detected_categories)
        
        # Generate meta descriptions
        meta_descriptions = await self._generate_meta_descriptions(content, target_keywords)
        
        # Generate content outline
        outline = await self._generate_content_outline(content, detected_categories)
        
        # Keyword analysis
        keyword_analysis = await self._analyze_keywords(content, target_keywords, detected_categories)
        
        # Calculate SEO score
        seo_score = self._calculate_seo_score(content, titles, meta_descriptions)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(content, detected_categories, seo_score)
        
        return SEOSuggestion(
            title_suggestions=titles,
            meta_descriptions=meta_descriptions,
            content_outline=outline,
            keyword_analysis=keyword_analysis,
            seo_score=seo_score,
            recommendations=recommendations
        )
    
    async def _generate_titles(self, content: str, keywords: List[str], categories: List[str]) -> List[str]:
        """Generate SEO-optimized titles"""
        base_titles = [
            "Guida Completa 2025",
            "Tutto quello che devi sapere",
            "Best Practices e Consigli",
            "Tendenze e Innovazioni 2025",
            "Strategie Vincenti per",
        ]
        
        category_terms = {
            "ai": "Intelligenza Artificiale",
            "security": "Sicurezza Informatica",
            "web": "Sviluppo Web",
            "mobile": "Sviluppo Mobile",
            "cloud": "Cloud Computing",
            "data": "Data Science"
        }
        
        titles = []
        for category in categories[:2]:  # Limit to 2 categories
            term = category_terms.get(category, "Tecnologia")
            for base in base_titles[:3]:  # Limit base titles
                titles.append(f"{term}: {base}")
        
        # Add keyword-based titles
        if keywords:
            for keyword in keywords[:2]:
                titles.append(f"{keyword.title()}: Guida Definitiva 2025")
                titles.append(f"Come funziona {keyword} - Tutorial Completo")
        
        return titles[:5]  # Return top 5 titles
    
    async def _generate_meta_descriptions(self, content: str, keywords: List[str]) -> List[str]:
        """Generate SEO-optimized meta descriptions"""
        descriptions = [
            f"Scopri tutto su {', '.join(keywords[:2])} con questa guida completa. Tips, best practices e esempi pratici per il 2025.",
            f"Guida definitiva su {', '.join(keywords[:2])}. Strategie, tools e consigli da esperti per migliorare le tue competenze IT.",
            f"Approfondimento completo su {', '.join(keywords[:2])}. Dalle basi alle tecniche avanzate, tutto quello che devi sapere."
        ]
        
        return descriptions[:3]
    
    async def _generate_content_outline(self, content: str, categories: List[str]) -> List[Dict[str, str]]:
        """Generate content outline structure"""
        outline = [
            {"level": "H1", "title": "Introduzione", "keywords": "introduzione, panoramica"},
            {"level": "H2", "title": "Cos'è e Come Funziona", "keywords": "definizione, funzionamento"},
            {"level": "H2", "title": "Vantaggi e Benefici", "keywords": "vantaggi, benefici, pro"},
            {"level": "H2", "title": "Best Practices", "keywords": "best practices, consigli, tips"},
            {"level": "H2", "title": "Tools e Strumenti", "keywords": "strumenti, software, tools"},
            {"level": "H2", "title": "Esempi Pratici", "keywords": "esempi, casi studio, pratica"},
            {"level": "H2", "title": "Tendenze Future", "keywords": "futuro, tendenze, previsioni"},
            {"level": "H2", "title": "Conclusioni", "keywords": "conclusioni, riassunto"}
        ]
        
        return outline[:6]  # Return 6 sections
    
    async def _analyze_keywords(self, content: str, keywords: List[str], categories: List[str]) -> Dict[str, Any]:
        """Analyze keywords and competition"""
        analysis = {
            "primary_keywords": [],
            "secondary_keywords": [],
            "long_tail_keywords": [],
            "keyword_density": {},
            "competition_analysis": {}
        }
        
        # Mock keyword data
        for category in categories:
            if category in self.italian_keywords:
                category_keywords = self.italian_keywords[category]
                analysis["primary_keywords"].extend(category_keywords[:2])
                analysis["secondary_keywords"].extend(category_keywords[2:4])
        
        # Generate long-tail keywords
        for kw in keywords[:3]:
            analysis["long_tail_keywords"].extend([
                f"come funziona {kw}",
                f"{kw} esempi pratici",
                f"guida {kw} 2025",
                f"migliori {kw} tools"
            ])
        
        # Mock keyword metrics
        for kw in analysis["primary_keywords"]:
            analysis["keyword_density"][kw] = {
                "volume": 15000 + hash(kw) % 10000,
                "difficulty": 45 + hash(kw) % 40,
                "cpc": 1.50 + (hash(kw) % 200) / 100,
                "trend": "↗ +25%"
            }
        
        return analysis
    
    def _calculate_seo_score(self, content: str, titles: List[str], descriptions: List[str]) -> float:
        """Calculate overall SEO score"""
        score = 0.0
        
        # Content length score
        content_length = len(content)
        if content_length > 1500:
            score += 25
        elif content_length > 800:
            score += 15
        else:
            score += 5
        
        # Title optimization score
        if titles:
            avg_title_length = sum(len(title) for title in titles) / len(titles)
            if 50 <= avg_title_length <= 60:
                score += 25
            elif 45 <= avg_title_length <= 65:
                score += 15
            else:
                score += 5
        
        # Meta description score
        if descriptions:
            avg_desc_length = sum(len(desc) for desc in descriptions) / len(descriptions)
            if 150 <= avg_desc_length <= 160:
                score += 25
            elif 140 <= avg_desc_length <= 165:
                score += 15
            else:
                score += 5
        
        # Structure score
        score += 25  # Base structure score
        
        return min(score, 100.0)
    
    def _generate_recommendations(self, content: str, categories: List[str], score: float) -> List[str]:
        """Generate SEO recommendations"""
        recommendations = []
        
        if score < 70:
            recommendations.extend([
                "Ottimizza la lunghezza del contenuto (min 1200 parole)",
                "Migliora la struttura con più sottotitoli H2/H3",
                "Aumenta la keyword density per i termini principali"
            ])
        
        if len(content) < 1200:
            recommendations.append("Espandi il contenuto con più dettagli e esempi")
        
        recommendations.extend([
            "Aggiungi link interni ad altri articoli correlati",
            "Includi immagini ottimizzate con alt text",
            "Crea una call-to-action chiara",
            "Ottimizza per mobile e velocità di caricamento"
        ])
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _get_mock_seo_suggestions(self, content: str) -> SEOSuggestion:
        """Mock SEO suggestions for testing"""
        return SEOSuggestion(
            title_suggestions=[
                "Intelligenza Artificiale 2025: Guida Completa alle Nuove Tendenze IT",
                "AI e Machine Learning: Le Tecnologie che Rivoluzioneranno il 2025",
                "Come l'AI sta Trasformando il Settore IT Italiano - Guida 2025"
            ],
            meta_descriptions=[
                "Scopri le ultime tendenze dell'intelligenza artificiale per il 2025. Guida completa su AI generativa, machine learning e tecnologie emergenti per il settore IT italiano.",
                "Esplora il futuro dell'AI nel 2025: dalle applicazioni business alle innovazioni tecnologiche. Tutto quello che devi sapere sull'intelligenza artificiale moderna."
            ],
            content_outline=[
                {"level": "H1", "title": "Intelligenza Artificiale 2025: La Rivoluzione Tecnologica", "keywords": "intelligenza artificiale, AI 2025"},
                {"level": "H2", "title": "Cos'è l'Intelligenza Artificiale Generativa", "keywords": "AI generativa, definizione"},
                {"level": "H3", "title": "ChatGPT e Large Language Models", "keywords": "ChatGPT, LLM"},
                {"level": "H2", "title": "Applicazioni AI nel Business Italiano", "keywords": "AI business, aziende italiane"},
                {"level": "H2", "title": "Tendenze Future e Previsioni 2025", "keywords": "futuro AI, previsioni"}
            ],
            keyword_analysis={
                "primary_keywords": ["intelligenza artificiale", "AI", "machine learning"],
                "secondary_keywords": ["AI generativa", "deep learning", "automazione"],
                "long_tail_keywords": ["come funziona intelligenza artificiale", "AI per aziende italiane", "migliori tools AI 2025"],
                "keyword_density": {
                    "intelligenza artificiale": {"volume": 22000, "difficulty": 65, "cpc": 2.30, "trend": "↗ +15%"},
                    "AI generativa": {"volume": 8900, "difficulty": 35, "cpc": 1.85, "trend": "↗ +45%"}
                }
            },
            seo_score=85.0,
            recommendations=[
                "Ottimizza i title tag per una lunghezza di 50-60 caratteri",
                "Aggiungi più link interni ad articoli correlati",
                "Includi immagini con alt text ottimizzato",
                "Migliora la struttura con più sottosezioni H3",
                "Crea una meta description accattivante di 155-160 caratteri"
            ]
        )

# Rate limiting
rate_limit_cache = TTLCache(maxsize=10000, ttl=60)

def rate_limit_key(request):
    """Generate rate limiting key from request"""
    return f"rate_limit:{request.client.host}"

async def check_rate_limit(request):
    """Check if rate limit exceeded"""
    key = rate_limit_key(request)
    current_requests = rate_limit_cache.get(key, 0)
    
    if current_requests >= config.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    rate_limit_cache[key] = current_requests + 1

# Initialize services
google_news_client = GoogleNewsClient(config.GNEWS_API_KEY)
youtube_client = YouTubeClient(config.YOUTUBE_API_KEY)
reddit_client = RedditClient(config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET)
seo_service = SEOService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting ZeroCrash backend...")
    init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ZeroCrash backend...")

# Create FastAPI app
app = FastAPI(
    title="ZeroCrash API",
    description="AI-powered IT content aggregation and SEO optimization platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def normalize_search_results(results: List[Dict], source: str) -> List[SearchResult]:
    """Normalize search results from different sources"""
    normalized = []
    
    for result in results:
        try:
            if source == "google_news":
                normalized.append(SearchResult(
                    id=hashlib.md5(result["url"].encode()).hexdigest(),
                    title=result["title"],
                    description=result["description"],
                    url=result["url"],
                    source="Google News",
                    author=result.get("source", {}).get("name"),
                    published_at=datetime.fromisoformat(result["publishedAt"].replace("Z", "+00:00")),
                    engagement={"views": 0, "shares": 0},
                    category=None,
                    tags=[]
                ))
            
            elif source == "youtube":
                stats = result.get("statistics", {})
                normalized.append(SearchResult(
                    id=result["id"]["videoId"],
                    title=result["snippet"]["title"],
                    description=result["snippet"]["description"],
                    url=f"https://youtube.com/watch?v={result['id']['videoId']}",
                    source="YouTube",
                    author=result["snippet"]["channelTitle"],
                    published_at=datetime.fromisoformat(result["snippet"]["publishedAt"].replace("Z", "+00:00")),
                    engagement={
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0))
                    },
                    category=None,
                    tags=[]
                ))
            
            elif source == "reddit":
                data = result["data"]
                normalized.append(SearchResult(
                    id=hashlib.md5(data["url"].encode()).hexdigest(),
                    title=data["title"],
                    description=data["selftext"][:200] + "..." if len(data["selftext"]) > 200 else data["selftext"],
                    url=f"https://reddit.com{data.get('permalink', '')}",
                    source="Reddit",
                    author=data["author"],
                    published_at=datetime.fromtimestamp(data["created_utc"]),
                    engagement={
                        "score": data["score"],
                        "upvote_ratio": data.get("upvote_ratio", 0),
                        "comments": data["num_comments"]
                    },
                    category=data["subreddit"],
                    tags=[]
                ))
                
        except Exception as e:
            logger.error(f"Error normalizing {source} result: {e}")
            continue
    
    return normalized

def save_search_results(query: str, results: List[SearchResult]):
    """Save search results to database"""
    try:
        conn = sqlite3.connect("zerocrash.db")
        for result in results:
            conn.execute("""
                INSERT OR REPLACE INTO search_results 
                (id, query, title, description, url, source, author, published_at, engagement_data, category, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.id,
                query,
                result.title,
                result.description,
                result.url,
                result.source,
                result.author,
                result.published_at,
                str(result.engagement),
                result.category,
                ",".join(result.tags),
                datetime.now()
            ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving search results: {e}")

async def get_cached_result(cache_key: str):
    """Get result from cache"""
    return memory_cache.get(cache_key)

def set_cached_result(cache_key: str, result: Any):
    """Set result in cache"""
    memory_cache[cache_key] = result

# API Endpoints

@app.post("/api/search", response_model=Dict[str, Any])
async def search_content(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Search for IT content across multiple sources
    """
    # Generate cache key
    cache_key = f"search:{hash(str(request.dict()))}"
    
    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        return cached_result
    
    all_results = []
    
    # Search Google News
    if "google_news" in request.sources:
        try:
            news_results = await google_news_client.search(
                query=request.query,
                category=request.category,
                days=7 if request.date_range == "week" else 30
            )
            normalized_news = normalize_search_results(news_results, "google_news")
            all_results.extend(normalized_news)
        except Exception as e:
            logger.error(f"Google News search error: {e}")
    
    # Search YouTube
    if "youtube" in request.sources:
        try:
            youtube_results = await youtube_client.search(
                query=request.query,
                max_results=min(request.max_results // len(request.sources), 20)
            )
            normalized_youtube = normalize_search_results(youtube_results, "youtube")
            all_results.extend(normalized_youtube)
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
    
    # Search Reddit
    if "reddit" in request.sources:
        try:
            reddit_results = await reddit_client.search(query=request.query)
            normalized_reddit = normalize_search_results(reddit_results, "reddit")
            all_results.extend(normalized_reddit)
        except Exception as e:
            logger.error(f"Reddit search error: {e}")
    
    # Sort by relevance and date
    all_results.sort(key=lambda x: x.published_at, reverse=True)
    
    # Limit results
    final_results = all_results[:request.max_results]
    
    # Prepare response
    response = {
        "query": request.query,
        "total_results": len(final_results),
        "sources": request.sources,
        "results": [result.dict() for result in final_results],
        "metadata": {
            "search_time": datetime.now().isoformat(),
            "cache_ttl": config.CACHE_TTL
        }
    }
    
    # Cache result
    set_cached_result(cache_key, response)
    
    # Save results in background
    background_tasks.add_task(save_search_results, request.query, final_results)
    
    return response

@app.post("/api/suggest-article", response_model=SEOSuggestion)
async def suggest_article_content(request: SEOSuggestionRequest):
    """
    Generate SEO-optimized article suggestions based on content
    """
    # Generate cache key based on content hash
    content_hash = hashlib.md5(request.content.encode()).hexdigest()
    cache_key = f"seo_suggestions:{content_hash}"
    
    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        return cached_result
    
    try:
        # Generate SEO suggestions
        suggestions = await seo_service.generate_suggestions(
            content=request.content,
            target_keywords=request.target_keywords
        )
        
        # Cache result
        set_cached_result(cache_key, suggestions.dict())
        
        # Save to database
        try:
            conn = sqlite3.connect("zerocrash.db")
            conn.execute("""
                INSERT OR REPLACE INTO seo_suggestions 
                (id, content_hash, suggestions_data, language, content_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"seo_{content_hash}",
                content_hash,
                str(suggestions.dict()),
                request.language,
                request.content_type,
                datetime.now()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving SEO suggestions: {e}")
        
        return suggestions
        
    except Exception as e:
        logger.error(f"SEO suggestion generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating SEO suggestions"
        )

@app.get("/api/taxonomy", response_model=List[TaxonomyItem])
async def get_it_taxonomy():
    """
    Get IT categories taxonomy with hierarchical structure
    """
    cache_key = "taxonomy"
    
    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        return cached_result
    
    try:
        conn = sqlite3.connect("zerocrash.db")
        cursor = conn.execute("""
            SELECT id, name, parent_id, description, 
                   (SELECT COUNT(*) FROM search_results WHERE category = c.name OR tags LIKE '%' || c.name || '%') as count
            FROM categories c
            ORDER BY name
        """)
        
        categories = []
        category_map = {}
        
        for row in cursor.fetchall():
            category = TaxonomyItem(
                id=row[0],
                name=row[1],
                parent_id=row[2],
                count=row[4] or 0
            )
            categories.append(category)
            category_map[category.id] = category
        
        # Build hierarchical structure
        root_categories = []
        for category in categories:
            if category.parent_id is None:
                root_categories.append(category)
            else:
                parent = category_map.get(category.parent_id)
                if parent:
                    parent.subcategories.append(category)
        
        conn.close()
        
        # Cache result
        result = [cat.dict() for cat in root_categories]
        set_cached_result(cache_key, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Taxonomy retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving taxonomy"
        )

@app.get("/api/connections/test", response_model=List[ConnectionTest])
async def test_api_connections():
    """
    Test connections to external APIs
    """
    tests = []
    
    # Test Google News
    start_time = datetime.now()
    try:
        if config.MOCK_MODE:
            status_result = "success"
            error = None
        else:
            # Make a simple test request
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{google_news_client.base_url}/search",
                    params={"q": "test", "token": config.GNEWS_API_KEY, "max": 1},
                    timeout=5.0
                )
                status_result = "success" if response.status_code == 200 else "error"
                error = f"HTTP {response.status_code}" if response.status_code != 200 else None
    except Exception as e:
        status_result = "error"
        error = str(e)
    
    response_time = (datetime.now() - start_time).total_seconds() * 1000
    tests.append(ConnectionTest(
        service="Google News (GNews.io)",
        status=status_result,
        response_time_ms=response_time,
        error=error
    ))
    
    # Test YouTube
    start_time = datetime.now()
    try:
        if config.MOCK_MODE:
            status_result = "success"
            error = None
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{youtube_client.base_url}/search",
                    params={"part": "snippet", "q": "test", "key": config.YOUTUBE_API_KEY, "maxResults": 1},
                    timeout=5.0
                )
                status_result = "success" if response.status_code == 200 else "error"
                error = f"HTTP {response.status_code}" if response.status_code != 200 else None
    except Exception as e:
        status_result = "error"
        error = str(e)
    
    response_time = (datetime.now() - start_time).total_seconds() * 1000
    tests.append(ConnectionTest(
        service="YouTube Data API v3",
        status=status_result,
        response_time_ms=response_time,
        error=error
    ))
    
    # Test Reddit
    start_time = datetime.now()
    try:
        if config.MOCK_MODE:
            status_result = "success"
            error = None
        else:
            # Test Reddit authentication
            url = "https://www.reddit.com/api/v1/access_token"
            auth = httpx.BasicAuth(config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data={"grant_type": "client_credentials"},
                    auth=auth,
                    headers={"User-Agent": "ZeroCrash/1.0"},
                    timeout=5.0
                )
                status_result = "success" if response.status_code == 200 else "error"
                error = f"HTTP {response.status_code}" if response.status_code != 200 else None
    except Exception as e:
        status_result = "error"
        error = str(e)
    
    response_time = (datetime.now() - start_time).total_seconds() * 1000
    tests.append(ConnectionTest(
        service="Reddit API",
        status=status_result,
        response_time_ms=response_time,
        error=error
    ))
    
    return tests

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint
    """
    # Check database
    db_status = "healthy"
    try:
        conn = sqlite3.connect("zerocrash.db")
        cursor = conn.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
    except Exception:
        db_status = "unhealthy"
    
    # Check cache
    cache_status = "healthy"
    try:
        memory_cache["health_check"] = "test"
        del memory_cache["health_check"]
    except Exception:
        cache_status = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if db_status == "healthy" and cache_status == "healthy" else "unhealthy"
    
    return HealthCheck(
        status=overall_status,
        timestamp=datetime.now(),
        services={
            "database": db_status,
            "google_news": "configured" if config.GNEWS_API_KEY != "your-gnews-api-key" else "not_configured",
            "youtube": "configured" if config.YOUTUBE_API_KEY != "your-youtube-api-key" else "not_configured",
            "reddit": "configured" if config.REDDIT_CLIENT_ID != "your-reddit-client-id" else "not_configured"
        },
        cache_status=cache_status
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)