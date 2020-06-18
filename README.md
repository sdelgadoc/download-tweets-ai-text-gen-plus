# download-tweets-ai-text-gen-plus

A small Python 3 script to download public Tweets from a given Twitter account into a format suitable for AI text generation tools (such as [gpt-2-simple](https://github.com/minimaxir/gpt-2-simple) for finetuning [GPT-2](https://openai.com/blog/better-language-models/)).

* Retrieves all tweets as a simple CSV with a single CLI command.
* Preprocesses tweets to remove URLs, extra spaces, and optionally usertags/hashtags.
* Saves tweets in batches (i.e. there is an error or you want to end collection early)

You can view examples of AI-generated tweets from datasets retrieved with this tool in the `/examples` folder.

## Usage

First, install the Python script dependencies:

```sh
pip3 install twint==2.1.4 fire tqdm textblob tweepy
```

Then download the `download_tweets.py` script from this repo.

The script is interacted via a command line interface. After `cd`ing into the directory where the script is stored in a terminal, run:

```sh
python3 download_tweets.py <twitter_username>
```

e.g. If you want to download all tweets (sans retweets/replies/quote tweets) from Twitter user [@santiagodc](https://twitter.com/santiagodc), run:

```sh
python3 download_tweets.py santiagodc
```

The script can can also download tweets from multiple usernames at one time.  To do so, first create a text file (.txt) with the list of usernames.  Then, run script referencing the file name:

```sh
python3 download_tweets.py <twitter_usernames_file_name>
```

The tweets will be downloaded to a single-column CSV titled `<usernames>_tweets.csv`.

The parameters you can pass to the command line interface (positionally or explicitly) are:

* username: Username of the account whose tweets or .txt file name with multiple usernames you want to download [required]
* limit: Number of tweets to download [default: all tweets possible]
* include_replies: Include replies from the user in the dataset [default: False]
* strip_usertags: Strips out `@` user tags in the tweet text [default: False]
* strip_hashtags: Strips out `#` hashtags in the tweet text [default: False]
* sentiments: Adds the specified number of sentiment categories to the output so you can then generate positive/negative tweets changing a parameter [default: 0, possible values: 0, 3, 5, 7]
* text_format: Specifies the format in which tweets will be returned.  The 'simple' format only returns the tweet text. The 'reply' format returns information on preceding tweets to train an AI that can reply to tweets [default: 'simple', possible values: 'simple', 'reply']

## How to collect tweets to train an AI that can reply to tweets

The code supports collecting tweets in a format that lets you train an AI that can reply to other tweets.  The output format is based on [the format](https://www.reddit.com/r/SubSimulatorGPT2Meta/comments/caelo0/could_you_give_more_details_on_the_input/et8j3b1/?context=3) used to train the [Subreddit Simulator](https://www.reddit.com/r/SubredditSimulator/) Reddit community.

The output format is the following:
```txt
****ARGUMENTS
ORIGINAL or REPLY: Whether the tweet is an original tweet or a reply
SENTIMENT: If the sentiment parameter is used, text describing the tweet text's sentiment
****PARENT
[Tweet text for the topmost tweet in a reply thread]
****IN_REPLY_TO
[Tweet text for the tweet that is being responded to]
****TWEET
[Tweet text for the tweet that was collected]
```

To collect tweets in the reply format, you will need to [create a Twitter app](https://developer.twitter.com/en/docs/basics/apps/overview) so you can obtain access to the Twitter API.  The Twitter API is used by the code to traverse reply threads, which is currently not possible in the Twint library.

Once you create your Twitter app, input your credentials into the ``keys.py`` file shown below:

```py
keys = {'consumer_key': "",
        'consumer_secret': "",
        'access_token': "",
        'access_token_secret': ""}
```

After inputting the credentials, you can collect tweets by running:

```sh
python3 download_tweets.py <twitter_username> None True False False False 7 reply
```

***Note:*** The collection of tweets with the 'reply' format will likely be up to 90% slower than the 'simple' format, due to the Twitter API's rate limitting.  But, because each tweet has more information, you might need fewer tweets to train your model

## How to Train an AI on the downloaded tweets

[gpt-2-simple](https://github.com/minimaxir/gpt-2-simple) has a special case for single-column CSVs, where it will automatically process the text for best training and generation. (i.e. by adding `<|startoftext|>` and `<|endoftext|>` to each tweet, allowing independent generation of tweets)

You can use [this Colaboratory notebook](https://colab.research.google.com/drive/1qxcQ2A1nNjFudAGN_mcMOnvV9sF_PkEb) (optimized from the original notebook for this use case) to train the model on your downloaded tweets, and generate massive amounts of Tweets from it. Note that without a lot of data, the model might easily overfit; you may want to train for fewer `steps` (e.g. `500`).

When generating, you'll always need to include certain parameters to decode the tweets, e.g.:

```python
gpt2.generate(sess,
              length=200,
              temperature=0.7,
              prefix='<|startoftext|>',
              truncate='<|endoftext|>',
              include_prefix=False
              )
```

## Helpful Notes

* You'll need *thousands* of tweets at minimum to feed to the input model for a good generation results. (ideally 1 MB of input text data, although with tweets that hard to achieve)
* To help you reach the 1 MB of input text data, you can load data from multiple similar Twitter usernames
* The download will likely end much earlier than the theoretical limit (inferred from the user profile) as the limit includes retweets/replies/whatever cache shennanigans Twitter is employing.
* The legalities of distributing downloaded tweets is ambigious, therefore it's recommended avoiding commiting raw Twitter data to GitHub, and is the reason examples of such data is not included in this repo. (AI-generated tweets themselves likely fall under derivative work/parody protected by Fair Use)

## Maintainer

Santiago Delgado  ([@santiagodc](https://twitter.com/santiagodc))
based on [download-tweets-ai-text-gen](https://github.com/minimaxir/download-tweets-ai-text-gen) by [@minimaxir](https://github.com/minimaxir)

## License

MIT

## Disclaimer

This repo has no affiliation with Twitter Inc.
