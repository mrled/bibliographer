"""Configuration file handling for bibliographer"""

import dataclasses
import pathlib
import subprocess
import textwrap
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

# The current config file version
CURRENT_VERSION = "2.3"

# Config file names for the current version
CONFIG_FILENAMES = ["bibliographer.conf", ".bibliographer.conf"]

# Config file names that default to version 2.1 if no version key is present
_LEGACY_21_CONFIG_FILENAMES = ["bibliographer.toml", ".bibliographer.toml"]

# Migration notes for upgrading from one version to another
# Key is the version being upgraded FROM
MIGRATION_NOTES: Dict[str, str] = {
    "2.1": textwrap.dedent(f"""\
        This is the first versioned config file format and requires some changes:
        - Rename the config file to one of {CONFIG_FILENAMES}
        - Check and update any path settings: bibliographer_data_root, default_slug_root, book_slug_root, article_slug_root, podcast_slug_root, video_slug_root
    """),
    "2.2": """Explicitly set the 'version' key to "2.3" in the config file.""",
}


def get_migration_note(from_version: str) -> Optional[str]:
    """Get migration notes for upgrading from a specific version.

    Args:
        from_version: The version to upgrade from

    Returns:
        Migration notes string, or None if no notes available
    """
    return MIGRATION_NOTES.get(from_version)


def detect_config_version(config_path: Optional[pathlib.Path], config_data: Dict[str, Any]) -> Optional[str]:
    """Detect the version of a config file.

    Version detection logic:
    1. If config_data contains a 'version' key, use that value
    2. If no 'version' key but filename is 'bibliographer.toml' or '.bibliographer.toml',
       default to version "2.1" (legacy unversioned config)
    3. If no config file exists, return None

    Args:
        config_path: Path to the config file, or None if no config file
        config_data: Parsed config data dictionary

    Returns:
        The detected version string, or None if no config file
    """
    if config_path is None:
        return None

    # Check if this is a legacy config file, all of which were unversioned
    if config_path.name in _LEGACY_21_CONFIG_FILENAMES:
        return "2.1"

    # Check for explicit version key in config data
    if "version" in config_data:
        return str(config_data["version"])

    # The 2.2 config file format did not require a version key
    return "2.2"


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


def find_config_file() -> Optional[pathlib.Path]:
    """Find the config file for the current version.

    Searches for config files in the current directory and parent directories,
    using the filenames defined in CONFIG_FILENAMES for the current version.

    Returns:
        Path to the config file if found, None otherwise
    """
    return find_file_in_parents(CONFIG_FILENAMES + _LEGACY_21_CONFIG_FILENAMES)


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
                "audible_login_file",
                pathlib.Path,
                pathlib.Path("./.bibliographer-audible-auth.json"),
            ),
            ConfigurationParameter(
                "bibliographer_data_root",
                pathlib.Path,
                pathlib.Path("./bibliographer/data"),
            ),
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
    result = f'version = "{CURRENT_VERSION}"\n\n'
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
