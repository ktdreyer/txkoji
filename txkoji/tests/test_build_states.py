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


def test_building_to_str():
    assert build_states.to_str(0) == 'BUILDING'


def test_complete_to_str():
    assert build_states.to_str(1) == 'COMPLETE'


def test_deleted_to_str():
    assert build_states.to_str(2) == 'DELETED'


def test_failed_to_str():
    assert build_states.to_str(3) == 'FAILED'


def test_canceled_to_str():
    assert build_states.to_str(4) == 'CANCELED'


def test_unknown_to_str():
    assert build_states.to_str(999) == '(unknown state 999)'
