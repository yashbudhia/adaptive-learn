from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

Base = declarative_base()


class GameActionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# SQLAlchemy Models
class Game(Base):
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    vocabulary = Column(JSON)  # Game-specific vocabulary and mechanics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    contexts = relationship("GameContext", back_populates="game")
    actions = relationship("BossAction", back_populates="game")


class GameContext(Base):
    __tablename__ = "game_contexts"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    context_hash = Column(String, index=True, nullable=False)  # Hash of the context for quick lookup
    player_context = Column(JSON, nullable=False)  # Player behavior data
    embedding_vector = Column(Text)  # Serialized embedding vector
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="contexts")
    actions = relationship("BossAction", back_populates="context")


class BossAction(Base):
    __tablename__ = "boss_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    context_id = Column(Integer, ForeignKey("game_contexts.id"), nullable=False)
    action_data = Column(JSON, nullable=False)  # The boss action response
    outcome = Column(String, nullable=True)  # SUCCESS, FAILURE, PARTIAL
    effectiveness_score = Column(Float, default=0.0)  # 0.0 to 1.0
    damage_dealt = Column(Float, default=0.0)
    player_hit = Column(Boolean, default=False)
    execution_time = Column(Float)  # Time taken to execute action
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="actions")
    context = relationship("GameContext", back_populates="actions")


class JigsawStackPrompt(Base):
    __tablename__ = "jigsawstack_prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    prompt_engine_id = Column(String, nullable=False)  # JigsawStack prompt ID
    prompt_name = Column(String, nullable=False)
    prompt_template = Column(Text, nullable=False)
    optimized_prompt = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Pydantic Models for API
class PlayerContextData(BaseModel):
    frequent_actions: List[str] = Field(..., description="List of frequent player actions")
    dodge_frequency: float = Field(..., ge=0.0, le=1.0, description="Frequency of dodging (0.0 to 1.0)")
    attack_patterns: List[str] = Field(..., description="Common attack patterns")
    movement_style: str = Field(..., description="Player movement style")
    reaction_time: float = Field(..., description="Average reaction time in seconds")
    health_percentage: float = Field(..., ge=0.0, le=1.0, description="Current health percentage")
    difficulty_preference: str = Field(..., description="Player's difficulty preference")
    session_duration: float = Field(..., description="Current session duration in minutes")
    recent_deaths: int = Field(..., ge=0, description="Number of recent deaths")
    equipment_level: int = Field(..., ge=1, description="Player equipment level")
    additional_context: Optional[Dict[str, Any]] = Field(default={}, description="Additional game-specific context")


class BossActionRequest(BaseModel):
    game_id: str = Field(..., description="Unique identifier for the game")
    player_context: PlayerContextData = Field(..., description="Current player context")
    boss_health_percentage: float = Field(..., ge=0.0, le=1.0, description="Boss current health percentage")
    battle_phase: str = Field(..., description="Current battle phase")
    environment_factors: Optional[Dict[str, Any]] = Field(default={}, description="Environmental factors")


class BossActionResponse(BaseModel):
    boss_action: str = Field(..., description="The boss action to execute")
    action_type: str = Field(..., description="Type of action (attack, defend, special, etc.)")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Action intensity (0.0 to 1.0)")
    target_area: Optional[str] = Field(None, description="Target area for the action")
    duration: Optional[float] = Field(None, description="Action duration in seconds")
    cooldown: Optional[float] = Field(None, description="Cooldown before next action")
    animation_id: Optional[str] = Field(None, description="Animation identifier")
    sound_effects: Optional[List[str]] = Field(default=[], description="Sound effects to play")
    visual_effects: Optional[List[str]] = Field(default=[], description="Visual effects to apply")
    damage_multiplier: Optional[float] = Field(1.0, description="Damage multiplier for this action")
    success_probability: Optional[float] = Field(None, description="Estimated success probability")
    reasoning: Optional[str] = Field(None, description="AI reasoning for this action choice")


class ActionOutcomeData(BaseModel):
    action_id: int = Field(..., description="ID of the executed action")
    outcome: GameActionOutcome = Field(..., description="Outcome of the action")
    effectiveness_score: float = Field(..., ge=0.0, le=1.0, description="Effectiveness score (0.0 to 1.0)")
    damage_dealt: float = Field(..., ge=0.0, description="Actual damage dealt")
    player_hit: bool = Field(..., description="Whether the player was hit")
    execution_time: float = Field(..., description="Time taken to execute the action")
    player_reaction: Optional[str] = Field(None, description="Player's reaction to the action")
    additional_metrics: Optional[Dict[str, Any]] = Field(default={}, description="Additional outcome metrics")


class GameRegistrationRequest(BaseModel):
    game_id: str = Field(..., description="Unique identifier for the game")
    name: str = Field(..., description="Game name")
    description: Optional[str] = Field(None, description="Game description")
    vocabulary: Dict[str, Any] = Field(..., description="Game-specific vocabulary and mechanics")


class GameRegistrationResponse(BaseModel):
    success: bool
    message: str
    game_id: str
    prompt_engine_id: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]