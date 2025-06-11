import pickle

MODEL_PATH = "models/rank_model_2020.pkl"

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

print(f"✅ モデル読み込み完了: {MODEL_PATH}\n")
print("📊 特徴量の重要度一覧（降順）:")

# 重要度でソートして表示
features = list(zip(model.feature_name_, model.feature_importances_))
features.sort(key=lambda x: x[1], reverse=True)

for name, importance in features:
    print(f"{name}: {importance}")