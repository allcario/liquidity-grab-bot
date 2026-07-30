"""
Genereert een chart-afbeelding bij een liquidity grab signaal: candles met
het geteste niveau erin getekend en de sweep-candle gemarkeerd.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def generate_chart(df: pd.DataFrame, result: dict, symbol: str, timeframe: str, direction: str,
                    out_path: str, lookback: int = 60):
    n = len(df)
    start = max(0, n - lookback)
    plot_df = df.iloc[start:n].reset_index(drop=True)
    dates = pd.to_datetime(plot_df["timestamp"], unit="ms")

    level_idx_in_plot = None
    if result.get("level_index") is not None:
        level_idx_in_plot = result["level_index"] - start

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")
    ax.tick_params(colors="#c9d1d9", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#30363d")
    ax.grid(True, color="#21262d", linewidth=0.5)

    for i, row in plot_df.iterrows():
        color = "#26a69a" if row["close"] >= row["open"] else "#ef5350"
        ax.plot([i, i], [row["low"], row["high"]], color=color, linewidth=1)
        ax.plot([i, i], [row["open"], row["close"]], color=color, linewidth=5)

    marker_color = "#ef5350" if direction == "SHORT" else "#26a69a"

    if level_idx_in_plot is not None and 0 <= level_idx_in_plot < len(plot_df):
        level_price = result["level_price"]
        ax.plot(
            [level_idx_in_plot, len(plot_df) - 1], [level_price, level_price],
            color="#f0a500", linewidth=1.3, linestyle="--"
        )
        ax.text(
            level_idx_in_plot, level_price, "  Liquidity-niveau",
            color="#f0a500", fontsize=8, va="bottom"
        )
        ax.scatter([level_idx_in_plot], [level_price], color="#f0a500", s=30, zorder=5)

    last_x = len(plot_df) - 1
    sweep_y = plot_df["high"].iloc[-1] if direction == "SHORT" else plot_df["low"].iloc[-1]
    ax.annotate(
        f"LIQUIDITY GRAB\n({direction})",
        xy=(last_x, sweep_y),
        xytext=(last_x - 12, sweep_y + (2 if direction == "SHORT" else -2)),
        color="#ffffff", fontsize=9, fontweight="bold",
        ha="center",
        arrowprops=dict(arrowstyle="->", color=marker_color, lw=1.8)
    )

    ax.set_title(f"{symbol}  ·  {timeframe}  ·  Kraken", color="#c9d1d9", fontsize=11, loc="left")
    direction_label = "SHORT" if direction == "SHORT" else "LONG"
    fig.suptitle(f"{symbol}  {timeframe}  —  Liquidity Grab {direction_label}",
                 color=marker_color, fontsize=13, y=0.99, fontweight="bold")
    ax.set_ylabel("Prijs", color="#c9d1d9", fontsize=9)

    n_ticks = 6
    tick_positions = list(range(0, len(plot_df), max(1, len(plot_df) // n_ticks)))
    tick_labels = [dates.iloc[i].strftime("%m-%d %H:%M") for i in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=30, ha="right")

    plt.tight_layout()
    plt.savefig(out_path, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
