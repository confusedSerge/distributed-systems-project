import tomllib


def load_config(path: str = "./config/config.dev.toml") -> dict:
    """Loads the configuration from the config file.

    Args:
        path (str, optional): The path to the config file. Defaults to "config/config.toml".

    Returns:
        dict: The configuration as a dictionary.
    """
    with open(path, "rb") as f:
        config = tomllib.load(f)

    return config
