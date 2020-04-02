#-*- coding: UTF-8 -*-

#from mpi4py import MPI 
import adios2
import numpy as np 


class reader_base():
    def __init__(self, shotnr, id):
        #comm = MPI.COMM_WORLD
        self.rank = 0
        self.size = 1

        self.shotnr = shotnr
        self.id = id
        self.adios = adios2.ADIOS()
        self.IO = self.adios.DeclareIO("stream_{0:03d}".format(self.rank))
        print("reader_base.__init__(): rank = {0:02d}".format(self.rank))


    def Open(self, worker_id=None):
        """Opens a new channel"""
        if worker_id is None:
            self.channel_name = gen_channel_name(self.shotnr, self.id, 0)
        else:
            self.channel_name = gen_channel_name(self.shotnr, self.worker_id, self.rank)
        print (f">>> Opening ...{self.channel_name}")

        if self.reader is None:
            self.reader = self.IO.Open(self.channel_name, adios2.Mode.Read)


    def BeginStep(self):
        """wrapper for reader.BeginStep()"""
        return self.reader.BeginStep()


    def InquireVariable(self, varname):
        """Wrapper for IO.InquireVariable"""
        return self.IO.InquireVariable(varname)


    def get_data(self, varname):
        """Attempt to load `varname` from the opened stream"""

        var = self.IO.InquireVariable(varname)
        io_array = np.zeros(np.prod(var.Shape()), dtype=np.float)
        self.reader.Get(var, io_array, adios2.Mode.Sync)

        return(io_array)


    def CurrentStep(self):
        """Wrapper for IO.CurrentStep()"""
        return self.reader.CurrentStep()

    
    def EndStep(self):
        """Wrapper for reader.EndStep()"""
        self.reader.EndStep()


class reader_dataman(reader_base):
    def __init__(self, shotnr, id):
        super().__init__(shotnr, id)
        self.IO.SetEngine("DataMan")
        self.reader = None

        dataman_port = 12300 + self.rank
        transport_params = {"IPAddress": "203.230.120.125",
                            "Port": f"{dataman_port:5d}",
                            "OpenTimeoutSecs": "600",
                            "AlwaysProvideLatestTimestep": "true"}
        self.IO.SetParameters(transport_params)
        print (">>> reader_dataman ... ")


class reader_bpfile(reader_base):
    def __init__(self, shotnr, id):
        super().__init__(shotnr, id)
        self.IO.SetEngine("BP4")
        self.IO.SetParameter("OpenTimeoutSecs", "600")
        self.reader = None
        print (">>> reader_bpfile ... ")

class reader_sst(reader_base):
    def __init__(self, shotnr, id):
        super().__init__(shotnr, id)
        self.IO.SetEngine("SST")
        self.IO.SetParameters({"OpenTimeoutSecs": "600.0"})
        self.reader = None
        print (">>> reader_sst ... ")

class reader_gen(reader_base):
    """ General reader to be initialized by name and parameters
    """
    def __init__(self, shotnr, id, engine, params):
        super().__init__(shotnr, id)
        self.IO.SetEngine(engine)
        _params = params
        if engine.lower() == "dataman":
            dataman_port = 12300 + self.rank
            _params.update(Port = f"{dataman_port:5d}")
        self.IO.SetParameters(_params)
        self.reader = None

# end of file readers.py
