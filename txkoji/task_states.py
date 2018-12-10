FREE = 0
OPEN = 1
CLOSED = 2
CANCELED = 3
ASSIGNED = 4
FAILED = 5


# Groups:
ACTIVE_GROUP = (FREE, OPEN, ASSIGNED)
DONE_GROUP = (CLOSED, CANCELED, FAILED)


def to_str(number):
    """
    Convert a task state ID number to a string.

    :param int number: task state ID, eg. 1
    :returns: state name like eg. "OPEN", or "(unknown)" if we don't know the
              name of this task state ID number.
    """
    states = globals()
    for name, value in states.items():
        if number == value and name.isalpha() and name.isupper():
            return name
    return '(unknown state %d)' % number
