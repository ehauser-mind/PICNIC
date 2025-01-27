from pathlib import Path


def get_path_to_jsons():
    """
    Locate the default_parameters json files and return a Path to them.
    """

    return Path(__file__).parent.absolute() / "default_parameters"


def get_path_to_json(keyword):
    """
    Locate a specific default_parameters json file and return a Path to it.
    """

    return get_path_to_jsons() / f"{keyword}.json"
