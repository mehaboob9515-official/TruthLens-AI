import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

# Load dataset
data = pd.read_csv("dataset/WELFake_Dataset.csv")

# Keep only required columns
data = data[["title", "text", "label"]]

# Remove missing values
data = data.dropna()

# Combine title and text
data["content"] = data["title"] + " " + data["text"]

# Features and labels
X = data["content"]
y = data["label"]

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# Create pipeline
model = Pipeline([
    ("tfidf", TfidfVectorizer(stop_words="english", max_features=50000)),
    ("classifier", SGDClassifier(loss="hinge", random_state=42))
])

# Train model
model.fit(X_train, y_train)

# Test model
predictions = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, predictions))
print(classification_report(y_test, predictions))

# Save the complete pipeline
joblib.dump(model, "model.pkl")

print("✅ model.pkl created successfully!")