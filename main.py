import json
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import tweepy  # https://github.com/tweepy/tweepy
import csv
import re
import string
import pyLDAvis
import pyLDAvis.sklearn
import argparse
import os

class TwitterHelper:
    # Twitter API credentials
    consumer_key = ""
    consumer_secret = ""
    access_key = ""
    access_secret = ""
    stopwords = ['https', 'RT', 'amp', 't.co']

    def init(self, filename):
        self.consumer_key = os.getenv('api_key')
        self.consumer_secret = os.getenv('api_secret')
        self.access_key = os.getenv('access_token')
        self.access_secret = os.getenv('access_secret')

        if self.access_key is None \
           or self.access_secret is None\
           or self.consumer_key is None \
           or self.consumer_secret is None:

            print("Failed to load data.  Do you have a your twitter api_key, api_secret, access_token and access_secret set as environment variables?")
            exit(1)
        else:
            print(self.consumer_key)
            print(self.consumer_secret)
            print(self.access_key)
            print(self.access_secret)
            print("Twitter access info read from environment variables.")

    def get_all_tweets(self, screen_name, n=1000):
        # Twitter only allows access to a users most recent 3240 tweets with this method

        # authorize twitter, initialize tweepy
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_key, self.access_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True)

        # initialize a list to hold all the tweepy Tweets
        alltweets = []

        # make initial request for most recent tweets (200 is the maximum allowed count)
        new_tweets = api.user_timeline(screen_name=screen_name, count=200)

        # save most recent tweets
        alltweets.extend(new_tweets)

        # save the id of the oldest tweet less one
        oldest = alltweets[-1].id - 1

        # keep grabbing tweets until there are no tweets left to grab
        if n > 200:
            while len(alltweets) < n:
                # while len(new_tweets) > 0:
                print(f"getting tweets before {oldest}")

                # all subsiquent requests use the max_id param to prevent duplicates
                new_tweets = api.user_timeline(screen_name=screen_name, count=200, max_id=oldest)

                # save most recent tweets
                alltweets.extend(new_tweets)

                # update the id of the oldest tweet less one
                oldest = alltweets[-1].id - 1

                print(f"...{len(alltweets)} tweets downloaded so far")

        # transform the tweepy tweets into a 2D array that will populate the csv
        outtweets = [[tweet.id_str, tweet.created_at, tweet.text] for tweet in alltweets]

        # write the csv
        with open(f'new_{screen_name}_tweets.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(["id", "created_at", "text"])
            writer.writerows(outtweets)

        pass
        return outtweets

    def display_topics(self, model, feature_names, no_top_words):
        for topic_idx, topic in enumerate(model.components_):
            print("Topic %d:" % (topic_idx))
            print(" ".join([feature_names[i]
                            for i in topic.argsort()[:-no_top_words - 1:-1]]))

    def clean_text(self, text):
        # Make text lowercase
        text = text.lower()
        # remove text in square brackets
        text = re.sub(r'\[.*?\]', '', text)
        # remove punctuation
        text = re.sub(r'[%s]' % re.escape(string.punctuation), '', text)
        # remove words containing numbers
        text = re.sub(r'\w*\d\w*', '', text)
        text = text.replace("’s", "")  # <-- Cluge
        text = text.replace("amp", "")
        return text

    def analyze_topics(self, filename):
        df = pd.read_csv(filename)
        tweets_df_clean = pd.DataFrame(df.text.apply(lambda x: self.clean_text(x)))
        vectorizer = CountVectorizer(
            analyzer='word',
            min_df=3,  # minimum required occurences of a word
            stop_words='english',  # remove stop words
            lowercase=True,  # convert all words to lowercase
            token_pattern='[a-zA-Z0-9]{3,}',  # num chars > 3
            max_features=5000,  # max number of unique words
        )
        data_matrix = vectorizer.fit_transform(tweets_df_clean.text)
        print(data_matrix.shape)
        lda_model = LatentDirichletAllocation(
            n_components=10,  # Number of topics
            learning_method='online',
            random_state=20,
            n_jobs=-1  # Use all available CPUs
        )
        lda_output = lda_model.fit_transform(data_matrix)
        data = pyLDAvis.sklearn.prepare(lda_model, data_matrix, vectorizer, mds='tsne')
        pyLDAvis.show(data)

    def wordcloud(self, filename):
        df = pd.read_csv(filename)
        text = "".join(df.text)
        text = self.clean_text(text)

        # Generate a word cloud image
        wordcloud = WordCloud().generate(text)

        # Display the generated image:
        # the matplotlib way:
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--load", help="Load data from twitter (Y/N). Requires setting env variables. (default='N')",
                        default='N')
    parser.add_argument("--tweets", help="Number of tweets to analyze. (default=1000)", type=int, default=1000)
    parser.add_argument("--user", help="Twitter handle. (default='realDonaldTrump')", default="realDonaldTrump")
    parser.add_argument("--wordcloud", help="Draw wordcloud.  (default='Y')", default="Y")
    args = parser.parse_args()
    twitterHelper = TwitterHelper()
    if args.load == 'Y':
        twitterHelper.init("keys.json")
        palotweets = twitterHelper.get_all_tweets(args.user, args.tweets)

    if args.wordcloud == 'Y':
        twitterHelper.wordcloud("new_{}_tweets.csv".format(args.user))
    print("Analysis will be available at http://localhost:8888")
    twitterHelper.analyze_topics("new_{}_tweets.csv".format(args.user))
    print("Done.")
