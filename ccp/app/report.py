"""Generate standalone HTML reports with interactive Plotly plots."""

import base64
from datetime import datetime
from pathlib import Path

import plotly.io as pio


def generate_html_report(trend_figs, perf_figs, summary_stats_df):
    """Generate a standalone HTML report with interactive Plotly plots.

    Parameters
    ----------
    trend_figs : list of plotly.graph_objects.Figure
        The 4 trend analysis figures (delta eff, head, power, p_disch).
    perf_figs : list of plotly.graph_objects.Figure
        The 4 performance curve figures (head, power, eff, p_disch).
    summary_stats_df : pandas.DataFrame or None
        Summary statistics dataframe from df.describe().

    Returns
    -------
    str
        Complete HTML string for the report.
    """
    # Encode logo as base64
    logo_path = Path(__file__).parent / "assets" / "ccp.png"
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
        logo_html = (
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'alt="CCP Logo" class="logo">'
        )
    else:
        logo_html = ""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Convert figures to HTML divs (share a single plotly.js)
    trend_divs = [
        pio.to_html(fig, full_html=False, include_plotlyjs=False)
        for fig in trend_figs
    ]
    perf_divs = [
        pio.to_html(fig, full_html=False, include_plotlyjs=False)
        for fig in perf_figs
    ]

    # Summary stats table
    if summary_stats_df is not None and not summary_stats_df.empty:
        stats_html = summary_stats_df.to_html(
            classes="stats-table",
            float_format=lambda x: f"{x:.4f}",
        )
    else:
        stats_html = "<p>No summary statistics available.</p>"

    # Build trend plots grid (2x2)
    trend_grid = ""
    for i, div in enumerate(trend_divs):
        trend_grid += f'<div class="plot-cell">{div}</div>'

    # Build performance plots grid (2x2)
    perf_grid = ""
    for i, div in enumerate(perf_divs):
        perf_grid += f'<div class="plot-cell">{div}</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CCP Performance Report — {timestamp}</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            color: #1a1a2e;
            background: #ffffff;
            line-height: 1.6;
            padding: 2rem 3rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }}
        .logo {{
            height: 60px;
        }}
        .header-text h1 {{
            font-size: 1.6rem;
            font-weight: 600;
            color: #1a1a2e;
        }}
        .header-text .timestamp {{
            font-size: 0.9rem;
            color: #666;
        }}
        h2 {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #1a1a2e;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid #e0e0e0;
        }}
        .plot-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .plot-cell {{
            border: 1px solid #eee;
            border-radius: 6px;
            padding: 0.5rem;
            background: #fafafa;
        }}
        .stats-table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
            font-size: 0.9rem;
        }}
        .stats-table th,
        .stats-table td {{
            border: 1px solid #ddd;
            padding: 0.5rem 0.75rem;
            text-align: right;
        }}
        .stats-table th {{
            background: #f5f5f5;
            font-weight: 600;
            text-align: center;
        }}
        .stats-table tr:nth-child(even) {{
            background: #fafafa;
        }}
        .stats-table tr:hover {{
            background: #f0f0f0;
        }}
        @media print {{
            body {{
                padding: 1rem;
            }}
            .plot-grid {{
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        {logo_html}
        <div class="header-text">
            <h1>Performance Evaluation Report</h1>
            <div class="timestamp">Generated on {timestamp}</div>
        </div>
    </div>

    <h2>Trend Analysis</h2>
    <div class="plot-grid">
        {trend_grid}
    </div>

    <h2>Performance Curves with Historical Points</h2>
    <div class="plot-grid">
        {perf_grid}
    </div>

    <h2>Summary Statistics</h2>
    {stats_html}
</body>
</html>"""

    return html
