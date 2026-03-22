"""Generate standalone HTML reports with interactive Plotly plots."""

import base64
from datetime import datetime
from pathlib import Path

import plotly.io as pio


def generate_html_report(trend_figs, perf_figs, summary_stats_df, session_name=""):
    """Generate a standalone HTML report with interactive Plotly plots.

    Parameters
    ----------
    trend_figs : list of plotly.graph_objects.Figure
        The 4 trend analysis figures (delta eff, head, power, p_disch).
    perf_figs : list of plotly.graph_objects.Figure
        The 4 performance curve figures (head, power, eff, p_disch).
    summary_stats_df : pandas.DataFrame or None
        Summary statistics dataframe from df.describe().
    session_name : str, optional
        Name of the evaluation session to display in the header.

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
        stats_html = "<p>Estatísticas resumidas não disponíveis.</p>"

    # Build trend plots grid (2x2)
    trend_grid = ""
    for i, div in enumerate(trend_divs):
        trend_grid += f'<div class="plot-cell">{div}</div>'

    # Build performance plots grid (2x2)
    perf_grid = ""
    for i, div in enumerate(perf_divs):
        perf_grid += f'<div class="plot-cell">{div}</div>'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Desempenho CCP — {timestamp}</title>
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
        .header-text .session-name {{
            font-size: 1.1rem;
            font-weight: 400;
            color: #444;
        }}
        .header-text .timestamp {{
            font-size: 0.9rem;
            color: #666;
        }}
        nav.toc {{
            position: fixed;
            top: 2rem;
            right: 2rem;
            width: 200px;
            font-size: 0.85rem;
            line-height: 1.8;
        }}
        nav.toc .toc-title {{
            font-weight: 600;
            color: #1a1a2e;
            margin-bottom: 0.4rem;
        }}
        nav.toc ul {{
            list-style: none;
            border-left: 3px solid #e0e0e0;
            padding-left: 0.75rem;
        }}
        nav.toc li {{
            padding: 0.1rem 0;
        }}
        nav.toc a {{
            color: #555;
            text-decoration: none;
        }}
        nav.toc a:hover,
        nav.toc a.active {{
            color: #1a73e8;
        }}
        nav.toc li.active {{
            border-left: 3px solid #1a73e8;
            margin-left: -0.75rem;
            padding-left: calc(0.75rem - 3px);
        }}
        .main-content {{
            margin-right: 240px;
        }}
        h2 {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #1a1a2e;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid #e0e0e0;
        }}
        .section-description {{
            color: #444;
            font-size: 0.95rem;
            margin-bottom: 1rem;
            line-height: 1.5;
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
            nav.toc {{
                display: none;
            }}
            .main-content {{
                margin-right: 0;
            }}
            body {{
                padding: 1rem;
            }}
            .plot-grid {{
                break-inside: avoid;
            }}
        }}
        @media (max-width: 1000px) {{
            nav.toc {{
                display: none;
            }}
            .main-content {{
                margin-right: 0;
            }}
        }}
    </style>
</head>
<body>
    <nav class="toc">
        <div class="toc-title">Nesta página</div>
        <ul>
            <li><a href="#tendencia">Análise de Tendência</a></li>
            <li><a href="#desempenho">Curvas de Desempenho</a></li>
            <li><a href="#estatisticas">Estatísticas Resumidas</a></li>
        </ul>
    </nav>

    <div class="main-content">
        <div class="header">
            {logo_html}
            <div class="header-text">
                <h1>Relatório de Avaliação de Desempenho</h1>
                {f'<div class="session-name">{session_name}</div>' if session_name else ''}
                <div class="timestamp">Gerado em {timestamp}</div>
            </div>
        </div>

        <h2 id="tendencia">Análise de Tendência</h2>
        <p class="section-description">
            Os gráficos abaixo apresentam a evolução temporal dos desvios percentuais
            entre os valores medidos e os valores esperados para eficiência, head,
            potência e pressão de descarga. A linha tracejada vermelha indica o valor
            de referência (desvio zero). Uma regressão linear com banda de confiança
            de 95% é incluída para identificar tendências de degradação ou melhoria
            ao longo do tempo.
        </p>
        <div class="plot-grid">
            {trend_grid}
        </div>

        <h2 id="desempenho">Curvas de Desempenho com Pontos Históricos</h2>
        <p class="section-description">
            Esta seção apresenta as curvas de desempenho do compressor (head,
            potência, eficiência e pressão de descarga) em função da vazão
            volumétrica de sucção. Os pontos operacionais medidos são sobrepostos
            às curvas esperadas, permitindo a comparação direta entre o desempenho
            real e o desempenho de projeto/garantia.
        </p>
        <div class="plot-grid">
            {perf_grid}
        </div>

        <h2 id="estatisticas">Estatísticas Resumidas</h2>
        <p class="section-description">
            A tabela a seguir apresenta as estatísticas descritivas dos desvios
            calculados, incluindo média, desvio padrão, valores mínimo e máximo,
            e quartis. Estes valores auxiliam na avaliação quantitativa do
            desempenho do compressor ao longo do período analisado.
        </p>
        {stats_html}
    </div>

    <script>
        // Highlight active TOC link on scroll
        (function() {{
            const sections = document.querySelectorAll('h2[id]');
            const tocLinks = document.querySelectorAll('nav.toc a');
            const tocItems = document.querySelectorAll('nav.toc li');

            function updateActive() {{
                let current = '';
                sections.forEach(function(section) {{
                    const top = section.getBoundingClientRect().top;
                    if (top <= 120) {{
                        current = section.getAttribute('id');
                    }}
                }});
                tocLinks.forEach(function(link, i) {{
                    link.classList.remove('active');
                    tocItems[i].classList.remove('active');
                    if (link.getAttribute('href') === '#' + current) {{
                        link.classList.add('active');
                        tocItems[i].classList.add('active');
                    }}
                }});
            }}

            window.addEventListener('scroll', updateActive);
            updateActive();
        }})();
    </script>
</body>
</html>"""

    return html
