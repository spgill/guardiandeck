# stdlib imports
import json
import os
import pathlib
import sys

# vendor imports

# local imports


# Default config data
_configDefault = {
    'api_key':          '',  # Bungie developer API key
}

# The blank canvas that everything should load from
_config = {}

# Resolve a path for the config file
_path = pathlib.Path(
    os.environ.get(
        'GUARDIANDECK_CONFIG',
        '~/.guardiandeck.json'
    )
).expanduser()


def _reload():
    # Reset the mutable config
    _config = {}

    # Update the mutable config with the default config data
    _config.update(_configDefault)

    # Unpack config file into default config
    _config.update(
        json.load(_path.open('r'))
    )

    # Store config vars into the module namespace
    module = sys.modules[__name__]
    for key, value in _config.items():
        setattr(module, key, value)


# Always run _reload it once on module load
_reload()
