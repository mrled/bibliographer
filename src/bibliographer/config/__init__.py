"""Configuration file handling for bibliographer"""

import dataclasses
import pathlib
import subprocess
from typing import Callable, Generic, List, Optional, Type, TypeVar


def find_file_in_parents(filenames: list[str]) -> Optional[pathlib.Path]:
    """Find a file in the current directory or any parent directory"""
    current = pathlib.Path.cwd()
    while current != current.parent:
        for filename in filenames:
            filepath = current / filename
            if filepath.exists():
                return filepath
        current = current.parent
    return None


T = TypeVar("T")


@dataclasses.dataclass
class ConfigurationParameter(Generic[T]):
    """A generic class for parameters set in the config file"""

    key: str
    vtype: Type[T]
    default: T


class SecretValueGetter:
    """A class for getting secrets

    The user can provide either the value directly,
    or a command to run to get the value.
    """

    _getter: Callable[[], str]

    def __init__(self, getcmd: Optional[str] = None, key: Optional[str] = None):
        self._key = None
        self._getter = lambda: self._key or ""
        if key:
            self._key = key
        elif getcmd:
            self._getter = (
                lambda: subprocess.run(getcmd, shell=True, check=True, capture_output=True).stdout.decode().strip()
            )

    def get(self) -> str:
        if not self._key:
            self._key = self._getter()
        return self._key or ""


class ConfigurationParameterSet:
    """All parameters set in the config file"""

    @staticmethod
    def scalars() -> List[ConfigurationParameter]:
        """Scalar parameters are set directly"""
        return [
            ConfigurationParameter("debug", bool, False),
            ConfigurationParameter("verbose", bool, False),
            ConfigurationParameter("google_books_key", str, ""),
            ConfigurationParameter("google_books_key_cmd", str, ""),
            ConfigurationParameter("audible_auth_password", str, ""),
            ConfigurationParameter("audible_auth_password_cmd", str, ""),
            ConfigurationParameter("librofm_username", str, ""),
            ConfigurationParameter("librofm_password", str, ""),
            ConfigurationParameter("librofm_password_cmd", str, ""),
            ConfigurationParameter("raindrop_token", str, ""),
            ConfigurationParameter("raindrop_token_cmd", str, ""),
            ConfigurationParameter("individual_bibliographer_json", bool, False),
        ]

    @staticmethod
    def paths() -> List[ConfigurationParameter]:
        """Path parameters are handled specially

        Relative paths set on the command-line are resolved relative to $PWD,
        while relative paths set in the config file are resolved relative to the config file's directory.
        """
        return [
            ConfigurationParameter("default_slug_root", pathlib.Path, pathlib.Path("./bibliographer/books")),
            ConfigurationParameter("book_slug_root", pathlib.Path, None),
            ConfigurationParameter("article_slug_root", pathlib.Path, None),
            ConfigurationParameter("podcast_slug_root", pathlib.Path, None),
            ConfigurationParameter("video_slug_root", pathlib.Path, None),
            ConfigurationParameter(
                "audible_login_file", pathlib.Path, pathlib.Path("./.bibliographer-audible-auth.json")
            ),
            ConfigurationParameter("bibliographer_data_root", pathlib.Path, pathlib.Path("./bibliographer/data")),
            # Individual file overrides for apicache
            ConfigurationParameter("audible_library_file", pathlib.Path, None),
            ConfigurationParameter("kindle_library_file", pathlib.Path, None),
            ConfigurationParameter("gbooks_volumes_file", pathlib.Path, None),
            ConfigurationParameter("librofm_library_file", pathlib.Path, None),
            ConfigurationParameter("raindrop_highlights_file", pathlib.Path, None),
            # Individual file overrides for usermaps
            ConfigurationParameter("combined_library_file", pathlib.Path, None),
            ConfigurationParameter("audible_slugs_file", pathlib.Path, None),
            ConfigurationParameter("kindle_slugs_file", pathlib.Path, None),
            ConfigurationParameter("librofm_slugs_file", pathlib.Path, None),
            ConfigurationParameter("raindrop_slugs_file", pathlib.Path, None),
            ConfigurationParameter("isbn2olid_map_file", pathlib.Path, None),
            ConfigurationParameter("search2asin_file", pathlib.Path, None),
            ConfigurationParameter("wikipedia_relevant_file", pathlib.Path, None),
        ]


def resolve_path_if_relative(path: pathlib.Path | str, root: pathlib.Path | str) -> pathlib.Path:
    """Return a resolved path

    If the path is relative, resolve it relative to the root.
    """
    path = pathlib.Path(path) if isinstance(path, str) else path
    root = pathlib.Path(root) if isinstance(root, str) else root
    if not path.is_absolute():
        return root / path
    return path


def get_example_config() -> str:
    """Get a string containing an example TOML config file

    This is kind of hacky,
    and a better solution might be to use the configparser module for the config file
    because unlike TOML Python can write it natively.
    """
    result = ""
    for param in ConfigurationParameterSet.scalars():
        value = param.default
        if isinstance(value, str):
            value = f'"{value}"'
        elif isinstance(value, bool):
            # Make this look right for TOML
            value = str(value).lower()
        result += f"{param.key} = {value}\n"
    for param in ConfigurationParameterSet.paths():
        # Skip parameters with None defaults (these are optional file overrides)
        if param.default is not None:
            result += f'{param.key} = "{param.default}"\n'
    return result
