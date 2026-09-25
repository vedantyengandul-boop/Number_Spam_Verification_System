import pandas as pd

# Load dataset
file_path = "data/dataset/spam_dataset.csv"

df = pd.read_csv(file_path)

print("\n===== DATASET LOADED SUCCESSFULLY =====")

print("\nFirst 5 rows:")
print(df.head())

print("\nDataset Shape:")
print(df.shape)

print("\nColumn Names:")
print(df.columns.tolist())

print("\nMissing Values:")
print(df.isnull().sum())

print("\nStatus Distribution:")
print(df["status"].value_counts())

print("\n===== DATASET CHECK COMPLETED =====")