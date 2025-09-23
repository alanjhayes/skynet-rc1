import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
from typing import List, Union

class LightweightEmbeddingService:
    """Lightweight embedding service using TF-IDF instead of heavy ML models"""
    
    def __init__(self, max_features: int = 5000):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True,
            strip_accents='unicode'
        )
        self.is_fitted = False
        self.model_path = "/app/data/tfidf_model.pkl"
        
        # Try to load existing model
        self.load_model()
    
    def fit_and_transform(self, texts: List[str]) -> np.ndarray:
        """Fit the vectorizer and transform texts to embeddings"""
        if not texts:
            return np.array([])
        
        # Clean texts
        clean_texts = [self._clean_text(text) for text in texts if text.strip()]
        
        if not clean_texts:
            return np.array([])
        
        # Fit and transform
        embeddings = self.vectorizer.fit_transform(clean_texts)
        self.is_fitted = True
        
        # Save model
        self.save_model()
        
        return embeddings.toarray()
    
    def transform(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Transform texts to embeddings using fitted vectorizer"""
        if isinstance(texts, str):
            texts = [texts]
        
        if not self.is_fitted:
            # If not fitted, fit on the input texts
            return self.fit_and_transform(texts)
        
        # Clean texts
        clean_texts = [self._clean_text(text) for text in texts if text.strip()]
        
        if not clean_texts:
            return np.zeros((len(texts), self.vectorizer.max_features or 5000))
        
        embeddings = self.vectorizer.transform(clean_texts)
        return embeddings.toarray()
    
    def encode(self, text: str) -> List[float]:
        """Encode a single text to embedding vector (compatible with sentence-transformers API)"""
        embedding = self.transform([text])
        if embedding.size == 0:
            # Return zero vector if encoding fails
            return [0.0] * (self.vectorizer.max_features or 5000)
        return embedding[0].tolist()
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text"""
        if not text:
            return ""
        
        # Basic cleaning
        text = text.strip()
        text = ' '.join(text.split())  # Normalize whitespace
        
        return text
    
    def save_model(self):
        """Save the fitted vectorizer"""
        if self.is_fitted:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.vectorizer, f)
    
    def load_model(self):
        """Load a previously fitted vectorizer"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                self.is_fitted = True
                print("Loaded existing TF-IDF model")
            except Exception as e:
                print(f"Failed to load TF-IDF model: {e}")
                self.is_fitted = False
        else:
            self.is_fitted = False
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        if self.is_fitted:
            return len(self.vectorizer.get_feature_names_out())
        return self.vectorizer.max_features or 5000

# For compatibility with sentence-transformers API
class SentenceTransformer:
    """Drop-in replacement for sentence-transformers.SentenceTransformer"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.embedding_service = LightweightEmbeddingService()
        self.model_name = model_name
    
    def encode(self, sentences: Union[str, List[str]]) -> Union[np.ndarray, List[float]]:
        """Encode sentences to embeddings"""
        if isinstance(sentences, str):
            return np.array(self.embedding_service.encode(sentences))
        
        embeddings = []
        for sentence in sentences:
            embeddings.append(self.embedding_service.encode(sentence))
        
        return np.array(embeddings)