import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score
import joblib

# Download NLTK data (if not already downloaded)
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords')

class SentimentAnalyzer:
    def __init__(self, model_path='sentiment_model.joblib', vectorizer_path='vectorizer.joblib'):
        self.model_path = model_path
        self.vectorizer_path = vectorizer_path
        self.model = None
        self.vectorizer = None
        self.stemmer = PorterStemmer()
        self.stopwords = set(stopwords.words('english'))

    def _preprocess_text(self, text):
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'@[^\s]+', '', text)
        text = re.sub(r'#', '', text)
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        text = text.lower()
        tokens = text.split()
        tokens = [self.stemmer.stem(word) for word in tokens if word not in self.stopwords]
        return " ".join(tokens)

    def train_model(self, data_path='sentiment140.parquet'):
        df = pd.read_parquet(data_path)
        df = df[['text', 'sentiment']]
        df['sentiment'] = df['sentiment'].replace({0: 'negative', 4: 'positive'})

        # For training purposes, let's use a smaller subset of the data to avoid long training times
        df = df.sample(n=100000, random_state=42)

        df['processed_text'] = df['text'].apply(self._preprocess_text)

        self.vectorizer = TfidfVectorizer(max_features=5000)
        X = self.vectorizer.fit_transform(df['processed_text'])
        y = df['sentiment']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model = MultinomialNB()
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        print(f"Model accuracy: {accuracy_score(y_test, y_pred)}")

        joblib.dump(self.model, self.model_path)
        joblib.dump(self.vectorizer, self.vectorizer_path)

    def load_model(self):
        try:
            self.model = joblib.load(self.model_path)
            self.vectorizer = joblib.load(self.vectorizer_path)
        except FileNotFoundError:
            print("Model not found. Training a new model...")
            self.train_model()

    def get_sentiment(self, text):
        if self.model is None or self.vectorizer is None:
            self.load_model()

        processed_text = self._preprocess_text(text)
        vectorized_text = self.vectorizer.transform([processed_text])
        prediction = self.model.predict(vectorized_text)
        return prediction[0]

if __name__ == '__main__':
    analyzer = SentimentAnalyzer()
    # This will train and save the model if it doesn't exist
    analyzer.load_model()

    # Example usage
    sample_text = "I love this book, it's amazing!"
    sentiment = analyzer.get_sentiment(sample_text)
    print(f"The sentiment of the text '{sample_text}' is: {sentiment}")

    sample_text_2 = "This book was a complete waste of time."
    sentiment_2 = analyzer.get_sentiment(sample_text_2)
    print(f"The sentiment of the text '{sample_text_2}' is: {sentiment_2}")
