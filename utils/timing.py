import datetime


def get_on_weekday(x):
    """
    Return on_weekday after checking it is in the right interval (0-6)
    """
    x = int(x)  # just in case a string was entered
    if x in [0,1,2,3,4,5,6]:
        return x
    else:
        raise Exception('ON_WEEKDAY should range from 0 to 6')


def get_on_day(x):
    """
    Return on_weekday after checking it is in the right interval (0-6)
    """
    x = int(x)  # just in case a string was entered
    if x in list(range(1,29)):
        return x
    else:
        raise Exception('ON_DAT should range from 1 to 28')


def get_hour_minute(at_time):
    """
    Convert the AT_TIME config variable from string to a couple of integers (hour, minutes)
    """
    if isinstance(at_time, int):
        # in this case assume there are no minutes:
        hours = at_time
        minutes = 0
    elif isinstance(at_time,str):
        # convert to integers:
        at_time = [int(x) for x in at_time.split(':')]
        if len(at_time) == 1:
            hours = at_time[0]
            minutes = 0
        else:
            hours = at_time[0]
            minutes = at_time[1]
    if hours > 23 or minutes > 59:
        raise Exception('AT_HOUR should have hours ranging from 0 to 23 and minutes ranging from 0 to 59')
    return [hours, minutes]


def retry_info():
    retry_for_funds = {}  # for funds error (insufficient balance)
    retry_for_network = {}  # generic network error

    # first element is the maximum number of attempts, second element is the waiting time in seconds
    retry_for_funds['minutely'] = [3, 10]  # for testing purpose
    retry_for_funds['daily'] = [1, 12*60*60]  # check only once after 12 hours
    retry_for_funds['weekly'] = [2, 24*60*60]
    retry_for_funds['bi-weekly'] = [2, 24*60*60]
    retry_for_funds['monthly'] = [3, 24*60*60]

    # first element is the maximum number of attempts, second element is the waiting time in seconds
    retry_for_network['minutely'] = [3, 10]  # for testing purpose
    retry_for_network['daily'] = [12, 1*60*60]  # check every hour for the next 12 hours
    retry_for_network['weekly'] = [24, 1*60*60]
    retry_for_network['bi-weekly'] = [24, 1*60*60]
    retry_for_network['monthly'] = [24, 1*60*60]

    return retry_for_funds, retry_for_network