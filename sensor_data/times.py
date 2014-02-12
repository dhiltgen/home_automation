#
from datetime import datetime, timedelta


"""
Utility routines for getting common DateTimes
"""
_week = timedelta(weeks=1)
_year = timedelta(weeks=52)
_day = timedelta(days=1)

def day_ago(t1=None):
    """
    :param t1: The starting DateTime (omit for Now)
    :returns: a DateTime for 1 day prior to t1
    """
    if t1 is None:
        t1 = datetime.utcnow().replace(tzinfo=utc)
    return t1 - _day

def week_ago(t1=None):
    """
    :param t1: The starting DateTime (omit for Now)
    :returns: a DateTime for 1 week prior to t1
    """
    if t1 is None:
        t1 = datetime.utcnow().replace(tzinfo=utc)
    return t1 - _week

def year_ago(t1=None):
    """
    :param t1: The starting DateTime (omit for Now)
    :returns: a DateTime for 1 year prior to t1
    """
    if t1 is None:
        t1 = datetime.utcnow().replace(tzinfo=utc)
    return t1 - _year

