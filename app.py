import base64
import json
import os
import logging
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from logging.config import fileConfig


app = Flask(__name__)
load_dotenv()

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_CONNECTION_STRING')
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)
API_NAME = os.environ.get('API_NAME')

client_key = os.environ.get('CONSUMER_KEY')
client_secret = os.environ.get('CONSUMER_SECRET')
key_secret = f'{client_key}:{client_secret}'.encode('ascii')
b64_encoded_key = base64.b64encode(key_secret)
b64_encoded_key = b64_encoded_key.decode('ascii')
BEARER_TOKEN = ''

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
app.logger = logging.getLogger()


class Tweet(db.Model):
    __tablename__ = 'tweet'
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

    hashtags = db.relationship('Tweet_Hashtag', backref='tweet', lazy=True)
    urls = db.relationship('Tweet_Url', backref='tweet', lazy=True)

    def to_dict(self):
        data_hashtags = []
        urls = {}
        entities = {
            'tweet_created_at': self.tweet_created_at,
            'tweet_id': self.tweet_id,
            'tweet_text': self.tweet_text,
            'tweet_result_type': self.tweet_result_type,
            'tweet_geo': self.tweet_geo,
            'tweet_coordinates': self.tweet_coordinates,
            'tweet_retweet_count': self.tweet_retweet_count,
            'tweet_favorite_count': self.tweet_favorite_count,
            'tweet_lang': self.tweet_lang,
        }

        user = {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_screenname': self.user_screenname,
            'user_location': self.user_location,
            'user_followers_count': self.user_followers_count,
            'user_friends_count': self.user_friends_count,
            'user_statuses_count': self.user_statuses_count,
            'user_lang': self.user_lang,
        }

        if self.hashtags:
            for hashtag in self.hashtags:
                data_hashtags.append(hashtag.hashtags)

        if self.urls:
            for data in self.urls:
                urls = {
                    'url': data.url,
                    'display_url': data.display_url,
                    'expanded_url': data.expanded_url,
                }

        response_data = {
            'Tweets_Entities': entities,
            'Tweets_User': user,
            'Tweets_Url': urls,
            'Tweets_Hashtag': data_hashtags,
        }

        return response_data


class Tweet_Hashtag(db.Model):
    __tablename__ = 'tweet_hashtag'
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String, db.ForeignKey('tweet.tweet_id'), nullable=False)
    hashtags = db.Column(db.Text)


class Tweet_Url(db.Model):
    __tablename__ = 'tweet_url'
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String, db.ForeignKey('tweet.tweet_id'), nullable=False)
    url = db.Column(db.Text)
    expanded_url = db.Column(db.Text)
    display_url = db.Column(db.Text)


def add_Tweet(item, tweet_id):

    tweet = Tweet(
        tweet_created_at=item['created_at'],
        tweet_id=tweet_id,
        tweet_text=item['text'],
        tweet_result_type=item['metadata']['result_type'],
        tweet_geo=item['geo'],
        tweet_coordinates=item['coordinates'],
        tweet_retweet_count=item['retweet_count'],
        tweet_favorite_count=item['favorite_count'],
        tweet_lang=item['lang'],
        user_id=item['user']['id'],
        user_name=item['user']['name'],
        user_screenname=item['user']['screen_name'],
        user_location=item['user']['location'],
        user_followers_count=item['user']['followers_count'],
        user_friends_count=item['user']['friends_count'],
        user_statuses_count=item['user']['statuses_count'],
        user_lang=item['user']['lang'],
    )
    db.session.add(tweet)


def add_Hashtag(item, tweet_id):
    for i in item['entities']['hashtags']:
        hashtags = Tweet_Hashtag(tweet_id=tweet_id, hashtags=i['text'])
        db.session.add(hashtags)


def add_Url(item, tweet_id):
    for i in item['entities']['urls']:
        urls = Tweet_Url(
            tweet_id=tweet_id,
            url=i['url'],
            expanded_url=i['expanded_url'],
            display_url=i['display_url'],
        )
        db.session.add(urls)


def get_validate_token():
    global BEARER_TOKEN
    base_url = 'https://api.twitter.com/'
    auth_url = f'{base_url}oauth2/token'
    auth_headers = {
        'Authorization': f'Basic {b64_encoded_key}',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    }
    auth_data = {'grant_type': 'client_credentials'}
    auth_resp = requests.post(auth_url, headers=auth_headers, data=auth_data)
    BEARER_TOKEN = auth_resp.json()['access_token']
    app.logger.info('getting_validate_token successfull')


# Sadece Admin tarafından kullanılacak
@app.route('/api/addTweettoDB', methods=['POST'])
def standart_search_tweets():
    app.logger.info(
        f'user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> id : {id} ==> method : {request.method}'
    )
    if not request.json:
        abort(400, 'Empty Content')

    base_url = 'https://api.twitter.com/1.1/'
    auth_url = f'{base_url}search/tweets.json'
    auth_headers = {'Authorization': f'Bearer {BEARER_TOKEN}'}
    data = {
        'q': request.json.get('q'),
        'geocode': request.json.get('geocode'),
        'lang': request.json.get('lang'),
        'locale': request.json.get('locale'),
        'result_type': request.json.get('result_type'),
        'count': request.json.get('count'),
        'until': request.json.get('until'),
        'since_id': request.json.get('since_id'),
        'max_id': request.json.get('max_id'),
        'include_entities': True,
    }
    get_tweets = requests.get(auth_url, headers=auth_headers, params=data)
    items = json.loads(get_tweets.content)
    counter = 0
    for item in items['statuses']:
        tweet_id = item['id_str']
        if Tweet.query.filter_by(tweet_id=tweet_id).first():
            app.logger.warn(f'{tweet_id} id sine sahip yinelenen kayıt')
            break
        add_Tweet(item, tweet_id)
        counter += 1

        if item['entities']['hashtags']:
            add_Hashtag(item, tweet_id)

        if item['entities']['urls']:
            add_Url(item, tweet_id)

    db.session.commit()
    app.logger.info('getting_standart_tweets successfull')
    return jsonify({f'{counter} tweet': 'OK'}), 200


@app.route('/api/tweets', methods=['GET'])
def get_all_tweet_from_db():
    app.logger.info(
        f'user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> method : {request.endpoint}'
    )
    tweets = Tweet.query.all()
    data_response = []

    for tweet in tweets:
        data_response.append(tweet.to_dict())

    return jsonify({'Statuses': data_response}), 200


@app.route('/api/tweet/<id>', methods=['GET'])
def get_tweet_from_db(id):
    app.logger.info(
        f'user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> id : {id} ==> method : {request.method}'
    )
    tweet = Tweet.query.filter_by(tweet_id=id).first()

    if not tweet:
        abort(404, 'Tweet not found')

    return jsonify({'Statuses': tweet.to_dict()}), 200


@app.route('/api/hashtags/<hashtag>', methods=['GET'])
def get_tweet_has_hashtags(hashtag):
    app.logger.info(
        f'user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> hashtag : {hashtag} ==> method : {request.method}'
    )
    hashtags = Tweet_Hashtag.query.all()
    response_data = []
    for hash in hashtags:
        if hash.hashtags == hashtag:
            tweet = Tweet.query.filter_by(tweet_id=hash.tweet_id).first()
            response_data.append(tweet.to_dict())

    if not response_data:
        abort(404, 'Hashtag not found')

    return jsonify({'Statuses': response_data}), 200


@app.route('/api/tweets/maxFavorited', methods=['GET'])
def get_maxFavorited():
    app.logger.info(
        f'user-agent : {request.user_agent} ==> base_url : {request.base_url} ==> endpoint : {request.endpoint} ==> method : {request.method}'
    )

    tweets = Tweet.query.order_by(Tweet.tweet_favorite_count.desc())
    response_data = []
    for tweet in tweets:
        response_data.append(tweet.to_dict())

    return jsonify({'Statuses': response_data}), 200


@app.errorhandler(404)
def custom404(error):
    return (
        jsonify(
            {
                'name': API_NAME,
                'status': 'Not Found',
                'code': 404,
                'message': error.description,
            }
        ),
        404,
    )


@app.errorhandler(400)
def custom400(error):
    return (
        jsonify(
            {
                'name': API_NAME,
                'status': 'Bad Request',
                'code': 400,
                'message': error.description,
            }
        ),
        400,
    )


if __name__:
    get_validate_token()
    app.run(host='127.0.0.1', port=5000, debug=True)
