import os
os.makedirs("figs", exist_ok=True)
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ファイル読み込み（学習用）
df = pd.read_csv("data/7th/step3_train_race_level.csv")

# 🔍 is_arareごとの特徴量平均の比較
grouped_means = df.groupby("is_arare").mean(numeric_only=True).T
diff = grouped_means[1] - grouped_means[0]
print("📊 is_arare=1 と 0 の平均差（1 - 0）:")
print(diff.sort_values(ascending=False))

# 🔍 相関係数（is_arareとの相関）
correlations = df.corr(numeric_only=True)["is_arare"].sort_values(ascending=False)
print("\n🔗 is_arareとの相関係数:")
print(correlations)

# 🔍 特徴量別の箱ひげ図（代表例）
plot_features = ["line_size_std", "num_solo", "avg_age"]
for feat in plot_features:
    # 表示から保存に変更
    plt.figure(figsize=(6, 4))
    sns.boxplot(x="is_arare", y=feat, data=df)
    plt.title(f"{feat} vs is_arare")
    plt.grid(True)
    plt.tight_layout()
    output_path = f"figs/boxplot_{feat}.png"
    plt.savefig(output_path)
    print(f"🖼️ 保存: {output_path}")
    plt.close()