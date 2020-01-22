# -*- coding: UTF-8 -*-

"""
This processor implements the one-to-one model using mpi

main loop is based on this tutorial:
https://www.roguelynn.com/words/asyncio-true-concurrency/
Jong's threaded queue code
Dask codes


To run on an interactive node
srun -n 4 python -m mpi4py.futures processor_mpi.py  --config configs/test_crossphase.json

"""

#from mpi4py import MPI 
#from mpi4py.futures import MPIPoolExecutor
import sys
sys.path.append("/home/rkube/software/adios2-release_25/lib64/python3.7/site-packages")


import logging
import random
import string
import queue
import concurrent.futures
import threading

import numpy as np
import attr
import timeit

import json
import argparse
import adios2

from backends.backend_numpy import backend_numpy
from readers.reader_mpi import reader_bpfile
from analysis.task_fft import task_fft_scipy
from analysis.tasks_mpi import task_cross_correlation, task_cross_phase, task_cross_power, task_coherence, task_bicoherence, task_skw, task_xspec


# task_object_dict maps the string-value of the analysis field in the json file
# to an object that defines an appropriate analysis function.
task_object_dict = {"cross_correlation": task_cross_correlation,
                    "cross_phase": task_cross_phase,
                    "cross_power": task_cross_power,
                    "coherence": task_coherence,
                    "bicoherence": task_bicoherence,
                    "xspec": task_xspec,
                    "cross_correlation": task_cross_correlation,
                    "skw": task_skw}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


@attr.s ``
class AdiosMessage:
    """Storage class used to transfer data from Kstar(Dataman) to
    local PoolExecutor"""
    tstep_idx = attr.ib(repr=True)
    data       = attr.ib(repr=False)


#def consume(Q, store_backend, my_fft, task_list, cfg):
def consume(Q, executor, my_fft, task_list, futures_list):
    """Executed by a local thread. Dispatch work items from the
    Queue to the PoolExecutor"""

    while True:
        msg = Q.get()
        logging.info(f"Consuming {msg}")

        # If we get our special break message, we exit
        if msg.tstep_idx == None:
            Q.task_done()
            break

        # Step 1) Perform STFT. TODO: We may distribute this among the tasks
        tic_fft = timeit.default_timer()
        fft_data = my_fft.do_fft_local(msg.data)
        toc_fft = timeit.default_timer()
        logging.info(f"FFT took {(toc_fft - tic_fft):6.4f}s")


        # Step 2) Distribute the work via PoolExecutor 
        for task in task_list:
            task.calculate(executor, fft_data)


        #with MPIPoolExecutor(max_workers=256) as executor:
        #    tic_tasks = timeit.default_timer()
        #    for task in task_list:
        #        logging.info("Executing task")
        #        task.calculate(executor, fft_data)
        #        task.store_data(store_backend, {"tstep": msg.tstep_idx})
        #
        #    toc_tasks = timeit.default_timer()
        #    logging.info(f"Performing analysis and storing took {(toc_tasks - tic_tasks):6.4f}s")
        Q.task_done()


def main():
    # Parse command line arguments and read configuration file
    parser = argparse.ArgumentParser(description="Receive data and dispatch analysis tasks to a dask queue")
    parser.add_argument('--config', type=str, help='Lists the configuration file', default='config_one_to_one_fluctana.json')
    args = parser.parse_args()
    with open(args.config, "r") as df:
        cfg = json.load(df)
        df.close()

    # Create the FFT task
    cfg["fft_params"]["fsample"] = cfg["ECEI_cfg"]["SampleRate"] * 1e3
    my_fft = task_fft_scipy(10_000, cfg["fft_params"], normalize=True, detrend=True)
    fft_params = my_fft.get_fft_params()

    # Create ADIOS reader object
    reader = reader_bpfile(cfg["shotnr"], cfg["ECEI_cfg"])
    reader.Open(cfg["datapath"])

    # Create storage backend
    store_backend = backend_numpy("/home/rkube/repos/delta/test_data")

    # Create a global executor
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=30)


    # Create the task list
    task_list = []
    for task_config in cfg["task_list"]:
        task_list.append(task_object_dict[task_config["analysis"]](task_config, fft_params, cfg["ECEI_cfg"]))
        task_list[-1].store_metadata(store_backend)

    dq = queue.Queue()
    msg = None

    worker = threading.Thread(target=consume, args=(dq, executor, my_fft, task_list))
    worker.start()

    logging.info(f"Starting main loop")
    while True:
        stepStatus = reader.BeginStep()

        if stepStatus:
            # Read data
            stream_data = reader.Get(save=False)
            tb = reader.gen_timebase()

            # Generate message id and publish is
            msg = AdiosMessage(tstep_idx=reader.CurrentStep(), data=stream_data)
            dq.put(msg)
            logging.info(f"Published message {msg}")

        if reader.CurrentStep() > 5:
            logging.info(f"Exiting: StepStatus={stepStatus}")
            dq.put(AdiosMessage(tstep_idx=None, data=None))
            break

    worker.join()
    dq.join()
    executor.shutdown()

if __name__ == "__main__":
    main()


# End of file processor_dask_mp.yp