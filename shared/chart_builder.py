"""
ChartBuilder - Shared visualization layer for QuantLab Data_Lab.

Provides standardized interactive Plotly charts for studies:
- Candlestick price charts with volume
- Forward returns grouped bar charts
- Win rate heatmaps
- Gap distribution histograms/scatter
- Equity curves with benchmark overlay
- Prediction market + price dual-axis overlay

All charts use plotly_dark template and return fig objects.
Optionally save as interactive HTML via save_path parameter.
"""

from pathlib import Path
from typing import Optional, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class ChartBuilder:
    """Static methods for building standardized QuantLab charts."""

    # ── colour palette ──────────────────────────────────────────────
    CANDLE_UP = "#26a69a"
    CANDLE_DOWN = "#ef5350"
    VOLUME_UP = "rgba(38,166,154,0.35)"
    VOLUME_DOWN = "rgba(239,83,80,0.35)"

    # ── helpers ─────────────────────────────────────────────────────
    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Lowercase and strip whitespace from all column names.

        Useful when receiving data from DataRouter (which returns
        capitalised columns like Open, High, Low, Close, Volume) and
        feeding it into ChartBuilder methods that expect lowercase.
        """
        df = df.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df

    @staticmethod
    def _save(fig: go.Figure, save_path: Optional[Path]) -> None:
        if save_path is not None:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(str(save_path))

    # ── 1. price_chart ──────────────────────────────────────────────
    @staticmethod
    def price_chart(
        df: pd.DataFrame,
        ticker: str,
        events: Optional[pd.DataFrame] = None,
        save_path: Optional[Path] = None,
    ) -> go.Figure:
        """Candlestick chart with volume bars in a subplot below.

        Parameters
        ----------
        df : DataFrame with columns open, high, low, close, volume
             (index should be datetime).
        ticker : Ticker symbol for the chart title.
        events : Optional DataFrame with columns ``date`` and ``label``
                 to draw vertical dashed yellow event lines.
        save_path : If provided, saves interactive HTML to this path.
        """
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
        )

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color=ChartBuilder.CANDLE_UP,
                decreasing_line_color=ChartBuilder.CANDLE_DOWN,
                increasing_fillcolor=ChartBuilder.CANDLE_UP,
                decreasing_fillcolor=ChartBuilder.CANDLE_DOWN,
                name="Price",
            ),
            row=1, col=1,
        )

        # Volume bars – colour by direction
        colours = [
            ChartBuilder.VOLUME_UP if c >= o else ChartBuilder.VOLUME_DOWN
            for c, o in zip(df["close"], df["open"])
        ]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["volume"],
                marker_color=colours,
                name="Volume",
                showlegend=False,
            ),
            row=2, col=1,
        )

        # Event markers
        if events is not None and not events.empty:
            for _, row in events.iterrows():
                x_val = str(row["date"])
                fig.add_vline(
                    x=x_val,
                    line_dash="dash",
                    line_color="yellow",
                    line_width=1,
                    row="all",
                )
                # Add annotation separately to avoid Plotly Timestamp arithmetic bug
                label = row.get("label", "")
                if label:
                    fig.add_annotation(
                        x=x_val,
                        y=1,
                        yref="paper",
                        text=label,
                        showarrow=False,
                        font=dict(color="yellow", size=10),
                        yanchor="bottom",
                    )

        fig.update_layout(
            template="plotly_dark",
            title=f"{ticker} — Price & Volume",
            xaxis_rangeslider_visible=False,
            yaxis_title="Price",
            yaxis2_title="Volume",
            height=700,
            margin=dict(l=60, r=30, t=50, b=30),
        )

        ChartBuilder._save(fig, save_path)
        return fig

    # ── 2. forward_returns ──────────────────────────────────────────
    @staticmethod
    def forward_returns(
        stats: Dict[str, Dict[str, float]],
        study_name: str,
        save_path: Optional[Path] = None,
    ) -> go.Figure:
        """Grouped bar chart comparing forward returns across groups.

        Parameters
        ----------
        stats : ``{'Group Name': {'+1d': float, '+3d': float, ...}}``
        study_name : Used in chart title.
        save_path : Optional HTML output path.
        """
        horizons = list(next(iter(stats.values())).keys())
        fig = go.Figure()

        for group, rets in stats.items():
            fig.add_trace(
                go.Bar(
                    name=group,
                    x=horizons,
                    y=[rets[h] for h in horizons],
                )
            )

        fig.add_hline(y=0, line_dash="dot", line_color="white", line_width=0.8)

        fig.update_layout(
            template="plotly_dark",
            title=f"{study_name} — Forward Returns (%)",
            barmode="group",
            xaxis_title="Horizon",
            yaxis_title="Mean Return (%)",
            height=500,
            margin=dict(l=60, r=30, t=50, b=30),
        )

        ChartBuilder._save(fig, save_path)
        return fig

    # ── 3. winrate_heatmap ──────────────────────────────────────────
    @staticmethod
    def winrate_heatmap(
        df: pd.DataFrame,
        study_name: str,
        save_path: Optional[Path] = None,
    ) -> go.Figure:
        """Heatmap of win-rate percentages (RdYlGn, zmid=0.5).

        Parameters
        ----------
        df : DataFrame where rows = signal categories, columns = horizons,
             values = win rates in [0, 1].
        study_name : Used in chart title.
        save_path : Optional HTML output path.
        """
        text_matrix = [[f"{v:.0%}" for v in row] for row in df.values]

        fig = go.Figure(
            go.Heatmap(
                z=df.values,
                x=df.columns.tolist(),
                y=df.index.tolist(),
                colorscale="RdYlGn",
                zmid=0.5,
                text=text_matrix,
                texttemplate="%{text}",
                textfont=dict(size=14),
                colorbar_title="Win Rate",
            )
        )

        fig.update_layout(
            template="plotly_dark",
            title=f"{study_name} — Win Rate Heatmap",
            xaxis_title="Horizon",
            yaxis_title="Signal",
            height=450,
            margin=dict(l=180, r=30, t=50, b=30),
        )

        ChartBuilder._save(fig, save_path)
        return fig

    # ── 4. gap_distribution ─────────────────────────────────────────
    @staticmethod
    def gap_distribution(
        events_df: pd.DataFrame,
        study_name: str,
        save_path: Optional[Path] = None,
    ) -> go.Figure:
        """Gap-size histogram + scatter of gap_pct vs day_return.

        Parameters
        ----------
        events_df : DataFrame with columns ``gap_pct``, ``day_return``,
                    ``forward_5d``.
        study_name : Used in chart title.
        save_path : Optional HTML output path.
        """
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=["Gap % Distribution", "Gap % vs Day Return"],
            horizontal_spacing=0.12,
        )

        # LEFT: histogram of gap_pct
        fig.add_trace(
            go.Histogram(
                x=events_df["gap_pct"],
                marker_color=ChartBuilder.CANDLE_UP,
                opacity=0.75,
                name="Gap %",
            ),
            row=1, col=1,
        )

        # RIGHT: scatter gap_pct vs day_return, coloured by forward_5d
        fig.add_trace(
            go.Scatter(
                x=events_df["gap_pct"],
                y=events_df["day_return"],
                mode="markers",
                marker=dict(
                    color=events_df["forward_5d"],
                    colorscale="RdYlGn",
                    colorbar=dict(title="Fwd 5d", x=1.02),
                    size=7,
                    line=dict(width=0.5, color="white"),
                ),
                name="Events",
            ),
            row=1, col=2,
        )

        fig.update_layout(
            template="plotly_dark",
            title=f"{study_name} — Gap Distribution",
            height=450,
            margin=dict(l=60, r=80, t=70, b=30),
        )
        fig.update_xaxes(title_text="Gap %", row=1, col=1)
        fig.update_xaxes(title_text="Gap %", row=1, col=2)
        fig.update_yaxes(title_text="Count", row=1, col=1)
        fig.update_yaxes(title_text="Day Return %", row=1, col=2)

        ChartBuilder._save(fig, save_path)
        return fig

    # ── 5. equity_curve ─────────────────────────────────────────────
    @staticmethod
    def equity_curve(
        returns_series: pd.Series,
        study_name: str,
        benchmark: Optional[pd.Series] = None,
        save_path: Optional[Path] = None,
    ) -> go.Figure:
        """Cumulative-returns line chart with optional benchmark.

        Parameters
        ----------
        returns_series : Daily simple returns (not cumulative).
        study_name : Used in chart title.
        benchmark : Optional daily returns series for overlay.
        save_path : Optional HTML output path.
        """
        cum = (1 + returns_series).cumprod()

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=cum.index,
                y=cum.values,
                mode="lines",
                name=study_name,
                line=dict(color=ChartBuilder.CANDLE_UP, width=2),
            )
        )

        if benchmark is not None:
            bench_cum = (1 + benchmark).cumprod()
            fig.add_trace(
                go.Scatter(
                    x=bench_cum.index,
                    y=bench_cum.values,
                    mode="lines",
                    name="Benchmark",
                    line=dict(color="orange", width=2, dash="dash"),
                )
            )

        fig.add_hline(y=1.0, line_dash="dot", line_color="white", line_width=0.8)

        fig.update_layout(
            template="plotly_dark",
            title=f"{study_name} — Equity Curve",
            xaxis_title="Date",
            yaxis_title="Cumulative Return",
            height=500,
            margin=dict(l=60, r=30, t=50, b=30),
        )

        ChartBuilder._save(fig, save_path)
        return fig

    # ── 6. pm_overlay ───────────────────────────────────────────────
    @staticmethod
    def pm_overlay(
        price_df: pd.DataFrame,
        odds_df: pd.DataFrame,
        ticker: str,
        market_name: str,
        save_path: Optional[Path] = None,
    ) -> go.Figure:
        """Dual y-axis: stock close price (left) + prediction-market
        probability (right, 0-1).

        Parameters
        ----------
        price_df : DataFrame with a ``close`` column (index = datetime).
        odds_df : DataFrame with a ``probability`` column (index = datetime).
        ticker : Ticker symbol.
        market_name : Prediction market question / title.
        save_path : Optional HTML output path.
        """
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=price_df.index,
                y=price_df["close"],
                mode="lines",
                name=f"{ticker} Close",
                line=dict(color=ChartBuilder.CANDLE_UP, width=2),
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=odds_df.index,
                y=odds_df["probability"],
                mode="lines",
                name="Probability",
                line=dict(color="orange", width=2, dash="dot"),
            ),
            secondary_y=True,
        )

        fig.update_layout(
            template="plotly_dark",
            title=f"{ticker} vs {market_name}",
            height=550,
            margin=dict(l=60, r=60, t=50, b=30),
        )
        fig.update_yaxes(title_text=f"{ticker} Close ($)", secondary_y=False)
        fig.update_yaxes(title_text="Probability", range=[0, 1], secondary_y=True)

        ChartBuilder._save(fig, save_path)
        return fig
