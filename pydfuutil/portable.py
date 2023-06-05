from time import sleep


def milli_sleep(msec: int) -> None:
    """
    :param msec: sleep timeout in milliseconds
    :return: None
    """
    sleep(int(msec / 1000))
