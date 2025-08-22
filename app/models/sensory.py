from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple
from uuid import UUID
from dnd.blocks.sensory import Senses, SensesType



class SensesSnapshot(BaseModel):
    """Interface model for a Senses block"""
    entities: Dict[UUID, Tuple[int, int]] = Field(default_factory=dict)
    visible: Dict[Tuple[int, int], bool] = Field(default_factory=dict)
    walkable: Dict[Tuple[int, int], bool] = Field(default_factory=dict)
    paths: Dict[Tuple[int, int], List[Tuple[int, int]]] = Field(default_factory=dict)
    extra_senses: List[SensesType] = Field(default_factory=list)
    position: Tuple[int, int]
    seen: List[Tuple[int, int]] = Field(default_factory=list)

    @classmethod
    def from_engine(cls, senses: Senses):
        return cls(
            entities=getattr(senses, "entities", {}),
            visible=getattr(senses, "visible", getattr(senses, "visible_tiles", {})),
            walkable=getattr(senses, "walkable", {}),
            paths=getattr(senses, "paths", {}),
            extra_senses=getattr(senses, "extra_senses", []),
            position=getattr(senses, "position"),
            seen=list(getattr(senses, "seen", [])),
        )