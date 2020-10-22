# -*- Encoding: UTF-8 -*-

"""Helper functions common to all data models"""


import numpy as np
from itertools import filterfalse

import data_models.kstar_ecei
from data_models.channels_2d import channel_2d, channel_range


class data_model_generator():
    """Returns the data model for a given configuration"""
    def __init__(self, cfg_diagnostic: dict):
        """Sets up data model generation.

        Parameters:
        ===========
        cfg_diagnostic: dict,
                        Diagnostic section of the config file
        """
        self.cfg = cfg_diagnostic

        if self.cfg["name"] == "kstarecei":
            self.data_type = data_models.kstar_ecei.ecei_chunk
        elif self["name"] == "nstxgpi":
            self.data_type = None
        else:
            raise ValeuError(f"No data model for diagnotisc {cfg['diagnostic']['name']}")

    def new_chunk(self, stream_data: np.array, chunk_idx: int):
        """Generates a data model from new chunk of streamed data.

        Parameters
        ----------
        stream_data : np.array
                      New data chunk read from reader_gen.

        """

        # Generate a time-base and a data model
        if self.cfg["name"] == "kstarecei":
            # Adapt configuration file parameters for use in timebase_streaming
            # constructor
            t_start, t_end, _ = self.cfg["parameters"]["TriggerTime"]
            f_sample = 1e3 * self.cfg["parameters"]["SampleRate"]
            samples_per_chunk = self.cfg["datasource"]["chunk_size"]

            tb = data_models.kstar_ecei.timebase_streaming(t_start, t_end, f_sample,
                                               samples_per_chunk, chunk_idx)

            return data_models.kstar_ecei.ecei_chunk(stream_data, tb)

        elif self.cfg["name"] == "nstxgpi":
            raise NotImplementedError("NSTX chunk generation not implemented")

        else:
            raise NameError(f"Data model name not understood: {self.cfg['diagnostic']['name']}")


def gen_channel_name(cfg_diagnostic: dict) -> str:
    """Generates a name for the ADIOS channel from the diagnostic configuration"""

    if cfg_diagnostic["name"] == "kstarecei":
        experiment = "KSTAR"
        diagnostic = "ECEI"
        shotnr = int(cfg_diagnostic["shotnr"])
        channel_rg = cfg_diagnostic["datasource"]["channel_range"][0]

        channel_name = f"{experiment}_{shotnr:05d}_{diagnostic}_{channel_rg}"
        return channel_name

    else:
        raise ValueError


def gen_channel_range(cfg_diagnostic: dict, chrg: list) -> channel_range:
    """Generates channel ranges for the diagnostics"""

    print(cfg_diagnostic)
    if cfg_diagnostic["name"] == "kstarecei":
        ch1 = channel_2d(chrg[0], chrg[1], 24, 8, order='horizontal')
        ch2 = channel_2d(chrg[2], chrg[3], 24, 8, order='horizontal')
        return channel_range(ch1, ch2)

    elif cfg_diagnostic["name"] == "nstxgpi":
        return None

    else:
        raise ValueError



def gen_var_name(cfg: dict) -> str:
    """Generates a variable name from the diagnostic configuration"""

    if cfg["diagnostic"]["name"] == "kstarecei":
        return cfg["diagnostic"]["datasource"]["channel_range"]

    else:
        raise ValueError


def unique_everseen(iterable, key=None):
    """List unique elements, preserving order. Remember all elements ever seen.
    Taken from https://docs.python.org/3/library/itertools.html#itertools-recipes"""

    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


class normalize_mean():
    """Performs normalization"""

    def __init__(self, offlev, offstd):
        """Stores offset and standard deviation of normalization time series.
        Parameters:
        -----------
        offlev....: ndarray, channel-wise offset level
        offstd....: ndarray, channel-wise offset standard deviation
        """
        self.offlev = offlev
        self.offstd = offstd

        self.siglev = None
        self.sigstd = None

    def __call__(self, data):
        """Normalizes data

        Parameters:
        -----------
        data......: array.
                    dim0...-2: spatial data. dim -1: Time
        """

        # For these asserts to hold we need to calculate offlev,offstd with keepdims=True

        assert(self.offlev.shape[:-1] == data.shape[:-1])
        assert(self.offstd.shape[:-1] == data.shape[:-1])
        assert(self.offlev.ndim == data.ndim)
        assert(self.offstd.ndim == data.ndim)

        data[:] = data - self.offlev
        self.siglev = np.median(data, axis=-1, keepdims=True)
        self.sigstd = data.std(axis=-1, keepdims=True)

        data[:] = data / data.mean(axis=-1, keepdims=True) - 1.0

        return None

# End of file helpers.py
