import pymongo
import pandas as pd
from pymongo import MongoClient


client = MongoClient('mongodb://localhost:27017')
db = client.moviedb
Dataset = db.dataset

try:
    df = pd.read_json('C:\Users\b00812132\Downloads\movie.dataset') 
    print("data loaded from JSON file:\n", df.head())
    
    data_to_insert = df.to_dicst(orient='records')
    
    if data_to_insert:
        for record in data_to_insert:
            Dataset.update_one({"unique_feild":record["unique_feild"]}, {"$set":record},upsert=True)
            
        print("dataset loaded")
    else:
        print("no data foudn")
        
except Exception as e:
    print("derror importing json file", e)