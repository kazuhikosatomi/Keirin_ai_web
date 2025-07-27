import pandas as pd
import numpy as np
import argparse
import os
import unicodedata

# 全角→半角変換関数（gradeカラム用）
def normalize_grade(grade):
    if pd.isna(grade):
        return grade
    return unicodedata.normalize('NFKC', grade)

def load_entry_data(entry_path):
    df = pd.read_csv(entry_path)
    # 型変換
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    for col in ['win_rate', 'top2_rate', 'top3_rate']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def create_race_features(df_entry):
    group_cols = ['date', 'venue_id', 'race_no']
    race_features = []

    for _, g in df_entry.groupby(group_cols):
        feature = {}
        feature['date'] = g['date'].iloc[0]
        feature['venue_id'] = g['venue_id'].iloc[0]
        feature['race_no'] = g['race_no'].iloc[0]

        # ライン構成
        valid_line = g[g['line_id'] != -1]
        line_sizes = valid_line.groupby('line_id')['racer_id'].count()
        feature['avg_line_size'] = line_sizes.mean() if not line_sizes.empty else 0
        feature['std_line_size'] = line_sizes.std(ddof=0) if not line_sizes.empty else 0
        feature['max_line_size'] = line_sizes.max() if not line_sizes.empty else 0
        feature['num_lines'] = valid_line['line_id'].nunique()
        feature['num_solo'] = sum(line_sizes == 1)
        feature['leader_count'] = sum(g['line_pos'] == 1)
        feature['group_diversity'] = g['line_id'].nunique()
        feature['has_cross_area_line'] = int(valid_line.groupby('line_id')['area'].nunique().gt(1).any()) if 'area' in g.columns else 0

        # 級別
        for grade in ['SS', 'S1', 'S2', 'A1', 'A2', 'A3', 'L1']:
            feature[f'num_{grade}'] = sum(g['grade'] == grade)

        # 年齢とscoreの統計量
        feature['age_std'] = g['age'].std(ddof=0)
        feature['score_std'] = g['score'].std(ddof=0)
        feature['score_max'] = g['score'].max()
        feature['score_min'] = g['score'].min()

        # 勝率・連対率・3連率
        for rate in ['win_rate', 'top2_rate', 'top3_rate']:
            feature[f'avg_{rate}'] = g[rate].mean()
            feature[f'std_{rate}'] = g[rate].std(ddof=0)

        # レースグレード
        feature['race_grade'] = g['race_grade'].iloc[0] if 'race_grade' in g.columns else ''

        # 出走人数
        feature['num_racers'] = len(g)

        # 最大 escape/sprint スコア
        feature['escape_max'] = g['style_escape'].max() if 'style_escape' in g.columns else 0
        feature['sprint_max'] = g['style_sprint'].max() if 'style_sprint' in g.columns else 0

        # is_arare
        feature['is_arare'] = g['is_arare'].iloc[0] if 'is_arare' in g.columns else 0

        race_features.append(feature)

    df = pd.DataFrame(race_features)
    # レースグレードを数値に変換
    race_grade_mapping = {
        'F': 0,
        'F1': 1,
        'F2': 2,
        'G3': 3,
        'G2': 4,
        'G1': 5,
        'GP': 6
    }
    df["race_grade_encoded"] = df["race_grade"].map(race_grade_mapping)
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="対象日（YYYY-MM-DD）")
    args = parser.parse_args()
    target_date = args.date
    entry_path = f"data/entries/{target_date[:4]}/entry_{target_date}.csv"
    out_path = "data/8th/tmp/step3_entry_features.csv"

    df_entry = load_entry_data(entry_path)

    # 地区情報の追加
    df_master = pd.read_csv("data/master/prefectures_master.csv")
    df_master["prefecture_short"] = df_master["prefecture"].str.replace("県|府|都", "", regex=True)
    df_entry["prefecture_short"] = df_entry["prefecture"].str.replace("県|府|都", "", regex=True)
    df_entry = df_entry.merge(
        df_master[["prefecture_short", "group"]].rename(columns={"group": "area"}),
        how="left",
        on="prefecture_short"
    )

    # gradeカラムを正規化
    df_entry["grade"] = df_entry["grade"].apply(normalize_grade)

    df_feat = create_race_features(df_entry)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_feat.to_csv(out_path, index=False)
    print(f"[OK] 出力完了: {out_path}")

if __name__ == "__main__":
    main()