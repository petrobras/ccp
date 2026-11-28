"""Analytics on evaluation results: trends, data reconciliation and fleets.

Fitting the fleet model (``ccp.analytics.fleet``) needs the optional
``bayes`` dependencies (``pip install ccp-performance[bayes]``); PyMC is
imported only when a fleet is fitted.
"""

from .reconciliation import Reconciliation, ReconciliationResult
from .trends import KpiTrend, TrendReport, analyse_trends, change_points, theil_sen

__all__ = [
    "KpiTrend",
    "Reconciliation",
    "ReconciliationResult",
    "TrendReport",
    "analyse_trends",
    "change_points",
    "theil_sen",
]
