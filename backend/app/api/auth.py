from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class AuthService:
    """Authentication and authorization service with WebSocket support"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def verify_websocket_token(self, token: str) -> Optional[dict]:
        """Verify JWT token for WebSocket connection (returns None on failure)"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning(f"WebSocket token verification failed: {str(e)}")
            return None
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return pwd_context.verify(plain_password, hashed_password)


# Global auth service instance
auth_service = AuthService()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user from JWT token"""
    try:
        payload = auth_service.verify_token(credentials.credentials)
        game_id: str = payload.get("sub")
        if game_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"game_id": game_id, "payload": payload}
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_websocket_user(websocket: WebSocket, token: str) -> Optional[dict]:
    """Get authenticated user for WebSocket connection"""
    try:
        payload = auth_service.verify_websocket_token(token)
        if payload:
            game_id: str = payload.get("sub")
            if game_id:
                return {"game_id": game_id, "payload": payload}
        return None
    except Exception as e:
        logger.error(f"WebSocket authentication error: {str(e)}")
        return None


def create_game_token(game_id: str, additional_claims: dict = None) -> str:
    """Create access token for a game"""
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    
    token_data = {"sub": game_id, "type": "game_access"}
    if additional_claims:
        token_data.update(additional_claims)
    
    access_token = auth_service.create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )
    return access_token


def create_websocket_token(game_id: str, session_id: str) -> str:
    """Create access token specifically for WebSocket connections"""
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    
    access_token = auth_service.create_access_token(
        data={
            "sub": game_id, 
            "type": "websocket_access",
            "session_id": session_id
        },
        expires_delta=access_token_expires
    )
    return access_token


# Optional authentication dependency (for public endpoints that can benefit from auth)
def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials)
    except HTTPException:
        return None