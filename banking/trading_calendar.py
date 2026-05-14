from __future__ import annotations
'''
Created on 02.02.2026

@author: Wolfg
'''
"""
Created on 02.02.2026

@author: Wolfg
"""

from enum import Enum
from functools import lru_cache
from datetime import date, timedelta
from typing import Optional, Union, Tuple, Type

# Third-party imports
import pandas as pd
from pandas.tseries.offsets import CustomBusinessDay


class Exchange(Enum):
    """
    Enumeration of supported stock exchanges.
    """
    XETRA = "XETRA"


class TradingCalendar:
    """
    Abstract base class for exchange-specific trading calendars.

    Provides utility methods for:
    - generating business day offsets
    - validating trading days
    - adjusting date ranges
    - retrieving trading periods
    """

    # Trading week definition (Monday to Friday)
    weekmask: str = "Mon Tue Wed Thu Fri"

    @classmethod
    def business_day(cls, start_year: int, end_year: int) -> CustomBusinessDay:
        """
        Create a pandas CustomBusinessDay object using the exchange holidays.

        Args:
            start_year: First year included in holiday calculation.
            end_year: Last year included in holiday calculation.

        Returns:
            Configured CustomBusinessDay instance.
        """
        return CustomBusinessDay(
            holidays=cls.holidays(start_year, end_year),
            weekmask=cls.weekmask,
        )

    @classmethod
    def holidays(cls, start_year: int, end_year: int) -> list[pd.Timestamp]:
        """
        Return exchange holidays for the given period.

        Must be implemented by subclasses.

        Args:
            start_year: Start year.
            end_year: End year.

        Raises:
            NotImplementedError:
                If subclass does not implement this method.
        """
        raise NotImplementedError

    @classmethod
    def adjust_period(
        cls,
        start: Union[str, pd.Timestamp],
        end: Union[str, pd.Timestamp],
        bday: Optional[CustomBusinessDay] = None,
        settlement_days: int = 0,
        as_str: bool = True,
    ) -> Tuple[Union[str, pd.Timestamp], Union[str, pd.Timestamp]]:
        """
        Adjust a date range to valid trading days.

        The method:
        1. Normalizes the dates
        2. Rolls dates to valid trading days
        3. Applies settlement offset if required
        4. Validates the resulting period

        Args:
            start: Start date.
            end: End date.
            bday: Optional preconfigured business day object.
            settlement_days: Settlement offset in trading days.
            as_str: Return values as strings if True.

        Returns:
            Tuple containing adjusted start and end dates.

        Raises:
            ValueError:
                If no valid trading period exists.
        """

        # Normalize timestamps to midnight
        start = pd.Timestamp(start).normalize()
        end = pd.Timestamp(end).normalize()

        # Create business day definition if not supplied
        if bday is None:
            bday = cls.business_day(start.year, end.year)

        # Roll dates to valid trading days
        start = bday.rollforward(start)
        end = bday.rollback(end)

        # Apply settlement adjustment
        if settlement_days:
            start += settlement_days * bday
            end += settlement_days * bday

            # Revalidate after settlement shift
            start = bday.rollforward(start)
            end = bday.rollback(end)

        # Validate resulting range
        if start > end:
            raise ValueError("No valid trading period")

        # Return formatted strings if requested
        if as_str:
            return (
                start.strftime("%Y-%m-%d"),
                end.strftime("%Y-%m-%d"),
            )

        return start, end

    @classmethod
    def last_trading_period(cls):
        """
        Return the previous two valid trading days.

        Useful for retrieving the latest completed trading period.

        Returns:
            Tuple containing:
            - previous trading day
            - last trading day
        """

        today = pd.Timestamp.today().normalize()

        # Safe year range for holiday generation
        # Handles year transitions correctly
        bday = cls.business_day(today.year - 1, today.year)

        # Determine most recent completed trading day
        last_trading_day = bday.rollback(today - pd.Timedelta(days=1))

        # Determine trading day before that
        prev_trading_day = last_trading_day - bday

        return cls.adjust_period(
            prev_trading_day,
            last_trading_day,
            bday=bday,
        )

    @classmethod
    def is_trading_day(
        cls,
        dt: Union[str, pd.Timestamp],
        bday: Optional[CustomBusinessDay] = None,
    ) -> bool:
        """
        Check whether a given date is a valid trading day.

        Args:
            dt: Date to validate.
            bday: Optional business day definition.

        Returns:
            True if date is a trading day, otherwise False.
        """

        dt = pd.Timestamp(dt).normalize()

        if bday is None:
            bday = cls.business_day(dt.year, dt.year)

        return bday.is_on_offset(dt)

    @classmethod
    def trading_days(
        cls,
        start: Union[str, pd.Timestamp],
        end: Union[str, pd.Timestamp],
        bday: Optional[CustomBusinessDay] = None,
        as_str: bool = False,
    ) -> list[Union[str, pd.Timestamp]]:
        """
        Generate all trading days within a period.

        Args:
            start: Start date.
            end: End date.
            bday: Optional business day definition.
            as_str: Return dates as strings if True.

        Returns:
            List of trading days.
        """

        start = pd.Timestamp(start)
        end = pd.Timestamp(end)

        if bday is None:
            bday = cls.business_day(start.year, end.year)

        # Generate valid trading dates only
        days = pd.date_range(
            start=start,
            end=end,
            freq=bday,
        )

        if as_str:
            return [d.strftime("%Y-%m-%d") for d in days]

        return list(days)


class XetraCalendar(TradingCalendar):
    """
    Trading calendar implementation for the XETRA exchange.
    """

    @staticmethod
    @lru_cache(maxsize=None)
    def _easter_sunday(year: int) -> date:
        """
        Calculate Easter Sunday using the Anonymous Gregorian algorithm.

        Args:
            year: Target year.

        Returns:
            Easter Sunday as date object.
        """

        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451

        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1

        return date(year, month, day)

    @classmethod
    @lru_cache(maxsize=None)
    def _holidays_for_year(cls, year: int) -> list[pd.Timestamp]:
        """
        Generate XETRA holidays for a single year.

        Args:
            year: Target year.

        Returns:
            List of holiday timestamps.
        """

        easter = cls._easter_sunday(year)

        return [
            pd.Timestamp(year, 1, 1),   # New Year's Day
            pd.Timestamp(year, 5, 1),   # Labour Day
            pd.Timestamp(year, 12, 25), # Christmas Day
            pd.Timestamp(year, 12, 26), # Boxing Day

            # Easter-related holidays
            pd.Timestamp(easter - timedelta(days=2)),  # Good Friday
            pd.Timestamp(easter + timedelta(days=1)),  # Easter Monday
        ]

    @classmethod
    @lru_cache(maxsize=None)
    def holidays(
        cls,
        start_year: int,
        end_year: int,
    ) -> list[pd.Timestamp]:
        """
        Generate all XETRA holidays for a year range.

        Args:
            start_year: First year.
            end_year: Last year.

        Returns:
            Sorted list of holiday timestamps.
        """

        holidays = []

        for year in range(start_year, end_year + 1):
            holidays.extend(cls._holidays_for_year(year))

        return sorted(holidays)


class TradingCalendarFactory:
    """
    Factory class for retrieving exchange-specific calendars.
    """

    @staticmethod
    def get_calendar(exchange: Exchange) -> Type[TradingCalendar]:
        """
        Return calendar implementation for the given exchange.

        Args:
            exchange: Exchange enum value.

        Returns:
            TradingCalendar subclass.

        Raises:
            ValueError:
                If exchange is not supported.
        """

        if exchange == Exchange.XETRA:
            return XetraCalendar

        raise ValueError(f"Unknown exchange: {exchange}")


# Create XETRA calendar reference
xetra_cls = TradingCalendarFactory.get_calendar(Exchange.XETRA)