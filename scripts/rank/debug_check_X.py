import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import pandas as pd
from scripts.rank.rank_step2_train import prepare_features

# 適当なファイルを読み込み（step1の出力ファイルなど）
df = pd.read_csv("data/entries_like/entry_like_2020-01-01.csv")

# 特徴量整形
X, y = prepare_features(df)

# 結果を表示
print("✅ 特徴量の中身:")
print(X.head())
print("\n📊 各カラムのユニーク値の数:")
print(X.nunique())