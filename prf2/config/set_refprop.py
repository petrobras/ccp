"""Set refprop path and configuration.

Will try to find REFPROP with os variable RPPREFIX. If not there, will look in
the current folder.

"""
import os
from pathlib import Path
import CoolProp.CoolProp as CP


class REFPROP:
    """Class used to set refprop and store configurations."""
    def __init__(self, path=None):
        if path is None:
            try:
                path = Path(os.environ['RPPREFIX'])
            except KeyError:
                path = Path.cwd()

        if os.name is 'posix':
            shared_library = 'librefprop.so'
        else:
            shared_library = 'REFPRP64.DLL'

        library_path = path / shared_library

        if not library_path.is_file():
            raise FileNotFoundError(f'{library_path}.\nREFPROP not configured.')

        self.library_path = library_path
        self.set_refprop_path(library_path)
        self.__version__ = CP.get_global_param_string('REFPROP_version')

    def set_refprop_path(self, path=None):
        CP.set_config_string(CP.ALTERNATIVE_REFPROP_PATH,
                             (path / self.library_path))
