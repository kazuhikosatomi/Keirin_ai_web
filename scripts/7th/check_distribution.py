# ファイル: check_distribution.py

import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("data/7th/step5_predictions.csv")
plt.figure(figsize=(8, 5))
plt.hist(df["predicted_score"], bins=20, edgecolor="black")
plt.title("予測スコア分布")
plt.xlabel("predicted_score")
plt.ylabel("件数")
plt.grid(True)
plt.savefig("data/7th/predicted_score_hist.png")  # 画像で保存
print("✅ ヒストグラム画像を保存しました：data/7th/predicted_score_hist.png")