# API Documentation

This page outlines the available FastAPI routes for the D&D engine.
See [API data models](data_models.md) for request and response schema details.

## Entities

### `GET /entities/`
- **Description**: List all entities.
- **Response**: `List[EntityListItem]` — each item includes `uuid` and `name`.
- **Example**
  - Request
    ```http
    GET /entities/
    ```
  - Response
    ```json
    [
      {"uuid": "123e4567-e89b-12d3-a456-426614174000", "name": "Fighter"},
      {"uuid": "223e4567-e89b-12d3-a456-426614174001", "name": "Goblin"}
    ]
    ```

### `GET /entities/summaries`
- **Description**: List entities with summary info.
- **Response**: `List[EntitySummary]` with fields like `uuid`, `name`, `current_hp`, `max_hp`, `armor_class`, `position`, and `senses`.
- **Example**
  - Request
    ```http
    GET /entities/summaries
    ```
  - Response
    ```json
    [
      {
        "uuid": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Fighter",
        "current_hp": 12,
        "max_hp": 20,
        "armor_class": 16,
        "position": [0, 0]
      }
    ]
    ```

### `GET /entities/{entity_uuid}`
- **Description**: Full snapshot of a specific entity.
- **Query**: `include_skill_calculations`, `include_attack_calculations`, `include_ac_calculation`, `include_saving_throw_calculations` (all boolean).
- **Response**: `EntitySnapshot` containing `ability_scores`, `skill_set`, `equipment`, `senses`, `saving_throws`, `health`, `action_economy`, `proficiency_bonus`, and `active_conditions`.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000?include_attack_calculations=true
    ```
  - Response
    ```json
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Fighter",
      "health": {"current_hit_points": 12, "max_hit_points": 20},
      "ability_scores": {"str": 15, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 8},
      "equipment": {"weapon_main_hand": {"name": "Longsword", "damage_dice": "1d8"}}
    }
    ```

### `GET /entities/{entity_uuid}/health`
- **Description**: Health block of an entity.
- **Response**: `HealthSnapshot` with `hit_dices`, `current_hit_points`, `max_hit_points`, and `resistances`.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000/health
    ```
  - Response
    ```json
    {
      "current_hit_points": 12,
      "max_hit_points": 20,
      "hit_dices": {"d10": 2},
      "resistances": []
    }
    ```

### `GET /entities/{entity_uuid}/ability_scores`
- **Description**: Ability score information.
- **Response**: `AbilityScoresSnapshot` per ability.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000/ability_scores
    ```
  - Response
    ```json
    {"str": 15, "dex": 12, "con": 14, "int": 10, "wis": 10, "cha": 8}
    ```

### `GET /entities/{entity_uuid}/skill_set`
- **Description**: Skills for the entity.
- **Response**: `SkillSetSnapshot` listing each skill bonus.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000/skill_set
    ```
  - Response
    ```json
    {"athletics": 4, "perception": 2, "stealth": 1}
    ```

### `GET /entities/{entity_uuid}/equipment`
- **Description**: Equipped items and bonuses.
- **Response**: `EquipmentSnapshot` including weapon/armor slots, `armor_class`, and attack/damage bonuses.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000/equipment
    ```
  - Response
    ```json
    {
      "weapon_main_hand": {"name": "Longsword", "damage_dice": "1d8"},
      "armor_class": 16
    }
    ```

### `GET /entities/{entity_uuid}/saving_throws`
- **Description**: Saving throw bonuses.
- **Response**: `SavingThrowSetSnapshot` for each ability.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000/saving_throws
    ```
  - Response
    ```json
    {"str": 2, "dex": 1, "con": 2, "int": 0, "wis": 0, "cha": -1}
    ```

### `GET /entities/{entity_uuid}/proficiency_bonus`
- **Description**: Proficiency bonus value.
- **Response**: `ModifiableValueSnapshot` with base and modifiers.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000/proficiency_bonus
    ```
  - Response
    ```json
    {"base_value": 2, "modifiers": [], "normalized_score": 2}
    ```

### `POST /entities/{entity_uuid}/equip`
- **Description**: Equip an item.
- **Body**: `EquipRequest` — `equipment_uuid` and optional `slot`.
- **Response**: Updated `EntitySnapshot`.
- **Example**
  - Request
    ```http
    POST /entities/123e4567-e89b-12d3-a456-426614174000/equip
    Content-Type: application/json

    {"equipment_uuid": "323e4567-e89b-12d3-a456-426614174002", "slot": "MAIN_HAND"}
    ```
  - Response
    ```json
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "equipment": {"weapon_main_hand": {"uuid": "323e4567-e89b-12d3-a456-426614174002", "name": "Longsword"}}
    }
    ```

### `POST /entities/{entity_uuid}/unequip/{slot}`
- **Description**: Unequip item from a slot.
- **Response**: Updated `EntitySnapshot`.
- **Example**
  - Request
    ```http
    POST /entities/123e4567-e89b-12d3-a456-426614174000/unequip/MAIN_HAND
    ```
  - Response
    ```json
    {"uuid": "123e4567-e89b-12d3-a456-426614174000", "equipment": {"weapon_main_hand": null}}
    ```

### `POST /entities/{entity_uuid}/conditions`
- **Description**: Add a condition to the entity.
- **Body**: `AddConditionRequest` — `condition_type`, `source_entity_uuid`, optional duration fields.
- **Response**: Updated `EntitySnapshot`.
- **Example**
  - Request
    ```http
    POST /entities/123e4567-e89b-12d3-a456-426614174000/conditions
    Content-Type: application/json

    {
      "condition_type": "BLINDED",
      "source_entity_uuid": "223e4567-e89b-12d3-a456-426614174001",
      "duration_type": "PERMANENT"
    }
    ```
  - Response
    ```json
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "active_conditions": {"BLINDED": {"duration_type": "PERMANENT"}}
    }
    ```

### `DELETE /entities/{entity_uuid}/conditions/{condition_name}`
- **Description**: Remove a condition by name.
- **Response**: Updated `EntitySnapshot`.
- **Example**
  - Request
    ```http
    DELETE /entities/123e4567-e89b-12d3-a456-426614174000/conditions/BLINDED
    ```
  - Response
    ```json
    {"uuid": "123e4567-e89b-12d3-a456-426614174000", "active_conditions": {}}
    ```

### `GET /entities/{entity_uuid}/conditions`
- **Description**: List active conditions.
- **Response**: `Dict[str, ConditionSnapshot]` keyed by condition name.
- **Example**
  - Request
    ```http
    GET /entities/123e4567-e89b-12d3-a456-426614174000/conditions
    ```
  - Response
    ```json
    {"BLINDED": {"duration_type": "PERMANENT"}}
    ```

### `POST /entities/{entity_uuid}/action-economy/refresh`
- **Description**: Reset action economy costs.
- **Query**: Same optional calculation flags as `GET /entities/{entity_uuid}`.
- **Response**: Updated `EntitySnapshot`.
- **Example**
  - Request
    ```http
    POST /entities/123e4567-e89b-12d3-a456-426614174000/action-economy/refresh
    ```
  - Response
    ```json
    {
      "uuid": "123e4567-e89b-12d3-a456-426614174000",
      "action_economy": {"action": true, "bonus_action": true, "reaction": true}
    }
    ```

### `POST /entities/{entity_uuid}/target/{target_uuid}`
- **Description**: Set the entity's target.
- **Query**: Optional calculation flags.
- **Response**: Updated `EntitySnapshot`.
- **Example**
  - Request
    ```http
    POST /entities/123e4567-e89b-12d3-a456-426614174000/target/223e4567-e89b-12d3-a456-426614174001
    ```
  - Response
    ```json
    {"uuid": "123e4567-e89b-12d3-a456-426614174000", "target_entity_uuid": "223e4567-e89b-12d3-a456-426614174001"}
    ```

### `POST /entities/{entity_uuid}/attack/{target_uuid}`
- **Description**: Execute an attack.
- **Query**: `weapon_slot` (WeaponSlot) and `attack_name` (string).
- **Response**: `AttackResponse` containing the resulting `EventSnapshot` and attack metadata such as `attack_roll`, `attack_total`, `damage_rolls`, and `total_damage`.
- **Example**
  - Request
    ```http
    POST /entities/123e4567-e89b-12d3-a456-426614174000/attack/223e4567-e89b-12d3-a456-426614174001?weapon_slot=MAIN_HAND&attack_name=Slash
    ```
  - Response
    ```json
    {
      "event": {"event_type": "ATTACK", "name": "Slash"},
      "metadata": {"attack_roll": 15, "attack_total": 20, "total_damage": 7}
    }
    ```

### `GET /entities/position/{x}/{y}`
- **Description**: Get entities at a map position.
- **Response**: `List[EntitySummary]`.
- **Example**
  - Request
    ```http
    GET /entities/position/0/0
    ```
  - Response
    ```json
    [
      {"uuid": "123e4567-e89b-12d3-a456-426614174000", "name": "Fighter", "position": [0,0]}
    ]
    ```

### `POST /entities/{entity_uuid}/move`
- **Description**: Move an entity to a new position.
- **Body**: `MoveRequest` — `position` and optional `include_paths_senses`.
- **Response**: `MovementResponse` with the movement `EventSnapshot`, updated `EntitySummary`, and optional `path_senses` map.
- **Example**
  - Request
    ```http
    POST /entities/123e4567-e89b-12d3-a456-426614174000/move
    Content-Type: application/json

    {"position": [1, 0]}
    ```
  - Response
    ```json
    {
      "event": {"event_type": "MOVE", "end_position": [1, 0]},
      "entity": {"uuid": "123e4567-e89b-12d3-a456-426614174000", "position": [1, 0]}
    }
    ```

## Equipment

### `GET /equipment/`
- **Description**: List all equipment. Optional filter by source entity.
- **Query**: `source_entity_uuid`.
- **Response**: List of `WeaponSnapshot`, `ArmorSnapshot`, or `ShieldSnapshot`. Notable fields include `name`, `damage_dice`/`ac`, and `properties`.
- **Example**
  - Request
    ```http
    GET /equipment/
    ```
  - Response
    ```json
    [
      {"uuid": "323e4567-e89b-12d3-a456-426614174002", "name": "Longsword", "damage_dice": "1d8"},
      {"uuid": "423e4567-e89b-12d3-a456-426614174003", "name": "Chain Mail", "ac": 16}
    ]
    ```

### `GET /equipment/{equipment_uuid}`
- **Description**: Get details for a specific piece of equipment.
- **Response**: `WeaponSnapshot`, `ArmorSnapshot`, or `ShieldSnapshot` depending on type.
- **Example**
  - Request
    ```http
    GET /equipment/323e4567-e89b-12d3-a456-426614174002
    ```
  - Response
    ```json
    {"uuid": "323e4567-e89b-12d3-a456-426614174002", "name": "Longsword", "damage_dice": "1d8", "properties": ["VERSATILE"]}
    ```

## Events

### `GET /events/{event_uuid}`
- **Description**: Retrieve an event by UUID.
- **Query**: `include_children`.
- **Response**: `EventSnapshot` with `uuid`, `name`, `timestamp`, `event_type`, `phase`, and child events.
- **Example**
  - Request
    ```http
    GET /events/523e4567-e89b-12d3-a456-426614174004
    ```
  - Response
    ```json
    {
      "uuid": "523e4567-e89b-12d3-a456-426614174004",
      "event_type": "ATTACK",
      "name": "Slash",
      "timestamp": 1700000000
    }
    ```

### `GET /events/lineage/{lineage_uuid}`
- **Description**: Events sharing a lineage UUID.
- **Query**: `include_children`.
- **Response**: `List[EventSnapshot]`.
- **Example**
  - Request
    ```http
    GET /events/lineage/623e4567-e89b-12d3-a456-426614174005
    ```
  - Response
    ```json
    [
      {"uuid": "523e4567-e89b-12d3-a456-426614174004", "event_type": "ATTACK"},
      {"uuid": "723e4567-e89b-12d3-a456-426614174006", "event_type": "DAMAGE"}
    ]
    ```

### `GET /events/latest/{count}`
- **Description**: Latest `count` events.
- **Query**: `include_children`.
- **Response**: `List[EventSnapshot]`.
- **Example**
  - Request
    ```http
    GET /events/latest/2
    ```
  - Response
    ```json
    [
      {"uuid": "823e4567-e89b-12d3-a456-426614174007", "event_type": "MOVE"},
      {"uuid": "523e4567-e89b-12d3-a456-426614174004", "event_type": "ATTACK"}
    ]
    ```

## Tiles

### `GET /tiles/`
- **Description**: Snapshot of the entire grid.
- **Response**: `GridSnapshot` containing `width`, `height`, and map of `TileSummary` objects.
- **Example**
  - Request
    ```http
    GET /tiles/
    ```
  - Response
    ```json
    {
      "width": 10,
      "height": 10,
      "tiles": {
        "(0,0)": {"walkable": true, "visible": true},
        "(1,0)": {"walkable": false, "visible": true}
      }
    }
    ```

### `GET /tiles/position/{x}/{y}`
- **Description**: Get tile at coordinates.
- **Response**: `TileSnapshot` with `uuid`, `position`, `walkable`, `visible`, `sprite_name`, and occupant entity UUIDs.
- **Example**
  - Request
    ```http
    GET /tiles/position/0/0
    ```
  - Response
    ```json
    {
      "uuid": "923e4567-e89b-12d3-a456-426614174008",
      "position": [0, 0],
      "walkable": true,
      "visible": true,
      "sprite_name": "floor"
    }
    ```

### `GET /tiles/{tile_uuid}`
- **Description**: Get tile by UUID.
- **Response**: `TileSnapshot`.
- **Example**
  - Request
    ```http
    GET /tiles/923e4567-e89b-12d3-a456-426614174008
    ```
  - Response
    ```json
    {
      "uuid": "923e4567-e89b-12d3-a456-426614174008",
      "position": [0, 0],
      "walkable": true
    }
    ```

### `POST /tiles/`
- **Description**: Create a tile.
- **Body**: `CreateTileRequest` — `position` and `tile_type`.
- **Response**: Created `TileSnapshot`.
- **Example**
  - Request
    ```http
    POST /tiles/
    Content-Type: application/json

    {"position": [2, 0], "tile_type": "FLOOR"}
    ```
  - Response
    ```json
    {
      "uuid": "a23e4567-e89b-12d3-a456-426614174009",
      "position": [2, 0],
      "walkable": true,
      "visible": true
    }
    ```

### `DELETE /tiles/position/{x}/{y}`
- **Description**: Delete tile at coordinates.
- **Response**: Message confirming deletion.
- **Example**
  - Request
    ```http
    DELETE /tiles/position/2/0
    ```
  - Response
    ```json
    {"message": "Tile at [2,0] deleted"}
    ```

### `GET /tiles/walkable/{x}/{y}`
- **Description**: Check if a position is walkable.
- **Response**: JSON with `position` and `walkable`.
- **Example**
  - Request
    ```http
    GET /tiles/walkable/0/0
    ```
  - Response
    ```json
    {"position": [0, 0], "walkable": true}
    ```

### `GET /tiles/visible/{x}/{y}`
- **Description**: Check if a position is visible.
- **Response**: JSON with `position` and `visible`.
- **Example**
  - Request
    ```http
    GET /tiles/visible/0/0
    ```
  - Response
    ```json
    {"position": [0, 0], "visible": true}
    ```

