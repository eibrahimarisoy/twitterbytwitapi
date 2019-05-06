import base64
import json
import os
import logging
import requests
from dotenv import load_dotenv
from flask import Flask
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
BEARER_TOKEN = ""

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
app.logger = logging.getLogger()


def get_validate_token():
    global BEARER_TOKEN
    base_url = 'https://api.twitter.com/'
    auth_url = f'{base_url}oauth2/token'
    auth_headers = {
        'Authorization': f'Basic {b64_encoded_key}',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    auth_data = {
        'grant_type': 'client_credentials'
    }
    auth_resp = requests.post(auth_url, headers=auth_headers, data=auth_data)
    BEARER_TOKEN = auth_resp.json()['access_token']
    app.logger.info('getting_validate_token successfull')


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


class Tweet_Hashtag(db.Model):
    __tablename__ = 'tweet_hashtag'
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String, db.ForeignKey('tweet.tweet_id'),
                         nullable=False)
    hashtags = db.Column(db.Text)


class Tweet_Url(db.Model):
    __tablename__ = 'tweet_url'
    id = db.Column(db.Integer, primary_key=True)
    tweet_id = db.Column(db.String, db.ForeignKey('tweet.tweet_id'),
                         nullable=False)
    url = db.Column(db.Text)
    expanded_url = db.Column(db.Text)
    display_url = db.Column(db.Text)


def add_Tweet(item, tweet_id):

    tweet = Tweet(tweet_created_at=item['created_at'], tweet_id=tweet_id,
                  tweet_text=item['text'], tweet_result_type=item['metadata']['result_type'],
                  tweet_geo=item['geo'], tweet_coordinates=item['coordinates'],
                  tweet_retweet_count=item['retweet_count'],
                  tweet_favorite_count=item['favorite_count'], tweet_lang=item['lang'],
                  user_id=item['user']['id'], user_name=item['user']['name'],
                  user_screenname=item['user']['screen_name'], user_location=item['user']['location'],
                  user_followers_count=item['user']['followers_count'], user_friends_count=item['user']['friends_count'],
                  user_statuses_count=item['user']['statuses_count'], user_lang=item['user']['lang'])
    db.session.add(tweet)


def add_Hashtag(item, tweet_id):
    for i in item['entities']['hashtags']:
        hashtags = Tweet_Hashtag(tweet_id=tweet_id, hashtags=i['text'])
        db.session.add(hashtags)


def add_Url(item, tweet_id):
    for i in item['entities']['urls']:
        urls = Tweet_Url(tweet_id=tweet_id, url=i['url'], expanded_url=i['expanded_url'],
                         display_url=i['display_url'])
        db.session.add(urls)


def get_standart_search_tweets(q='', geocode='', lang='', locale='', result_type='',
                               count=15, until='', since_id='', max_id=''):
    base_url = 'https://api.twitter.com/1.1/'
    auth_url = f'{base_url}search/tweets.json'

    auth_headers = {
        'Authorization': f'Bearer {BEARER_TOKEN}',
    }

    data = {
        'q': q,
        'geocode': geocode,
        'lang': lang,
        'locale': locale,
        'result_type': result_type,
        'count': count,
        'until': until,
        'since_id': since_id,
        'max_id': max_id,
        'include_entities': True
    }

    get_tweets = requests.get(auth_url, headers=auth_headers, params=data)
    items = json.loads(get_tweets.content)

    for item in items['statuses']:
        tweet_id = item['id_str']
        if Tweet.query.filter_by(tweet_id=tweet_id).first():
            app.logger.warn(f'{tweet_id} id sine sahip yinelenen kayıt')
            break
        add_Tweet(item, tweet_id)

        if item['entities']['hashtags']:
            add_Hashtag(item, tweet_id)

        if item['entities']['urls']:
            add_Url(item, tweet_id)

    db.session.commit()
    app.logger.info('getting_standart_tweets successfull')


if __name__:
    get_validate_token()
    get_standart_search_tweets(q='seçim', lang='tr', result_type='popular',
                               until='2019-05-06')
    app.run()
