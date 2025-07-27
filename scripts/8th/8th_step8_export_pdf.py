import argparse
import pandas as pd
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import os

def register_font():
    font_path = Path("fonts/ipaexg.ttf")
    if font_path.exists():
        pdfmetrics.registerFont(TTFont("IPAexGothic", str(font_path)))
        return "IPAexGothic"
    else:
        print(f"⚠️ フォントファイルが見つかりません: {font_path}")
        return "Helvetica"

def save_pdf(df, output_path):
    font_name = register_font()
    styles = getSampleStyleSheet()
    style_title = styles["Heading3"]
    style_title.fontName = font_name
    style_title.alignment = 1  # center

    doc = SimpleDocTemplate(str(output_path), pagesize=A4)
    elements = []

    date = df["date"].iloc[0]
    title_text = f"競輪AIアタルくん　AI予想　{date}"
    elements.append(Paragraph(title_text, style_title))
    elements.append(Spacer(1, 6))

    df = df.drop(columns=["date", "venue_id"], errors="ignore")

    # predict_scoreを小数第3位まで0埋めで表示する
    if "predict_score" in df.columns:
        df["predict_score"] = df["predict_score"].map(lambda x: f"{x:.3f}")

    # top10フラグに★を表示（10位以内に★マーク）
    if "predict_rank" in df.columns:
        df["top10"] = df["predict_rank"].apply(lambda x: "★" if int(x) <= 10 else "")

    table_data = [df.columns.tolist()] + df.values.tolist()
    table = Table(table_data, repeatRows=1)

    table_style = TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ])

    if "venue_name" in df.columns:
        venue_col = df.columns.get_loc("venue_name")
        prev_venue = None
        for i, row in enumerate(df.itertuples(index=False), start=1):  # 1行目はヘッダーのため +1
            current_venue = getattr(row, "venue_name", None)
            if prev_venue is not None and current_venue != prev_venue:
                table_style.add('LINEABOVE', (0, i), (-1, i), 0.75, colors.black)
            prev_venue = current_venue

    table.setStyle(table_style)
    elements.append(table)

    doc.build(elements)
    print(f"✅ PDF出力完了: {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    input_path = Path(f"docs/predict/csv/8th/final_prediction_arare_{args.date}.csv")
    output_path = f"docs/predict/pdf/8th/final_prediction_arare_{args.date}.pdf"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df = pd.read_csv(input_path)
    save_pdf(df, output_path)

if __name__ == "__main__":
    main()