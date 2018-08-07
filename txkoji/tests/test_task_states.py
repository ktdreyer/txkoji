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


def test_done_group():
    assert task_states.CLOSED in task_states.DONE_GROUP
    assert task_states.CANCELED in task_states.DONE_GROUP
    assert task_states.FAILED in task_states.DONE_GROUP
