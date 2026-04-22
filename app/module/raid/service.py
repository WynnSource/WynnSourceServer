import datetime
from collections import defaultdict

from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.scheduler import SCHEDULER
from app.core.security.model import User
from app.module.pool.service import calculate_submission_weight

from .config import FUZZY_WINDOW, GAMBIT_COUNT, GAMBIT_REGION, GAMBIT_SEPARATOR, get_gambit_rotation
from .model import Gambit, GambitRepository, GambitSubmission, GambitSubmissionRepository
from .schema import GambitSubmissionSchema


async def submit_gambit_data(session: AsyncSession, data: GambitSubmissionSchema, user: User):
    # Timestamp validation (±10 minutes)
    now = datetime.datetime.now(tz=datetime.UTC)
    if abs(now - data.client_timestamp) > datetime.timedelta(minutes=10):
        raise ValueError("Client timestamp is too far from server time")

    gambit_repo = GambitRepository(session)
    submission_repo = GambitSubmissionRepository(session)

    rotation = get_gambit_rotation(data.client_timestamp)
    gambit = await gambit_repo.get_or_create_gambit(
        region=GAMBIT_REGION,
        rotation=rotation,
    )

    fuzzy = (
        abs(gambit.rotation_start - data.client_timestamp) < FUZZY_WINDOW
        or abs(gambit.rotation_end - data.client_timestamp) < FUZZY_WINDOW
    )

    submission = GambitSubmission(
        user_id=user.id,
        client_timestamp=data.client_timestamp,
        mod_version=data.mod_version,
        gambit_names=[g.name for g in data.gambits],
        gambit_descriptions=[g.description for g in data.gambits],
        weight=calculate_submission_weight(user, fuzzy),
    )

    # One submission per user per gambit rotation
    existing = await submission_repo.get_user_submission_for_gambit(user.id, gambit.id)
    is_first_of_rotation = existing is None

    if existing is not None:
        await submission_repo.delete(existing)

    submission.gambit = gambit
    await submission_repo.save(submission)

    # Force UPDATE via SQL; see pool/service.py for rationale.
    await session.execute(sql_update(Gambit).where(Gambit.id == gambit.id).values(needs_recalc=True))

    if is_first_of_rotation:
        _schedule_instant_gambit_recalc(gambit.region, gambit.rotation_start)


def _schedule_instant_gambit_recalc(region: str, rotation_start: datetime.datetime) -> None:
    """Schedule a one-off recalc for the current gambit on first-of-rotation submission.

    Debounced by job id; delayed 2s so the submit transaction commits first.
    """
    run_date = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(seconds=2)
    SCHEDULER.add_job(
        compute_gambit_consensus,
        trigger=DateTrigger(run_date=run_date),
        id=f"instant_recalc:gambit:{region}:{rotation_start.isoformat()}",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=60,
        max_instances=1,
    )


@SCHEDULER.scheduled_job(
    IntervalTrigger(minutes=5),
    id="compute_gambit_consensus",
    misfire_grace_time=60,
    coalesce=True,
)
async def compute_gambit_consensus() -> int:
    async with get_session() as session:
        gambit_repo = GambitRepository(session)
        rotation = get_gambit_rotation(datetime.datetime.now(tz=datetime.UTC))
        active_gambits = await gambit_repo.list_gambits(
            region=GAMBIT_REGION,
            rotation_start=rotation.start,
            needs_recalc=True,
            for_update=True,
        )

        for gambit in active_gambits:
            submissions = gambit.submissions

            if not submissions:
                gambit.consensus_data = []
                gambit.confidence = 0.0
                gambit.needs_recalc = False
                continue

            # Aggregate weighted votes per slot position (0-3)
            # Users submit the first N gambits in order, so slot index is meaningful
            # slot_weights[slot]["name|desc"] = total_weight
            slot_weights: list[dict[str, float]] = [defaultdict(float) for _ in range(GAMBIT_COUNT)]

            for sub in submissions:
                for slot, (name, desc) in enumerate(zip(sub.gambit_names, sub.gambit_descriptions)):
                    key = f"{name}{GAMBIT_SEPARATOR}{desc}"
                    slot_weights[slot][key] += sub.weight

            # For each slot, pick the entry with the highest weight (if any votes exist)
            consensus_data: list[str] = []
            slot_confidences: list[float] = []

            for slot in range(GAMBIT_COUNT):
                if not slot_weights[slot]:
                    continue

                best_entry = max(slot_weights[slot], key=slot_weights[slot].__getitem__)
                best_weight = slot_weights[slot][best_entry]
                total_slot_weight = sum(slot_weights[slot].values())

                consensus_data.append(best_entry)
                slot_confidences.append(best_weight / total_slot_weight if total_slot_weight > 0 else 0.0)

            gambit.consensus_data = consensus_data
            gambit.confidence = round(sum(slot_confidences) / len(slot_confidences) if slot_confidences else 0.0, 4)
            gambit.needs_recalc = False

        return len(active_gambits)


async def get_gambit_consensus(
    session: AsyncSession,
    rotation_start: datetime.datetime,
) -> tuple[list[tuple[str, str]], float] | None:
    """Returns ([(name, description), ...], confidence) or None if no data."""
    gambit_repo = GambitRepository(session)
    gambits = await gambit_repo.list_gambits(
        region=GAMBIT_REGION,
        rotation_start=rotation_start,
    )

    if not gambits:
        return None

    gambit = gambits[0]
    if not gambit.consensus_data:
        return [], gambit.confidence

    # Decode "name|description" entries
    pairs: list[tuple[str, str]] = []
    for entry in gambit.consensus_data:
        name, _, desc = entry.partition(GAMBIT_SEPARATOR)
        pairs.append((name, desc))

    return pairs, gambit.confidence
