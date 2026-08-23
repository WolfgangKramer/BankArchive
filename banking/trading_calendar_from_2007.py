from __future__ import annotations

from enum import Enum
from typing import Tuple, Union

import pandas as pd
import exchange_calendars as xcals


class Exchange(Enum):
    """
    The calendar names in exchange_calendars
    generally correspond to MIC codes (ISO 10383)
    or established exchange tickers. Frequently used entries include:

    Exchange    Calendar Name
    Xetra    XETR
    Frankfurt (XFRA)    XFRA
    New York Stock Exchange    XNYS
    Nasdaq    XNAS
    London Stock Exchange    XLON
    Euronext Paris    XPAR
    Euronext Amsterdam    XAMS
    SIX Swiss Exchange    XSWX
    Borsa Italiana    XMIL
    Madrid    XMAD
    Toronto    XTSE
    Australian Securities Exchange    XASX
    Tokyo Stock Exchange    XTKS
    Hong Kong    XHKG
    Singapore    XSES
    Korea Exchange    XKRX
    Taiwan Stock Exchange    XTAI
    Bombay Stock Exchange    XBOM
    """
    XETRA = "XETR"
    FRANKFURT = "XFRA"
    NYSE = "XNYS"
    NASDAQ = "XNAS"
    LSE = "XLON"
    SIX = "XSWX"


class TradingCalendar:
    """
    Wrapper um exchange_calendars.
    Enthält ausschließlich projektspezifische Logik.
    """

    def __init__(self, exchange: Exchange):
        self.cal = xcals.get_calendar(exchange.value)

    def is_trading_day(
        self,
        dt: Union[str, pd.Timestamp],
    ) -> bool:

        ts = pd.Timestamp(dt).normalize()
        return self.cal.is_session(ts)

    def trading_days(
        self,
        start: Union[str, pd.Timestamp],
        end: Union[str, pd.Timestamp],
        as_str: bool = False,
    ):

        sessions = self.cal.sessions_in_range(
            pd.Timestamp(start),
            pd.Timestamp(end),
        )

        if as_str:
            return sessions.date().isoformat().tolist()

        return list(sessions)

    def adjust_period(
        self,
        start,
        end,
        settlement_days: int = 0,
        as_str: bool = True,
    ) -> Tuple:

        start = pd.Timestamp(start).normalize()
        end = pd.Timestamp(end).normalize()

        start = self.cal.date_to_session(
            start,
            direction="next",
        )

        end = self.cal.date_to_session(
            end,
            direction="previous",
        )

        if settlement_days:

            sessions = self.cal.sessions

            start_loc = sessions.get_loc(start)
            end_loc = sessions.get_loc(end)

            start = sessions[start_loc + settlement_days]
            end = sessions[end_loc + settlement_days]

        if start > end:
            raise ValueError("No valid trading period")

        if as_str:
            return (
                start.date().isoformat(),
                end.date().isoformat(),
            )

        return start, end

    def last_trading_period(self):

        cal = self.cal

        today = pd.Timestamp.today().normalize()

        last = cal.date_to_session(
            today - pd.Timedelta(days=1),
            direction="previous",
        )

        prev = cal.previous_session(last)

        return (
            prev.date().isoformat(),
            last.date().isoformat(),
        )


xetra_cls = TradingCalendar(Exchange.XETRA)
