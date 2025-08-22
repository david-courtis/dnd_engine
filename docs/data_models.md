# API Data Models

This reference outlines the Pydantic schemas used by the FastAPI service.
All payloads are JSON serialisations of these models.

## Entity models

### EntityListItem

| Field    | Type   | Description       |
| -------- | ------ | ----------------- |
| `uuid` | UUID   | Entity identifier |
| `name` | string | Display name      |

### EntitySummary

| Field                  | Type                           | Description               |
| ---------------------- | ------------------------------ | ------------------------- |
| `uuid`               | UUID                           | Entity identifier         |
| `name`               | string                         | Display name              |
| `current_hp`         | integer                        | Current hit points        |
| `max_hp`             | integer                        | Maximum hit points        |
| `armor_class`        | integer?                       | Computed AC if available  |
| `target_entity_uuid` | UUID?                          | Current target            |
| `position`           | `[x, y]`                     | Tile coordinates          |
| `sprite_name`        | string?                        | Optional sprite reference |
| `senses`             | [SensesSnapshot](#sensessnapshot) | Perception data           |

### ConditionSnapshot

| Field                  | Type               | Description                     |
| ---------------------- | ------------------ | ------------------------------- |
| `uuid`               | UUID               | Condition identifier            |
| `name`               | string             | Condition name                  |
| `description`        | string?            | Details of the effect           |
| `duration_type`      | string             | `ROUNDS`, `PERMANENT`, etc. |
| `duration_value`     | integer or string? | Rounds or trigger condition     |
| `source_entity_name` | string?            | Source entity name              |
| `source_entity_uuid` | UUID               | Source entity id                |
| `applied`            | boolean            | Whether effect is active        |

### EntitySnapshot

Full representation of an entity.

| Field                         | Type                                                    |
| ----------------------------- | ------------------------------------------------------- |
| `uuid`                      | UUID                                                    |
| `name`                      | string                                                  |
| `description`               | string?                                                 |
| `target_entity_uuid`        | UUID?                                                   |
| `target_summary`            | [EntitySummary](#entitysummary)?                           |
| `position`                  | `[x, y]`                                              |
| `sprite_name`               | string?                                                 |
| `ability_scores`            | [AbilityScoresSnapshot](#abilityscoressnapshot)            |
| `skill_set`                 | [SkillSetSnapshot](#skillsetsnapshot)                      |
| `equipment`                 | [EquipmentSnapshot](#equipmentsnapshot)                    |
| `senses`                    | [SensesSnapshot](#sensessnapshot)                          |
| `saving_throws`             | [SavingThrowSetSnapshot](#savingthrowsetsnapshot)          |
| `health`                    | [HealthSnapshot](#healthsnapshot)                          |
| `action_economy`            | [ActionEconomySnapshot](#actioneconomysnapshot)            |
| `proficiency_bonus`         | [ModifiableValueSnapshot](#modifiablevaluesnapshot)        |
| `skill_calculations`        | dict[SkillName, SkillBonusCalculationSnapshot]          |
| `attack_calculations`       | dict[WeaponSlot, AttackBonusCalculationSnapshot]        |
| `ac_calculation`            | [ACBonusCalculationSnapshot](#acbonuscalculationsnapshot)? |
| `saving_throw_calculations` | dict[AbilityName, SavingThrowBonusCalculationSnapshot]  |
| `active_conditions`         | dict[str, ConditionSnapshot]                            |

### Ability models

#### AbilitySnapshot

| Field              | Type                    |
| ------------------ | ----------------------- |
| `uuid`           | UUID                    |
| `name`           | AbilityName             |
| `ability_score`  | ModifiableValueSnapshot |
| `modifier_bonus` | ModifiableValueSnapshot |
| `modifier`       | integer                 |

#### AbilityScoresSnapshot

| Field                      | Type                  |
| -------------------------- | --------------------- |
| `uuid`                   | UUID                  |
| `name`                   | string                |
| `source_entity_uuid`     | UUID                  |
| `source_entity_name`     | string?               |
| `strength`..`charisma` | AbilitySnapshot       |
| `abilities`              | list[AbilitySnapshot] |

### Skill models

#### SkillSnapshot

| Field                      | Type                    |
| -------------------------- | ----------------------- |
| `uuid`                   | UUID                    |
| `name`                   | SkillName               |
| `ability`                | AbilityName             |
| `proficiency`            | boolean                 |
| `expertise`              | boolean                 |
| `skill_bonus`            | ModifiableValueSnapshot |
| `proficiency_multiplier` | float                   |
| `effective_bonus`        | integer?                |

#### SkillSetSnapshot

| Field                        | Type                           |
| ---------------------------- | ------------------------------ |
| `uuid`                     | UUID                           |
| `name`                     | string                         |
| `source_entity_uuid`       | UUID                           |
| `source_entity_name`       | string?                        |
| `skills`                   | dict[SkillName, SkillSnapshot] |
| `proficient_skills`        | list[SkillName]                |
| `expertise_skills`         | list[SkillName]                |
| `skills_requiring_sight`   | list[SkillName]                |
| `skills_requiring_hearing` | list[SkillName]                |
| `skills_requiring_speak`   | list[SkillName]                |
| `skills_social`            | list[SkillName]                |

#### SkillBonusCalculationSnapshot

Breakdown for skill bonus calculation.

| Field                            | Type                    |
| -------------------------------- | ----------------------- |
| `skill_name`                   | SkillName               |
| `ability_name`                 | AbilityName             |
| `proficiency_bonus`            | ModifiableValueSnapshot |
| `normalized_proficiency_bonus` | ModifiableValueSnapshot |
| `skill_bonus`                  | ModifiableValueSnapshot |
| `ability_bonus`                | ModifiableValueSnapshot |
| `ability_modifier_bonus`       | ModifiableValueSnapshot |
| `has_cross_entity_effects`     | boolean                 |
| `target_entity_uuid`           | UUID?                   |
| `total_bonus`                  | ModifiableValueSnapshot |
| `final_modifier`               | integer                 |

### Equipment models

#### RangeSnapshot

| Field      | Type      |
| ---------- | --------- |
| `type`   | RangeType |
| `normal` | integer   |
| `long`   | integer?  |

#### DamageSnapshot

| Field                  | Type                     |
| ---------------------- | ------------------------ |
| `uuid` or `name`   | identifiers              |
| `damage_dice`        | integer                  |
| `dice_numbers`       | integer                  |
| `damage_bonus`       | ModifiableValueSnapshot? |
| `damage_type`        | DamageType               |
| `source_entity_uuid` | UUID                     |
| `target_entity_uuid` | UUID?                    |

#### WeaponSnapshot

| Field             | Type                     |
| ----------------- | ------------------------ |
| `uuid`          | UUID                     |
| `name`          | string                   |
| `description`   | string?                  |
| `damage_dice`   | integer                  |
| `dice_numbers`  | integer                  |
| `damage_type`   | DamageType               |
| `damage_bonus`  | ModifiableValueSnapshot? |
| `attack_bonus`  | ModifiableValueSnapshot  |
| `range`         | RangeSnapshot            |
| `properties`    | list[string]             |
| `extra_damages` | list[DamageSnapshot]     |

#### ShieldSnapshot

| Field           | Type                    |
| --------------- | ----------------------- |
| `uuid`        | UUID                    |
| `name`        | string                  |
| `description` | string?                 |
| `ac_bonus`    | ModifiableValueSnapshot |

#### ArmorSnapshot

| Field                                            | Type                    |
| ------------------------------------------------ | ----------------------- |
| `uuid`                                         | UUID                    |
| `name`                                         | string                  |
| `description`                                  | string?                 |
| `type`                                         | string                  |
| `body_part`                                    | string                  |
| `ac`                                           | ModifiableValueSnapshot |
| `max_dex_bonus`                                | ModifiableValueSnapshot |
| `strength_requirement`..`wisdom_requirement` | integer?                |
| `stealth_disadvantage`                         | boolean?                |

#### EquipmentSnapshot

| Field                    | Type                              |
| ------------------------ | --------------------------------- |
| `uuid`                 | UUID                              |
| `name`                 | string                            |
| `source_entity_uuid`   | UUID                              |
| `source_entity_name`   | string?                           |
| `helmet`..`cloak`    | ArmorSnapshot?                    |
| `weapon_main_hand`     | WeaponSnapshot?                   |
| `weapon_off_hand`      | WeaponSnapshot or ShieldSnapshot? |
| `unarmored_ac_type`    | string                            |
| `unarmored_ac`         | ModifiableValueSnapshot           |
| `ac_bonus`             | ModifiableValueSnapshot           |
| `damage_bonus`         | ModifiableValueSnapshot           |
| `attack_bonus`         | ModifiableValueSnapshot           |
| `melee_attack_bonus`   | ModifiableValueSnapshot           |
| `ranged_attack_bonus`  | ModifiableValueSnapshot           |
| `melee_damage_bonus`   | ModifiableValueSnapshot           |
| `ranged_damage_bonus`  | ModifiableValueSnapshot           |
| `unarmed_attack_bonus` | ModifiableValueSnapshot           |
| `unarmed_damage_bonus` | ModifiableValueSnapshot           |
| `unarmed_damage_type`  | DamageType                        |
| `unarmed_damage_dice`  | integer                           |
| `unarmed_dice_numbers` | integer                           |
| `unarmed_properties`   | list[string]                      |
| `armor_class`          | integer?                          |

#### AttackBonusCalculationSnapshot

| Field                        | Type                          |
| ---------------------------- | ----------------------------- |
| `weapon_slot`              | WeaponSlot                    |
| `proficiency_bonus`        | ModifiableValueSnapshot       |
| `weapon_bonus`             | ModifiableValueSnapshot       |
| `attack_bonuses`           | list[ModifiableValueSnapshot] |
| `ability_bonuses`          | list[ModifiableValueSnapshot] |
| `range`                    | RangeSnapshot                 |
| `weapon_name`              | string?                       |
| `is_unarmed`               | boolean                       |
| `is_ranged`                | boolean                       |
| `properties`               | list[string]                  |
| `has_cross_entity_effects` | boolean                       |
| `target_entity_uuid`       | UUID?                         |
| `total_bonus`              | ModifiableValueSnapshot       |
| `final_modifier`           | integer                       |

#### ACBonusCalculationSnapshot

| Field                        | Type                           |
| ---------------------------- | ------------------------------ |
| `is_unarmored`             | boolean                        |
| `unarmored_values`         | list[ModifiableValueSnapshot]? |
| `unarmored_abilities`      | list[AbilityName]?             |
| `ability_bonuses`          | list[ModifiableValueSnapshot]? |
| `ability_modifier_bonuses` | list[ModifiableValueSnapshot]? |
| `armored_values`           | list[ModifiableValueSnapshot]? |
| `max_dexterity_bonus`      | ModifiableValueSnapshot?       |
| `dexterity_bonus`          | ModifiableValueSnapshot?       |
| `dexterity_modifier_bonus` | ModifiableValueSnapshot?       |
| `combined_dexterity_bonus` | ModifiableValueSnapshot?       |
| `has_cross_entity_effects` | boolean                        |
| `target_entity_uuid`       | UUID?                          |
| `total_bonus`              | ModifiableValueSnapshot        |
| `final_ac`                 | integer                        |
| `outgoing_advantage`       | string                         |
| `outgoing_critical`        | string                         |
| `outgoing_auto_hit`        | string                         |

### Health models

#### HitDiceSnapshot

| Field                  | Type                    |
| ---------------------- | ----------------------- |
| `uuid`               | UUID                    |
| `name`               | string                  |
| `hit_dice_value`     | ModifiableValueSnapshot |
| `hit_dice_count`     | ModifiableValueSnapshot |
| `mode`               | string                  |
| `ignore_first_level` | boolean                 |
| `hit_points`         | integer                 |

#### ResistanceSnapshot

| Field           | Type   |
| --------------- | ------ |
| `damage_type` | string |
| `status`      | string |

#### HealthSnapshot

| Field                          | Type                     |
| ------------------------------ | ------------------------ |
| `uuid`                       | UUID                     |
| `name`                       | string                   |
| `source_entity_uuid`         | UUID                     |
| `source_entity_name`         | string?                  |
| `hit_dices`                  | list[HitDiceSnapshot]    |
| `max_hit_points_bonus`       | ModifiableValueSnapshot  |
| `temporary_hit_points`       | ModifiableValueSnapshot  |
| `damage_taken`               | integer                  |
| `damage_reduction`           | ModifiableValueSnapshot  |
| `resistances`                | list[ResistanceSnapshot] |
| `hit_dices_total_hit_points` | integer                  |
| `total_hit_dices_number`     | integer                  |
| `current_hit_points`         | integer?                 |
| `max_hit_points`             | integer?                 |

### Saving throw models

#### SavingThrowSnapshot

| Field                      | Type                    |
| -------------------------- | ----------------------- |
| `uuid`                   | UUID                    |
| `name`                   | string                  |
| `ability`                | AbilityName             |
| `proficiency`            | boolean                 |
| `bonus`                  | ModifiableValueSnapshot |
| `proficiency_multiplier` | float                   |
| `effective_bonus`        | integer?                |

#### SavingThrowSetSnapshot

| Field                        | Type                                   |
| ---------------------------- | -------------------------------------- |
| `uuid`                     | UUID                                   |
| `name`                     | string                                 |
| `source_entity_uuid`       | UUID                                   |
| `source_entity_name`       | string?                                |
| `saving_throws`            | dict[AbilityName, SavingThrowSnapshot] |
| `proficient_saving_throws` | list[AbilityName]                      |

#### SavingThrowBonusCalculationSnapshot

| Field                            | Type                    |
| -------------------------------- | ----------------------- |
| `ability_name`                 | AbilityName             |
| `proficiency_bonus`            | ModifiableValueSnapshot |
| `normalized_proficiency_bonus` | ModifiableValueSnapshot |
| `saving_throw_bonus`           | ModifiableValueSnapshot |
| `ability_bonus`                | ModifiableValueSnapshot |
| `ability_modifier_bonus`       | ModifiableValueSnapshot |
| `has_cross_entity_effects`     | boolean                 |
| `target_entity_uuid`           | UUID?                   |
| `total_bonus`                  | ModifiableValueSnapshot |
| `final_modifier`               | integer                 |

### ActionEconomySnapshot

| Field                       | Type                            |
| --------------------------- | ------------------------------- |
| `uuid`                    | UUID                            |
| `name`                    | string                          |
| `source_entity_uuid`      | UUID                            |
| `source_entity_name`      | string?                         |
| `actions`                 | ModifiableValueSnapshot         |
| `bonus_actions`           | ModifiableValueSnapshot         |
| `reactions`               | ModifiableValueSnapshot         |
| `movement`                | ModifiableValueSnapshot         |
| `base_actions`            | integer                         |
| `base_bonus_actions`      | integer                         |
| `base_reactions`          | integer                         |
| `base_movement`           | integer                         |
| `action_costs`            | list[NumericalModifierSnapshot] |
| `bonus_action_costs`      | list[NumericalModifierSnapshot] |
| `reaction_costs`          | list[NumericalModifierSnapshot] |
| `movement_costs`          | list[NumericalModifierSnapshot] |
| `available_actions`       | integer                         |
| `available_bonus_actions` | integer                         |
| `available_reactions`     | integer                         |
| `available_movement`      | integer                         |

### SensesSnapshot

| Field            | Type                               |
| ---------------- | ---------------------------------- |
| `entities`     | dict[UUID,`[x, y]`]              |
| `visible`      | dict[`[x, y]`, bool]             |
| `walkable`     | dict[`[x, y]`, bool]             |
| `paths`        | dict[`[x, y]`, list[`[x, y]`]] |
| `extra_senses` | list[string]                       |
| `position`     | `[x, y]`                         |
| `seen`         | list[`[x, y]`]                   |

## Request/response helpers

### EquipRequest

| Field              | Type                   |
| ------------------ | ---------------------- |
| `equipment_uuid` | UUID                   |
| `slot`           | string? (`SlotType`) |

### AddConditionRequest

| Field                  | Type     |
| ---------------------- | -------- |
| `condition_type`     | string   |
| `source_entity_uuid` | UUID     |
| `duration_type`      | string   |
| `duration_rounds`    | integer? |

### MoveRequest

| Field                    | Type       |
| ------------------------ | ---------- |
| `position`             | `[x, y]` |
| `include_paths_senses` | boolean    |

### MovementResponse

| Field           | Type                             |
| --------------- | -------------------------------- |
| `event`       | EventSnapshot                    |
| `entity`      | EntitySummary                    |
| `path_senses` | dict[`[x, y]`, SensesSnapshot] |

### AttackMetadata

| Field              | Type           |
| ------------------ | -------------- |
| `weapon_slot`    | string         |
| `attack_roll`    | integer?       |
| `attack_total`   | integer?       |
| `target_ac`      | integer?       |
| `attack_outcome` | string?        |
| `damage_rolls`   | list[integer]? |
| `total_damage`   | integer?       |
| `damage_types`   | list[string]?  |

### AttackResponse

| Field        | Type           |
| ------------ | -------------- |
| `event`    | EventSnapshot  |
| `metadata` | AttackMetadata |

### CreateTileRequest

| Field         | Type                                       |
| ------------- | ------------------------------------------ |
| `position`  | `[x, y]`                                 |
| `tile_type` | string (`floor`, `wall`, or `water`) |

## Event models

### EventSnapshot

| Field                  | Type                  |
| ---------------------- | --------------------- |
| `uuid`               | UUID                  |
| `name`               | string                |
| `lineage_uuid`       | UUID                  |
| `timestamp`          | string (ISO datetime) |
| `event_type`         | string                |
| `phase`              | string                |
| `modified`           | boolean               |
| `canceled`           | boolean               |
| `parent_event`       | UUID?                 |
| `status_message`     | string?               |
| `source_entity_uuid` | UUID                  |
| `source_entity_name` | string?               |
| `target_entity_uuid` | UUID?                 |
| `target_entity_name` | string?               |
| `child_events`       | list[EventSnapshot]   |

### D20EventSnapshot

Adds to `EventSnapshot`:

| Field         | Type                               |
| ------------- | ---------------------------------- |
| `dc`        | integer or ModifiableValueSnapshot |
| `bonus`     | integer or ModifiableValueSnapshot |
| `dice_roll` | object                             |
| `result`    | boolean?                           |

### SavingThrowEventSnapshot

Adds `ability_name` (AbilityName).

### SkillCheckEventSnapshot

Adds `skill_name` (SkillName).

### AttackEventSnapshot

| Field              | Type                     |
| ------------------ | ------------------------ |
| `weapon_slot`    | WeaponSlot               |
| `range`          | RangeSnapshot?           |
| `attack_bonus`   | ModifiableValueSnapshot? |
| `ac`             | ModifiableValueSnapshot? |
| `dice_roll`      | object?                  |
| `attack_outcome` | string?                  |
| `damages`        | list[DamageSnapshot]?    |
| `damage_rolls`   | list[object]?            |

## Tile models

### TileSummary

| Field           | Type       |
| --------------- | ---------- |
| `uuid`        | UUID       |
| `name`        | string     |
| `position`    | `[x, y]` |
| `walkable`    | boolean    |
| `visible`     | boolean    |
| `sprite_name` | string?    |

### TileSnapshot

| Field           | Type       |
| --------------- | ---------- |
| `uuid`        | UUID       |
| `name`        | string     |
| `position`    | `[x, y]` |
| `walkable`    | boolean    |
| `visible`     | boolean    |
| `sprite_name` | string?    |
| `entities`    | list[UUID] |

### GridSnapshot

| Field      | Type                          |
| ---------- | ----------------------------- |
| `width`  | integer                       |
| `height` | integer                       |
| `tiles`  | dict[`[x, y]`, TileSummary] |

## Value & modifier helpers

### ModifiableValueSnapshot

| Field                  | Type                               |
| ---------------------- | ---------------------------------- |
| `uuid`               | UUID                               |
| `name`               | string                             |
| `source_entity_uuid` | UUID                               |
| `source_entity_name` | string?                            |
| `target_entity_uuid` | UUID?                              |
| `target_entity_name` | string?                            |
| `score`              | integer                            |
| `normalized_score`   | integer                            |
| `min_value`          | integer?                           |
| `max_value`          | integer?                           |
| `advantage`          | string                             |
| `outgoing_advantage` | string                             |
| `critical`           | string                             |
| `outgoing_critical`  | string                             |
| `auto_hit`           | string                             |
| `outgoing_auto_hit`  | string                             |
| `resistances`        | dict[DamageType, ResistanceStatus] |
| `base_modifier`      | NumericalModifierSnapshot?         |
| `channels`           | list[ModifierChannelSnapshot]      |

### ModifierChannelSnapshot

| Field                    | Type                             |
| ------------------------ | -------------------------------- |
| `name`                 | string                           |
| `is_outgoing`          | boolean                          |
| `is_contextual`        | boolean                          |
| `value_modifiers`      | list[NumericalModifierSnapshot]  |
| `min_constraints`      | list[NumericalModifierSnapshot]  |
| `max_constraints`      | list[NumericalModifierSnapshot]  |
| `advantage_modifiers`  | list[AdvantageModifierSnapshot]  |
| `critical_modifiers`   | list[CriticalModifierSnapshot]   |
| `auto_hit_modifiers`   | list[AutoHitModifierSnapshot]    |
| `size_modifiers`       | list[SizeModifierSnapshot]       |
| `resistance_modifiers` | list[ResistanceModifierSnapshot] |
| `score`                | integer                          |
| `normalized_score`     | integer                          |
| `min_value`            | integer?                         |
| `max_value`            | integer?                         |

### NumericalModifierSnapshot

| Field                  | Type    |
| ---------------------- | ------- |
| `uuid`               | UUID    |
| `name`               | string? |
| `source_entity_uuid` | UUID    |
| `source_entity_name` | string? |
| `target_entity_uuid` | UUID?   |
| `target_entity_name` | string? |
| `value`              | integer |
| `normalized_value`   | integer |

Other modifier snapshots (`AdvantageModifierSnapshot`, `CriticalModifierSnapshot`, `AutoHitModifierSnapshot`, `ResistanceModifierSnapshot`, `SizeModifierSnapshot`) follow the same pattern with a `value` field describing the specific status.

---

This document should be used alongside the [API route guide](API.md) to build well-typed clients.
