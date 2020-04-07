# -*- coding: UTF-8 -*-

from mpi4py import MPI
import adios2
import numpy as np
import json
from contextlib import contextmanager

import logging

from streaming.adios_helpers import gen_channel_name, gen_io_name

class writer_base():
    def __init__(self, shotnr, id):
        comm = MPI.COMM_WORLD
        self.rank = comm.Get_rank()
        self.size = comm.Get_size()

        self.shotnr = shotnr
        self.id = id
        self.adios = adios2.ADIOS(MPI.COMM_SELF)
        self.IO = self.adios.DeclareIO(gen_io_name(self.rank))
        self.writer = None


    def DefineVariable(self, data_name:str, data_array:np.ndarray):
        """Wrapper around DefineVariable

        Input:
        ======
        data_name: Name of data
        data_array: array with same shape and data type that will be sent in 
                             all subsequent steps
        """
        self.variable =  self.IO.DefineVariable(data_name, data_array, 
                                                data_array.shape, # shape
                                                list(np.zeros_like(data_array.shape, dtype=int)),  # start 
                                                data_array.shape, # count
                                                adios2.ConstantDims)

        logging.info(f"Defined A2 variable {data_name}")

        return(self.variable)


    def DefineAttributes(self, attrsname: str, attrs: dict):
        """Wrapper around DefineAttribute, takes in dictionary and writes each as an Attribute
        NOTE: Currently no ADIOS cmd to use dict, pickle to string

        Input:
        ======
        attrs: Dictionary of key,value pairs to be put into attributes

        """
        attrsstr = json.dumps(attrs)
        self.attrs = self.IO.DefineAttribute(attrsname,attrsstr)

    def Open(self):
        """Opens a new channel. 
        """

        self.channel_name = gen_channel_name(self.shotnr, self.id, 0)  

        if self.writer is None:
            self.writer = self.IO.Open(self.channel_name, adios2.Mode.Write)

    def BeginStep(self):
        """wrapper for writer.BeginStep()"""
        return self.writer.BeginStep()

    def EndStep(self):
        """wrapper for writer.EndStep()"""
        return self.writer.EndStep()

    def put_data(self, data:np.ndarray):
        """Opens a new stream and send data through it
        Input:
        ======
        var: adios2 object from DefineVariable
        data: ndarray. Data to send)
        """

        if self.writer is not None:
            self.writer.Put(self.variable, data, adios2.Mode.Sync)

    #RMC - I find relying on this gives segfaults in bp files.
    #Better to explicitly close it in the main program
    #def __del__(self):
    #    """Close the IO."""
    #    if self.writer is not None:
    #        self.writer.Close()

    @contextmanager
    def step(self):
        """ This is for using with with keyword """
        self.writer.BeginStep()
        try:
            yield self
        finally:
            self.writer.EndStep()


class writer_dataman(writer_base):
    def __init__(self, shotnr, id):
        super().__init__(shotnr, id)
        self.IO.SetEngine("DataMan")
        dataman_port = 12300 + self.rank
        transport_params = {"IPAddress": "203.230.120.125",
                            "Port": "{0:5d}".format(dataman_port),
                            "OpenTimeoutSecs": "600",
                            "Verbose": "20"}
        self.IO.SetParameters(transport_params)

class writer_bpfile(writer_base):
    def __init__(self, shotnr, id):
        super().__init__(shotnr, id)
        self.IO.SetEngine("BP4")
        
class writer_sst(writer_base):
    def __init__(self, shotnr, id):
        super().__init__(shotnr, id)
        self.IO.SetEngine("SST")
        self.IO.SetParameter("OpenTimeoutSecs", "600")

class writer_gen(writer_base):
    """ General writer to be initialized by name and parameters
    """
    def __init__(self, shotnr, id, engine, params):
        super().__init__(shotnr, id)
        self.IO.SetEngine(engine)
        _params = params
        if engine.lower() == "dataman":
            logging.info("DATAMAN!!!")

            dataman_port = 12300 + self.rank
            _params.update(Port = "{0:5d}".format(dataman_port))
        self.IO.SetParameters(_params)

# End of file a2_sender.py