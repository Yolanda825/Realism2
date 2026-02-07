"""Pydantic models for all JSON schemas in the realism enhancement pipeline."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for fake signals."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(str, Enum):
    """Priority levels for enhancement strategy."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"


class Strength(str, Enum):
    """Strength levels for enhancement operations."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"


class ModuleType(str, Enum):
    """Types of enhancement modules."""
    LIGHTING = "lighting"
    TEXTURE = "texture"
    NOISE = "noise"


class AgentType(str, Enum):
    """Types of expert agents."""
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
    PRESERVE = "preserve"
    CORRECT = "correct"


class Locality(str, Enum):
    """Locality of enhancement operations."""
    GLOBAL = "global"
    LOCAL = "local"


class JobStatus(str, Enum):
    """Status of a processing job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Stage 1: Scene Classification
class SceneClassification(BaseModel):
    """Output schema for Stage 1: Scene Classifier."""
    primary_scene: str = Field(
        ...,
        description="Primary scene type (e.g., portrait, landscape, interior, product, street)"
    )
    secondary_attributes: list[str] = Field(
        default_factory=list,
        description="Secondary attributes like lighting conditions, composition style, etc."
    )
    ai_likelihood: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Likelihood (0.0-1.0) that the image is AI-generated"
    )


# Stage 2: Fake Signal Detection
class FakeSignal(BaseModel):
    """A single fake signal detected in the image."""
    signal: str = Field(..., description="Description of the detected fake signal")
    severity: Severity = Field(..., description="Severity level of the signal")


class FakeSignalList(BaseModel):
    """Container for fake signals."""
    fake_signals: list[FakeSignal] = Field(default_factory=list)


# Stage 3: RAG - Realism Constraints
class RealismConstraints(BaseModel):
    """Output schema for Stage 3: RAG Module."""
    scene_rules: list[str] = Field(
        default_factory=list,
        description="Rules for realistic appearance based on scene type"
    )
    avoid_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns to avoid that indicate AI generation"
    )


# Stage 4: Strategy Generator
class Operation(BaseModel):
    """A single enhancement operation."""
    module: ModuleType = Field(..., description="Target enhancement module")
    action: str = Field(..., description="Description of the action to perform")
    strength: Strength = Field(..., description="Strength of the enhancement")
    locality: Locality = Field(..., description="Whether the operation is global or local")


class Strategy(BaseModel):
    """Output schema for Stage 4: Strategy Generator."""
    goal: str = Field(..., description="Overall goal of the enhancement strategy")
    priority: Priority = Field(..., description="Priority level of the enhancement")
    operations: list[Operation] = Field(
        default_factory=list,
        description="List of enhancement operations to perform"
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Constraints that must be preserved during enhancement"
    )


# Stage 5: Execution Plan
class ModuleInstruction(BaseModel):
    """A single instruction for an enhancement module."""
    action: str = Field(..., description="The action to perform")
    parameters: dict = Field(default_factory=dict, description="Parameters for the action")
    target_region: Optional[str] = Field(None, description="Target region if local operation")


class ExecutionPlan(BaseModel):
    """Output schema for Stage 5: Execution Planner."""
    lighting_module: list[ModuleInstruction] = Field(
        default_factory=list,
        description="Instructions for the lighting enhancement module"
    )
    texture_module: list[ModuleInstruction] = Field(
        default_factory=list,
        description="Instructions for the texture enhancement module"
    )
    noise_module: list[ModuleInstruction] = Field(
        default_factory=list,
        description="Instructions for the noise addition module"
    )


# Stage 6: Realism Scorer
class RealismScore(BaseModel):
    """Output schema for Stage 6: Realism Scorer."""
    before: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated realism score before enhancement"
    )
    after: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated realism score after enhancement"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence level of the score estimation"
    )
    notes: str = Field(default="", description="Additional notes about the scoring")


# Agent Prompt (structured prompt for each expert)
class AgentPromptSchema(BaseModel):
    """Structured prompt for an expert agent."""
    agent_type: str = Field(..., description="Type of agent")
    positive_prompt: str = Field(default="", description="What to add/enhance (English, for image model)")
    negative_prompt: str = Field(default="", description="What to avoid/remove (English, for image model)")
    intensity: str = Field(default="medium", description="Intensity: light, medium, strong")
    specific_instructions: list[str] = Field(default_factory=list, description="Specific instructions in Chinese")
    target_areas: list[str] = Field(default_factory=list, description="Target areas to modify")
    # New fields for preservation/correction
    preservation_prompt: str = Field(default="", description="What to preserve (identity, pose, expression if natural)")
    correction_prompt: str = Field(default="", description="What to correct (expression muscles, etc.)")
    denoising_strength: float = Field(default=0.2, description="Suggested denoising strength for img2img")
    expression_mode: str = Field(default="preserve", description="Expression handling mode: preserve or correct")
    expression_type: str = Field(default="neutral", description="Detected expression type")
    expression_issues: list[str] = Field(default_factory=list, description="Detected expression problems")


# Expert Agent Results
class ExpertAgentResult(BaseModel):
    """Result from a single expert agent."""
    agent_type: str = Field(..., description="Type of agent (skin, lighting, etc.)")
    success: bool = Field(..., description="Whether the agent succeeded")
    description: str = Field(default="", description="Description of what was done")
    changes_made: list[str] = Field(default_factory=list, description="List of changes made")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    prompt_used: Optional[AgentPromptSchema] = Field(None, description="The prompt used by this agent")


class IterationResult(BaseModel):
    """Result of a single iteration in the enhancement loop."""
    iteration: int = Field(..., description="Iteration number (1-based)")
    ai_likelihood_before: float = Field(..., description="AI likelihood before this iteration")
    ai_likelihood_after: float = Field(..., description="AI likelihood after this iteration")
    agents_invoked: list[str] = Field(default_factory=list, description="Agents invoked in this iteration")
    agent_results: list[ExpertAgentResult] = Field(default_factory=list, description="Results from each agent")
    routing_reasoning: str = Field(default="", description="Why these agents were selected")
    agent_prompts: list[AgentPromptSchema] = Field(default_factory=list, description="Prompts for each agent")


class ExpertEnhancementResult(BaseModel):
    """Result from the expert enhancement system."""
    success: bool = Field(..., description="Whether enhancement succeeded")
    total_iterations: int = Field(..., description="Total number of iterations performed")
    initial_ai_likelihood: float = Field(..., description="AI likelihood before enhancement")
    final_ai_likelihood: float = Field(..., description="AI likelihood after enhancement")
    iterations: list[IterationResult] = Field(default_factory=list, description="Details of each iteration")
    summary: str = Field(default="", description="Human-readable summary")
    stopped_reason: str = Field(default="", description="Why the loop stopped")
    enhanced_image_base64: Optional[str] = Field(None, description="Base64-encoded enhanced image")


# Model Routing Information (legacy, kept for compatibility)
class ModelRouting(BaseModel):
    """Information about which model to use for enhancement."""
    model_name: str = Field(..., description="Name of the model to use")
    model_type: str = Field(..., description="Type of model (e.g., img2img, inpainting)")
    prompt: str = Field(..., description="Prompt to send to the model")
    negative_prompt: str = Field(default="", description="Negative prompt")
    parameters: dict = Field(default_factory=dict, description="Model-specific parameters")
    reasoning: str = Field(default="", description="Why this model was selected")


# Enhancement Result (legacy, kept for compatibility)
class EnhancementResult(BaseModel):
    """Result of image enhancement."""
    success: bool = Field(..., description="Whether enhancement succeeded")
    enhanced_image_base64: Optional[str] = Field(None, description="Base64-encoded enhanced image")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# Final Pipeline Result with Enhanced Image
class PipelineResult(BaseModel):
    """Final output combining all pipeline stages."""
    scene_classification: SceneClassification
    fake_signals: list[FakeSignal]
    realism_constraints: RealismConstraints
    strategy: Strategy
    execution_plan: ExecutionPlan
    realism_score: RealismScore
    # Expert enhancement system results
    expert_enhancement: Optional[ExpertEnhancementResult] = Field(
        None, description="Results from expert enhancement system"
    )
    # Legacy fields (kept for compatibility)
    model_routing: Optional[ModelRouting] = Field(None, description="Model routing decision")
    enhancement_result: Optional[EnhancementResult] = Field(None, description="Enhancement result")


# API Response Models
class UploadResponse(BaseModel):
    """Response for image upload endpoint."""
    job_id: str = Field(..., description="Unique identifier for the processing job")
    message: str = Field(default="Image uploaded successfully")


class JobResponse(BaseModel):
    """Response for job status and result."""
    job_id: str = Field(..., description="Unique identifier for the processing job")
    status: JobStatus = Field(..., description="Current status of the job")
    result: Optional[PipelineResult] = Field(None, description="Pipeline result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
