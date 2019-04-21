import json
import requests
import base64
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
config = json.load(open('config.json', 'r'))
app.config['SECRET_KEY'] = config['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = config['db_connection_string']
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)
API_NAME = config['api_name']

client_key = config['CONSUMER_KEY']
client_secret = config['CONSUMER_SECRET']
key_secret = '{}:{}'.format(client_key, client_secret).encode('ascii')
b64_encoded_key = base64.b64encode(key_secret)
b64_encoded_key = b64_encoded_key.decode('ascii')
BEARER_TOKEN = ""


def get_validate_token():
    global BEARER_TOKEN
    base_url = 'https://api.twitter.com/'
    auth_url = '{}oauth2/token'.format(base_url)
    auth_headers = {
        'Authorization': 'Basic {}'.format(b64_encoded_key),
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    auth_data = {
        'grant_type': 'client_credentials'
    }
    auth_resp = requests.post(auth_url, headers=auth_headers, data=auth_data)
    access_token = auth_resp.json()['access_token']
    BEARER_TOKEN = access_token


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


def get_standart_search_tweets():
    base_url = 'https://api.twitter.com/1.1/'
    auth_url = '{}search/tweets.json'.format(base_url)

    auth_headers = {
        'Authorization': 'Bearer {}'.format(BEARER_TOKEN),
    }

    data = {
        'q': 'istanbul',
        'geocode': '',
        'lang': 'tr',
        'locale': '',
        'result_type': 'popular',
        'count': 15,
        'until': '2019-04-19',
        'since_id': '',
        'max_id': '',
        'include_entities': True
    }

    get_tweets = requests.get(auth_url, headers=auth_headers, params=data)
    items = json.loads(get_tweets.content)

    for item in items['statuses']:
        tweet_created_at = item['created_at']
        tweet_text = item['text']
        tweet_id = item['id_str']
        tweet_result_type = item['metadata']['result_type']
        tweet_geo = item['geo']
        tweet_coordinates = item['coordinates']
        tweet_retweet_count = item['retweet_count']
        tweet_favorite_count = item['favorite_count']
        tweet_lang = item['lang']
        user_id = item['user']['id']
        user_name = item['user']['name']
        user_screenname = item['user']['screen_name']
        user_location = item['user']['location']
        user_followers_count = item['user']['followers_count']
        user_friends_count = item['user']['friends_count']
        user_statuses_count = item['user']['statuses_count']
        user_lang = item['user']['lang']

        tweet = Tweet(tweet_created_at=tweet_created_at, tweet_id=tweet_id,
                      tweet_text=tweet_text, tweet_result_type=tweet_result_type,
                      tweet_geo=tweet_geo, tweet_coordinates=tweet_coordinates,
                      tweet_retweet_count=tweet_retweet_count,
                      tweet_favorite_count=tweet_favorite_count, tweet_lang=tweet_lang,
                      user_id=user_id, user_name=user_name, user_screenname=user_screenname,
                      user_location=user_location, user_followers_count=user_followers_count,
                      user_friends_count=user_friends_count, user_statuses_count=user_statuses_count,
                      user_lang=user_lang)
        db.session.add(tweet)

        if (item['entities']['hashtags']):
            for i in item['entities']['hashtags']:
                hashtag = i['text']
                hashtags = Tweet_Hashtag(tweet_id=tweet_id, hashtags=hashtag)
                db.session.add(hashtags)

        if (item['entities']['urls']):
            for i in item['entities']['urls']:
                url = i['url']
                expanded_url = i['expanded_url']
                display_url = i['display_url']
                urls = Tweet_Url(tweet_id=tweet_id, url=url, expanded_url=expanded_url,
                                 display_url=display_url)
                db.session.add(urls)

    db.session.commit()


if __name__:
    get_validate_token()
    get_standart_search_tweets()
    app.run()
