"""Module for performance evaluation based on historical data."""


class Evaluation:
    """Class for performance evaluation based on historical data."""

    def __init__(self, data, impellers):
        """Initialize the evaluation class.

        Parameters
        ----------
        data : pandas.DataFrame
            Historical data of pressure, temperature and speed to calculate performance.
        impellers : list
            List of impellers with design curves.

        Returns
        -------
        None.
        """
        self.data = data
        self.impellers = impellers
