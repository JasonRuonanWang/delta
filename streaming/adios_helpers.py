# -*- Encoding: UTF-8 -*-

"""
Helper functions for managing ADIOS2
"""


def gen_io_name(rank: int):
    """Generates an IO name for ADIOS2 objects"""

    return f"stream_{rank:03d}"

def gen_channel_name(shotnr: int, channel_id: int, rank: int):
    """Generates a channel ID for readers."""

    return f"{shotnr:05d}_ch{channel_id:03d}_r{rank:03d}.bp"

def gen_channel_name_v2(shotnr: int, channel_rg: str):
    """Generates a channel ID using channel range strings. (see analysis/channels.py)"""

    return f"{shotnr:05d}_ch{channel_rg:s}.bp"


# End of file adios_helpers.py