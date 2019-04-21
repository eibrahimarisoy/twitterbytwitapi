import json
import sqlalchemy
import requests
from flask import Flask,request,jsonify,json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column,Integer,Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ARRAY
from requests_oauthlib import OAuth1


app=Flask(__name__)
config=json.load(open('config.json','r'))
app.config['SECRET_KEY'] = config['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = config['db_connection_string']
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

CONSUMER_KEY=config['CONSUMER_KEY']
CONSUMER_SECRET=config['CONSUMER_SECRET']
ACCESS_TOKEN=config['ACCESS_TOKEN']
ACCESS_TOKEN_SECRET=config['ACCESS_TOKEN_SECRET']



db=SQLAlchemy(app)
API_NAME=config['api_name']

#authentication with OAuth1
auth=OAuth1(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_TOKEN_SECRET)



#twitter class
class Twitter(db.Model):
    __tablename__ = 'twitter'
    id=Column(Integer,primary_key=True)
    created_at=db.Column(db.Text)
    text=db.Column(db.Text)
    hashtag=db.Column(postgresql.JSON)
    symbol=db.Column(postgresql.JSON)
    user_mentions=db.Column(postgresql.JSON)
    url=db.Column(db.Text)
    expanded_url=db.Column(db.Text)
    display_url=db.Column(db.Text)
    indices=db.Column(postgresql.JSON)
    result_type=db.Column(db.Text)
    geo=db.Column(db.Text)
    retweet_count=db.Column(db.Integer)
    favorite_count=db.Column(db.Integer)


def add_twit():
    #search url
    url = 'https://api.twitter.com/1.1/search/tweets.json'
    #query params
    body={
        'q':'python',
        'result_type':'popular',
        'count':'5'  
    }
    #GET Method
    r=requests.get(url,params=body,auth=auth)
    #convert to JSON     
    item=json.loads(r.content)
    #getting values
    for i in item['statuses']:

        created_at=i['created_at']
        text=i['text']
        hashtag=i['entities']["hashtags"]
        symbol=i['entities']['symbols']
        user_mentions=i['entities']['user_mentions']
        url=i['entities']['urls'][0]['url']
        expanded_url=i['entities']['urls'][0]['expanded_url']
        display_url=i['entities']['urls'][0]['display_url']
        indices=i['entities']['urls'][0]['indices']
        result_type=i['metadata']['result_type']
        geo=i['geo']
        retweet_count=i['retweet_count']
        favorite_count=i['favorite_count']
    
        twit=Twitter(created_at=created_at,text=text,hashtag=hashtag,symbol=symbol,
        user_mentions=user_mentions,url=url,expanded_url=expanded_url,
        display_url=display_url,indices=indices,result_type=result_type,
        geo=geo,retweet_count=retweet_count,favorite_count=favorite_count)
        
        db.session.add(twit)
        db.session.commit()  


          
    

if __name__:
    add_twit()
    app.run()




