from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity  
from pymongo import MongoClient
from bson import ObjectId 
from flask import jsonify 

app = Flask(__name__)
CORS(app)
def serialize_objectid(data):
    if isinstance(data, dict):
        return {k: serialize_objectid(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_objectid(i) for i in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data
      
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

'''
mongoimport --db moviedb --collection movies --jsonArray moviedb.movies.json
'''
client = MongoClient("mongodb://127.0.0.1:27017")
mongo_db = client.moviedb
movies = mongo_db.movies
Dataset = mongo_db.dataset
users = mongo_db.users

movies.create_index([("title", "text"), ("description", "text")])

class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password 
        
@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    password = request.json.get('password')
    if users.find_one({"username": username}):
       return make_response(jsonify({"error": "username exists"}), 400) 
   
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = {
        "username":username, 
        "password": hashed_password
        }
    users.insert_one(new_user)
    return make_response(jsonify({"message": "User registration successful"}), 201)

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    user = users.find_one({"username": username})
    
    if user and bcrypt.check_password_hash(user['password'], password):
        access_token = create_access_token(identity=username)
        return make_response(jsonify({"access_token": access_token}), 200)
    else:
        return make_response(jsonify({"error": "invalid credentials"}), 401)


@app.route("/api/v1.0/movies", methods=['GET'])
def show_all_movies():
    movies_list = list(movies.find())
    serialized_data = serialize_objectid(movies_list)
    return jsonify(serialized_data), 200 

@app.route("/api/v1.0/movies/<string:id>", methods=["GET"])
def show_one_movie(id):
    movie = movies.find_one({'_id': ObjectId(id)})
    if movie:
        return jsonify(serialize_objectid(movie)), 200
    else:
        return jsonify({"Error": "invalid movie id"}), 404
    
@app.route("/api/v1.0/movies", methods=["POST"])
@jwt_required()
def add_movie():
    new_movie = {
        'name': request.json['name'],
        'year': request.json['year'],
        'imdb_rating': request.json['imdb_rating'],
        'genre': request.json['genre'],
        'reviews': []   
    }
    new_movie_id = movies.insert_one(new_movie)
    new_movie_link = f"http://localhost:5000/api/v1.0/movies/{new_movie_id.inserted_id}"
    return make_response(jsonify({"url": new_movie_link}), 201)

@app.route("/api/v1.0/movies/<string:id>", methods=["PUT"])
@jwt_required()
def edit_movie(id):
    updated_data = {key: request.json[key] for key in ['name', 'year', 'imdb_rating', 'genre']if key in request.json}
    result = movies.update_one({'_id': ObjectId(id)}, {"$set": updated_data})
    if result.matched_count ==1:
        return make_response(jsonify({"message": "movie updated"}), 200)
    else:
        return make_response(jsonify({"error": "invalid movie id"}), 404)

@app.route("/api/v1.0/movies/<string:id>", methods=["DELETE"])
@jwt_required()
def delete_movie(id):
    result = movies.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 1:
        return make_response(jsonify({}), 200)
    else:
        return make_response(jsonify({"error": "invalid movie id"}), 404)
    
@app.route("/api/v1.0/movies/search", methods=["GET"]) 
def find_movies():
    filters = {}
    
    if 'search' in request.args:
        search_term = request.args['search']
        filters["$text"] = {"$search": search_term}
        
    if 'genre' in request.args:
        filters['genre'] = request.args['genre']
   
    if 'imdb_rating_min' in request.args:
        try:
            filters['imdb_rating'] = {'$gte': float(request.args['imdb_rating_min'])}
        except ValueError:
            return jsonify({"error": "Minimum must be a number"}), 400
   
    if 'imdb_rating_max' in request.args:
        try:
            filters.setdefault('imdb_rating', {})['$lte'] = float(request.args['imdb_rating_max'])
        except ValueError:
            return jsonify({"error": "maximum rating must be a number"}), 400
        
    if 'year' in request.args:
        try:
            filters['year'] = int(request.args['year'])
        except ValueError:
            return jsonify({"error": "year must be a number"}), 400
   
    if 'reviewer' in request.args:
        filters['reviews.username'] = request.args['reviewer']
   
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))

   
    movies_list = list(movies.find(filters).skip((page-1) *limit).limit(limit))
   
    serialized_data = serialize_objectid(movies_list)
    return jsonify(serialized_data), 200  
        

@app.route("/api/v1.0/movies/<string:id>/reviews", methods=["POST"])
@jwt_required()
def add_new_review(id):
    current_user = get_jwt_identity()
    new_review = {
        '_id': ObjectId(),
        'username': current_user,
        'genre': request.json.get('genre'),
        'comment': request.json.get('comment')
    }
    movies.update_one({"_id": ObjectId(id)}, {"$push": {"reviews": new_review}})
    
    new_review_link = f"http://localhost:5000/api/v1.0/movies/{id}/reviews/{new_review['_id']}"
    return make_response(jsonify({"url": new_review_link}), 201)


@app.route("/api/v1.0/movies/<string:id>/reviews", methods=["GET"])
def fetch_all_reviews(id):
    movie = movies.find_one({"_id": ObjectId(id)}, {"reviews": 1})
    if movie and 'reviews' in movie:
        return jsonify(serialize_objectid(movie['reviews'])), 200
    else:
        return jsonify({"error": "no reviews/ invalid id"}), 400

@app.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=["PUT"])
@jwt_required()
def edit_review(m_id, r_id):
    updated_review = {
        "reviews.$.genre": request.json.get('genre'),
        "reviews.$.comment": request.json.get('comment')
    }
    result = movies.update_one(
        {"_id": ObjectId(m_id), "reviews._id": ObjectId(r_id)},
        {"$set": updated_review}
    )
    if result.modified_count ==1:
        return make_response(jsonify({"message": "Review updated"}), 200)
    else:
        return make_response(jsonify({"error": "invalid movie id or review id"}), 404)

@app.route("/api/v1.0/movies/<string:m_id>/reviews/<string:r_id>", methods=["DELETE"])
@jwt_required()
def delete_review(m_id, r_id):
    result = movies.update_one(
        {"_id": ObjectId(m_id)},
        {"$pull": {"reviews": {"_id": ObjectId(r_id)}}}
    )
    if result.modified_count ==1:
        return make_response(jsonify({}), 200)
    else:
        return make_response(jsonify({"error": "invalid movie id or review id"}), 404)
    
@app.route("/api/v1.0/dataset", methods=['GET'])
def show_all_dataset():
    dataset_list = list(Dataset.find())
    serialize_data = serialize_objectid(dataset_list)
    return jsonify(serialize_data), 200

@app.route("/api/v1.0/dataset/<string:id>", methods=['GET'])
def show_one_dataset(id):
    dataset = Dataset.find_one({'_id': ObjectId(id)})
    if dataset:
        return jsonify(serialize_objectid(dataset)), 200
    else:
        return jsonify({"error": "invalid dataset id"}), 404
    
if __name__ == "__main__":
    app.run(debug=True, port = 4999)