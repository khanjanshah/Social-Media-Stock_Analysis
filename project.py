# Twitter API authentication
from nltk.stem import WordNetLemmatizer
from textblob import TextBlob
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import seaborn as sns
import tweepy
import pandas as pd
import psycopg2
import time as time
import numpy as np
# Machine learning libraries
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score

from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

from flask import Flask, render_template    # Import Flask class or object from flask library
# from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)  # instantiate Flask Object with name as parameter ( object value in py)


@app.route('/')  # route your app-page to localhost
def home():
    return render_template('home.html')

@app.route('/analysis/')
def analysis():

    api_key = 'xxfFhKuv7R2Irh6xKrPD5uGW1'
    api_secret_key = 'woFS1ImjD2pqWFiURuVTmmmbIrSV81oWyc3IOKsPnFSP2mlvf6'
    access_token = '2289730268-f9NnKZjscacX37JjhJiER3AA3MV51NORRAxxJWH'
    access_token_secret = 'mAgYXNZNH7h6f8PUv4kQbabLTxbBKO5dGksHcYdxqP8mQ'

    # authorize the API Key
    authentication = tweepy.OAuthHandler(api_key, api_secret_key)

    # authorization to user's access token and access token secret
    authentication.set_access_token(access_token, access_token_secret)

    # call the api
    api = tweepy.API(authentication)

    tweets = api.search('@reliancejio', count=10000)
    # Retrieve tweets

    for tweet in tweets:
        print("-->", tweet.text)

        # print(tweets)
    data = pd.DataFrame(data=[tweet.text for tweet in tweets], columns=['Tweets'])
    #
    print(data.head(10))
    print(data.size)
    print(tweets[0].created_at)

    # print(data.head(10), data.size, tweets[0].created_at)

    # Only tweets we want to retrieve...

    class MyStreamListener(tweepy.StreamListener):

        def __init__(self, time_limit=300):
            self.start_time = time.time()
            self.limit = time_limit
            super(MyStreamListener, self).__init__()

        def on_connect(self):
            print("Connected to Twitter API.")

        def on_status(self, status):

            # Tweet ID
            tweet_id = status.id

            # User ID
            user_id = status.user.id
            # Username
            username = status.user.name

            # Tweet
            if status.truncated == True:
                tweet = status.extended_tweet['full_text']
                hashtags = status.extended_tweet['entities']['hashtags']
            else:
                tweet = status.text
                hashtags = status.entities['hashtags']

            # Extract hashtags
            def read_hashtags(tag_list):
                hashtags = []
                for tag in tag_list:
                    hashtags.append(tag['text'])
                return hashtags

            # Read hastags
            hashtags = read_hashtags(hashtags)

            # Retweet count
            retweet_count = status.retweet_count
            # Language
            lang = status.lang

            # If tweet is not a retweet and tweet is in English
            if  hasattr(status, "retweeted_status") and lang == "en":
                # Connect to database
                dbConnect(user_id, username, tweet_id, tweet, retweet_count, hashtags,sentiment)

            if (time.time() - self.start_time) > self.limit:
                print(time.time(), self.start_time, self.limit)
                return False

        def on_error(self, status_code):
            if status_code == 420:
                # Returning False in on_data disconnects the stream
                return False

    def dbConnect(user_id, user_name, tweet_id, tweet, retweet_count, hashtags):
        conn = psycopg2.connect(host="localhost", database="TwitterDB", port=5432, user="postgres",
                                password="kjshah007")

        cur = conn.cursor()

        # insert user information
        command = '''INSERT INTO TwitterUser (user_id, user_name) VALUES (%s,%s) ON CONFLICT
                     (User_Id) DO NOTHING;'''
        cur.execute(command, (user_id, user_name))

        # insert tweet information
        command = '''INSERT INTO TwitterTweet (tweet_id, user_id, tweet, retweet_count) VALUES (%s,%s,%s,%s);'''
        cur.execute(command, (tweet_id, user_id, tweet, retweet_count))

        # insert entity information
        for i in range(len(hashtags)):
            hashtag = hashtags[i]
            command = '''INSERT INTO TwitterEntity (tweet_id, hashtag) VALUES (%s,%s);'''
            cur.execute(command, (tweet_id, hashtag))


        # Create

        # Commit changes
        conn.commit()

        # Disconnect
        cur.close()
        conn.close()

    def preprocess(tweet):

        # remove links
        tweet = re.sub(r'http\S+', '', tweet)
        # remove mentions
        tweet = re.sub("@\w+", "", tweet)
        # alphanumeric and hashtags
        tweet = re.sub("[^a-zA-Z#]", " ", tweet)
        # remove multiple spaces
        tweet = re.sub("\s+", " ", tweet)
        tweet = tweet.lower()
        # Lemmatize
        lemmatizer = WordNetLemmatizer()
        sent = ' '.join([lemmatizer.lemmatize(w) for w in tweet.split() if len(lemmatizer.lemmatize(w)) > 3])

        return sent

    def DbConnect1(query):
        conn = psycopg2.connect(host="localhost", database="TwitterDB", port=5432, user="postgres",
                                password="kjshah007")
        curr = conn.cursor()

        curr.execute(query)

        rows = curr.fetchall()

        return rows

    data_tweet = DbConnect1("SELECT User_Id, Tweet_Id, Tweet FROM TwitterTweet;")
    df_tweet = pd.DataFrame(columns=['User_Id', 'Tweet_Id', 'Clean_Tweet'])
    for data in data_tweet:
        index = len(df_tweet)
        df_tweet.loc[index, 'User_Id'] = data[0]
        df_tweet.loc[index, 'Tweet_Id'] = data[1]
        df_tweet.loc[index, 'Clean_Tweet'] = preprocess(data[2])
    print(df_tweet.head())

    # Most commomly occuring words
    def keywords():
        all_words = ' '.join([text for text in df_tweet['Clean_Tweet']])
        wordcloud = WordCloud(width=800, height=500, random_state=21, max_font_size=110).generate(all_words)
        plt.figure(figsize=(10, 7))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis('off')
        plt.show()

    keywords()

    # Sentiment analysis using Textblob

    def sentiment(tweet):
        analysis = TextBlob(tweet)
        if analysis.sentiment.polarity > 0:
            return 1
        elif analysis.sentiment.polarity == 0:
            return 0
        else:
            return -1

    df_tweet['Sentiment'] = df_tweet['Clean_Tweet'].apply(sentiment)

    print(df_tweet.head(20))
    def dbConnect(user_id, tweet_id, tweet, sentiment):
        conn = psycopg2.connect(host="localhost", database="TwitterDB", port=5432, user="postgres",
                                password="kjshah007")

        cur = conn.cursor()

        command = '''INSERT INTO TwitterSentiments (tweet_id, user_id, tweet, sentiment) VALUES (%s,%s,%s,%s);'''
        cur.execute(command, (tweet_id, user_id, tweet, sentiment))
        conn.commit()

    # Disconnect
        cur.close()
        conn.close()

    # Querying hashtags from database
    data_tags = DbConnect1("SELECT Tweet_Id, Hashtag FROM TwitterEntity;")

    df_tags = pd.DataFrame(columns=['Tweet_Id', 'Hashtags'])

    for data in data_tags:
        index = len(df_tags)
        df_tags.loc[index, 'Tweet_Id'] = data[0]
        df_tags.loc[index, 'Hashtags'] = data[1]

    print(df_tags.head(20))

    # # Unique hashtag counts
    table = df_tags.pivot_table(index="Hashtags", values='Tweet_Id', aggfunc=len)

    # # Convert pivot table to dataframe
    df_pivot = pd.DataFrame(table.to_records())

    print(df_pivot.head())

    # # Plotting hashtags counts

    data = df_pivot.nlargest(columns="Tweet_Id", n=15)

    # # Creating bar graph
    plt.figure(figsize=(8, 3))
    ax = sns.barplot(data=data, x="Hashtags", y="Tweet_Id", palette=("Reds_d"))

    # # Altering the visual elements
    sns.set_context("poster")
    ax.set(ylabel='Count')
    ax.set_xticklabels(labels=ax.get_xticklabels(), rotation=70)

    plt.title('Reliance Jio #Hastags Analysis')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)

    # # Output plot
    plt.show()
    #

    if __name__ == '__main__':
        myStreamListener = MyStreamListener()
        myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener,
                                 tweet_mode="extended")

        myStream.filter(track=['reliancejio', 'Jiocare', 'MukeshAmbanima', 'reliancegroup'])

    return render_template("analysis.html")

@app.route('/prediction/')
def prediction():
    # Data Manupulation

    # Read the data from Yahoo
    df = pd.read_csv('RELIANCE.NS.csv')
    df = df[['Open', 'High', 'Low', 'Close']]
    df.head()

    # Predictor variables
    df['Open-Close'] = df.Open - df.Close
    df['High-Low'] = df.High - df.Low
    df = df.dropna()
    X = df[['Open-Close', 'High-Low']]
    X.head()

    # Target variable
    Y = np.where(df['Close'].shift(-1) > df['Close'], 1, -1)

    # Splitting the dataset
    split_percentage = 0.7
    split = int(split_percentage * len(df))

    X_train = X[:split]
    Y_train = Y[:split]

    X_test = X[split:]
    Y_test = Y[split:]

    # Instantiate KNN learning model(k=15)
    knn = KNeighborsClassifier(n_neighbors=15)

    # fit the model
    knn.fit(X_train, Y_train)

    # Accuracy Score
    accuracy_train = accuracy_score(Y_train, knn.predict(X_train))
    accuracy_test = accuracy_score(Y_test, knn.predict(X_test))

    print('Train_data Accuracy: %.2f' % accuracy_train)
    print('Test_data Accuracy: %.2f' % accuracy_test)

    # Predicted Signal
    df['Predicted_Signal'] = knn.predict(X)

    # SPY Cumulative Returns
    df['SPY_returns'] = np.log(df['Close'] / df['Close'].shift(1))
    Cumulative_SPY_returns = df[split:]['SPY_returns'].cumsum() * 100

    # Cumulative Strategy Returns
    df['Startegy_returns'] = df['SPY_returns'] * df['Predicted_Signal'].shift(1)
    Cumulative_Strategy_returns = df[split:]['Startegy_returns'].cumsum() * 100

    # Plot the results to visualize the performance

    plt.figure(figsize=(10, 5))
    plt.plot(Cumulative_SPY_returns, color='r', label='Jio Twitter Stock Price')
    plt.plot(Cumulative_Strategy_returns, color='g', label='Jio Yahoo Finance')
    plt.legend()
    plt.show()

    # Calculate Sharpe reatio
    Std = Cumulative_Strategy_returns.std()
    Sharpe = (Cumulative_Strategy_returns - Cumulative_SPY_returns) / Std
    Sharpe = Sharpe.mean()
    print('Sharpe ratio: %.2f' % Sharpe)

    return render_template('prediction.html')

@app.route('/visualize/')
def visualize():
    def DbConnect1(query):
        conn = psycopg2.connect(host="localhost", database="TwitterDB", port=5432, user="postgres",
                                password="kjshah007")
        curr = conn.cursor()

        curr.execute(query)

        rows = curr.fetchall()

        return rows

    predict = DbConnect1("SELECT * FROM prediction;")
    df_tweet = pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume'])
    for data in predict:
        index = len(df_tweet)
        df_tweet.loc[index, 'Date'] = data[0]
        df_tweet.loc[index, 'Open'] = data[1]
        df_tweet.loc[index, 'High'] = data[2]
        df_tweet.loc[index, 'Low'] = data[3]
        df_tweet.loc[index, 'Close'] = data[4]
        df_tweet.loc[index, 'Adj_Close'] = data[5]
        df_tweet.loc[index, 'Volume'] = data[6]
    print(df_tweet.head())

    # prepare dataset to work with
    jio_df = df_tweet[['Date', 'High', 'Open', 'Low', 'Close']]
    jio_df.head(10)

    plt.figure(figsize=(10, 5))
    # plt.get_current_fig_manager().window.wm_maxsize()
    plt.title('JIO Stocks Closing Price History 2019-2020')
    plt.plot(jio_df['Date'], jio_df['Close'])
    plt.xlabel('Date', fontsize=18)
    plt.ylabel('Close Price INR ', fontsize=18)
    plt.style.use('fivethirtyeight')
    plt.show()

    return render_template('visualize.html')

@app.route('/about/')
def about():
    return render_template('about.html')


if __name__ == '__main__':   # main method from where whole script runs.
    app.run(debug=True)




# In website to deploy we are creating virtual environment so that the libraries we want to install
#and use in this website are under virtual env. so python not be overloaded with libraries .