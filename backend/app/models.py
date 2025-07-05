from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

Base = declarative_base()

# Database Models
class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    vocabulary = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    contexts = relationship("GameContext", back_populates="game")
    actions = relationship("BossAction", back_populates="game")
    prompts = relationship("JigsawStackPrompt", back_populates="game")
    websocket_sessions = relationship("WebSocketSession", back_populates="game")


class GameContext(Base):
    __tablename__ = "game_contexts"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    context_hash = Column(String(64), index=True, nullable=False)
    player_context = Column(JSON, nullable=False)
    embedding_vector = Column(Text)  # Hex-encoded embedding
    usage_count = Column(Integer, default=1)
    avg_effectiveness = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="contexts")
    actions = relationship("BossAction", back_populates="context")
    
    # Indexes
    __table_args__ = (
        Index('idx_game_context_hash', 'game_id', 'context_hash'),
        Index('idx_context_effectiveness', 'avg_effectiveness'),
    )


class BossAction(Base):
    __tablename__ = "boss_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    context_id = Column(Integer, ForeignKey("game_contexts.id"), nullable=False)
    websocket_session_id = Column(Integer, ForeignKey("websocket_sessions.id"), nullable=True)
    action_data = Column(JSON, nullable=False)
    outcome = Column(String(20))  # success, failure, partial
    effectiveness_score = Column(Float)
    damage_dealt = Column(Float)
    player_hit = Column(Boolean)
    execution_time = Column(Float)
    response_time = Column(Float)  # Time to generate the action
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="actions")
    context = relationship("GameContext", back_populates="actions")
    websocket_session = relationship("WebSocketSession", back_populates="actions")
    
    # Indexes
    __table_args__ = (
        Index('idx_action_game_context', 'game_id', 'context_id'),
        Index('idx_action_effectiveness', 'effectiveness_score'),
        Index('idx_action_created', 'created_at'),
    )


class JigsawStackPrompt(Base):
    __tablename__ = "jigsawstack_prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    prompt_engine_id = Column(String(100), unique=True, nullable=False)
    prompt_name = Column(String(200), nullable=False)
    prompt_template = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="prompts")


class WebSocketSession(Base):
    __tablename__ = "websocket_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    client_info = Column(JSON)  # Client metadata
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now())
    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    disconnected_at = Column(DateTime(timezone=True))
    
    # Relationships
    game = relationship("Game", back_populates="websocket_sessions")
    actions = relationship("BossAction", back_populates="websocket_session")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_game_active', 'game_id', 'is_active'),
        Index('idx_session_heartbeat', 'last_heartbeat'),
    )


# Pydantic Models for API
class GameActionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class PlayerContextData(BaseModel):
    frequent_actions: List[str] = Field(..., description="Most frequent player actions")
    dodge_frequency: float = Field(..., ge=0.0, le=1.0, description="Frequency of dodge actions")
    attack_patterns: List[str] = Field(..., description="Common attack patterns")
    movement_style: str = Field(..., description="Player movement style")
    reaction_time: float = Field(..., gt=0.0, description="Average reaction time in seconds")
    health_percentage: float = Field(..., ge=0.0, le=1.0, description="Current health percentage")
    difficulty_preference: str = Field(..., description="Preferred difficulty level")
    session_duration: float = Field(..., ge=0.0, description="Current session duration in minutes")
    recent_deaths: int = Field(..., ge=0, description="Number of recent deaths")
    equipment_level: int = Field(..., ge=1, description="Equipment/power level")
    additional_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BossActionRequest(BaseModel):
    game_id: str = Field(..., description="Unique game identifier")
    player_context: PlayerContextData
    boss_health_percentage: float = Field(..., ge=0.0, le=1.0)
    battle_phase: str = Field(..., description="Current battle phase")
    environment_factors: Dict[str, Any] = Field(default_factory=dict)
    realtime: bool = Field(default=False, description="Request real-time WebSocket response")
    session_id: Optional[str] = Field(None, description="WebSocket session ID for real-time")


class BossActionResponse(BaseModel):
    boss_action: str = Field(..., description="Primary boss action to execute")
    action_type: str = Field(..., description="Type of action")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Action intensity")
    target_area: Optional[str] = Field(None, description="Target area for the action")
    duration: Optional[float] = Field(None, description="Action duration in seconds")
    cooldown: Optional[float] = Field(None, description="Cooldown before next action")
    animation_id: Optional[str] = Field(None, description="Animation identifier")
    sound_effects: List[str] = Field(default_factory=list)
    visual_effects: List[str] = Field(default_factory=list)
    damage_multiplier: Optional[float] = Field(1.0, description="Damage multiplier")
    success_probability: Optional[float] = Field(None, description="Estimated success probability")
    reasoning: Optional[str] = Field(None, description="AI reasoning for the action")
    response_time: Optional[float] = Field(None, description="Time taken to generate response")
    similar_contexts_used: int = Field(0, description="Number of similar contexts used")


class ActionOutcomeData(BaseModel):
    action_id: int = Field(..., description="Database ID of the action")
    outcome: GameActionOutcome = Field(..., description="Action outcome")
    effectiveness_score: float = Field(..., ge=0.0, le=1.0, description="Effectiveness score")
    damage_dealt: float = Field(..., ge=0.0, description="Damage dealt to player")
    player_hit: bool = Field(..., description="Whether player was hit")
    execution_time: float = Field(..., gt=0.0, description="Time to execute action")
    player_reaction: Optional[str] = Field(None, description="Player's reaction")
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)


class GameRegistrationRequest(BaseModel):
    game_id: str = Field(..., min_length=3, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    vocabulary: Dict[str, Any] = Field(..., description="Game-specific vocabulary and mechanics")


class GameRegistrationResponse(BaseModel):
    success: bool
    message: str
    game_id: str
    prompt_engine_id: Optional[str] = None
    access_token: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]
    websocket_connections: int = 0


# WebSocket Message Models
class WebSocketMessageType(str, Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    BOSS_ACTION_REQUEST = "boss_action_request"
    BOSS_ACTION_RESPONSE = "boss_action_response"
    ACTION_OUTCOME = "action_outcome"
    LEARNING_UPDATE = "learning_update"
    ERROR = "error"
    STATUS = "status"


class WebSocketMessage(BaseModel):
    type: WebSocketMessageType
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    game_id: Optional[str] = None


class WebSocketConnectData(BaseModel):
    game_id: str
    access_token: str
    client_info: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WebSocketBossActionRequest(BaseModel):
    player_context: PlayerContextData
    boss_health_percentage: float = Field(..., ge=0.0, le=1.0)
    battle_phase: str
    environment_factors: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None  # For tracking responses


class WebSocketActionOutcome(BaseModel):
    action_id: int
    outcome: GameActionOutcome
    effectiveness_score: float = Field(..., ge=0.0, le=1.0)
    damage_dealt: float = Field(..., ge=0.0)
    player_hit: bool
    execution_time: float = Field(..., gt=0.0)
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)


class LearningUpdateData(BaseModel):
    contexts_learned: int
    avg_effectiveness: float
    recent_improvements: List[str] = Field(default_factory=list)
    performance_trend: str  # "improving", "stable", "declining"


class RealtimeStats(BaseModel):
    active_sessions: int
    actions_per_minute: float
    avg_response_time: float
    learning_rate: float
    cache_hit_rate: float