import twint
import fire
import re
import csv
from tqdm import tqdm
import logging
from datetime import datetime
from time import sleep
import os
from textblob import TextBlob
from keys import keys
import tweepy

# Surpress random twint warnings
logger = logging.getLogger()
logger.disabled = True

def download_tweets(username=None,
                    limit=None,
                    include_replies=False,
                    include_links=False,
                    strip_usertags=False,
                    strip_hashtags=False,
                    sentiment = 0,
                    text_format = "simple"):
    """
    Download public Tweets from one or multiple Twitter accounts
    into a format suitable for training with AI text generation tools.
    :param username: Twitter @ username to gather tweets or .txt file name 
        with multiple usernames
    :param limit: # of tweets to gather; None for all tweets.
    :param include_replies: Whether to include replies to other tweets.
    :param include_links: Whether to include tweets with links.
    :param strip_usertags: Whether to remove user tags from the tweets.
    :param strip_hashtags: Whether to remove hashtags from the tweets.
    :param sentiment: Number of sentiment categories to include in text.
    :param text_format: Type of output format for the tweet.
    """

    # Validate that a username or .txt file name is specified
    assert username, "You must specify a username or file name"
    
    # Create an empty list of usernames for which to dowload tweets
    usernames = []
    filename = username
    api = None
	
	# Authenticate if the text format requires the Twitter API
    if text_format == "reply":
        auth = tweepy.OAuthHandler(keys["consumer_key"], keys["consumer_secret"])
        auth.set_access_token(keys["access_token"], keys["access_token_secret"])
        api = tweepy.API(auth)
	
    # Get the file's current directory
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    # If username is a .txt file, append all usernames to usernames list
    if username[-4:] == ".txt":
        # Open username file and copy usernames to usernames list
        
        pathfilename = os.path.join(dir_path, filename)
        with open(pathfilename, 'r') as f:
            [usernames.append(username.rstrip('\n')) for username in f]
                
    
    #If username is not a .txt file, append username to usernames list
    else:
        filename = username
        usernames.append(username)
    
    # Download tweets for all usernames and write to file
    with open(dir_path + '/{}_tweets.csv'.format(filename), 'w', encoding='utf8') as f:
        w = csv.writer(f)
        w.writerow(['tweets']) # gpt-2-simple expects a CSV header by default
        
        
        for username in usernames:
            download_account_tweets(username, limit, include_replies, 
                                    strip_usertags, strip_hashtags, 
                                    include_links, sentiment, text_format, 
                                    api, w)
            
    
def download_account_tweets(username=None,
                            limit=None,
                            include_replies=False,
                            include_links=False,
                            strip_usertags=False,
                            strip_hashtags=False,
                            sentiment = 0,
                            text_format = "simple",
                            api = None,
                            w = None):
    """
    Download public Tweets from one Twitter account into a format suitable 
    for training with AI text generation tools.
    :param username: Twitter @ username to gather tweets or .txt file name
        with multiple usernames
    :param limit: # of tweets to gather; None for all tweets.
    :param include_replies: Whether to include replies to other tweets.
    :param include_links: Whether to include tweets with links.
    :param strip_usertags: Whether to remove user tags from the tweets.
    :param strip_hashtags: Whether to remove hashtags from the tweets.
    :param sentiment: Number of sentiment categories to include in text.
    :param text_format: Type of output format for the tweet.
    :param api: Open Twitter API reference
    :param w: Open file reference to write output
    """

    print("Retrieving tweets for @{}...".format(username))

    # Validate that it is a multiple of 40; set total number of tweets
    if limit:
        assert limit % 40 == 0, "`limit` must be a multiple of 40."
        
        pbar = tqdm(range(limit), desc="Oldest Tweet")

    # If no limit specifed, don't specify total number of tweet
    else:
        pbar = tqdm()
    
    # Create an empty file to store pagination id
    with open(".temp", "w", encoding="utf-8") as f:
        f.write(str(-1))

    # Set the loop's iterator
    i = 0
    # Iterate forever, and break based on reaching limit or no more tweets
    while(True):
        
        # If a limit is specified, break once it's reached
        if limit:
            if i >= (limit // 40): break
        
        # Create an empty list to store retrieved tweet objects
        tweet_data = []

        # twint may fail; give it up to 5 tries to return tweets
        for _ in range(0, 4):
            if len(tweet_data) == 0:
                c = twint.Config()
                c.Store_object = True
                c.Hide_output = True
                c.Username = username
                c.Limit = 40
                c.Resume = ".temp"

                c.Store_object_tweets_list = tweet_data

                twint.run.Search(c)

                # If it fails, sleep before retry.
                if len(tweet_data) == 0:
                    sleep(1.0)
            else:
                continue

        # If still no tweets after 5 tries, stop downloading tweets
        if len(tweet_data) == 0:
            break

        # Do not filter out replies
        if include_replies:
            
            for tweet in tweet_data:
                tweet_text = format_text(tweet, strip_usertags,
                                         strip_hashtags,sentiment,
                                         text_format, api)
        
                # Do not write tweet to file if the tweet_text is empty
                if tweet_text != "":
                    # Write tweet text to file
                    w.writerow([tweet_text])
        # Filter out replies
        else:
            
            for tweet in tweet_data:
                if not is_reply(tweet):
                    tweet_text = format_text(tweet, strip_usertags,
                                             strip_hashtags,sentiment,
                                             text_format, api)
            
                    # Do not write tweet to file if the tweet_text is empty
                    if tweet_text != "":
                        # Write tweet text to file
                        w.writerow([tweet_text])
            
    
        pbar.update(40)

        oldest_tweet = datetime.utcfromtimestamp(tweet_data[-1].datetime / 
                                                 1000.0).strftime(
                                                 "%Y-%m-%d %H:%M:%S")
        pbar.set_description("Oldest Tweet: " + oldest_tweet)
        
        # Increase the loop's iterator
        i = i +1
            
    pbar.close()
    os.remove(".temp")
    
    # Return 0
    return 0


def format_text(tweet_object, 
                strip_usertags = False,
                strip_hashtags = False,
                sentiment = 0,
                text_format = "simple",
                api = None):
    """
    Format a tweet's text for output based on certain parameters
    :param tweet_object: Twint tweet object whose object will be formated
    :param strip_usertags: Whether to remove user tags from the tweets.
    :param strip_hashtags: Whether to remove hashtags from the tweets.
    :param sentiment: Number of sentiment categories to include in text.
    :param text_format: Type of output format for the tweet.
    :param api: Open Twitter API reference
    """
    
    output_tweet_text = ""
    
    # 'simple' text format only returns the tweet text
    if text_format == "simple":
        
        # Clean the tweet's text
        cleaned_text = clean_text(tweet_object.tweet, strip_usertags,
                                  strip_hashtags)
        
        # If we should include sentiment information
        if sentiment > 0:
            output_tweet_text += sentiment_text(cleaned_text, sentiment) + "\n"
        
        output_tweet_text += cleaned_text
    
        # Return an empty string if cleaned_text is empty
        if cleaned_text == "":
            output_tweet_text = ""
   
   
    # 'reply' text format includes text from the tweets that were replied-to
    if text_format == "reply":
        
        # How many second to wait after calling Twitter API
        api_delay = 1.5
        
        # Clean the tweet's text
        cleaned_text = clean_text(tweet_object.tweet, strip_usertags,
                                  strip_hashtags)
        
        # Add the arguments delimieter
        output_tweet_text = "****ARGUMENTS\n"
        
        # Specify whether the tweet is an original tweet or a reply
        if is_reply(tweet_object):
            output_tweet_text += "REPLY\n"
        else:
            output_tweet_text += "ORIGINAL\n"
        
        # If we should include sentiment information
        if sentiment > 0:
            output_tweet_text += sentiment_text(cleaned_text, sentiment) + "\n"
        
        # Write the parent tweet delimieter
        output_tweet_text += "****PARENT\n"
        
        # Add the thread's parent tweet text if the tweet is a reply
        parent_tweet_found = True
        
        if is_reply(tweet_object):
            
            # Sometimes Twitter references non-existant tweets, so handle error
            try:
                # Get the object of the thread's parent tweet
                parent_tweet_object = api.get_status(tweet_object.conversation_id,
                                                     tweet_mode="extended")
                # Delay to avoid hitting rate limits
                sleep(api_delay)
                
                cleaned_text = clean_text(parent_tweet_object.full_text, 
                                          strip_usertags, strip_hashtags)
            
            # If tweet is non-existant, use original cleaned tweet text
            except tweepy.error.TweepError:
                parent_tweet_found = False
            
            output_tweet_text += cleaned_text + "\n"
        
        # Write the parent tweet delimieter
        output_tweet_text += "****IN_REPLY_TO\n"
        
        # Add in-reply to tweet text if the tweet is a reply
        if is_reply(tweet_object):
            
            api_tweet_object = api.get_status(tweet_object.id_str, 
                                              tweet_mode="extended")
            # Delay to avoid hitting rate limits
            sleep(api_delay)
                    
            
            in_reply_to_status_id_str = api_tweet_object.in_reply_to_status_id_str
            
            # Only get in-reply tweet object if different from the parent tweet
            if in_reply_to_status_id_str != tweet_object.conversation_id:

                # Sometimes Twitter references non-existant tweets, so handle error
                try:
                    in_reply_tweet_object = api.get_status(in_reply_to_status_id_str, 
                                                           tweet_mode="extended")
                    # Delay to avoid hitting rate limits
                    sleep(api_delay)
                    
                    cleaned_text = clean_text(in_reply_tweet_object.full_text, 
                                          strip_usertags, strip_hashtags)
                    
                # If tweet is non-existant, use original cleaned tweet text
                except tweepy.error.TweepError:
                    pass
                    
            output_tweet_text += cleaned_text + "\n"
       
        # Convert to ORIGINAL if tweet is REPLY but can't retrieve parent tweet
        if is_reply(tweet_object) and not parent_tweet_found:
            
            # Add the arguments delimieter
            output_tweet_text = "****ARGUMENTS\n"
            output_tweet_text += "ORIGINAL\n"
            
            # If we should include sentiment information
            if sentiment > 0:
                output_tweet_text += sentiment_text(cleaned_text, sentiment)+"\n"
        
            # Add empty PARENT and IN_REPLY_TO sections
            output_tweet_text += "****PARENT\n"
            output_tweet_text += "****IN_REPLY_TO\n"
        
        # Write the reply tweet delimieter
        output_tweet_text += "****TWEET\n"
        
        # Clean the tweet's text
        cleaned_text = clean_text(tweet_object.tweet, strip_usertags,
                                  strip_hashtags)
        
        # Add the cleaned tweet text
        output_tweet_text += cleaned_text
        
            
    return(output_tweet_text)


def sentiment_text(tweet_text, sentiment = 0):
    """
    Returns a string describing the tweet text's sentiment
    :param tweet_text: Text for which sentiment should be measured
    :param sentiment: Number of sentiment categories to include in text.
    """
    
    output_tweet_text = ""
    
    blob = TextBlob(tweet_text)
    
    # If sentiment is divided into 3 categories
    if sentiment == 3:
        if blob.sentiment.polarity < 0:
            output_tweet_text += "NEGATIVE"
        elif blob.sentiment.polarity == 0:
            output_tweet_text += "NEUTRAL"
        else:
            output_tweet_text += "POSITIVE"
    
    # If sentiment is divided into 5 categories
    elif sentiment == 5:
        if blob.sentiment.polarity < -0.5:
            output_tweet_text += "VERY NEGATIVE"
        elif blob.sentiment.polarity < 0:
            output_tweet_text += "NEGATIVE"
        elif blob.sentiment.polarity == 0:
            output_tweet_text += "NEUTRAL"
        elif blob.sentiment.polarity > 0.5:
            output_tweet_text += "VERY POSITIVE"
        else:
            output_tweet_text += "POSITIVE"
    
    # If sentiment is divided into 7 categories
    elif sentiment == 7:
        if blob.sentiment.polarity < -2/3:
            output_tweet_text += "EXTREMELY NEGATIVE"
        elif blob.sentiment.polarity < -1/3:
            output_tweet_text += "VERY NEGATIVE"
        elif blob.sentiment.polarity < 0:
            output_tweet_text += "NEGATIVE"
        elif blob.sentiment.polarity == 0:
            output_tweet_text += "NEUTRAL"
        elif blob.sentiment.polarity > 2/3:
            output_tweet_text += "EXTREMELY POSITIVE"
        elif blob.sentiment.polarity > 1/3:
            output_tweet_text += "VERY POSITIVE"
        else:
            output_tweet_text += "POSITIVE"
    
    return output_tweet_text


def clean_text(tweet_text, strip_usertags = False, strip_hashtags = False):
    """
    Remove sections of the tweet text (clean) based on parameters
    :param tweet_text: Text for which sentiment should be measured
    :param strip_usertags: Whether to remove user tags from the tweets.
    :param strip_hashtags: Whether to remove hashtags from the tweets.
    """
    
    # Strip all the leading usertags
    while re.search(r"^@[a-zA-Z0-9_]+", tweet_text):
        tweet_text = re.sub(r"^@[a-zA-Z0-9_]+", '', tweet_text).strip()

    # Regex pattern for removing URL's
    pattern = r"http\S+|pic\.\S+|\xa0|…"
    
    if strip_usertags:
        pattern += r"|@[a-zA-Z0-9_]+"
    
    if strip_hashtags:
        pattern += r"|#[a-zA-Z0-9_]+"
    
    tweet_text = re.sub(pattern, '', tweet_text).strip()
    
    return tweet_text


def is_reply(tweet):
    """
    Determines if the tweet is a reply to another tweet.
    :param tweet: Twint tweet object whose object will be formated
    """

    # If not a reply to another user, there will only be 1 entry in reply_to
    if len(tweet.reply_to) == 1:
        return False

    # Check to see if any of the other users "replied" are in the tweet text
    users = tweet.reply_to[1:]
    conversations = [user["username"] in tweet.tweet for user in users]

    # If any if the usernames are not present in text, then it must be a reply
    if sum(conversations) < len(users):
        return True
    
    # On older tweets, tweets starting with an "@" are de-facto replies
    if tweet.tweet.startswith('@'):
        return True
        
    return False


if __name__ == "__main__":
    fire.Fire(download_tweets)
