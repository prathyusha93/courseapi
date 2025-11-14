from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")  
db = client["bookdb"]  # Database name

courses_collection = db["courses"]
modules_collection = db["modules"]
topics_collection = db["topics"]
contents_collection = db["contents"]
enrollment_collection = db["enrollments"]
