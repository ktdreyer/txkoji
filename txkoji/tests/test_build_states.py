from txkoji import build_states


def test_building():
    assert build_states.BUILDING == 0


def test_complete():
    assert build_states.COMPLETE == 1


def test_deleted():
    assert build_states.DELETED == 2


def test_failed():
    assert build_states.FAILED == 3


def test_canceled():
    assert build_states.CANCELED == 4
