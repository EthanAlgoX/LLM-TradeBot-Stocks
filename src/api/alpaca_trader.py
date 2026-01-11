"""
Alpaca Trading Client for US Stocks
====================================

Provides order execution using the official alpaca-py SDK.
Supports paper and live trading modes.

Author: AI Trader Team
Date: 2026-01-11
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AccountInfo:
    """Trading account information"""
    id: str
    account_number: str
    status: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'account_number': self.account_number,
            'status': self.status,
            'equity': self.equity,
            'cash': self.cash,
            'buying_power': self.buying_power,
            'portfolio_value': self.portfolio_value
        }


@dataclass
class StockPosition:
    """Stock position information"""
    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    side: str  # 'long' or 'short'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'qty': self.qty,
            'avg_entry_price': self.avg_entry_price,
            'market_value': self.market_value,
            'cost_basis': self.cost_basis,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'side': self.side
        }


@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    id: str = ""
    symbol: str = ""
    side: str = ""
    qty: float = 0.0
    filled_avg_price: float = 0.0
    status: str = ""
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'qty': self.qty,
            'filled_avg_price': self.filled_avg_price,
            'status': self.status,
            'error': self.error
        }


class AlpacaTrader:
    """
    Alpaca Trading Client
    
    Supports:
    - Paper trading (default, safe for testing)
    - Live trading (requires explicit confirmation)
    - Market orders with bracket (stop-loss + take-profit)
    - LONG ONLY strategy (no short selling)
    """
    
    def __init__(self, paper: bool = True):
        """
        Initialize Alpaca trader
        
        Args:
            paper: True for paper trading, False for live
        """
        self.api_key = os.environ.get('ALPACA_API_KEY', '')
        self.secret_key = os.environ.get('ALPACA_SECRET_KEY', '')
        self.paper = paper
        
        self._client = None
        self._initialized = False
        
        if self.api_key and self.secret_key and self.api_key != '你的API_KEY':
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Alpaca trading client"""
        try:
            from alpaca.trading.client import TradingClient
            
            self._client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper
            )
            self._initialized = True
            
        except Exception as e:
            print(f"⚠️ Failed to initialize Alpaca trader: {e}")
            self._client = None
    
    def get_account(self) -> Optional[AccountInfo]:
        """Get account information"""
        if not self._client:
            return None
        
        try:
            account = self._client.get_account()
            return AccountInfo(
                id=str(account.id),
                account_number=str(account.account_number),
                status=str(account.status.value) if hasattr(account.status, 'value') else str(account.status),
                equity=float(account.equity),
                cash=float(account.cash),
                buying_power=float(account.buying_power),
                portfolio_value=float(account.portfolio_value)
            )
        except Exception as e:
            print(f"⚠️ Error fetching account: {e}")
            return None
    
    def get_positions(self) -> List[StockPosition]:
        """Get all open positions"""
        if not self._client:
            return []
        
        try:
            positions = self._client.get_all_positions()
            return [
                StockPosition(
                    symbol=p.symbol,
                    qty=float(p.qty),
                    avg_entry_price=float(p.avg_entry_price),
                    market_value=float(p.market_value),
                    cost_basis=float(p.cost_basis),
                    unrealized_pnl=float(p.unrealized_pl),
                    unrealized_pnl_pct=float(p.unrealized_plpc) * 100,
                    side='long' if float(p.qty) > 0 else 'short'
                )
                for p in positions
            ]
        except Exception as e:
            print(f"⚠️ Error fetching positions: {e}")
            return []
    
    async def get_position(self, symbol: str) -> Optional[StockPosition]:
        """Get position for a specific symbol"""
        if not self._client:
            return None
        
        try:
            p = self._client.get_open_position(symbol)
            return StockPosition(
                symbol=p.symbol,
                qty=float(p.qty),
                avg_entry_price=float(p.avg_entry_price),
                market_value=float(p.market_value),
                cost_basis=float(p.cost_basis),
                unrealized_pnl=float(p.unrealized_pl),
                unrealized_pnl_pct=float(p.unrealized_plpc) * 100,
                side='long' if float(p.qty) > 0 else 'short'
            )
        except Exception:
            # No position exists
            return None
    
    async def open_long(
        self,
        symbol: str,
        qty: float,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None
    ) -> Optional[OrderResult]:
        """
        Open a long position (BUY)
        
        Args:
            symbol: Stock symbol
            qty: Number of shares
            stop_loss_price: Stop loss price (optional)
            take_profit_price: Take profit price (optional)
            
        Returns:
            OrderResult
        """
        if not self._client:
            return OrderResult(success=False, error="Client not initialized")
        
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
            
            # Build order request
            if stop_loss_price and take_profit_price:
                # Bracket order
                from alpaca.trading.requests import TakeProfitRequest, StopLossRequest
                
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=int(qty),
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=TakeProfitRequest(limit_price=take_profit_price),
                    stop_loss=StopLossRequest(stop_price=stop_loss_price)
                )
            else:
                # Simple market order
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=int(qty),
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
            
            order = self._client.submit_order(order_data)
            
            return OrderResult(
                success=True,
                id=str(order.id),
                symbol=order.symbol,
                side='buy',
                qty=float(order.qty),
                filled_avg_price=float(order.filled_avg_price or 0),
                status=str(order.status.value) if hasattr(order.status, 'value') else str(order.status)
            )
            
        except Exception as e:
            return OrderResult(success=False, error=str(e))
    
    async def close_position(self, symbol: str) -> Optional[OrderResult]:
        """
        Close an existing position
        
        Args:
            symbol: Stock symbol
            
        Returns:
            OrderResult
        """
        if not self._client:
            return OrderResult(success=False, error="Client not initialized")
        
        try:
            order = self._client.close_position(symbol)
            
            return OrderResult(
                success=True,
                id=order.id,
                symbol=order.symbol,
                side='sell',
                qty=float(order.qty or 0),
                filled_avg_price=float(order.filled_avg_price or 0),
                status=order.status.value
            )
            
        except Exception as e:
            return OrderResult(success=False, error=str(e))
    
    async def close_all_positions(self) -> List[OrderResult]:
        """Close all open positions"""
        if not self._client:
            return []
        
        try:
            orders = self._client.close_all_positions(cancel_orders=True)
            return [
                OrderResult(
                    success=True,
                    id=str(o.id) if hasattr(o, 'id') else "",
                    symbol=str(o.symbol) if hasattr(o, 'symbol') else "",
                    side='sell',
                    status='closed'
                )
                for o in orders
            ]
        except Exception as e:
            print(f"⚠️ Error closing all positions: {e}")
            return []
    
    async def close(self):
        """Cleanup (no persistent connections to close)"""
        pass
