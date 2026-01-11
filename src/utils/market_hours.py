"""
US Stock Market Hours Utility
=============================

Provides trading hours information for US stock markets.
Supports regular hours and extended hours (pre-market, after-hours).

Author: AI Trader Team
Date: 2026-01-11
"""

from datetime import datetime, time, date
from typing import Optional
from enum import Enum
from zoneinfo import ZoneInfo


# US Eastern Time
ET = ZoneInfo("America/New_York")


class MarketSession(Enum):
    """Market session types"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


class MarketHours:
    """
    US Stock Market Hours
    
    Regular Hours: 9:30 AM - 4:00 PM ET
    Pre-Market: 4:00 AM - 9:30 AM ET
    After-Hours: 4:00 PM - 8:00 PM ET
    """
    
    # Regular trading hours
    MARKET_OPEN = time(9, 30)
    MARKET_CLOSE = time(16, 0)
    
    # Extended hours
    PRE_MARKET_OPEN = time(4, 0)
    AFTER_HOURS_CLOSE = time(20, 0)
    
    # US Market holidays (2026)
    HOLIDAYS_2026 = [
        date(2026, 1, 1),   # New Year's Day
        date(2026, 1, 19),  # MLK Day
        date(2026, 2, 16),  # Presidents Day
        date(2026, 4, 3),   # Good Friday
        date(2026, 5, 25),  # Memorial Day
        date(2026, 7, 3),   # Independence Day (observed)
        date(2026, 9, 7),   # Labor Day
        date(2026, 11, 26), # Thanksgiving
        date(2026, 12, 25), # Christmas
    ]
    
    def __init__(self):
        """Initialize market hours"""
        pass
    
    def get_current_time_et(self) -> datetime:
        """Get current time in US Eastern Time"""
        return datetime.now(ET)
    
    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """
        Check if a given date is a trading day
        
        Args:
            check_date: Date to check (default: today)
            
        Returns:
            True if trading day
        """
        if check_date is None:
            check_date = self.get_current_time_et().date()
        
        # Check if weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if holiday
        if check_date in self.HOLIDAYS_2026:
            return False
        
        return True
    
    def get_current_session(self) -> MarketSession:
        """
        Get current market session
        
        Returns:
            MarketSession enum value
        """
        now = self.get_current_time_et()
        current_time = now.time()
        
        # Check if trading day
        if not self.is_trading_day(now.date()):
            return MarketSession.CLOSED
        
        # Check session
        if current_time >= self.MARKET_OPEN and current_time < self.MARKET_CLOSE:
            return MarketSession.REGULAR
        elif current_time >= self.PRE_MARKET_OPEN and current_time < self.MARKET_OPEN:
            return MarketSession.PRE_MARKET
        elif current_time >= self.MARKET_CLOSE and current_time < self.AFTER_HOURS_CLOSE:
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.CLOSED
    
    def is_market_open(self, include_extended: bool = False) -> bool:
        """
        Check if market is currently open
        
        Args:
            include_extended: Include pre-market and after-hours
            
        Returns:
            True if market is open
        """
        session = self.get_current_session()
        
        if include_extended:
            return session in (
                MarketSession.REGULAR,
                MarketSession.PRE_MARKET,
                MarketSession.AFTER_HOURS
            )
        else:
            return session == MarketSession.REGULAR
    
    def format_status(self) -> str:
        """
        Get formatted market status string
        
        Returns:
            Human-readable status string
        """
        session = self.get_current_session()
        now = self.get_current_time_et()
        
        status_map = {
            MarketSession.REGULAR: f"🟢 Market Open ({now.strftime('%H:%M')} ET)",
            MarketSession.PRE_MARKET: f"🟡 Pre-Market ({now.strftime('%H:%M')} ET)",
            MarketSession.AFTER_HOURS: f"🟡 After-Hours ({now.strftime('%H:%M')} ET)",
            MarketSession.CLOSED: f"🔴 Market Closed ({now.strftime('%H:%M')} ET)"
        }
        
        return status_map.get(session, "Unknown")
    
    def time_until_open(self) -> Optional[int]:
        """
        Get minutes until market opens
        
        Returns:
            Minutes until open, or None if already open
        """
        session = self.get_current_session()
        
        if session == MarketSession.REGULAR:
            return None  # Already open
        
        now = self.get_current_time_et()
        
        # Calculate time to next open
        open_time = datetime.combine(now.date(), self.MARKET_OPEN, tzinfo=ET)
        
        if now.time() >= self.MARKET_CLOSE:
            # After close, next open is tomorrow
            from datetime import timedelta
            open_time = open_time + timedelta(days=1)
        
        # Skip weekends
        while not self.is_trading_day(open_time.date()):
            from datetime import timedelta
            open_time = open_time + timedelta(days=1)
        
        diff = open_time - now
        return int(diff.total_seconds() / 60)
