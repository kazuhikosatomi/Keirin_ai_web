import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib.font_manager as fm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="対象日（YYYY-MM-DD）")
args = parser.parse_args()
target_date = args.date

# フォント登録関数（PDF用）
def register_font():
    font_path = Path("fonts/ipaexg.ttf")
    if font_path.exists():
        font_prop = fm.FontProperties(fname=str(font_path))
        plt.rcParams["font.family"] = font_prop.get_name()
        return font_prop
    else:
        print(f"⚠️ フォントファイルが見つかりません: {font_path}")
        return None

# 表描画用にmatplotlibにもフォントを適用
def set_matplotlib_font(font_name):
    plt.rcParams["font.family"] = font_name

def export_pdf_from_step5(step5_csv_path, output_pdf_path):
    font_prop = register_font()

    df = pd.read_csv(step5_csv_path)

    # venue_name を補完（必要に応じて）
    venue_master_path = Path("data/master/venue_master.csv")
    if venue_master_path.exists():
        venue_df = pd.read_csv(venue_master_path)
        df = df.merge(venue_df[["venue_id", "venue_name"]], on="venue_id", how="left")
    else:
        print("⚠️ venue_master.csv が見つかりません")

    # 欠損処理
    df = df.fillna("-")

    # 出力先フォルダの作成
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(output_pdf_path) as pdf:
        rows_per_page = 25
        for i in range(0, len(df), rows_per_page):
            page_df = df.iloc[i:i+rows_per_page]
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.axis("off")

            table_data = []
            for _, row in page_df.iterrows():
                table_data.append([
                    row.get("date", "-"),
                    row.get("venue_name", "-"),
                    f'R{int(row["race_no"])}' if pd.notnull(row.get("race_no")) else "-",
                    f'{row.get("predicted_score", 0.0):.4f}'
                ])

            col_labels = ["日付", "競輪場名", "レース", "スコア"]
            table = ax.table(cellText=table_data, colLabels=col_labels, loc="center")
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.2, 1.5)

            for key, cell in table.get_celld().items():
                if font_prop:
                    cell.set_text_props(fontproperties=font_prop)

            pdf.savefig(fig)
            plt.close(fig)

    print(f"✅ PDF出力完了: {output_pdf_path}")

# 実行部分
if __name__ == "__main__":
    input_csv = Path(f"data/7th/tmp/step5_2_predictions_{target_date}.csv")
    output_pdf = Path(f"docs/predict/pdf/7th/final_prediction_arare_{target_date}.pdf")
    export_pdf_from_step5(input_csv, output_pdf)