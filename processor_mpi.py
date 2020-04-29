# -*- coding: UTF-8 -*-

"""
This processor implements the one-to-one model using mpi

main loop is based on:
* https://www.roguelynn.com/words/asyncio-true-concurrency/
* Jong's threaded queue code
* Dask codes


To run on an interactive node
srun -n 4 python -m mpi4py.futures processor_mpi.py  --config configs/test_crossphase.json

"""

import os
from mpi4py import MPI
from mpi4py.futures import MPIPoolExecutor, MPICommExecutor
import sys
#sys.path.append("/global/homes/r/rkube/software/adios2-current/lib64/python3.7/site-packages")

import logging
import logging.config
import random
import string
import queue
#import concurrent.futures
import threading

import numpy as np
import attr
import timeit
import datetime

import json
import yaml
import argparse
import adios2

import backends

<<<<<<< HEAD
from streaming.reader_mpi import reader_bpfile, reader_dataman, reader_sst
=======
from streaming.reader_mpi import reader_gen
>>>>>>> 8d1396632742289d44d8722271da3ab0c2de0768
from analysis.task_fft import task_fft_scipy
from analysis.tasks_mpi import task_spectral
from analysis.channels import channel_range


@attr.s 
class AdiosMessage:
    """Storage class used to transfer data from Kstar(Dataman) to
    local PoolExecutor"""
    tstep_idx = attr.ib(repr=True)
    data      = attr.ib(repr=False)


cfg = {}


def consume(Q, executor, my_fft, task_list):
    """Executed by a local thread. Dispatch work items from the
    Queue to the PoolExecutor"""

    logger = logging.getLogger('simple')
    global cfg

    comm  = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    while True:
        msg = Q.get()
        # If we get our special break message, we exit
        if msg.tstep_idx == None:
            Q.task_done()
            break

        # Step 1) Perform STFT. TODO: We may distribute this among the tasks
        tic_fft = timeit.default_timer()
        fft_data = my_fft.do_fft_local(msg.data)
        toc_fft = timeit.default_timer()
        logger.info(f"rank {rank}: tidx={msg.tstep_idx}: FFT took {(toc_fft - tic_fft):6.4f}s")

        # Step 2) Distribute the work via the executor 
        for task in task_list:
            #task.calc_and_store(executor, fft_data, msg.tstep_idx, cfg)
            task.submit(executor, fft_data, msg.tstep_idx, cfg)

        Q.task_done()
        logger.info(f"rank {rank}: Consumed {msg}")


def main():
    # Parse command line arguments and read configuration file
    parser = argparse.ArgumentParser(description="Receive data and dispatch analysis tasks to a mpi queue")
    parser.add_argument('--config', type=str, help='Lists the configuration file', default='configs/config_null.json')
    parser.add_argument('--benchmark', action="store_true")
    args = parser.parse_args()

    global cfg

    with open(args.config, "r") as df:
        cfg = json.load(df)
        df.close()
    
    # Load logger configuration from file: 
    # http://zetcode.com/python/logging/
    with open('configs/logger.yaml', 'r') as f:
        log_cfg = yaml.safe_load(f.read())
    logging.config.dictConfig(log_cfg)

    comm  = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()


    # Create a global executor
    #executor = concurrent.futures.ThreadPoolExecutor(max_workers=60)
    #executor = MPIPoolExecutor(max_workers=24)

    adios2_varname = channel_range.from_str(cfg["transport"]["channel_range"][0])

    with MPICommExecutor(MPI.COMM_WORLD) as executor:
        if executor is not None:

            logger = logging.getLogger('simple')
            logger.info(f"Starting up. Using adios2 from {adios2.__file__}")
            cfg['run_id'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            logger.info(f"Starting run {cfg['run_id']}")
    
            # Instantiate a storage backend and store the run configuration and task configuration
            if cfg['storage']['backend'] == "numpy":
                store_backend = backends.backend_numpy(cfg['storage'])
            elif cfg['storage']['backend'] == "mongo":
                store_backend = backends.backend_mongodb(cfg)
            elif cfg['storage']['backend'] == "null":
                store_backend = backends.backend_null(cfg['storage'])

            store_backend.store_one({"run_id": cfg['run_id'], "run_config": cfg})

            # Create the FFT task
            cfg["fft_params"]["fsample"] = cfg["ECEI_cfg"]["SampleRate"] * 1e3
            my_fft = task_fft_scipy(10_000, cfg["fft_params"], normalize=True, detrend=True)
            fft_params = my_fft.get_fft_params()

            # Create ADIOS reader object
<<<<<<< HEAD
            if cfg["transport"]["engine"].lower() == "bp4":
                reader = reader_bpfile(cfg)
            elif cfg["transport"]["engine"].lower() == "dataman":
                reader = reader_dataman(cfg)
            elif cfg["transport"]["engine"].lower() == "sst":
                reader = reader_sst(cfg)
            else:
                raise KeyError(f"cfg[transport][engine] = {cfg['transport']['engine']}. But it should be either bp4 or dataman")
=======
            reader = reader_gen(cfg)
>>>>>>> 8d1396632742289d44d8722271da3ab0c2de0768

            # Create the task list
            logger.info(f"Storing metadata")
            task_list = []
            for task_config in cfg["task_list"]:
                task_list.append(task_spectral(task_config, fft_params, cfg["ECEI_cfg"]))
                store_backend.store_metadata(task_config, task_list[-1].get_dispatch_sequence())
                
            dq = queue.Queue()
            msg = None

            tic_main = timeit.default_timer()

            worker = threading.Thread(target=consume, args=(dq, executor, my_fft, task_list))
            worker.start()

            # reader.Open() is blocking until it opens the data file or receives the
            # data stream. Put this right before entering the main loop
            logger.info(f"{rank} Waiting for generator")
            reader.Open()
            last_step = 0

            rx_list = []
            while True:
                stepStatus = reader.BeginStep()
                if last_step == reader.CurrentStep():
                    continue

                if stepStatus:
                    # Read data
                    stream_data = reader.Get(adios2_varname, save=True)
                    rx_list.append(reader.CurrentStep())

                    # Generate message id and publish is
                    msg = AdiosMessage(tstep_idx=reader.CurrentStep(), data=stream_data)
                    dq.put(msg)
<<<<<<< HEAD
                    logger.info(f"rank{rank} Published message {msg}")
                else:
                    logger.info(f"rank{rank} Exiting: StepStatus={stepStatus}")
                    break

                if reader.CurrentStep() >= 90:
                    logger.info(f"rank{rank} Exiting: StepStatus={stepStatus}")
=======
                    logger.info(f"Published message {msg}")
                    reader.EndStep()
                else:
                    logger.info(f"Exiting: StepStatus={stepStatus}")
>>>>>>> 8d1396632742289d44d8722271da3ab0c2de0768
                    dq.put(AdiosMessage(tstep_idx=None, data=None))
                    break
                step = step + 1

                #if reader.CurrentStep() >= 5:
                #    logger.info(f"Exiting: StepStatus={stepStatus}")
                #    dq.put(AdiosMessage(tstep_idx=None, data=None))
                #    break

                last_step = reader.CurrentStep()

            logger.info("Exiting main loop")
            worker.join()
            logger.info("Workers have joined")
            dq.join()
            logger.info("Queue joined")

            # Shotdown the executioner
            executor.shutdown(wait=True)

            toc_main = timeit.default_timer()
            logger.info(f"Run {cfg['run_id']} finished in {(toc_main - tic_main):6.4f}s")
            logger.info(f"Processed time_chunks {rx_list}")
    # End MPICommExecutor section

if __name__ == "__main__":
    main()

<<<<<<< HEAD
# End of file processor_mpi.py
=======

# End of file processor_mpi.py
>>>>>>> 8d1396632742289d44d8722271da3ab0c2de0768
