import os
from typing import Optional
from pydantic import BaseSettings
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    
    # JigsawStack Configuration
    jigsawstack_api_key: str
    
    # Database Configuration
    database_url: str
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # FAISS Configuration
    faiss_index_path: str = "./data/faiss_indexes/"
    embedding_dimension: int = 1536
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class SecurityManager:
    """Handles encryption/decryption of sensitive data"""
    
    def __init__(self, secret_key: str):
        # Generate a key from the secret key
        key = Fernet.generate_key()
        self.cipher_suite = Fernet(key)
        self._key = key
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def get_key(self) -> bytes:
        """Get the encryption key"""
        return self._key


# Global settings instance
settings = Settings()

# Global security manager
security_manager = SecurityManager(settings.secret_key)