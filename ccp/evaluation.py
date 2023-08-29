"""Module for performance evaluation based on historical data."""


class Evaluation:
    """Class for performance evaluation based on historical data."""

    def __init__(
        self,
        data,
        window=3,
        data_type=None,
        temperature_fluctuation=0.5,
        pressure_fluctuation=2,
        speed_fluctuation=0.5,
        impellers=None,
    ):
        """Initialize the evaluation class.

        Parameters
        ----------
        data : pandas.DataFrame
            Historical data of pressure, temperature and speed to calculate performance.
        window : int, optional
            Window size for rolling calculation, meaning how many rolls will be used
            to calculate the fluctuation.
            The default is 3.
        data_type : dict
            Dictionary with data types for each column.
            Values for data_type can be: "pressure", "temperature", "speed".
        temperature_fluctuation : float, optional
            Maximum fluctuation for temperature data.
            The default is 0.5.
        pressure_fluctuation : float, optional
            Maximum fluctuation for pressure data.
            The default is 2.
        speed_fluctuation : float, optional
            Maximum fluctuation for speed data.
            The default is 0.5.
        impellers : list
            List of impellers with design curves.

        Returns
        -------
        None.
        """
        self.data = data
        self.window = window
        self.data_type = data_type
        self.temperature_fluctuation = temperature_fluctuation
        self.pressure_fluctuation = pressure_fluctuation
        self.speed_fluctuation = speed_fluctuation
        self.impellers = impellers
