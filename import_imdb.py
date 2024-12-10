import pymongo
import pandas as pd
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client.moviedb
Dataset = db.dataset

try:
    # Update this path to your actual JSON file location
    df = pd.read_json(r'C:\Users\b00812132\Downloads\movie.dataset\moviedb.movies.json') 
    print("Data loaded from JSON file:\n", df.head())
    
    # Convert DataFrame to a list of records (dictionaries)
    data_to_insert = df.to_dict(orient='records')
    
    if data_to_insert:
        for record in data_to_insert:
            # Ensure that the document is matched by the unique _id field
            Dataset.update_one({"_id": record["_id"]}, {"$set": record}, upsert=True)
            
        print("Dataset loaded successfully.")
    else:
        print("No data found.")
        
except Exception as e:
    print("Error importing JSON file:", e)
