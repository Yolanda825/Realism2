"""Base class for enhancement agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from app.agents.router import AgentPrompt


class AgentType(str, Enum):
    """Types of enhancement agents."""
    SKIN = "skin"
    LIGHTING = "lighting"
    TEXTURE = "texture"
    GEOMETRY = "geometry"
    COLOR = "color"
    EXPRESSION = "expression"


class ExpressionType(str, Enum):
    """Types of facial expressions."""
    NEUTRAL = "neutral"
    BIG_LAUGH = "big_laugh"
    CRYING = "crying"
    SURPRISE = "surprise"
    ANGER = "anger"
    OTHER = "other"


class ExpressionMode(str, Enum):
    """Mode for expression handling."""
    PRESERVE = "preserve"  # Keep expression as-is
    CORRECT = "correct"    # Fix unnatural expression


@dataclass
class EnhancementContext:
    """Context passed to enhancement agents."""
    image_base64: str
    scene_type: str
    ai_likelihood: float
    fake_signals: list  # List of FakeSignal objects
    iteration: int = 0
    previous_enhancements: list = field(default_factory=list)
    # Agent-specific prompt from router
    agent_prompt: Optional["AgentPrompt"] = None
    # Expression-related fields
    expression_type: str = "neutral"  # ExpressionType value
    expression_mode: str = "preserve"  # ExpressionMode value
    expression_issues: list = field(default_factory=list)  # List of detected expression problems
    expression_natural: bool = True  # Whether expression appears natural


@dataclass
class AgentResult:
    """Result from an enhancement agent."""
    success: bool
    agent_type: AgentType
    enhanced_image_base64: Optional[str] = None
    description: str = ""
    changes_made: list = field(default_factory=list)
    error_message: Optional[str] = None
    # Include the prompt that was used
    prompt_used: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "agent_type": self.agent_type.value,
            "description": self.description,
            "changes_made": self.changes_made,
            "error_message": self.error_message,
            "prompt_used": self.prompt_used,
        }


class BaseEnhancementAgent(ABC):
    """
    Base class for all enhancement agents.
    
    Each agent specializes in fixing a specific type of AI artifact.
    """
    
    agent_type: AgentType = None
    
    @abstractmethod
    async def can_handle(self, context: EnhancementContext) -> bool:
        """
        Check if this agent can handle the issues in the context.
        
        Args:
            context: The enhancement context with image and detected issues
            
        Returns:
            True if this agent should be invoked
        """
        pass
    
    @abstractmethod
    async def enhance(self, context: EnhancementContext) -> AgentResult:
        """
        Perform enhancement on the image.
        
        Args:
            context: The enhancement context with image and detected issues
            
        Returns:
            AgentResult with the enhanced image or error
        """
        pass
    
    def _find_relevant_signals(self, context: EnhancementContext, keywords: list[str]) -> list:
        """
        Find fake signals that match any of the given keywords.
        
        Args:
            context: The enhancement context
            keywords: List of keywords to match against signal descriptions
            
        Returns:
            List of matching FakeSignal objects
        """
        relevant = []
        for signal in context.fake_signals:
            signal_lower = signal.signal.lower()
            if any(kw.lower() in signal_lower for kw in keywords):
                relevant.append(signal)
        return relevant
    
    def _get_prompt_dict(self, context: EnhancementContext) -> Optional[dict]:
        """Get the prompt as a dictionary for result reporting."""
        if context.agent_prompt:
            return context.agent_prompt.to_dict()
        return None
