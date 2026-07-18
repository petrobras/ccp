"""Helpers to save/load ccp objects to/from files.

The file format is determined by the file suffix (e.g. ``.toml`` or
``.json``). Classes get file persistence by inheriting from
:class:`Serializable` and implementing ``to_dict``/``from_dict``.
"""

import json
import os
from pathlib import Path

import toml

_FORMATS = {
    ".toml": (toml.load, toml.dump),
    ".json": (json.load, lambda data, file: json.dump(data, file, indent=2)),
}


def _dispatch(file_name):
    """Return (path, (load, dump)) for a file based on its suffix."""
    file_path = Path(file_name)
    try:
        return file_path, _FORMATS[file_path.suffix]
    except KeyError:
        raise ValueError(
            f"Unsupported file format {file_path.suffix!r} for {file_path.name!r}. "
            f"Supported formats: {', '.join(sorted(_FORMATS))}."
        ) from None


def save_dict(data, file_name):
    """Save a dict to a file, with format given by the file suffix.

    The write is atomic: data is written to a temporary file which is then
    renamed, so an error during serialization never truncates an existing file.

    Parameters
    ----------
    data : dict
        Data to save.
    file_name : str or pathlib.Path
        File name ending in one of the supported suffixes (.toml, .json).
    """
    file_path, (_, dump) = _dispatch(file_name)
    tmp_path = file_path.with_name(file_path.name + ".tmp")
    try:
        with open(tmp_path, mode="w") as f:
            dump(data, f)
        os.replace(tmp_path, file_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def load_dict(file_name):
    """Load a dict from a file, with format given by the file suffix.

    Parameters
    ----------
    file_name : str or pathlib.Path
        File name ending in one of the supported suffixes (.toml, .json).

    Returns
    -------
    data : dict
        Data loaded from the file.
    """
    file_path, (load, _) = _dispatch(file_name)
    with open(file_path) as f:
        return load(f)


class Serializable:
    """Mixin that adds file persistence to a class.

    Subclasses must implement ``to_dict()`` and ``from_dict(parameters)``;
    ``save``/``load`` then work for every supported file format.
    """

    def to_dict(self):
        raise NotImplementedError

    @classmethod
    def from_dict(cls, dict_parameters):
        raise NotImplementedError

    def save(self, file_name):
        """Save object to a file.

        The file format is defined by the file_name suffix
        (e.g. "point.toml" or "point.json").
        The file records the ccp version that wrote it in a "ccp_version"
        key, so that future versions can migrate old files if the format
        changes.

        Parameters
        ----------
        file_name : str or pathlib.Path
            File name ending in one of the supported suffixes (.toml, .json).
        """
        import ccp

        save_dict({"ccp_version": ccp.__version__, **self.to_dict()}, file_name)

    @classmethod
    def load(cls, file_name):
        """Load object from a file.

        The file format is defined by the file_name suffix
        (e.g. "point.toml" or "point.json").

        Parameters
        ----------
        file_name : str or pathlib.Path
            File name ending in one of the supported suffixes (.toml, .json).

        Returns
        -------
        object
            Instance of the class loaded from the file.
        """
        return cls.from_dict(load_dict(file_name))
