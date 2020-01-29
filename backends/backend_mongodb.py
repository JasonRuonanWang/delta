#Coding: UTF-8 -*-

import datetime
import numpy as np
import pickle
import string
import random
import logging
import json

import pymongo 
import gridfs
from bson.binary import Binary

from .backend import backend, serialize_dispatch_seq


class backend_mongodb(backend):
    """
    Author: Ralph Kube

    This defines an access to the mongodb storage backend.
    """
    def __init__(self, cfg_mongo):
        # Connect to mongodb

        #logger = logging.getLogger("DB")
        #print("mongodb_backend: Initializing mongodb backend")
        self.client = pymongo.MongoClient("mongodb://mongodb07.nersc.gov/delta-fusion", 
                                          username = cfg_mongo["storage"]["username"],
                                          password = cfg_mongo["storage"]["password"])
        #print("mongodb_backend: Connection established")
        db = self.client.get_database()
        #print("mongodb_backend: db = ", db)
        try:
            self.collection = db.get_collection("test_analysis_" + cfg_mongo['run_id'])

            # Initialize gridfs
            self.fs = gridfs.GridFS(db)
            #print("mongodb_backend: collection: ", self.collection)
        except:
            print("Could not get a collection")

    def store_metadata(self, cfg, dispatch_seq):
        """Stores the metadata to the database

        Parameters
        ----------
        cfg: The configuration of the analysis run
        dispatch_seq: The serialized task dispatch sequence
        """

        logger = logging.getLogger("DB")
        logger.debug("backend_mongodb: entering store_metadata")

        #db = self.client.get_database()
        #collection = db.get_collection("test_analysis_" + cfg['run_id'])
        #logger.info(f"backend_mongodb Connected to database {db.name}")
        #logger.info(f"backend_mongodb Using collection {collection.name}")

        j_str = serialize_dispatch_seq(dispatch_seq)
        # Put the channel serialization in the corresponding key
        j_str = '{"channel_serialization": ' + j_str + '}'
        j = json.loads(j_str)
        # Adds the channel_serialization key to cfg
        cfg.update(j)
        cfg.update({"timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %X UTC")})
    

        try:
            result = self.collection.insert_one(cfg)
        except pymongo.errors.PyMongoError as e:
            logger.error("An error has occurred in store_metadata:: ", e)

        return result.inserted_id


    def store_task(self, task, future=None, dummy=True):
        """Stores data from an analysis task in the mongodb backend.

        The data anylsis results from analysis_task object are evaluated in this method.

        Parameters
        ----------
        task: analysis_task object. 
        dummy: bool. If true, do not insert the item into the database
        
        Returns
        -------
        None
        """

        # Gather the results from all futures in the task
        # This locks until all futures are evaluated.
        result = []
        for future in task.futures_list:
            result.append(future.result())
        result = np.array(result)
        print("***Backend.store: result = ", result.shape)

        # Write results to the backend
        storage_scheme = task.storage_scheme
        # Add a time stamp to the scheme
        storage_scheme["time"] =  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


        if dummy:
            storage_scheme["results"] = result
            print(storage_scheme)
        else:
            storage_scheme["results"] = Binary(pickle.dumps(result))
            self.collection.insert_one(storage_scheme)
            print("***mongodb_backend*** Storing...")

        return None


    def store_data(self, data, info_dict):
        """Stores data in mongodb

        Parameters
        ----------
        data: ndarray, float.
        info_dict: Dictionary with metadata to store
        cfg: delta configuration object
        """
        import sys
        #logger = logging.get("DB")
        #print(f"MongoDB: Storing data")

        #info_dict['result'] = Binary(pickle.dumps(data))
        # Create a binary object and store it in gridfs
        fid = self.fs.put(Binary(pickle.dumps(data)))

        info_dict['result_gridfs'] = fid
        info_dict['timestamp'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        #print("Inserting:")
        #inserted_id = self.connection.insert_one(info_dict)
        try:
            inserted_id = self.collection.insert_one(info_dict)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

        #print(f"Wrote to MongoDB backend; id = {inserted_id}")


    def store_one(self, key, value):
        """Stores a single key-value pair"""

        self.collection.insert_one({key: value})


# End of file mongodb.py