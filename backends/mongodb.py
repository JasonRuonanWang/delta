#Coding: UTF-8 -*-

from pymongo import MongoClient
from bson.binary import Binary
import datetime

# Schemes that describe how results from a given analysis is stored in the database
schemes_dict={"power_spectrum": lambda task, result: {"routine_name": task.task_name,
                                                      "channel": task.channel_list[0],
                                                      "kwargs": task.kw_dict,
                                                      "f": result[0].tolist(),
                                                      "Pxx": result[1].tolist()}}


class mongodb_backend():
    def __init__(self, rank=0, channel_list=[]):
        # Connect to mongodb
        self.client = MongoClient("mongodb://mongodb07.nersc.gov/delta-fusion", 
                                  username="delta-fusion_admin",
                                  password="eeww33ekekww212aa")

        self.db = self.client.get_database()
        self.collection = self.db.test_analysis
        print("***mongodb_backend*** Connected to database {0:s}".format(self.db.name))
        

    def store(self, task, dummy=True):
        """Stores data from an analysis task in the mongodb backend.

        The data anylsis results from analysis_task object are evaluated in this method.

        Input:
        ======
        task: analysis_task object. 
        dummy: bool. If true, do not insert the item into the database
        
        Returns:
        ========
        None
        """

        storage_scheme = schemes_dict[task.task_name](task, task.future.result())
        # Add a time stamp to the scheme
        storage_scheme["time"] =  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        #print(storage_scheme)
        #self.collection.insert_one(storage_scheme)
        print("***mongodb_backend*** Storing...")

        return None


# End of file mongodb.py