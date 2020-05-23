#!/usr/bin/env python2

import json
import random
import pytest


RANDOM_FRAME = []
for frameLen in range(1, 100, 5):
    for run in range(100):
        frame = None
        while (not frame) or (frame in RANDOM_FRAME):
            frame = []
            for _ in range(frameLen):
                frame += [random.randint(0x00, 0xff)]
        RANDOM_FRAME.append(frame)
RANDOM_FRAME = [json.dumps(f) for f in RANDOM_FRAME]


@pytest.fixture(params=RANDOM_FRAME)
def random_frame(request):
    return request.param


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
