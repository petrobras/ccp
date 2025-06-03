"""Data processing functions for ccp."""

import pandas as pd


def fluctuation(x):
    """Calculate fluctuation of x.

    Fluctuation as defined in the ASME PTC 10-1997 is the highest reading minus
    the lowest reading divided by the mean of the readings.

    Parameters
    ----------
    x : array-like
        Array of values.

    Returns
    -------
    float
        Fluctuation of x.

    Examples
    --------
    >>> fluctuation([1, 2, 3, 4, 5])
    80.0
    >>> fluctuation([1, 1, 1, 1, 1])
    0.0
    """
    if x.mean() == 0:
        return 100
    else:
        return 100 * (x.max() - x.min()) / x.mean()


def fluctuation_data(df, window=3):
    """Calculate fluctuation of dataframe columns.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe with data to be filtered.
    window : int, optional
        Window size for rolling calculation. The default is 3.

    Returns
    -------
    pandas.DataFrame
        Dataframe with fluctuation values.


    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    >>> fluctuation_data(df)
         a    b
    0  0.0  0.0
    1  0.0  0.0
    2  0.0  0.0
    >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    >>> fluctuation_data(df, window=2)
            a    b
    0     0.0  0.0
    1  1000.0  0.0
    2  1000.0  0.0
    """
    fluctuation_df = (
        df.apply(pd.to_numeric)
        .rolling(
            window=window,
        )
        .apply(fluctuation)
        .fillna(0.0)
    )
    fluctuation_df = fluctuation_df[window - 1 :]
    return fluctuation_df


def mean_data(df, window=3):
    """Calculate the mean of dataframe columns.

    The mean is calculated using a rolling window.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe with data to be filtered.
    window : int, optional
        Window size for rolling calculation. The default is 3.

    Returns
    -------
    pandas.DataFrame
        Dataframe with mean values.


    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    >>> fluctuation_data(df)
         a    b
    0  0.0  0.0
    1  0.0  0.0
    2  0.0  0.0
    >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    >>> fluctuation_data(df, window=2)
            a    b
    0     0.0  0.0
    1  1000.0  0.0
    2  1000.0  0.0
    """
    mean_df = (
        df.apply(pd.to_numeric)
        .rolling(
            window=window,
        )
        .mean()
    )
    mean_df = mean_df[window - 1 :]
    return mean_df


def filter_data(
    df,
    window=3,
    data_type=None,
    temperature_fluctuation=0.5,
    pressure_fluctuation=2,
    speed_fluctuation=0.5,
    drop_invalid_values=True,
):
    """Filter data according to fluctuation values.

    This function performs two filters:
        1. Remove rows where the speed is zero.
        2. Remove rows where the fluctuation of the data is higher than the
        maximum fluctuation defined by the user.

    After filtering, it returns the mean value for set of values defined by
    the window size.
    Default values for maximum fluctuation are based on ASME PTC 10-1997.
    As per ASME PTC 10-1997, the minimum duration of a test point is 15 minutes.
    Assuming that we need a minimum of 3 measurements to calculate the fluctuation, the
    time span between each measurement is 7.5 minutes.

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe with data to be filtered.
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
    drop_invalid_values : bool, optional
        Drop invalid values from the dataframe.
        If false, a column 'valid' will be added to the dataframe with True for valid.
        The default is True.

    Returns
    -------
    pandas.DataFrame
        Filtered dataframe.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'a': [1, 2, 3, 4, 4.01, 4.02], 'b': [4, 5, 6, 6.01, 6.02, 6.03]})
    >>> data_type = {'a': 'pressure', 'b': 'temperature'}
    >>> filter_data(df, window=3, data_type=data_type)
    """
    fluctuation_df = fluctuation_data(df, window=window)
    mean_df = mean_data(df, window=window)
    mean_df["valid"] = True
    # filter mean_df based on fluctuation_df max values
    if drop_invalid_values:
        for column, property_type in data_type.items():
            if column in mean_df.columns:
                if property_type == "pressure":
                    max_fluctuation = pressure_fluctuation
                    # remove pressure values below 0
                    mean_df.loc[mean_df[column] < 0, column] = None
                elif property_type == "temperature":
                    max_fluctuation = temperature_fluctuation
                    # remove temperature values below 0
                    mean_df.loc[mean_df[column] < 0, column] = None
                elif property_type == "speed":
                    max_fluctuation = speed_fluctuation
                    # remove speed values below 1
                    mean_df.loc[mean_df[column] < 1, column] = None
                elif property_type == "delta_p":
                    max_fluctuation = 100
                    # remove pressure values equal to 0
                    if "delta_p" in mean_df.columns:
                        mean_df.loc[mean_df[column] <= 0, column] = None
                else:
                    raise ValueError(
                        f"Invalid data type for column {column}. "
                        "Valid data types are: pressure, temperature and speed."
                    )
                mean_df.loc[fluctuation_df[column] > max_fluctuation, column] = None
        mean_df = mean_df.dropna()
    else:
        for column, property_type in data_type.items():
            if column in mean_df.columns:
                if property_type == "pressure":
                    max_fluctuation = pressure_fluctuation
                    # remove pressure values below 0
                    mean_df.loc[mean_df[column] < 0, "valid"] = False
                elif property_type == "temperature":
                    max_fluctuation = temperature_fluctuation
                    # remove temperature values below 0
                    mean_df.loc[mean_df[column] < 0, "valid"] = False
                elif property_type == "speed":
                    max_fluctuation = speed_fluctuation
                    # remove speed values below 1
                    mean_df.loc[mean_df[column] < 1, "valid"] = False
                elif property_type == "delta_p":
                    max_fluctuation = 100
                    # remove pressure values equal to 0
                    if "delta_p" in mean_df.columns:
                        mean_df.loc[mean_df[column] <= 0, "valid"] = False
                else:
                    raise ValueError(
                        f"Invalid data type for column {column}. "
                        "Valid data types are: pressure, temperature and speed."
                    )
                mean_df.loc[fluctuation_df[column] > max_fluctuation, "valid"] = False
    return mean_df
