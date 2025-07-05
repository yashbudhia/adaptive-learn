import os
from typing import Optional
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    """Application settings with secure credential management"""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Database Configuration
    database_url: str = "postgresql://adaptive_user:adaptive_password@localhost:5432/adaptive_boss_db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your_secret_key_generate_a_strong_one"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Encryption key for sensitive data
    encryption_key: Optional[str] = None
    
    # AI Service Configuration
    openai_api_key: str = "your_openai_api_key_here"
    jigsawstack_api_key: str = "your_jigsawstack_api_key_here"
    
    # FAISS Configuration
    faiss_index_path: str = "./data/faiss_indexes/"
    embedding_dimension: int = 1536  # OpenAI ada-002 dimension
    
    # WebSocket Configuration
    websocket_heartbeat_interval: int = 30  # seconds
    websocket_timeout: int = 300  # 5 minutes
    max_websocket_connections: int = 1000
    
    # Real-time Configuration
    realtime_action_timeout: int = 10  # seconds
    realtime_batch_size: int = 10
    realtime_update_interval: float = 0.1  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Generate encryption key if not provided
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
    
    @property
    def fernet(self) -> Fernet:
        """Get Fernet encryption instance"""
        return Fernet(self.encryption_key.encode())
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential"""
        return self.fernet.encrypt(credential.encode()).decode()
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential"""
        return self.fernet.decrypt(encrypted_credential.encode()).decode()


# Global settings instance
settings = Settings()