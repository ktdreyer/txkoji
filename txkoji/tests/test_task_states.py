from txkoji import task_states


def test_free():
    assert task_states.FREE == 0


def test_open():
    assert task_states.OPEN == 1


def test_closed():
    assert task_states.CLOSED == 2


def test_canceled():
    assert task_states.CANCELED == 3


def test_assigned():
    assert task_states.ASSIGNED == 4


def test_failed():
    assert task_states.FAILED == 5


def test_active_group():
    assert task_states.FREE in task_states.ACTIVE_GROUP
    assert task_states.OPEN in task_states.ACTIVE_GROUP
    assert task_states.ASSIGNED in task_states.ACTIVE_GROUP


def test_done_group():
    assert task_states.CLOSED in task_states.DONE_GROUP
    assert task_states.CANCELED in task_states.DONE_GROUP
    assert task_states.FAILED in task_states.DONE_GROUP


def test_free_to_str():
    assert task_states.to_str(0) == 'FREE'


def test_open_to_str():
    assert task_states.to_str(1) == 'OPEN'


def test_closed_to_str():
    assert task_states.to_str(2) == 'CLOSED'


def test_canceled_to_str():
    assert task_states.to_str(3) == 'CANCELED'


def test_assigned_to_str():
    assert task_states.to_str(4) == 'ASSIGNED'


def test_failed_to_str():
    assert task_states.to_str(5) == 'FAILED'


def test_unknown_to_str():
    assert task_states.to_str(999) == '(unknown state 999)'
