"""IO module.

yaml will be the base format to IO. Other file types will be converted to yaml
before beeing loaded.

"""

from .processing import fluctuation, fluctuation_data, mean_data, filter_data
