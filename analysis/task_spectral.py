# coding: UTF-8 -*-

from analysis.channels import channel, channel_range
import itertools

#import numpy as np


class task_spectral():
    """Serves as the super-class for analysis methods. Do not instantiate directly"""

    def __init__(self, task_config):
        """Initialize the object with a fixed channel list, a fixed name of the analysis to be performed
        and a fixed set of parameters for the analysis routine

        Inputs:
        =======
        channel_range: list of strings, defines the name of the channels. This should probably match the
                      name of the channels in the BP file.
        task_name: string, defines the name of the analysis to be performed
        kw_dict: dict, is passed to the analysis routine
        """


        # Stores the description of the task. This can be arbitrary
        self.description = task_config["description"]
        # Stores the name of the analysis we are going to execute
        self.analysis = task_config["analysis"]
        # Parse the reference and cross channels.
        try:
            kwargs = task_config["kwargs"]
            # These channels serve as reference for the spectral diagnostics
            self.ref_channels = channel_range.from_str(kwargs["ref_channels"][0])
            # These channels serve as the cross-data for the spectrail diagnostics
            self.x_channels = channel_range.from_str(kwargs["x_channels"][0])
        except KeyError:
            self.kwargs = None

        self.storage_scheme =  {"ref_channels": self.ref_channels.to_str(),
                                "cross_channels": self.x_channels.to_str()}


    def calculate(self, *args):
        raise NotImplementedError


class task_cross_phase(task_spectral):
    """This class calculates the cross-phase via the calculate method."""
    def __init__(self, task_config):
        super().__init__(task_config)
        self.storage_scheme["analysis_name"] = "cross_phase"



    def calculate(self, dask_client, fft_future):
        """Calculates the cross phase of signal data.
        The data is assumed to be distributed to the clients.
        Before calling this method the following steps needs to be done:
        
        Scatter time-chunk data to the cluster
        >>> data_future = client.scatter(data, broadcast=True)
        Calculate the fft. Do this with a special method, so we don't use dask array
        >>> fft_future = my_fft.do_fft(client, data_future)
        Gather the results
        >>> results = client.gather(fft_future)
        Create a dask array from the fourier-transformed data
        >>> fft_data = da.from_array(results)
        Scatter the dask array to all clients.
        >>> fft_future = client.scatter(fft_data, broadcast=True)

        Input:
        ======
        client: dask client
        fft_future: A future to the fourier-transformed data. 

        Output:
        =======
        future: dask future that holds the result of the analysis.
        """

        # Somehow dask complains when we don't define the function in the local scope.
        def cross_phase(fft_data, ch0, ch1):
            """Kernel that calculates the cross-phase between two channels.
            Input:
            ======
            fft_data: dask_array, float: Contains the fourier-transformed data. dim0: channel, dim1: Fourier Coefficients
            ch0: int, index for first channel
            ch1: int, index for second channel

            Returns:
            ========
            cp: float, the cross phase
            """    

            from math import atan2
            _tmp1 = (fft_data[ch0, :] * fft_data[ch1, :].conj()).mean().compute()
            return(atan2(_tmp1.real, _tmp1.imag).real)


        #self.futures_list = []
        # TODO: We dispatch each cross_phase calculation to a kernel function.
        # See how the performance of this method stacks against using dask array methods directly.
        # Compare to tests_analysis/test_crossphase.py

        # We need to calculate 

        self.futures_list = [dask_client.submit(cross_phase, fft_future, ch_r.idx(), ch_x.idx()) for ch_r in self.ref_channels for ch_x in self.x_channels]

        return None


class task_cross_power(task_spectral):
    """This class calculates the cross-power between two channels."""
    def __init__(self, task_config):
        super().__init__(task_config)
        self.storage_scheme["analysis_name"] = "cross_power"
 

    def calculate(self, dask_client, fft_future):
        def cross_power(fft_data, ch0, ch1):
            """Kernel that calculates the cross-power between two channels.
            Input:
            ======    
            fft_data: dask_array, float: Contains the fourier-transformed data. dim0: channel, dim1: Fourier Coefficients
            ch0: int, index for first channel
            ch1: int, index for second channel

            Returns:
            ========
            cross_power, float.
            """
            return((fft_data[ch0, :] * fft_data[ch1, :].conj()).mean().__abs__().compute())
    

        self.futures_list = [dask_client.submit(cross_power, fft_future, ch_r.idx(), ch_x.idx()) for ch_r in self.ref_channels for ch_x in self.x_channels]
        return None        


class task_coherence(task_spectral):
    """This class calculates the coherence between two channels."""
    def __init__(self, task_config):
        super().__init__(task_config)
        self.storage_scheme["analysis_name"] = "coherence"

    
    def calculate(self, dask_client, fft_future):
        def coherence(fft_data, ch0, ch1):
            """Kernel that calculates the coherence between two channels.
            Input:
            ======    
            fft_data: dask_array, float: Contains the fourier-transformed data. dim0: channel, dim1: Fourier Coefficients
            ch0: int, index for first channel
            ch1: int, index for second channel

            Returns:
            ========
            coherence, float.
            """

            from numpy import sqrt, mean, fabs
            X = fft_data[ch0, :].compute()
            Y = fft_data[ch1, :].compute()
            Gxy = fabs(mean(X * Y.conj() / sqrt(X * X.conj() * Y * Y.conj())).real)

            return(Gxy)

        self.futures_list = [dask_client.submit(coherence, fft_future, ch_r.idx(), ch_x.idx()) for ch_r in self.ref_channels for ch_x in self.x_channels]
        return None  


class task_xspec(task_spectral):
    """This class calculates the coherence between two channels."""
    def __init__(self, task_config):
        super().__init__(task_config)
        self.storage_scheme["analysis_name"] = "xspec"
    
    def calculate(self, dask_client, fft_future):
        def xspec(fft_data, ch0, ch1):
            """Kernel that calculates the coherence between two channels.
            Input:
            ======    
            fft_data: dask_array, float: Contains the fourier-transformed data. dim0: channel, dim1: Fourier Coefficients
            ch0: int, index for first channel
            ch1: int, index for second channel

            Returns:
            ========
            coherence, float.
            """

           return 0.0

        #self.futures_list = [dask_client.submit(coherence, fft_future, ch_r.idx(), ch_x.idx()) for ch_r in self.ref_channels for ch_x in self.x_channels]
        raise NotImplementedError
        return None  


class task_bicoherence(task_spectral):
    """This class calculates the bicoherence between two channels."""
    def __init__(self, task_config):
        super().__init__(task_config)
        self.storage_scheme["analysis_name"] = "xspec"
    
    def calculate(self, dask_client, fft_future):
        def bicoherence(fft_data, ch0, ch1): 
            """Kernel that calculates the bi-coherence between two channels.
            Input:
            ======    
            fft_data: dask_array, float: Contains the fourier-transformed data. dim0: channel, dim1: Fourier Coefficients
            ch0: int, index for first channel
            ch1: int, index for second channel

            Returns:
            ========
            bicoherence, float.
            """
            import numpy as np

            X = fft_data[ch0, :].compute()
            Y = fft_data[ch1, :].compute()

            





    #    # 1)
    #     if self.analysis == "cwt":
    #         raise NotImplementedError
    #     # 3)
    #     elif self.analysis == "coherence":
    #         raise NotImplementedError        
    #     # 5)
    #     elif self.analysis == "correlation":
    #         raise NotImplementedError

    #     # 6)
    #     elif self.analysis == "corr_coeff":
    #         raise NotImplementedError


    #     # 8)
    #     elif self.analysis == "skw":
    #         raise NotImplementedError

    #     # 9)
    #     elif self.analysis == "bicoherence":
    #         raise NotImplementedError

    #     print(self.futures_list)


# End of file analysis_package.py