"""
Test suite for ZeroCrash backend API
"""

import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app, SearchRequest, SEOSuggestionRequest

client = TestClient(app)

class TestSearchAPI:
    """Test search functionality"""
    
    def test_search_endpoint_mock_mode(self):
        """Test search endpoint in mock mode"""
        request_data = {
            "query": "machine learning",
            "sources": ["google_news", "youtube", "reddit"],
            "max_results": 10
        }
        
        response = client.post("/api/search", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "total_results" in data
        assert "results" in data
        assert data["query"] == "machine learning"
        assert isinstance(data["results"], list)
    
    def test_search_endpoint_validation(self):
        """Test search endpoint input validation"""
        # Empty query should fail
        response = client.post("/api/search", json={"query": ""})
        assert response.status_code == 422
        
        # Invalid source should still work (filtered out)
        request_data = {
            "query": "python",
            "sources": ["invalid_source"],
            "max_results": 5
        }
        response = client.post("/api/search", json=request_data)
        assert response.status_code == 200
    
    def test_search_endpoint_max_results(self):
        """Test search endpoint max results limit"""
        request_data = {
            "query": "artificial intelligence",
            "sources": ["google_news"],
            "max_results": 200  # Over limit
        }
        
        response = client.post("/api/search", json=request_data)
        assert response.status_code == 422  # Should fail validation

class TestSEOAPI:
    """Test SEO suggestion functionality"""
    
    def test_suggest_article_endpoint(self):
        """Test SEO suggestion endpoint"""
        request_data = {
            "content": "Questo è un articolo sull'intelligenza artificiale e machine learning. Parleremo di algoritmi avanzati e applicazioni pratiche nel settore IT italiano.",
            "target_keywords": ["intelligenza artificiale", "machine learning", "AI"],
            "language": "it",
            "content_type": "article"
        }
        
        response = client.post("/api/suggest-article", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "title_suggestions" in data
        assert "meta_descriptions" in data
        assert "content_outline" in data
        assert "keyword_analysis" in data
        assert "seo_score" in data
        assert "recommendations" in data
        
        # Check data types
        assert isinstance(data["title_suggestions"], list)
        assert isinstance(data["meta_descriptions"], list)
        assert isinstance(data["content_outline"], list)
        assert isinstance(data["keyword_analysis"], dict)
        assert isinstance(data["seo_score"], float)
        assert isinstance(data["recommendations"], list)
    
    def test_suggest_article_validation(self):
        """Test SEO suggestion input validation"""
        # Content too short
        response = client.post("/api/suggest-article", json={"content": "short"})
        assert response.status_code == 422

class TestTaxonomyAPI:
    """Test taxonomy functionality"""
    
    def test_taxonomy_endpoint(self):
        """Test taxonomy retrieval"""
        response = client.get("/api/taxonomy")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Check if we have IT categories
        category_names = [cat["name"] for cat in data]
        expected_categories = ["AI & Machine Learning", "Cybersecurity", "Cloud Computing"]
        
        for expected in expected_categories:
            assert any(expected in name for name in category_names)

class TestHealthAPI:
    """Test health and connection endpoints"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "cache_status" in data
        
        # Check services status
        services = data["services"]
        assert "database" in services
        assert "google_news" in services
        assert "youtube" in services
        assert "reddit" in services
    
    def test_connections_test_endpoint(self):
        """Test API connections test"""
        response = client.get("/api/connections/test")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3  # Should test at least 3 services
        
        for connection_test in data:
            assert "service" in connection_test
            assert "status" in connection_test
            assert "response_time_ms" in connection_test

class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_search_to_seo_workflow(self):
        """Test complete workflow from search to SEO suggestions"""
        # First, perform a search
        search_request = {
            "query": "cybersecurity trends 2025",
            "sources": ["google_news"],
            "max_results": 5
        }
        
        search_response = client.post("/api/search", json=search_request)
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        # Use search results for SEO suggestions
        if search_data["results"]:
            first_result = search_data["results"][0]
            seo_request = {
                "content": f"{first_result['title']} - {first_result['description']}",
                "target_keywords": ["cybersecurity", "security", "2025"],
                "language": "it"
            }
            
            seo_response = client.post("/api/suggest-article", json=seo_request)
            assert seo_response.status_code == 200
            seo_data = seo_response.json()
            
            # Verify SEO suggestions are generated
            assert len(seo_data["title_suggestions"]) > 0
            assert len(seo_data["meta_descriptions"]) > 0
            assert seo_data["seo_score"] > 0

# Mock API clients for testing
class TestMockClients:
    """Test mock API client functionality"""
    
    def test_google_news_mock_data(self):
        """Test Google News mock data generation"""
        from main import GoogleNewsClient
        
        client = GoogleNewsClient("mock-key")
        mock_data = client._get_mock_news_data("test query")
        
        assert isinstance(mock_data, list)
        assert len(mock_data) > 0
        
        for article in mock_data:
            assert "title" in article
            assert "description" in article
            assert "url" in article
            assert "publishedAt" in article
            assert "source" in article
    
    def test_youtube_mock_data(self):
        """Test YouTube mock data generation"""
        from main import YouTubeClient
        
        client = YouTubeClient("mock-key")
        mock_data = client._get_mock_youtube_data("test query")
        
        assert isinstance(mock_data, list)
        assert len(mock_data) > 0
        
        for video in mock_data:
            assert "id" in video
            assert "snippet" in video
            assert "statistics" in video
    
    def test_reddit_mock_data(self):
        """Test Reddit mock data generation"""
        from main import RedditClient
        
        client = RedditClient("mock-id", "mock-secret")
        mock_data = client._get_mock_reddit_data("test query")
        
        assert isinstance(mock_data, list)
        assert len(mock_data) > 0
        
        for post in mock_data:
            assert "data" in post
            post_data = post["data"]
            assert "title" in post_data
            assert "url" in post_data
            assert "author" in post_data

# Performance tests
class TestPerformance:
    """Performance and load tests"""
    
    def test_search_response_time(self):
        """Test search endpoint response time"""
        import time
        
        request_data = {
            "query": "performance test",
            "sources": ["google_news"],
            "max_results": 10
        }
        
        start_time = time.time()
        response = client.post("/api/search", json=request_data)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 5.0  # Should respond within 5 seconds
    
    def test_seo_response_time(self):
        """Test SEO endpoint response time"""
        import time
        
        request_data = {
            "content": "Test content for performance measurement. This is a longer text to simulate real usage scenarios with multiple keywords and technical terms related to IT and software development.",
            "target_keywords": ["performance", "test", "software"]
        }
        
        start_time = time.time()
        response = client.post("/api/suggest-article", json=request_data)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 3.0  # Should respond within 3 seconds

if __name__ == "__main__":
    pytest.main([__file__])