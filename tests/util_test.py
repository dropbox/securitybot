from unittest2 import TestCase

from datetime import datetime, timedelta
import securitybot.util as util

class VarTest(TestCase):
    def test_hours(self):
        assert util.OPENING_HOUR < util.CLOSING_HOUR, 'Closing hour must be after opening hour.'

class NamedTupleTest(TestCase):
    def test_empty(self):
        tup = util.tuple_builder()
        assert tup.answer is None
        assert tup.text == ''

    def test_full(self):
        tup = util.tuple_builder(True, 'Yes')
        assert tup.answer is True
        assert tup.text == 'Yes'

class BusinessHoursTest(TestCase):
    def test_weekday(self):
        '''Test business hours during a weekday.'''
        # 18 July 2016 is a Monday. If this changes, please contact the IERS.
        morning = datetime(year=2016, month=7, day=18, hour=util.OPENING_HOUR,
                           tzinfo=util.LOCAL_TZ)
        assert util.during_business_hours(morning)
        noon = datetime(year=2016, month=7, day=18, hour=12, tzinfo=util.LOCAL_TZ)
        assert util.during_business_hours(noon), \
            'This may fail if noon is no longer during business hours.'
        afternoon = datetime(year=2016, month=7, day=18, hour=util.CLOSING_HOUR - 1,
                             minute=59, second=59, tzinfo=util.LOCAL_TZ)
        assert util.during_business_hours(afternoon)

        breakfast = datetime(year=2016, month=7, day=18, hour=util.OPENING_HOUR - 1, minute=59,
                             second=59, tzinfo=util.LOCAL_TZ)
        assert not util.during_business_hours(breakfast)
        supper = datetime(year=2016, month=7, day=18, hour=util.CLOSING_HOUR,
                          tzinfo=util.LOCAL_TZ)
        assert not util.during_business_hours(supper)

    def test_weekend(self):
        '''Test "business hours" during a weekend.'''
        # As such, 17 July 2016 is a Sunday.
        sunday_morning = datetime(year=2016, month=7, day=17, hour=util.OPENING_HOUR,
                                  tzinfo=util.LOCAL_TZ)
        assert not util.during_business_hours(sunday_morning)

class ExpirationTimeTest(TestCase):
    def test_same_day(self):
        '''Test time delta within the same day.'''
        date = datetime(year=2016, month=7, day=18, hour=util.OPENING_HOUR, tzinfo=util.LOCAL_TZ)
        td = timedelta(hours=((util.CLOSING_HOUR - util.OPENING_HOUR) % 24) / 2)
        after = date + td
        assert util.get_expiration_time(date, td) == after

    def test_next_weekday(self):
        '''Test time delta overnight.'''
        date = datetime(year=2016, month=7, day=18, hour=util.CLOSING_HOUR - 1,
                        tzinfo=util.LOCAL_TZ)
        next_date = datetime(year=2016, month=7, day=19, hour=util.OPENING_HOUR + 1,
                             tzinfo=util.LOCAL_TZ)
        assert util.get_expiration_time(date, timedelta(hours=2)) == next_date

    def test_edge_weekday(self):
        '''Test time delta overnight just barely within range.'''
        date = datetime(year=2016, month=7, day=18, hour=util.CLOSING_HOUR - 1, minute=59,
                        second=59, tzinfo=util.LOCAL_TZ)
        td = timedelta(seconds=1)
        after = datetime(year=2016, month=7, day=19, hour=util.OPENING_HOUR,
                         tzinfo=util.LOCAL_TZ)
        assert util.get_expiration_time(date, td) == after

    def test_next_weekend(self):
        '''Test time delta over a weekend.'''
        date = datetime(year=2016, month=7, day=15, hour=util.CLOSING_HOUR - 1,
                        tzinfo=util.LOCAL_TZ)
        next_date = datetime(year=2016, month=7, day=18, hour=util.OPENING_HOUR + 1,
                             tzinfo=util.LOCAL_TZ)
        assert util.get_expiration_time(date, timedelta(hours=2)) == next_date

    def test_edge_weekend(self):
        '''Test time delta over a weekend just barely within range.'''
        date = datetime(year=2016, month=7, day=15, hour=util.CLOSING_HOUR - 1, minute=59,
                        second=59, tzinfo=util.LOCAL_TZ)
        td = timedelta(seconds=1)
        after = datetime(year=2016, month=7, day=18, hour=util.OPENING_HOUR,
                         tzinfo=util.LOCAL_TZ)
        assert util.get_expiration_time(date, td) == after
