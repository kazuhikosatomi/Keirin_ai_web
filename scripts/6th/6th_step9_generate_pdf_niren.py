import argparse
import pandas as pd
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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

    for venue_id in df["venue_id"].unique():
        df_page = df[df["venue_id"] == venue_id]
        date = df_page["date"].iloc[0]
        venue_name = df_page["venue_name"].iloc[0] if "venue_name" in df_page.columns else f"競輪場{venue_id}"

        title_text = f"競輪AIアタルくん　AI予想　{date}　{venue_name}"
        elements.append(Paragraph(title_text, style_title))
        elements.append(Spacer(1, 6))

        df_page = df_page.drop(columns=["date", "venue_id"], errors="ignore")
        table_data = [df_page.columns.tolist()] + df_page.values.tolist()
        table = Table(table_data, repeatRows=1)

        table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ])

        # Emphasize row breaks on race_no change
        if 'race_no' in df_page.columns:
            race_no_col = df_page.columns.get_loc('race_no')
            prev_race_no = None
            for i, row in enumerate(df_page.itertuples(index=False), start=1):  # offset by 1 due to header
                current_race_no = getattr(row, 'race_no', None)
                if prev_race_no is not None and current_race_no != prev_race_no:
                    table_style.add('LINEABOVE', (0, i), (-1, i), 0.75, colors.black)
                prev_race_no = current_race_no

        table.setStyle(table_style)
        elements.append(table)
        elements.append(PageBreak())

    doc.build(elements)
    print(f"📄 PDFを出力しました: {output_path}")

def main(date_str):
    input_path = Path(f"output/predict/6th/final_prediction_niren_{date_str}.csv")
    output_path = Path(f"output/predict/pdf/6th/final_prediction_niren_{date_str}.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    save_pdf(df, output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="予測日付（例: 2025-06-21）")
    args = parser.parse_args()
    main(args.date)