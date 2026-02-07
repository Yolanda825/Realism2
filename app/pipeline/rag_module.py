"""Stage 3: RAG Module - Retrieves realism constraints based on scene type."""

import json
from pathlib import Path
from typing import Optional

from app.models.schemas import RealismConstraints


class RAGModule:
    """
    Retrieves realism constraints from a knowledge base.

    This is a placeholder implementation using a JSON file.
    In production, this could be replaced with a vector database
    like ChromaDB, Pinecone, or similar.
    """

    def __init__(self, knowledge_path: Optional[str] = None):
        """
        Initialize the RAG module.

        Args:
            knowledge_path: Path to the knowledge base JSON file.
                           Defaults to knowledge/scene_rules.json
        """
        if knowledge_path is None:
            # Default to project root knowledge directory
            knowledge_path = Path(__file__).parent.parent.parent / "knowledge" / "scene_rules.json"
        else:
            knowledge_path = Path(knowledge_path)

        self.knowledge_path = knowledge_path
        self._knowledge_base: Optional[dict] = None

    def _load_knowledge_base(self) -> dict:
        """Load the knowledge base from JSON file."""
        if self._knowledge_base is None:
            if self.knowledge_path.exists():
                with open(self.knowledge_path, "r", encoding="utf-8") as f:
                    self._knowledge_base = json.load(f)
            else:
                self._knowledge_base = {}
        return self._knowledge_base

    async def retrieve_constraints(self, scene_type: str) -> RealismConstraints:
        """
        Retrieve realism constraints for a given scene type.

        Args:
            scene_type: The primary scene type from scene classification

        Returns:
            RealismConstraints with scene rules and patterns to avoid
        """
        knowledge = self._load_knowledge_base()

        # Normalize scene type for lookup
        scene_key = scene_type.lower().strip()

        # Get scene-specific rules, fall back to default
        scene_data = knowledge.get(scene_key, knowledge.get("default", {}))

        return RealismConstraints(
            scene_rules=scene_data.get("scene_rules", []),
            avoid_patterns=scene_data.get("avoid_patterns", []),
        )

    def get_available_scene_types(self) -> list[str]:
        """
        Get list of scene types available in the knowledge base.

        Returns:
            List of scene type keys
        """
        knowledge = self._load_knowledge_base()
        return list(knowledge.keys())
