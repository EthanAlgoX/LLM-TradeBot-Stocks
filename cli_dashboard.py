#!/usr/bin/env python3
"""
AI Stock Daily Dashboard - CLI Mode
====================================

命令行模式查看今日选股和昨日复盘
"""
import argparse
import sys
from datetime import date
from pathlib import Path

# 添加 server 到 path
sys.path.insert(0, str(Path(__file__).parent / "server"))

from app.services import session_loader, picks_service, performance_service
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box

console = Console()


def show_dashboard(preset: str = "all"):
    """显示 Dashboard 概览"""
    console.clear()
    
    # 获取数据
    session = session_loader.get_latest_session()
    perf = performance_service.get_rolling_performance(days=7, preset=preset)
    today = picks_service.get_today_picks(preset=preset)
    yesterday = picks_service.get_yesterday_recap(preset=preset)
    
    # Header
    console.print(Panel.fit(
        f"[bold cyan]📊 AI Stock Daily Dashboard[/bold cyan]\n"
        f"Session: [yellow]{session}[/yellow]",
        border_style="cyan"
    ))
    
    # KPI Cards
    kpi = perf.get("kpi", {})
    console.print("\n[bold]📈 7 Day Performance[/bold]")
    
    kpi_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    kpi_table.add_column(justify="left")
    kpi_table.add_column(justify="right")
    kpi_table.add_column(justify="left")
    kpi_table.add_column(justify="right")
    
    total_return = kpi.get("total_return_pct", 0)
    win_rate = kpi.get("win_rate", 0)
    total_trades = kpi.get("total_trades", 0)
    avg_daily = kpi.get("avg_daily_return_pct", 0)
    
    return_color = "green" if total_return >= 0 else "red"
    
    kpi_table.add_row(
        "Total Return:", f"[{return_color}]{total_return:+.2f}%[/{return_color}]",
        "Win Rate:", f"[cyan]{win_rate*100:.1f}%[/cyan]"
    )
    kpi_table.add_row(
        "Total Trades:", f"[white]{total_trades}[/white]",
        "Avg Daily:", f"[yellow]{avg_daily:+.2f}%[/yellow]"
    )
    
    console.print(kpi_table)
    
    # Today's Picks
    console.print(f"\n[bold]🎯 Today's Picks ({len(today.get('picks', []))}) - {today.get('date', '')}[/bold]")
    
    picks = today.get("picks", [])
    if picks:
        picks_table = Table(box=box.ROUNDED)
        picks_table.add_column("Symbol", style="cyan bold")
        picks_table.add_column("Action", style="green")
        picks_table.add_column("Entry", justify="right")
        picks_table.add_column("Max Potential", justify="right", style="green")
        picks_table.add_column("Reason", max_width=50)
        
        for pick in picks[:10]:  # 只显示前 10 个
            picks_table.add_row(
                pick.get("symbol", ""),
                pick.get("action", ""),
                f"${pick.get('entry_price', 0):.2f}",
                f"+{pick.get('max_potential_pct', 0):.1f}%",
                pick.get("reason", "")[:50]
            )
        
        console.print(picks_table)
    else:
        console.print("[dim]No picks today[/dim]")
    
    # Yesterday's Recap
    console.print(f"\n[bold]📋 Yesterday's Recap - {yesterday.get('date', '')}[/bold]")
    
    summary = yesterday.get("summary", {})
    trades = yesterday.get("trades", [])
    
    if summary.get("total", 0) > 0:
        total_pnl = summary.get("total_pnl_pct", 0)
        pnl_color = "green" if total_pnl >= 0 else "red"
        
        console.print(
            f"Total: {summary.get('total', 0)} | "
            f"Wins: [green]{summary.get('wins', 0)}[/green] | "
            f"Losses: [red]{summary.get('losses', 0)}[/red] | "
            f"Win Rate: [cyan]{summary.get('win_rate', 0)*100:.1f}%[/cyan] | "
            f"PnL: [{pnl_color}]{total_pnl:+.2f}%[/{pnl_color}]"
        )
        
        if trades:
            recap_table = Table(box=box.ROUNDED)
            recap_table.add_column("Symbol", style="cyan bold")
            recap_table.add_column("Entry", justify="right")
            recap_table.add_column("Exit", justify="right")
            recap_table.add_column("PnL", justify="right")
            recap_table.add_column("Exit Reason")
            
            for trade in trades[:10]:
                pnl = trade.get("pnl_pct", 0)
                pnl_color = "green" if pnl >= 0 else "red"
                
                recap_table.add_row(
                    trade.get("symbol", ""),
                    f"${trade.get('entry_price', 0):.2f}",
                    f"${trade.get('exit_price', 0):.2f}",
                    f"[{pnl_color}]{pnl:+.2f}%[/{pnl_color}]",
                    trade.get("exit_reason", "")
                )
            
            console.print(recap_table)
    else:
        console.print("[dim]No trades yesterday[/dim]")


def show_today(preset: str = "all"):
    """显示今日选股详情"""
    console.clear()
    
    data = picks_service.get_today_picks(preset=preset)
    picks = data.get("picks", [])
    
    console.print(Panel.fit(
        f"[bold cyan]🎯 Today's Picks ({len(picks)})[/bold cyan]\n"
        f"Date: [yellow]{data.get('date', '')}[/yellow]",
        border_style="cyan"
    ))
    
    if not picks:
        console.print("\n[dim]No picks for today[/dim]")
        return
    
    table = Table(box=box.ROUNDED)
    table.add_column("Symbol", style="cyan bold")
    table.add_column("Action", style="green")
    table.add_column("OR15 Close", justify="right")
    table.add_column("Entry", justify="right")
    table.add_column("Max Potential", justify="right", style="green")
    table.add_column("Reason", max_width=60)
    
    for pick in picks:
        table.add_row(
            pick.get("symbol", ""),
            pick.get("action", ""),
            f"${pick.get('or15_close', 0):.2f}",
            f"${pick.get('entry_price', 0):.2f}",
            f"+{pick.get('max_potential_pct', 0):.1f}%",
            pick.get("reason", "")
        )
    
    console.print(table)


def show_yesterday(preset: str = "all"):
    """显示昨日复盘详情"""
    console.clear()
    
    data = picks_service.get_yesterday_recap(preset=preset)
    trades = data.get("trades", [])
    summary = data.get("summary", {})
    
    console.print(Panel.fit(
        f"[bold cyan]📋 Yesterday's Recap[/bold cyan]\n"
        f"Date: [yellow]{data.get('date', '')}[/yellow]",
        border_style="cyan"
    ))
    
    # Summary
    if summary.get("total", 0) > 0:
        total_pnl = summary.get("total_pnl_pct", 0)
        pnl_color = "green" if total_pnl >= 0 else "red"
        
        console.print(
            f"\n[bold]Summary:[/bold] "
            f"Total: {summary.get('total', 0)} | "
            f"Wins: [green]{summary.get('wins', 0)}[/green] | "
            f"Losses: [red]{summary.get('losses', 0)}[/red] | "
            f"Win Rate: [cyan]{summary.get('win_rate', 0)*100:.1f}%[/cyan] | "
            f"Total PnL: [{pnl_color}]{total_pnl:+.2f}%[/{pnl_color}]\n"
        )
    
    if not trades:
        console.print("[dim]No trades yesterday[/dim]")
        return
    
    table = Table(box=box.ROUNDED)
    table.add_column("Symbol", style="cyan bold")
    table.add_column("Entry", justify="right")
    table.add_column("Exit", justify="right")
    table.add_column("PnL", justify="right")
    table.add_column("Exit Reason")
    table.add_column("Duration")
    
    for trade in trades:
        pnl = trade.get("pnl_pct", 0)
        pnl_color = "green" if pnl >= 0 else "red"
        
        table.add_row(
            trade.get("symbol", ""),
            f"${trade.get('entry_price', 0):.2f}",
            f"${trade.get('exit_price', 0):.2f}",
            f"[{pnl_color}]{pnl:+.2f}%[/{pnl_color}]",
            trade.get("exit_reason", ""),
            trade.get("holding_time", "")
        )
    
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="AI Stock Daily Dashboard - CLI Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "mode",
        choices=["dashboard", "today", "yesterday"],
        default="dashboard",
        nargs="?",
        help="Display mode (default: dashboard)"
    )
    
    parser.add_argument(
        "--preset",
        choices=["all", "momentum", "ai"],
        default="all",
        help="Stock preset filter (default: all)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "dashboard":
            show_dashboard(args.preset)
        elif args.mode == "today":
            show_today(args.preset)
        elif args.mode == "yesterday":
            show_yesterday(args.preset)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
