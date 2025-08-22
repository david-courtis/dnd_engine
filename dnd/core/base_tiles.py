from typing import Dict, Optional, Any, List, Self, Literal,ClassVar, Union, Callable, Tuple, DefaultDict
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator, computed_field,field_validator
from dnd.core.values import ModifiableValue, StaticValue
from dnd.core.modifiers import NumericalModifier, DamageType , ResistanceStatus, ContextAwareCondition, BaseObject, saving_throws, ResistanceModifier
from dnd.core.base_conditions import BaseCondition
from dnd.core.events import EventHandler, Trigger, Event
from enum import Enum
from random import randint
from functools import cached_property
from typing import Literal as TypeLiteral
from collections import defaultdict
from dnd.core.shadowcast import compute_fov
from dnd.core.dijkstra import dijkstra, get_neighbors



class Tile(BaseObject):
    name: str = Field(default="Floor", description="The name of the tile")
    position: Tuple[int, int] = Field(description="The position of the tile on the grid")
    movement_cost: int = Field(default=1, ge=1, description="Cost to move onto this tile")
    blocks_movement: bool = Field(default=False, description="Whether the tile blocks movement")
    blocks_vision: bool = Field(default=False, description="Whether the tile blocks line of sight")
    sprite_name: Optional[str] = Field(default=None, description="The name of the sprite to use for the tile")
    _tile_registry: ClassVar[Dict[UUID, 'Tile']] = {}
    _tile_by_position: ClassVar[Dict[Tuple[int, int], 'Tile']] = {}

    def __init__(self, **data):
        """
        Initialize the BaseBlock and register it in the class registry.

        Args:
            **data: Keyword arguments to initialize the BaseBlock attributes.
        """
        super().__init__(**data)
        self.__class__._tile_registry[self.uuid] = self
        self.__class__._tile_by_position[self.position] = self

    @classmethod
    def get_all_tiles(cls) -> List['Tile']:
        return list(cls._tile_registry.values())
    
    @classmethod
    def get_tile_at_position(cls, position: Tuple[int,int]) -> Optional['Tile']:
        return cls._tile_by_position.get(position)
    
    @classmethod
    def get(cls, uuid: UUID) -> Optional['Tile']:
        return cls._tile_registry.get(uuid)
    
    @classmethod
    def grid_size(cls) -> Tuple[int,int]:
        return max(tile.position[0] for tile in cls.get_all_tiles()) + 1, max(tile.position[1] for tile in cls.get_all_tiles()) + 1
    
    @computed_field(return_type=bool)
    def walkable(self) -> bool:
        return not self.blocks_movement

    @computed_field(return_type=bool)
    def visible(self) -> bool:
        return not self.blocks_vision

    @classmethod
    def create(
        cls,
        position: Tuple[int, int],
        sprite_name: Optional[str] = None,
        can_walk: bool = True,
        can_see: bool = True,
        movement_cost: int = 1,
        name: str = "Floor",
    ) -> 'Tile':
        tile_uuid = uuid4()
        return cls(
            uuid=tile_uuid,
            source_entity_uuid=tile_uuid,
            target_entity_uuid=tile_uuid,
            position=position,
            sprite_name=sprite_name,
            blocks_movement=not can_walk,
            blocks_vision=not can_see,
            movement_cost=movement_cost,
            name=name,
        )

    @classmethod
    def is_visible(cls, position: Tuple[int,int]) -> bool:
        tile = cls.get_tile_at_position(position)
        if tile is None:
            return False
        return tile.visible
    
    @classmethod
    def is_walkable(cls, position: Tuple[int,int]) -> bool:
        tile = cls.get_tile_at_position(position)
        if tile is None:
            return False
        return tile.walkable
    
    @classmethod
    def get_fov(cls, source_pos: Tuple[int, int], max_distance: Optional[float] = None) -> List[Tuple[int, int]]:
        """
        Compute the field of view from a given position using shadowcasting.
        
        Args:
            source_pos: The position to compute FOV from
            max_distance: Maximum view distance (optional)
            
        Returns:
            List of visible positions
        """
        visible_positions: List[Tuple[int, int]] = []
        
        def is_blocking(x: int, y: int) -> bool:
            tile = cls.get_tile_at_position((x, y))
            return tile is None or tile.blocks_vision
            
        def mark_visible(x: int, y: int) -> None:
            visible_positions.append((x, y))
            
        compute_fov(source_pos, is_blocking, mark_visible, max_distance)
        return visible_positions

    @classmethod
    def get_paths(cls, start_pos: Tuple[int, int], max_distance: Optional[int] = None) -> Tuple[Dict[Tuple[int, int], int], Dict[Tuple[int, int], List[Tuple[int, int]]]]:
        """
        Compute all possible paths from a starting position using Dijkstra's algorithm.
        
        Args:
            start_pos: Starting position
            max_distance: Maximum path distance (optional)
            
        Returns:
            Tuple of (distances_dict, paths_dict) where:
            - distances_dict maps positions to their distance from start
            - paths_dict maps positions to the path list to reach them
        """
        width, height = cls.grid_size()
        
        def is_walkable(x: int, y: int) -> bool:
            tile = cls.get_tile_at_position((x, y))
            return tile is not None and tile.walkable

        def cost(x: int, y: int) -> int:
            tile = cls.get_tile_at_position((x, y))
            return tile.movement_cost if tile else 1

        return dijkstra(start_pos, is_walkable, width, height, diagonal=True, max_distance=max_distance, cost=cost)

    @classmethod
    def get_adjacent_positions(cls, position: Tuple[int, int], diagonal: bool = True) -> List[Tuple[int, int]]:
        tile = cls.get_tile_at_position(position)
        if tile is None:
            return []
        width, height = cls.grid_size()
        return get_neighbors(position, diagonal, width, height)


def floor_factory(position: Tuple[int,int]) -> Tile:
    return Tile.create(position, sprite_name="floor.png", can_walk=True, can_see=True)

def wall_factory(position: Tuple[int,int]) -> Tile:
    return Tile.create(position, sprite_name="wall.png", can_walk=False, can_see=False)

def water_factory(position: Tuple[int,int]) -> Tile:
    return Tile.create(position, sprite_name="water.png", can_walk=False, can_see=True)



