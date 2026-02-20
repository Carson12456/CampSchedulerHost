from pathlib import Path

import pytest

from activities import get_all_activities
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json


@pytest.fixture(scope="session")
def troops():
    data_file = Path(__file__).resolve().parent.parent / "data" / "troops" / "tc_week1_troops.json"
    return load_troops_from_json(str(data_file))


@pytest.fixture(scope="session")
def schedule(troops):
    scheduler = ConstrainedScheduler(troops, get_all_activities())
    return scheduler.schedule_all()

