# TODO: use https://pypi.python.org/pypi/enum34

BUILDING = 0
COMPLETE = 1
DELETED = 2
FAILED = 3
CANCELED = 4


def to_str(number):
    """
    Convert a build state ID number to a string.

    :param int number: build state ID, eg. 1
    :returns: state name like eg. "BUILDING", or "(unknown)" if we don't know
              the name of this build state ID number.
    """
    states = globals()
    for name, value in states.items():
        if number == value and name.isalpha() and name.isupper():
            return name
    return '(unknown state %d)' % number
