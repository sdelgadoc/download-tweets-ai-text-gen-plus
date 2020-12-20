import fire
import re
import csv
from tqdm import tqdm
from time import sleep
import os
from textblob import TextBlob
from keys import keys, environment_name
import tweepy

# Seconds to wait after calling Twitter API to avoid rate limits
api_delay = 2

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

    # Authenticate with the Twitter API
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
    :param api: Open Twitter API reference.
    :param w: Open file reference to write output.
    """

    print("Retrieving tweets for @{}...".format(username))

    # Validate that authentication tokens have been entered
    assert keys["consumer_key"] != "",  "Enter your consumer key into the keys.py file"
    assert keys["consumer_secret"] != "",  "Enter your consumer secret key into the keys.py file"
    assert keys["access_token"] != "", "Enter your access tokens into the keys.py file"
    assert keys["access_token_secret"] != "", "Enter your access token secret into the keys.py file"
    assert environment_name != "", "Enter your environment name into the keys.py file"

    # Validate that limit is a multiple of 100; set total number of tweets
    if limit:
        assert limit % 100 == 0, "`limit` must be a multiple of 100."
        
        pbar = tqdm(range(limit), desc="Oldest Tweet")

    # If no limit specifed, don't specify total number of tweet
    else:
        pbar = tqdm()
    
    # Create a tweepy cursor with or without a limit depending on parameters
    if limit is not None:
        cursor = tweepy.Cursor(api.search_full_archive, 
                               environment_name=environment_name,
                               query = "from:" + username,
                               fromDate="200603220000").items(limit)
    else:
        cursor = tweepy.Cursor(api.search_full_archive,
                               environment_name=environment_name,
                               query = "from:" + username,
                               fromDate="200603220000").items()

    
    # Iterate until the StopIteration exception is hit
    while True:
        try:
            # Get the next tweet from the cursos
            tweet = cursor.next()
            
            # Get the tweet's full text depending where it is located
            tweet_full_text = ""
            if tweet.truncated:
                tweet_full_text = tweet.extended_tweet["full_text"]
            else:
                tweet_full_text = tweet.text
            
            # If the tweet is not a retweet
            if tweet_full_text[:3] != "RT ":
            
                # If we do not filter out replies
                if include_replies:
                    
                    tweet_text = format_text(tweet, strip_usertags,
                                             strip_hashtags,sentiment,
                                             text_format, api)
                
                    # Do not write tweet to file if the tweet_text is empty
                    if tweet_text != "":
                        # Write tweet text to file
                        w.writerow([tweet_text])
                        
                
                # If we do filter out replies
                else:
                    
                    if not is_reply(tweet):
                        tweet_text = format_text(tweet, strip_usertags,
                                                 strip_hashtags,sentiment,
                                                 text_format, api)
                
                        # Do not write tweet to file if the tweet_text is empty
                        if tweet_text != "":
                            # Write tweet text to file
                            w.writerow([tweet_text])
                            
            # Update the progress bar with one iteration
            pbar.update(1)
            # Pause to avoid hitting rate limits
            sleep(api_delay)
                

        except StopIteration:
            break
    
    pbar.close()
    
    # Return 0
    return 0


def format_text(tweet, 
                strip_usertags = False,
                strip_hashtags = False,
                sentiment = 0,
                text_format = "simple",
                api = None):
    """
    Format a tweet's text for output based on certain parameters
    :param tweet_object: Twitter API tweet object whose object will be formated
    :param strip_usertags: Whether to remove user tags from the tweets.
    :param strip_hashtags: Whether to remove hashtags from the tweets.
    :param sentiment: Number of sentiment categories to include in text.
    :param text_format: Type of output format for the tweet.
    :param api: Open Twitter API reference
    """
    
    output_tweet_text = ""
    
    # 'simple' text format only returns the tweet text
    if text_format == "simple":
        
        
        # Get the tweet's full text depending where it is
        tweet_full_text = ""
        if tweet.truncated:
            tweet_full_text = tweet.extended_tweet["full_text"]
        else:
            tweet_full_text = tweet.text
        
        # Clean the tweet's text
        cleaned_text = clean_text(tweet_full_text, strip_usertags,
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
        
        # Add the arguments delimieter
        output_tweet_text = "****ARGUMENTS\n"
        
        # Specify whether the tweet is an original tweet or a reply
        if is_reply(tweet):
            output_tweet_text += "REPLY\n"
        else:
            output_tweet_text += "ORIGINAL\n"
        
        # Get the tweet's full text depending where it is
        tweet_full_text = ""
        if tweet.truncated:
            tweet_full_text = tweet.extended_tweet["full_text"]
        else:
            tweet_full_text = tweet.text
        
        # Clean the tweet's text
        cleaned_text = clean_text(tweet_full_text, strip_usertags,
                                  strip_hashtags)
        
        # If we should include sentiment information, do so
        if sentiment > 0:
            # Add sentiment information
            output_tweet_text += sentiment_text(cleaned_text, sentiment) + "\n"
        
        # Write the parent tweet delimieter
        output_tweet_text += "****PARENT\n"
        
        
        # Declare tweet objects as none for future comparison
        in_reply_to_tweet = None
        parent_tweet = None
        
        # If the tweet is a reply, try to get the replied to tweet
        if is_reply(tweet):
            
            # Sometimes Twitter references non-existant tweets, so handle errors
            try:
                # Get the object for the tweet that was replied to
                in_reply_to_tweet = api.get_status(tweet.in_reply_to_status_id_str,
                                                  tweet_mode="extended")
                # Delay to avoid hitting rate limits
                sleep(api_delay)
            
            # If tweet is non-existant, move on
            except tweepy.error.TweepError:
                pass
            
        # If the replied to tweet was found, find parent
        if in_reply_to_tweet is not None:
            
            # Sometimes Twitter references non-existant tweets, so handle errors
            try:
                # Get the object for the parent tweet
                parent_tweet = api.get_status(in_reply_to_tweet.in_reply_to_status_id_str,
                                              tweet_mode="extended")
                # Delay to avoid hitting rate limits
                sleep(api_delay)
            
            # If tweet is non-existant, move on
            except tweepy.error.TweepError:
                # If you can't find the parent tweet, assign reply_to to parent
                parent_tweet = in_reply_to_tweet
        
        # If we could find the parent tweet, populate with text
        if parent_tweet is not None:
            cleaned_text = clean_text(parent_tweet.full_text, 
                                          strip_usertags, strip_hashtags)
            
            output_tweet_text += cleaned_text + "\n"
            
        # Write the parent tweet delimieter
        output_tweet_text += "****IN_REPLY_TO\n"
        
        # If we could find the parent tweet, populate with text
        if in_reply_to_tweet is not None:
            cleaned_text = clean_text(in_reply_to_tweet.full_text, 
                                          strip_usertags, strip_hashtags)
            
            output_tweet_text += cleaned_text + "\n"
            
       
        # Convert to ORIGINAL if tweet is REPLY but can't retrieve parent tweet
        if is_reply(tweet) and in_reply_to_tweet is None:
            
            # Add the arguments delimieter
            output_tweet_text = "****ARGUMENTS\n"
            output_tweet_text += "ORIGINAL\n"
            
            # If we should include sentiment information
            if sentiment > 0:
                
                # Get the tweet's full text depending where it is
                tweet_full_text = ""
                if tweet.truncated:
                    tweet_full_text = tweet.extended_tweet["full_text"]
                else:
                    tweet_full_text = tweet.text
        
                
                cleaned_text = clean_text(tweet_full_text, strip_usertags,
                                  strip_hashtags)
                output_tweet_text += sentiment_text(cleaned_text, sentiment)+"\n"
        
            # Add empty PARENT and IN_REPLY_TO sections
            output_tweet_text += "****PARENT\n"
            output_tweet_text += "****IN_REPLY_TO\n"
        
        # Write the reply tweet delimieter
        output_tweet_text += "****TWEET\n"
        
        # Get the tweet's full text depending where it is
        tweet_full_text = ""
        if tweet.truncated:
            tweet_full_text = tweet.extended_tweet["full_text"]
        else:
            tweet_full_text = tweet.text
        
        
        # Clean the tweet's text
        cleaned_text = clean_text(tweet_full_text, strip_usertags,
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
    :param tweet: Tweepy tweet object for which to determine if it's a replt
    """

    # If the tweet does not have an in_reply value
    if tweet.in_reply_to_screen_name is None:
        return False
    else:
        return True


if __name__ == "__main__":
    fire.Fire(download_tweets)
