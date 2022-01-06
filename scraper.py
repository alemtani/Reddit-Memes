from app import db, Subreddits, get_or_create

from bs4 import BeautifulSoup

import os
import praw

reddit = praw.Reddit(client_id=os.environ.get('REDDIT_CLIENT_ID'), 
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'), 
    user_agent='my user agent')

subreddit = reddit.subreddit("listofsubreddits")
soup = BeautifulSoup(subreddit.wiki["memes50k"].content_html, "lxml")

# Scrape all the subreddits in the list of meme subreddits
for ele in soup.findAll('a'):
    if ele['href'].startswith('/r'):
        name = ele['href']
        get_or_create(db.session, Subreddits, name=name, url=f"https://reddit.com{name}")