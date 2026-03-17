import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "sentiment_model.pkl")

model = joblib.load(MODEL_PATH)

def predict_sentiment(text):
    return model.predict([text])[0]