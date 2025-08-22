import random
from uuid import uuid4

import pytest
from pydantic import ValidationError

from dnd.core.dice import Dice, RollType, AttackOutcome, DiceRoll
from dnd.core.values import ModifiableValue, AdvantageStatus, CriticalStatus, AutoHitStatus
from dnd.entity import determine_attack_outcome


def make_bonus(value=0):
    """Helper to create a basic ModifiableValue with given base value."""
    return ModifiableValue.create(source_entity_uuid=uuid4(), base_value=value, value_name="bonus")


def test_damage_roll_requires_attack_outcome():
    bonus = make_bonus()
    with pytest.raises(ValueError):
        Dice(count=1, value=6, bonus=bonus, roll_type=RollType.DAMAGE)


def test_non_damage_roll_rejects_attack_outcome():
    bonus = make_bonus()
    with pytest.raises(ValueError):
        Dice(count=1, value=20, bonus=bonus, roll_type=RollType.ATTACK, attack_outcome=AttackOutcome.HIT)


def test_non_damage_roll_multiple_dice_invalid():
    bonus = make_bonus()
    with pytest.raises(ValueError):
        Dice(count=2, value=20, bonus=bonus, roll_type=RollType.ATTACK)


def test_damage_roll_crit_doubles_dice(monkeypatch):
    bonus = make_bonus(2)
    dice = Dice(count=2, value=6, bonus=bonus, roll_type=RollType.DAMAGE, attack_outcome=AttackOutcome.CRIT)
    rolls = [1, 2, 3, 4]

    def fake_randint(a, b):
        return rolls.pop(0)

    monkeypatch.setattr("dnd.core.dice.random.randint", fake_randint)
    roll = dice.roll
    assert roll.results == [1, 2, 3, 4]
    assert roll.total == sum([1, 2, 3, 4]) + bonus.normalized_score


def test_attack_roll_applies_bonus(monkeypatch):
    bonus = make_bonus(3)
    dice = Dice(count=1, value=20, bonus=bonus, roll_type=RollType.ATTACK)
    monkeypatch.setattr("dnd.core.dice.random.randint", lambda a, b: 10)
    roll = dice.roll
    assert roll.results == 10
    assert roll.total == 10 + bonus.normalized_score


@pytest.mark.parametrize(
    "roll,total,ac,expected",
    [
        (1, 1, 10, AttackOutcome.CRIT_MISS),
        (20, 20, 10, AttackOutcome.CRIT),
        (15, 17, 16, AttackOutcome.HIT),
        (5, 7, 10, AttackOutcome.MISS),
    ],
)
def test_determine_attack_outcome_basic(roll, total, ac, expected):
    dice_roll = DiceRoll(
        dice_uuid=uuid4(),
        roll_type=RollType.ATTACK,
        results=roll,
        total=total,
        bonus=total - roll,
        advantage_status=AdvantageStatus.NONE,
        critical_status=CriticalStatus.NONE,
        auto_hit_status=AutoHitStatus.NONE,
        source_entity_uuid=uuid4(),
    )
    assert determine_attack_outcome(dice_roll, ac) == expected


def test_determine_attack_outcome_auto_statuses():
    dice_roll = DiceRoll(
        dice_uuid=uuid4(),
        roll_type=RollType.ATTACK,
        results=10,
        total=10,
        bonus=0,
        advantage_status=AdvantageStatus.NONE,
        critical_status=CriticalStatus.AUTOCRIT,
        auto_hit_status=AutoHitStatus.AUTOHIT,
        source_entity_uuid=uuid4(),
    )
    assert determine_attack_outcome(dice_roll, 30) == AttackOutcome.CRIT

    dice_roll = dice_roll.model_copy(update={
        "critical_status": CriticalStatus.NONE,
        "auto_hit_status": AutoHitStatus.AUTOHIT,
    })
    assert determine_attack_outcome(dice_roll, 30) == AttackOutcome.HIT

    dice_roll = dice_roll.model_copy(update={
        "auto_hit_status": AutoHitStatus.AUTOMISS,
    })
    assert determine_attack_outcome(dice_roll, 1) == AttackOutcome.MISS


def test_custom_dice_notation_parsing_failure():
    bonus = make_bonus()
    with pytest.raises(ValidationError):
        Dice(
            count="2d6+3",
            value=6,
            bonus=bonus,
            roll_type=RollType.DAMAGE,
            attack_outcome=AttackOutcome.HIT,
        )


def test_determine_attack_outcome_critical_adjustments():
    dice_roll = DiceRoll(
        dice_uuid=uuid4(),
        roll_type=RollType.ATTACK,
        results=15,
        total=18,
        bonus=3,
        advantage_status=AdvantageStatus.NONE,
        critical_status=CriticalStatus.AUTOCRIT,
        auto_hit_status=AutoHitStatus.NONE,
        source_entity_uuid=uuid4(),
    )
    assert determine_attack_outcome(dice_roll, 18) == AttackOutcome.CRIT

    dice_roll = dice_roll.model_copy(update={"results": 1, "total": 1})
    assert determine_attack_outcome(dice_roll, 0) == AttackOutcome.CRIT_MISS


def test_average_roll_calculation(monkeypatch):
    bonus = make_bonus(2)
    sequence = [1, 2, 3, 4, 5, 6]

    def fake_randint(a, b):
        val = sequence.pop(0)
        sequence.append(val)
        return val

    monkeypatch.setattr("dnd.core.dice.random.randint", fake_randint)

    rolls = []
    for _ in range(6):
        dice = Dice(
            count=1,
            value=6,
            bonus=bonus,
            roll_type=RollType.DAMAGE,
            attack_outcome=AttackOutcome.HIT,
        )
        rolls.append(dice.roll.total)

    expected_avg = (6 + 1) / 2 + bonus.normalized_score
    assert sum(rolls) / len(rolls) == expected_avg