import base64
import json
import os
import logging
import requests
from datetime import date
from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort, g
from flask_caching import Cache
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer,
    BadSignature,
    SignatureExpired,
)
from logging.config import fileConfig
from passlib.apps import custom_app_context as pwd_context

app = Flask(__name__)
load_dotenv()

auth = HTTPBasicAuth()
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_CONNECTION_STRING")
app.config["SQLALCHEMY_COMMIT_ON_TEARDOWN"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["CACHE_TYPE"] = os.environ.get("CACHE_TYPE")
app.config["CACHE_DEFAULT_TYPE"] = os.environ.get("CACHE_DEFAULT_TYPE")

db = SQLAlchemy(app)
API_NAME = os.environ.get("API_NAME")
cache = Cache(app)

client_key = os.environ.get("CONSUMER_KEY")
client_secret = os.environ.get("CONSUMER_SECRET")
key_secret = f"{client_key}:{client_secret}".encode("ascii")
b64_encoded_key = base64.b64encode(key_secret)
b64_encoded_key = b64_encoded_key.decode("ascii")
BEARER_TOKEN = ""

logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
app.logger = logging.getLogger()


class Tweet(db.Model):
    __tablename__ = "tweet"
    id = db.Column(db.Integer, primary_key=True)
    tweet_created_at = db.Column(db.Text)
    tweet_id = db.Column(db.String, unique=True)
    tweet_text = db.Column(db.Text)
    tweet_result_type = db.Column(db.Text)
    tweet_geo = db.Column(db.Text)
    tweet_coordinates = db.Column(db.Text)
    tweet_retweet_count = db.Column(db.Integer)
    tweet_favorite_count = db.Column(db.Integer)
    tweet_lang = db.Column(db.Text)
    user_id = db.Column(db.Text)
    user_name = db.Column(db.Text)
    user_screenname = db.Column(db.Text)
    user_location = db.Column(db.Text)
    user_followers_count = db.Column(db.Integer)
    user_friends_count = db.Column(db.Integer)
    user_statuses_count = db.Column(db.Integer)
    user_lang = db.Column(db.Text)

    hashtags = db.relationship("Tweet_Hashtag", backref="tweet", lazy=True)
    urls = db.relationship("Tweet_Url", backref="tweet", lazy=True)

    def to_dict(self):
        data_hashtags = []
        urls = {}
        entities = {
            "tweet_created_at": self.tweet_created_at,
            "tweet_id": self.tweet_id,
            "tweet_text": self.tweet_text,
            "tweet_result_type": self.tweet_result_type,
            "tweet_geo": self.tweet_geo,
            "tweet_coordinates": self.tweet_coordinates,
            "tweet_retweet_count": self.tweet_retweet_count,
            "tweet_favorite_count": self.tweet_favorite_count,
            "tweet_lang": self.tweet_lang,
        }

        user = {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_screenname": self.user_screenname,
            "user_location": self.user_location,
            "user_followers_count": self.user_followers_count,
            "user_friends_count": self.user_friends_count,
            "user_statuses_count": self.user_statuses_count,
            "user_lang": self.user_lang,
        }

        if self.hashtags:
            for hashtag in self.hashtags:
                data_hashtags.append(hashtag.hashtags)

        if self.urls:
            for data in self.urls:
                urls = {
                    "url": data.url,
                    "display_url": data.display_url,
                    "expanded_url": data.expanded_url,
                }

        response_data = {
            "Tweets_Entities": entities,
            "Tweets_User": user,
            "Tweets_Url": urls,
            "Tweets_Hashtag": data_hashtags,
        }

        return response_data


class Tweet_Hashtag(db.Model):
    __tablename__ = "tweet_hashtag"
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String, db.ForeignKey("tweet.tweet_id"), nullable=False)
    hashtags = db.Column(db.Text)


class Tweet_Url(db.Model):
    __tablename__ = "tweet_url"
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String, db.ForeignKey("tweet.tweet_id"), nullable=False)
    url = db.Column(db.Text)
    expanded_url = db.Column(db.Text)
    display_url = db.Column(db.Text)


class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120))

    def hash_password(self, password):
        self.password = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)

    def generate_auth_token(self, expiration=100):
        s = Serializer(os.environ.get("SECRET_KEY"), expires_in=expiration)
        return s.dumps({"id": self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(os.environ.get("SECRET_KEY"))
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        user = User.query.get(data["id"])
        return user

    def to_dict(self):
        response_data = {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "email": self.email,
        }
        return response_data


def add_Tweet(item, tweet_id):

    tweet = Tweet(
        tweet_created_at=item["created_at"],
        tweet_id=tweet_id,
        tweet_text=item["text"],
        tweet_result_type=item["metadata"]["result_type"],
        tweet_geo=item["geo"],
        tweet_coordinates=item["coordinates"],
        tweet_retweet_count=item["retweet_count"],
        tweet_favorite_count=item["favorite_count"],
        tweet_lang=item["lang"],
        user_id=item["user"]["id"],
        user_name=item["user"]["name"],
        user_screenname=item["user"]["screen_name"],
        user_location=item["user"]["location"],
        user_followers_count=item["user"]["followers_count"],
        user_friends_count=item["user"]["friends_count"],
        user_statuses_count=item["user"]["statuses_count"],
        user_lang=item["user"]["lang"],
    )
    db.session.add(tweet)


def add_Hashtag(item, tweet_id):
    for i in item["entities"]["hashtags"]:
        hashtags = Tweet_Hashtag(tweet_id=tweet_id, hashtags=i["text"])
        db.session.add(hashtags)


def add_Url(item, tweet_id):
    for i in item["entities"]["urls"]:
        urls = Tweet_Url(
            tweet_id=tweet_id,
            url=i["url"],
            expanded_url=i["expanded_url"],
            display_url=i["display_url"],
        )
        db.session.add(urls)


def authentication_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        user = User.verify_auth_token(token)
        if not token or not user:
            abort(403, "You are forbidden to see this page")

        if f.__name__ == "standart_search_tweets":
            if not user.username == "admin":
                abort(403, "You are forbidden to see this page")

        g.user = user
        return f(*args, **kwargs)

    return decorated_function


def get_paginated_list(results, url, start, limit):
    count = len(results)
    # make response
    response_data = {}
    response_data["start"] = start
    response_data["limit"] = limit
    response_data["count"] = count
    if start - limit > 0:
        response_data["previous"] = url + f"?start={start-limit}&limit={limit}"
    if start + limit > count:
        limit = count - start
    else:
        response_data["next"] = url + f"?start={start+limit}&limit={limit}"

    statuses = []

    for i in range((start - 1), start + limit - 1):
        statuses.append(results[i].to_dict())
        response_data["Statuses"] = statuses

    return response_data


def get_validate_token():
    global BEARER_TOKEN
    base_url = "https://api.twitter.com/"
    auth_url = f"{base_url}oauth2/token"
    auth_headers = {
        "Authorization": f"Basic {b64_encoded_key}",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    }
    auth_data = {"grant_type": "client_credentials"}
    auth_resp = requests.post(auth_url, headers=auth_headers, data=auth_data)
    BEARER_TOKEN = auth_resp.json()["access_token"]
    app.logger.info("getting_validate_token successfull")


# Sadece Admin tarafından kullanılacak
@app.route("/v1/api/addTweettoDB", methods=["POST"])
@authentication_required
def standart_search_tweets():
    app.logger.info(
        f"user : {g.user.username} ==> user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> method : {request.method}"
    )
    if not request.json:
        abort(400, "Empty Content")

    base_url = "https://api.twitter.com/1.1/"
    auth_url = f"{base_url}search/tweets.json"
    auth_headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    until = request.json.get("until")
    if not until:
        until = str(date.today())

    data = {
        "q": request.json.get("q"),
        "geocode": request.json.get("geocode"),
        "lang": request.json.get("lang"),
        "locale": request.json.get("locale"),
        "result_type": request.json.get("result_type"),
        "count": request.json.get("count"),
        "until": until,
        "since_id": request.json.get("since_id"),
        "max_id": request.json.get("max_id"),
        "include_entities": True,
    }
    get_tweets = requests.get(auth_url, headers=auth_headers, params=data)
    items = json.loads(get_tweets.content)
    counter = 0
    for item in items["statuses"]:
        tweet_id = item["id_str"]
        if Tweet.query.filter_by(tweet_id=tweet_id).first():
            app.logger.warn(f"{tweet_id} id sine sahip yinelenen kayıt")
            break
        add_Tweet(item, tweet_id)
        counter += 1

        if item["entities"]["hashtags"]:
            add_Hashtag(item, tweet_id)

        if item["entities"]["urls"]:
            add_Url(item, tweet_id)

    db.session.commit()
    app.logger.info("getting_standart_tweets successfull")
    return jsonify({f"{counter} tweet": "OK"}), 200


@app.route("/v1/api/tweets/page", methods=["GET"])
def get_all_tweet_from_db():
    app.logger.info(
        f"user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> method : {request.endpoint}"
    )
    tweets = Tweet.query.all()
    if not tweets:
        abort(404)

    return jsonify(
        get_paginated_list(
            tweets,
            "/v1/api/tweets/page",
            start=int(request.args.get("start")),
            limit=int(request.args.get("limit")),
        )
    )


@app.route("/v1/api/tweet/<tweetid>", methods=["GET"])
@authentication_required
@cache.cached(timeout=50)
def get_tweet_from_db(tweetid):
    app.logger.info(
        f"user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> id : {id} ==> method : {request.method}"
    )
    tweet = Tweet.query.filter_by(tweet_id=tweetid).first()

    if not tweet:
        abort(404, "Tweet not found")

    return jsonify({"Statuses": tweet.to_dict()}), 200


@app.route("/v1/api/hashtags/<hashtag>", methods=["GET"])
@authentication_required
@cache.cached(timeout=50)
def get_tweet_has_hashtags(hashtag):
    app.logger.info(
        f"user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> hashtag : {hashtag} ==> method : {request.method}"
    )
    hashtags = Tweet_Hashtag.query.all()
    response_data = []
    for hash in hashtags:
        if hash.hashtags == hashtag:
            tweet = Tweet.query.filter_by(tweet_id=hash.tweet_id).first()
            response_data.append(tweet.to_dict())

    if not response_data:
        abort(404, "Hashtag not found")

    return jsonify({"Statuses": response_data}), 200


@app.route("/v1/api/tweets/maxFavorited", methods=["GET"])
@cache.cached(timeout=50)
@authentication_required
def get_maxFavorited():
    app.logger.info(
        f"user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> method : {request.method}"
    )

    tweets = Tweet.query.order_by(Tweet.tweet_favorite_count.desc())
    response_data = []
    for tweet in tweets:
        response_data.append(tweet.to_dict())

    return jsonify({"Statuses": response_data}), 200


@app.route("/v1/api/adduser", methods=["POST"])
def add_new_user():
    if not request.json:
        abort(400)

    name = request.json.get("name")
    username = request.json.get("username")
    email = request.json.get("email")
    password = request.json.get("password")
    app.logger.info(
        f"user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> method : {request.method}"
    )
    if not name or not username or not email or not password:
        abort(400)

    if User.query.filter_by(username=username).first():
        abort(400, "Username is already taken")

    if User.query.filter_by(email=email).first():
        abort(400, "The Email Adress is already using")

    user = User(name=name, username=username, email=email)
    user.hash_password(password)

    db.session.add(user)
    db.session.commit()
    data = {
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "id": user.id,
    }
    return jsonify(data), 201


@app.route("/v1/api/login", methods=["POST"])
@auth.verify_password
def verify_password():
    g.user = None

    token = request.json.get("token")
    app.logger.info(
        f"user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> method : {request.method}"
    )
    if token:
        user = User.verify_auth_token(token)

        if not user:
            abort(401, "Authorization token is invalid or expired")
        g.user = user
        data = {
            "id": g.user.id,
            "username": g.user.username,
            "name": g.user.name,
            "email": g.user.email,
            "token": g.user.generate_auth_token(9999),
        }
        return jsonify(data), 200

    elif request.json.get("username") and request.json.get("password"):
        user = User.query.filter_by(username=request.json.get("username")).first()
        if not user or not user.verify_password(request.json.get("password")):
            abort(401, "Username or password is invalid.")
        g.user = user
        data = {
            "id": g.user.id,
            "username": g.user.username,
            "name": g.user.name,
            "email": g.user.email,
            "token": g.user.generate_auth_token(9999).decode("utf-8"),
        }
        return jsonify(data), 200
    abort(400)


@app.route("/v1/api/users", methods=["GET"])
@cache.cached(timeout=50)
def get_users():
    users = User.query.all()
    if not users:
        abort(404)
    data_response = []

    for user in users:
        data_response.append(user.to_dict())

    return jsonify({"Users": data_response}), 200


@app.route("/v1/api/user/<int:id>", methods=["GET"])
@cache.cached(timeout=50)
def get_user(id):
    user = User.query.filter_by(id=id).first()
    if not user:
        abort(404)

    return jsonify(user.to_dict()), 200


@app.route("/v1/api/user/<int:id>", methods=["DELETE"])
@authentication_required
def delete_user(id):
    user = User.query.filter_by(id=id).first()
    if not user:
        abort(404)

    db.session.delete(user)
    db.session.commit()

    return jsonify(user.to_dict()), 200


@app.route("/v1/api/user/<int:id>", methods=["PATCH"])
@authentication_required
def update_user(id):
    user = User.query.filter_by(id=id).first()
    if not user:
        abort(404)

    if not request.json:
        abort(400)

    username = request.json.get("username")
    name = request.json.get("name")
    email = request.json.get("email")

    if username:
        if User.query.filter_by(username=username).first():
            abort(400, "Username is already in use.")
        user.username = username

    if name:
        user.name = name

    if email:
        if User.query.filter_by(email=email).first():
            abort(400, "Email is already in use.")
        user.email = email

    db.session.commit()

    return (
        jsonify({"code": 200, "status": "OK", "message": "User profile updated."}),
        200,
    )


@app.route("/v1/api/user/passwordChange/<int:id>", methods=["PATCH"])
@authentication_required
def password_change(id):
    user = User.query.filter_by(id=id).first()
    if not user:
        abort(400)

    if g.user.id is not id:
        abort(401)

    last_password = request.json.get("lastpassword")
    new_password = request.json.get("newpassword")

    if not user.verify_password(last_password):
        abort(400, "Password not correct")

    user.hash_password(new_password)
    db.session.commit()

    return (
        jsonify({"code": 200, "status": "OK", "message": "User password updated."}),
        200,
    )


@app.errorhandler(400)
def custom400(error):
    return (
        jsonify(
            {
                "name": API_NAME,
                "status": "Bad Request",
                "code": 400,
                "message": error.description,
            }
        ),
        400,
    )


@app.errorhandler(401)
def custom401(error):
    return (
        jsonify(
            {
                "name": API_NAME,
                "status": "Unauthorized",
                "code": 401,
                "message": error.description,
            }
        ),
        401,
    )


@app.errorhandler(403)
def custom403(error):
    return (
        jsonify(
            {
                "name": API_NAME,
                "status": "Forbidden",
                "code": 403,
                "message": error.description,
            }
        ),
        403,
    )


@app.errorhandler(404)
def custom404(error):
    return (
        jsonify(
            {
                "name": API_NAME,
                "status": "Not Found",
                "code": 404,
                "message": error.description,
            }
        ),
        404,
    )


if __name__:
    # get_validate_token()
    app.run(host="127.0.0.1", port=5000, debug=True)
