from models import Users, Posts, Subreddits

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

import json
import requests
import os
import praw

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)
reddit = praw.Reddit(client_id=os.environ.get('REDDIT_CLIENT_ID'), 
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'), 
    user_agent='my user agent')

# This needs to be filled with the Page Access Token that will be provided
# by the Facebook App that will be created.
PAT = os.environ.get('FACEBOOK_PAT')

# Create the query string to peruse all meme subreddits
subreddits = Subreddits.query.all()
query = str()

for subreddit in subreddits:
    subreddit = subreddit[:3]
    if len(query) == 0:
        query += subreddit
    else:
        query += '+' + subreddit


def get_or_create(session, model, **kwargs):
    """
    Get the instance from the model or create it.
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


@app.route('/', methods=['GET'])
def handle_verification():
    """
    The verify_token object that is sent by Messenger is
    declared when we create the Facebook App.
    """
    print("Handling Verification.")
    if request.args.get('hub.verify_token', '') == 'my_voice_is_my_password_verify_me':
        print("Verification successful!")
        return request.args.get('hub.challenge', '')
    else:
        print("Verification failed!")
        return 'Error, wrong validation token'


@app.route('/', methods=['POST'])
def handle_messages():
    """
    Grab the message payload and use the function
    messaging_events to generate an iterator and extract the
    user id and message sent for each message.

    While iterating over each message, call the function
    send_message to send the messages back to the user.
    """
    print("Handling Messages")
    payload = request.get_data()
    print(payload)
    for sender, message in messaging_events(payload):
        print("Incoming from %s: %s" % (sender, message))
        send_message(PAT, sender, message)
    return "ok"


def messaging_events(payload):
    """
    Generate tuples of (sender_id, message_text) from the
    provided payload.
    """
    data = json.loads(payload)
    messaging_events = data["entry"][0]["messaging"]
    for event in messaging_events:
        if "message" in event and "text" in event["message"]:
            yield event["sender"]["id"], event["message"]["text"].encode('unicode_escape')
        else:
            yield event["sender"]["id"], "I can't echo this"


def send_message(token, recipient, text):
    """
    Send the message text to recipient with id recipient.
    """

    # Create or get user to reply meme
    myUser = get_or_create(db.session, Users, name=recipient)

    # Default meme
    payload = "https://i.imgur.com/YLyEJB7.jpeg"
    
    for submission in reddit.subreddit(query).search(text):
        # Check if submission contains an image
        if (submission.link_flair_css_class == 'image') or ((submission.is_self != True) and ((".jpg" in submission.url) or (".png" in submission.url))):
            query_result = Posts.query.filter(Posts.name == submission.id).first()
            if query_result is None:
                # Submission has never been sent to anyone
                myPost = Posts(submission.id, submission.url)
                myUser.posts.append(myPost)
                db.session.commit()
                payload = submission.url
                break
            elif myUser not in query_result.users:
                # Submission has never been sent to this user
                myUser.posts.append(query_result)
                db.session.commit()
                payload = submission.url
                break
            else:
                # Submission has already been sent to this user
                continue

    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
        params={"access_token": token},
        data=json.dumps({
            "recipient": {"id": recipient},
            "message": {"attachment": {
                        "type": "image",
                        "payload": {
                            "url": payload
                        }
            }}
        }),
        headers={'Content-type': 'application/json'})

    if r.status_code != requests.codes.ok:
        print(r.text)


if __name__ == "__main__":
    app.run()