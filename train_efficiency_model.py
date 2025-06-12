import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# Load dataset from CSV
df = pd.read_csv("efficiency.csv")

# Split features and labels
X = df.drop(columns=["label"])
y = df["label"]

# Train model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

# Save the model
joblib.dump(model, "recommendation.pkl")
print("✅ Model trained and saved as 'recommendation.pkl'")
