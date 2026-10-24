"""Data reconciliation and gross-error detection over redundant tags.

Plant data often measure one variable with several tags (dual transmitters,
the header pressure seen by each train, two speed probes, a flow meter and an
orifice) and tie variables by balances (header flow = sum of train flows).
Reconciliation finds, at each timestamp, the variable values closest to the
measurements in the weighted least-squares sense that satisfy the balances:

    minimise (y - M x)' V^-1 (y - M x)   subject to   C x = 0

with ``y`` the measurements, ``V`` their variances, ``M`` the incidence of
measurements on variables and ``C`` the balance coefficients. The adjustments
``a = y - M x`` give the global test (``a' V^-1 a`` is chi-square with the
redundancy as degrees of freedom) and the measurement test (each adjustment
over its standard deviation), which locate gross errors; a gross error is
removed and the row reconciled again (serial elimination). Persistent biases
are the rolling median of the adjustments.

Reference: S. Narasimhan and C. Jordache, Data Reconciliation and Gross Error
Detection, Gulf Publishing, 2000.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

__all__ = ["Reconciliation", "ReconciliationResult"]

# relative tolerance under which two measurement tests are equal
_TIE_RTOL = 1e-6


@dataclass
class ReconciliationResult:
    """Result of :meth:`Reconciliation.reconcile`.

    Attributes
    ----------
    variables : pandas.DataFrame
        Reconciled value of each variable (NaN when not observable).
    measurements : pandas.DataFrame
        Reconciled value of each measured tag (``M x``).
    adjustments : pandas.DataFrame
        Measurement minus reconciled value, per tag (NaN for missing
        measurements; a removed measurement is compared with the values
        reconciled without it).
    z : pandas.DataFrame
        Measurement test: adjustment over its standard deviation (NaN for a
        measurement without redundancy).
    global_test : pandas.DataFrame
        ``statistic``, ``dof`` and ``p_value`` of the global test per row,
        after the gross-error elimination.
    gross_errors : pandas.DataFrame
        True where a measurement was removed as a gross error.
    biases : pandas.DataFrame
        Rolling median of the adjustments (persistent bias per tag).
    """

    variables: pd.DataFrame
    measurements: pd.DataFrame
    adjustments: pd.DataFrame
    z: pd.DataFrame
    global_test: pd.DataFrame
    gross_errors: pd.DataFrame
    biases: pd.DataFrame

    def summary(self):
        """Per tag: median adjustment, median measurement test, gross-error rate."""
        return pd.DataFrame(
            {
                "median_adjustment": self.adjustments.median(),
                "median_z": self.z.median(),
                "gross_error_rate": self.gross_errors.mean(),
                "available": self.adjustments.notna().mean(),
            }
        )


class Reconciliation:
    """Weighted least-squares reconciliation of redundant plant tags.

    Parameters
    ----------
    sigmas : dict
        Standard deviation of each tag (the DataFrame column). A number is an
        absolute value in the tag units; a string ending in ``%`` is relative
        to the measured value (e.g. ``"0.25%"``). A reading of 0 on a tag with
        a relative standard deviation is treated as missing.
    redundancy : dict, optional
        Variable name -> list of tags measuring it. Tags not listed are a
        variable of their own, with the tag name.
    balances : list of dict, optional
        Linear balances between variables, as ``{variable: coefficient}``
        with ``sum(coefficient * variable) = 0``; e.g.
        ``{"flow_header": 1, "flow_A": -1, "flow_B": -1}``.
    alpha : float, optional
        Significance level of the global and measurement tests.
        The default is 0.05.
    max_eliminations : int, optional
        Maximum number of gross errors removed per row. The default is 1.
        Nothing is removed when the largest measurement test is shared by
        several tags (an equivalency set, such as the two tags of a dual
        transmitter or the tags of one balance): the gross error cannot be
        located there, the row keeps failing the global test and the
        adjustments are split between those tags. Three tags of a variable
        locate a biased one.
    bias_window : str, optional
        Window of the rolling median of the adjustments (pandas offset
        alias for a DatetimeIndex, else a number of rows). The default is
        "7D".

    Examples
    --------
    >>> import pandas as pd
    >>> rec = Reconciliation(
    ...     sigmas={"ps_A": 0.01, "ps_B": 0.01, "ps_C": 0.01},
    ...     redundancy={"ps": ["ps_A", "ps_B", "ps_C"]},
    ... )
    >>> df = pd.DataFrame({"ps_A": [10.0], "ps_B": [10.02], "ps_C": [10.01]})
    >>> round(float(rec.reconcile(df).variables["ps"].iloc[0]), 4)
    10.01
    """

    def __init__(
        self,
        sigmas,
        redundancy=None,
        balances=None,
        alpha=0.05,
        max_eliminations=1,
        bias_window="7D",
    ):
        self.tags = list(sigmas)
        self.sigma_abs = np.zeros(len(self.tags))
        self.sigma_rel = np.zeros(len(self.tags))
        for j, tag in enumerate(self.tags):
            value = sigmas[tag]
            if isinstance(value, str) and value.strip().endswith("%"):
                self.sigma_rel[j] = float(value.strip()[:-1]) / 100
            else:
                self.sigma_abs[j] = float(value)
            if self.sigma_abs[j] <= 0 and self.sigma_rel[j] <= 0:
                raise ValueError(f"Tag {tag!r} needs a positive standard deviation.")
        redundancy = dict(redundancy or {})
        grouped = {tag: var for var, tags in redundancy.items() for tag in tags}
        unknown = set(grouped) - set(self.tags)
        if unknown:
            raise ValueError(f"Tags without a standard deviation: {sorted(unknown)}")
        self.variables = []
        for tag in self.tags:
            var = grouped.get(tag, tag)
            if var not in self.variables:
                self.variables.append(var)
        for balance in balances or []:
            for var in balance:
                if var not in self.variables:
                    raise ValueError(
                        f"Balance variable {var!r} is not measured by any tag."
                    )
        self.M = np.zeros((len(self.tags), len(self.variables)))
        for j, tag in enumerate(self.tags):
            self.M[j, self.variables.index(grouped.get(tag, tag))] = 1.0
        self.C = np.zeros((len(balances or []), len(self.variables)))
        for i, balance in enumerate(balances or []):
            for var, coefficient in balance.items():
                self.C[i, self.variables.index(var)] = coefficient
        self.alpha = alpha
        self.max_eliminations = max_eliminations
        self.bias_window = bias_window

    def _observable(self, M):
        """Variables fixed by the measurement incidence ``M`` and the balances."""
        A = np.vstack([M, self.C])
        if A.shape[0] == 0:
            return np.zeros(len(self.variables), dtype=bool)
        _, s, vt = np.linalg.svd(A)
        rank = int(np.sum(s > 1e-10 * max(s.max(initial=0.0), 1.0)))
        null = vt[rank:]
        return np.linalg.norm(null, axis=0) < 1e-8

    def _solve(self, y, sigma, use):
        """Reconcile rows that share the measurement mask ``use``.

        Returns reconciled variables, adjustments, measurement tests,
        global statistic and degrees of freedom.
        """
        n_rows = len(y)
        n_var = len(self.variables)
        n_bal = len(self.C)
        M = self.M[use]
        ys = y[:, use]
        w = 1.0 / sigma[:, use] ** 2
        G = np.einsum("ji,bj,jk->bik", M, w, M)
        K = np.zeros((n_rows, n_var + n_bal, n_var + n_bal))
        K[:, :n_var, :n_var] = G
        K[:, :n_var, n_var:] = self.C.T
        K[:, n_var:, :n_var] = self.C
        rhs = np.zeros((n_rows, n_var + n_bal))
        rhs[:, :n_var] = np.einsum("ji,bj,bj->bi", M, w, ys)
        K_inv = np.linalg.pinv(K)
        x = np.einsum("bik,bk->bi", K_inv, rhs)[:, :n_var]
        cov_x = K_inv[:, :n_var, :n_var]
        # a variable is observable when the measurements and balances fix it,
        # i.e. it does not move along the null space of [M; C] (the same for
        # every row of this pattern); otherwise pinv returns a min-norm value
        observable = self._observable(M)
        x = np.where(observable, x, np.nan)
        fitted = np.einsum("ji,bi->bj", M, np.nan_to_num(x))
        adjustment = ys - fitted
        var_a = sigma[:, use] ** 2 - np.einsum("ji,bik,jk->bj", M, cov_x, M)
        z = np.where(
            var_a > 1e-12 * sigma[:, use] ** 2,
            adjustment / np.sqrt(np.clip(var_a, 1e-300, None)),
            np.nan,
        )
        statistic = np.sum(adjustment**2 * w, axis=1)
        dof = np.sum(var_a * w, axis=1)
        return x, adjustment, z, statistic, dof

    def reconcile(self, df):
        """Reconcile every row of ``df`` (columns are the tags).

        Parameters
        ----------
        df : pandas.DataFrame
            Measurements; missing values (NaN) are left out of their row.

        Returns
        -------
        ReconciliationResult
        """
        missing = [t for t in self.tags if t not in df.columns]
        if missing:
            raise KeyError(f"Tags not found in the data: {missing}")
        y = df[self.tags].to_numpy(dtype=float)
        sigma = np.sqrt(self.sigma_abs**2 + (self.sigma_rel * np.abs(y)) ** 2)
        # a reading of 0 on a tag with only a relative sigma (a dead
        # transmitter, a shutdown) would have infinite weight: treat it as
        # missing
        available = np.isfinite(y) & (sigma > 0)
        removed = np.zeros_like(available)
        n_rows, n_tags = y.shape
        x = np.full((n_rows, len(self.variables)), np.nan)
        adjustment = np.full((n_rows, n_tags), np.nan)
        z = np.full((n_rows, n_tags), np.nan)
        statistic = np.full(n_rows, np.nan)
        dof = np.full(n_rows, np.nan)
        pending = np.ones(n_rows, dtype=bool)
        for iteration in range(self.max_eliminations + 1):
            use_all = available & ~removed
            patterns, inverse = np.unique(use_all[pending], axis=0, return_inverse=True)
            rows_pending = np.flatnonzero(pending)
            for p, use in enumerate(patterns):
                rows = rows_pending[inverse.ravel() == p]
                if not use.any():
                    continue
                xs, a, zs, s, d = self._solve(y[rows], sigma[rows], use)
                x[rows] = xs
                adjustment[np.ix_(rows, use)] = a
                adjustment[np.ix_(rows, ~use)] = np.nan
                z[np.ix_(rows, use)] = zs
                z[np.ix_(rows, ~use)] = np.nan
                statistic[rows] = s
                dof[rows] = d
            if iteration == self.max_eliminations:
                break
            # serial elimination: remove the largest measurement test of the
            # rows that fail the global test, when it is significant
            with np.errstate(invalid="ignore"):
                p_value = stats.chi2.sf(statistic, np.maximum(dof, 1e-9))
                fail = pending & (dof > 0.5) & (p_value < self.alpha)
                abs_z = np.where(np.isfinite(z), np.abs(z), -np.inf)
                worst = np.argmax(abs_z, axis=1)
                n_used = (available & ~removed).sum(axis=1)
                critical = stats.norm.ppf(1 - self.alpha / (2 * np.maximum(n_used, 1)))
                worst_z = abs_z[np.arange(n_rows), worst]
                # measurements of an equivalency set (two tags of one
                # variable, the tags of one balance) have the same test: the
                # gross error cannot be located, so nothing is removed
                if n_tags > 1:
                    second_z = np.sort(abs_z, axis=1)[:, -2]
                else:
                    second_z = np.full(n_rows, -np.inf)
                tied = second_z >= (1 - _TIE_RTOL) * worst_z
            fail &= (worst_z > critical) & ~tied
            if not fail.any():
                break
            removed[np.flatnonzero(fail), worst[fail]] = True
            pending = fail
        with np.errstate(invalid="ignore"):
            p_value = np.where(
                dof > 0.5, stats.chi2.sf(statistic, np.maximum(dof, 1e-9)), np.nan
            )
        index = df.index
        variables = pd.DataFrame(x, index=index, columns=self.variables)
        fitted = pd.DataFrame(
            np.einsum("ji,bi->bj", self.M, x), index=index, columns=self.tags
        )
        # a removed measurement keeps its adjustment against the values
        # reconciled without it: that is the size of its error
        adjustment = np.where(removed, y - fitted.to_numpy(), adjustment)
        adjustments = pd.DataFrame(adjustment, index=index, columns=self.tags)
        if isinstance(index, pd.DatetimeIndex) and isinstance(self.bias_window, str):
            biases = adjustments.rolling(self.bias_window, min_periods=1).median()
        else:
            window = self.bias_window if isinstance(self.bias_window, int) else 50
            biases = adjustments.rolling(window, min_periods=1).median()
        return ReconciliationResult(
            variables=variables,
            measurements=fitted,
            adjustments=adjustments,
            z=pd.DataFrame(z, index=index, columns=self.tags),
            global_test=pd.DataFrame(
                {"statistic": statistic, "dof": dof, "p_value": p_value}, index=index
            ),
            gross_errors=pd.DataFrame(removed, index=index, columns=self.tags),
            biases=biases,
        )
