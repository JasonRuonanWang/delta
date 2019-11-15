#-*- coding: UTF-8 -*-

"""
This processor implements the one-to-one model. Code is adapted from processor_dask_one_to_one.py
to use the kstar fluctana object class.

The processor runs as a single-task program and receives data from a single
Dataman stream. 
The configuration file defines a list of analysis routines together with a list of channel
data on which to apply a given routine. 
In the receive loop, this data is gathered and dispatched into a task queue


The task queue is implemented using Dask. Run this implementation within an interactive session.
Documentation on how to run with dask on nersc is here: https://docs.nersc.gov/programming/high-level-environments/python/dask/


On an interactice node:
1. Start the dask scheduler:
python -u $(which dask-scheduler) --scheduler-file $SCRATCH/scheduler.json

2. Start the worker tasks
srun -u -n 10 python -u $(which dask-worker) --scheduler-file $SCRATCH/scheduler.json --nthreads 1 &

3. Launch the dask program:
python -u processor_dask.py

"""

# Add project directory into the python path so that imports work in code that is
# distributed to dask worker clients
import sys
sys.path.append("/global/homes/r/rkube/repos/delta")

import numpy as np 

import json
import argparse
from distributed import Client, progress

from backends.mongodb import mongodb_backend
from readers.reader_one_to_one import reader_bpfile
from analysis.task_fluctana import task_fluctana


# This object manages storage to a backend.
mongo_client = mongodb_backend()
# Interface to worker nodes
dask_client = Client(scheduler_file="/global/cscratch1/sd/rkube/scheduler.json")


# Parse command line arguments and read configuration file
parser = argparse.ArgumentParser(description="Receive data and dispatch analysis tasks to a dask queue")
parser.add_argument('--config', type=str, help='Lists the configuration file', default='config_one_to_one_fluctana.json')
args = parser.parse_args()

with open(args.config, "r") as df:
    cfg = json.load(df)
    df.close()

# Build list of analysis tasks that are performed at any given time step
task_list = []
for task_config in cfg["task_list"]:
    task_list.append(task_fluctana(cfg["shotnr"], task_config))


datapath = cfg["datapath"]
shotnr = cfg["shotnr"]
reader = reader_bpfile(shotnr)
reader.Open(cfg["datapath"])

print("Starting main loop")
s = 0

while(True):
    stepStatus = reader.BeginStep()

    # Iterate over the task list and update the required data at the current time step
    if stepStatus:
        print("ok")
        task_futures = []

        # generate a dummy time-base for the data of the current chunk
        dummy_tb = np.arange(0.0, 1e-2, 1e-6) * float(s)
        for task in task_list:
            # Create a channel list object for the current task
            #
            ecei_data = reader.Get(task.ch_list)

            print(np.shape(ecei_data))
            #task.update_data(ecei_data, dummy_tb)
            #for channel in task.channel_list:
            #    ecei_data = reader.Get("ECEI_" + channel)
            #    task.update_data(ecei_data, channel, dummy_tb)

            #task.create_task_object()

            #task_futures.append(task.calculate(dask_client))
            #task.dispatch(dask_client)

            task_futures.append(dask_client.submit(task.method(), task.fluct_data))

    else:
        print("End of stream")
        break

    reader.EndStep()

#     # Pass the task object to our backend for storage
#     for task in task_list:
#         mongo_client.store(task)

    for task, future in zip(task_list, task_futures):
        print(task, future)

    # Do only 10 time steps for now
    s -= -1
    if s >= 2:
        break


# End of file processor_dask_one_to_one.py.