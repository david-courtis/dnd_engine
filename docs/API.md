# API Documentation

This page outlines the available FastAPI routes for the D&D engine.

## Entities

### `GET /entities/`

- **Description**: List all entities.
- **Response**: `List[EntityListItem]` — each item includes `uuid` and `name`.

### `GET /entities/summaries`

- **Description**: List entities with summary info.
- **Response**: `List[EntitySummary]` with fields like `uuid`, `name`, `current_hp`, `max_hp`, `armor_class`, `position`, and `senses`.

### `GET /entities/{entity_uuid}`

- **Description**: Full snapshot of a specific entity.
- **Query**: `include_skill_calculations`, `include_attack_calculations`, `include_ac_calculation`, `include_saving_throw_calculations` (all boolean).
- **Response**: `EntitySnapshot` containing `ability_scores`, `skill_set`, `equipment`, `senses`, `saving_throws`, `health`, `action_economy`, `proficiency_bonus`, and `active_conditions`.

### `GET /entities/{entity_uuid}/health`

- **Description**: Health block of an entity.
- **Response**: `HealthSnapshot` with `hit_dices`, `current_hit_points`, `max_hit_points`, and `resistances`.

### `GET /entities/{entity_uuid}/ability_scores`

- **Description**: Ability score information.
- **Response**: `AbilityScoresSnapshot` per ability.

### `GET /entities/{entity_uuid}/skill_set`

- **Description**: Skills for the entity.
- **Response**: `SkillSetSnapshot` listing each skill bonus.

### `GET /entities/{entity_uuid}/equipment`

- **Description**: Equipped items and bonuses.
- **Response**: `EquipmentSnapshot` including weapon/armor slots, `armor_class`, and attack/damage bonuses.

### `GET /entities/{entity_uuid}/saving_throws`

- **Description**: Saving throw bonuses.
- **Response**: `SavingThrowSetSnapshot` for each ability.

### `GET /entities/{entity_uuid}/proficiency_bonus`

- **Description**: Proficiency bonus value.
- **Response**: `ModifiableValueSnapshot` with base and modifiers.

### `POST /entities/{entity_uuid}/equip`

- **Description**: Equip an item.
- **Body**: `EquipRequest` — `equipment_uuid` and optional `slot`.
- **Response**: Updated `EntitySnapshot`.

### `POST /entities/{entity_uuid}/unequip/{slot}`

- **Description**: Unequip item from a slot.
- **Response**: Updated `EntitySnapshot`.

### `POST /entities/{entity_uuid}/conditions`

- **Description**: Add a condition to the entity.
- **Body**: `AddConditionRequest` — `condition_type`, `source_entity_uuid`, optional duration fields.
- **Response**: Updated `EntitySnapshot`.

### `DELETE /entities/{entity_uuid}/conditions/{condition_name}`

- **Description**: Remove a condition by name.
- **Response**: Updated `EntitySnapshot`.

### `GET /entities/{entity_uuid}/conditions`

- **Description**: List active conditions.
- **Response**: `Dict[str, ConditionSnapshot]` keyed by condition name.

### `POST /entities/{entity_uuid}/action-economy/refresh`

- **Description**: Reset action economy costs.
- **Query**: Same optional calculation flags as `GET /entities/{entity_uuid}`.
- **Response**: Updated `EntitySnapshot`.

### `POST /entities/{entity_uuid}/target/{target_uuid}`

- **Description**: Set the entity's target.
- **Query**: Optional calculation flags.
- **Response**: Updated `EntitySnapshot`.

### `POST /entities/{entity_uuid}/attack/{target_uuid}`

- **Description**: Execute an attack.
- **Query**: `weapon_slot` (WeaponSlot) and `attack_name` (string).
- **Response**: `AttackResponse` containing the resulting `EventSnapshot` and attack metadata such as `attack_roll`, `attack_total`, `damage_rolls`, and `total_damage`.

### `GET /entities/position/{x}/{y}`

- **Description**: Get entities at a map position.
- **Response**: `List[EntitySummary]`.

### `POST /entities/{entity_uuid}/move`

- **Description**: Move an entity to a new position.
- **Body**: `MoveRequest` — `position` and optional `include_paths_senses`.
- **Response**: `MovementResponse` with the movement `EventSnapshot`, updated `EntitySummary`, and optional `path_senses` map.

## Equipment

### `GET /equipment/`

- **Description**: List all equipment. Optional filter by source entity.
- **Query**: `source_entity_uuid`.
- **Response**: List of `WeaponSnapshot`, `ArmorSnapshot`, or `ShieldSnapshot`. Notable fields include `name`, `damage_dice`/`ac`, and `properties`.

### `GET /equipment/{equipment_uuid}`

- **Description**: Get details for a specific piece of equipment.
- **Response**: `WeaponSnapshot`, `ArmorSnapshot`, or `ShieldSnapshot` depending on type.

## Events

### `GET /events/{event_uuid}`

- **Description**: Retrieve an event by UUID.
- **Query**: `include_children`.
- **Response**: `EventSnapshot` with `uuid`, `name`, `timestamp`, `event_type`, `phase`, and child events.

### `GET /events/lineage/{lineage_uuid}`

- **Description**: Events sharing a lineage UUID.
- **Query**: `include_children`.
- **Response**: `List[EventSnapshot]`.

### `GET /events/latest/{count}`

- **Description**: Latest `count` events.
- **Query**: `include_children`.
- **Response**: `List[EventSnapshot]`.

## Tiles

### `GET /tiles/`

- **Description**: Snapshot of the entire grid.
- **Response**: `GridSnapshot` containing `width`, `height`, and map of `TileSummary` objects.

### `GET /tiles/position/{x}/{y}`

- **Description**: Get tile at coordinates.
- **Response**: `TileSnapshot` with `uuid`, `position`, `walkable`, `visible`, `sprite_name`, and occupant entity UUIDs.

### `GET /tiles/{tile_uuid}`

- **Description**: Get tile by UUID.
- **Response**: `TileSnapshot`.

### `POST /tiles/`

- **Description**: Create a tile.
- **Body**: `CreateTileRequest` — `position` and `tile_type`.
- **Response**: Created `TileSnapshot`.

### `DELETE /tiles/position/{x}/{y}`

- **Description**: Delete tile at coordinates.
- **Response**: Message confirming deletion.

### `GET /tiles/walkable/{x}/{y}`

- **Description**: Check if a position is walkable.
- **Response**: JSON with `position` and `walkable`.

### `GET /tiles/visible/{x}/{y}`

- **Description**: Check if a position is visible.
- **Response**: JSON with `position` and `visible`.
