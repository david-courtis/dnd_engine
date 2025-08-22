import pytest
from uuid import uuid4

from dnd.core.dice import (
    DiceRoll,
    RollType,
    AdvantageStatus,
    CriticalStatus,
    AutoHitStatus,
    AttackOutcome,
)
from dnd.entity import determine_attack_outcome


@pytest.mark.parametrize(
    "roll_kwargs, ac, expected",
    [
        (  # auto miss
            {
                "results": 10,
                "total": 10,
                "auto_hit_status": AutoHitStatus.AUTOMISS,
            },
            5,
            AttackOutcome.MISS,
        ),
        (  # auto hit crit
            {
                "results": 20,
                "total": 20,
                "auto_hit_status": AutoHitStatus.AUTOHIT,
            },
            15,
            AttackOutcome.CRIT,
        ),
        (  # auto hit non crit
            {
                "results": 5,
                "total": 5,
                "auto_hit_status": AutoHitStatus.AUTOHIT,
            },
            2,
            AttackOutcome.HIT,
        ),
        (  # natural one
            {
                "results": 1,
                "total": 1,
            },
            5,
            AttackOutcome.CRIT_MISS,
        ),
        (  # critical hit by roll
            {
                "results": 20,
                "total": 20,
            },
            10,
            AttackOutcome.CRIT,
        ),
        (  # normal hit
            {
                "results": 15,
                "total": 15,
            },
            10,
            AttackOutcome.HIT,
        ),
        (  # miss
            {
                "results": 10,
                "total": 10,
            },
            15,
            AttackOutcome.MISS,
        ),
    ],
)
def test_determine_attack_outcome_all_branches(roll_kwargs, ac, expected):
    roll = DiceRoll(
        dice_uuid=uuid4(),
        roll_type=RollType.ATTACK,
        results=roll_kwargs["results"],
        total=roll_kwargs["total"],
        bonus=0,
        advantage_status=AdvantageStatus.NONE,
        critical_status=roll_kwargs.get("critical_status", CriticalStatus.NONE),
        auto_hit_status=roll_kwargs.get("auto_hit_status", AutoHitStatus.NONE),
        source_entity_uuid=uuid4(),
    )
    assert determine_attack_outcome(roll, ac) == expected
