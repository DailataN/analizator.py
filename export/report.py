"""
Modul generowania raportu PDF dla Analizatora danych pacjentow.

Struktura raportu:
    1. Strona tytulowa
    2. Opis metodologii i pipeline
    3. Statystyki
    4. Wykres
    5. Wnioski automatyczne
"""

import os
from datetime import datetime


def _get_font():
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("PolishFont", fp))
                    return "PolishFont"
                except Exception:
                    continue
    except Exception:
        pass
    return "Helvetica"


def _draw_page_header(c, width, height, font, page_num, title="Raport analizy danych"):
    c.setFont(font, 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(50, height - 20, title)
    c.drawRightString(width - 50, height - 20, f"Strona {page_num}")
    c.line(50, height - 25, width - 50, height - 25)
    c.line(50, 30, width - 50, 30)
    c.drawCentredString(width / 2, 18,
        f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Analizator danych pacjentow")
    c.setFillColorRGB(0, 0, 0)


def _wrap_text(c, text, x, y, font, size, max_width, line_height):
    c.setFont(font, size)
    words = text.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if c.stringWidth(test, font, size) < max_width:
            line = test
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = word
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y


def _auto_conclusions(df, df_filtered, filters):
    lines = []
    if df is not None and df_filtered is not None:
        total = len(df)
        filtered = len(df_filtered)
        pct = (filtered / total * 100) if total > 0 else 0
        lines.append(
            f"Po zastosowaniu {len(filters)} filtrow pozostalo {filtered:,} z {total:,} "
            f"rekordow ({pct:.1f}% zbioru wejsciowego)."
        )

        missing = df_filtered.isnull().sum().sum()
        if missing == 0:
            lines.append("Zbior danych nie zawiera brakow danych.")
        else:
            lines.append(f"Wykryto {missing:,} brakujacych wartosci w przefiltrowanym zbiorze.")

        num_cols = df_filtered.select_dtypes(include="number").columns
        text_cols = df_filtered.select_dtypes(include="object").columns
        lines.append(
            f"Analiza obejmuje {len(num_cols)} kolumn numerycznych i {len(text_cols)} kolumn tekstowych."
        )

        for col in list(num_cols)[:3]:
            s_orig = df[col].dropna()
            s_filt = df_filtered[col].dropna()
            if len(s_orig) > 0 and len(s_filt) > 0 and s_orig.mean() != 0:
                change = ((s_filt.mean() - s_orig.mean()) / abs(s_orig.mean()) * 100)
                if abs(change) > 1:
                    direction = "wzrosla" if change > 0 else "spadla"
                    lines.append(
                        f"Srednia wartosci kolumny '{col}' {direction} o {abs(change):.1f}% "
                        f"po filtracji ({s_orig.mean():.4g} -> {s_filt.mean():.4g})."
                    )

    lines.append(
        "Analiza zostala przeprowadzona z wykorzystaniem aplikacji Analizator Danych Pacjentow, "
        "zbudowanej w Pythonie z uzyciem bibliotek pandas, matplotlib i PyQt5."
    )
    return lines


def generate_report(
    filename,
    df=None,
    df_filtered=None,
    filters=None,
    stats_text="",
    plot_buf=None,
    sql_df=None,
    sql_query="",
    source="csv",
):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.utils import ImageReader

    filters = filters or []
    width, height = A4
    font = _get_font()
    page_num = 1

    c = rl_canvas.Canvas(filename, pagesize=A4)

    # STRONA 1: TYTULOWA
    _draw_page_header(c, width, height, font, page_num)

    c.setFillColorRGB(0.13, 0.37, 0.65)
    c.rect(0, height - 140, width, 140, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(font, 22)
    c.drawCentredString(width / 2, height - 62, "Raport analizy danych pacjentow")
    c.setFont(font, 12)
    c.drawCentredString(width / 2, height - 88,
        "Analizator Danych Pacjentow — PyQt5 / pandas / SQLite")
    c.setFont(font, 10)
    c.drawCentredString(width / 2, height - 112,
        datetime.now().strftime("%d.%m.%Y, %H:%M"))
    c.setFillColorRGB(0, 0, 0)

    y = height - 175
    c.setFont(font, 13)
    c.setFillColorRGB(0.13, 0.37, 0.65)
    c.drawString(50, y, "Informacje o zbiorze danych")
    c.setFillColorRGB(0, 0, 0)
    c.line(50, y - 4, width - 50, y - 4)
    y -= 28

    data_source = df_filtered if source == "csv" else sql_df
    c.setFont(font, 11)
    if data_source is not None:
        src_label = "plik CSV/Excel" if source == "csv" else "zapytanie SQL"
        info_lines = [f"Zrodlo danych: {src_label}"]
        if source == "csv" and df is not None and df_filtered is not None:
            info_lines.append(f"Liczba rekordow: {len(df_filtered):,} (z {len(df):,} calkowitych)")
        else:
            info_lines.append(f"Liczba rekordow: {len(data_source):,}")
        info_lines.append(f"Liczba kolumn: {len(data_source.columns)}")
        cols_preview = ", ".join(data_source.columns[:8].tolist())
        if len(data_source.columns) > 8:
            cols_preview += "..."
        info_lines.append(f"Kolumny: {cols_preview}")
        for line in info_lines:
            c.drawString(60, y, line)
            y -= 20

    if filters and source == "csv":
        y -= 10
        c.setFont(font, 13)
        c.setFillColorRGB(0.13, 0.37, 0.65)
        c.drawString(50, y, "Zastosowane filtry")
        c.setFillColorRGB(0, 0, 0)
        c.line(50, y - 4, width - 50, y - 4)
        y -= 28
        c.setFont(font, 11)
        for col, op, val in filters:
            c.drawString(60, y, f"• {col} {op} {val}")
            y -= 18

    # STRONA 2: METODOLOGIA
    c.showPage()
    page_num += 1
    _draw_page_header(c, width, height, font, page_num)

    y = height - 60
    c.setFont(font, 16)
    c.setFillColorRGB(0.13, 0.37, 0.65)
    c.drawString(50, y, "Cel i metodologia")
    c.setFillColorRGB(0, 0, 0)
    c.line(50, y - 4, width - 50, y - 4)
    y -= 30

    c.setFont(font, 12)
    c.setFillColorRGB(0.13, 0.37, 0.65)
    c.drawString(50, y, "Cel analizy")
    c.setFillColorRGB(0, 0, 0)
    y -= 18
    cel = (
        "Niniejszy raport przedstawia wyniki analizy danych medycznych z wykorzystaniem aplikacji "
        "Analizator Danych Pacjentow. Celem analizy jest eksploracja danych klinicznych, "
        "identyfikacja wzorcow oraz ocena wplywu zastosowanych parametrow filtrowania "
        "na uzyskane wyniki statystyczne."
    )
    y = _wrap_text(c, cel, 50, y, font, 10, width - 100, 14)
    y -= 20

    c.setFont(font, 12)
    c.setFillColorRGB(0.13, 0.37, 0.65)
    c.drawString(50, y, "Pipeline przetwarzania danych")
    c.setFillColorRGB(0, 0, 0)
    c.line(50, y - 4, width - 50, y - 4)
    y -= 25

    pipeline_steps = [
        ("1. Import danych",
         "Wczytanie danych z pliku CSV, Excel lub bazy SQLite. "
         "Automatyczne wykrywanie separatora i kodowania."),
        ("2. Walidacja",
         "Sprawdzenie kompletnosci danych, wykrycie brakow i bledow typow."),
        ("3. Czyszczenie",
         "Usuniecie nadmiarowych spacji, ujednolicenie formatow liczbowych."),
        ("4. Filtrowanie",
         "Zastosowanie warunkow filtrowania z operatorami numerycznymi i tekstowymi. Logika AND/OR."),
        ("5. Analiza SQL",
         "Wykonanie zapytan JOIN miedzy tabelami relacyjnymi bazy danych pacjentow."),
        ("6. Statystyki",
         "Obliczenie metryk: count, mean, median, min, max, std z grupowaniem po kolumnach."),
        ("7. Wizualizacja",
         "Generowanie wykresow z automatycznym doborem typu na podstawie typow danych."),
        ("8. Raport",
         "Eksport wynikow do pliku PDF z opisem metodologii i wnioskami."),
    ]

    for title, desc in pipeline_steps:
        if y < 100:
            c.showPage()
            page_num += 1
            _draw_page_header(c, width, height, font, page_num)
            y = height - 60
        c.setFont(font, 11)
        c.setFillColorRGB(0.13, 0.37, 0.65)
        c.drawString(50, y, title)
        c.setFillColorRGB(0, 0, 0)
        y -= 15
        y = _wrap_text(c, desc, 65, y, font, 10, width - 115, 13)
        y -= 8

    if source == "sql" and sql_query:
        if y < 150:
            c.showPage()
            page_num += 1
            _draw_page_header(c, width, height, font, page_num)
            y = height - 60
        y -= 10
        c.setFont(font, 12)
        c.setFillColorRGB(0.13, 0.37, 0.65)
        c.drawString(50, y, "Zapytanie SQL")
        c.setFillColorRGB(0, 0, 0)
        c.line(50, y - 4, width - 50, y - 4)
        y -= 20
        c.setFont(font, 9)
        for line in sql_query.splitlines():
            if y < 60:
                c.showPage()
                page_num += 1
                _draw_page_header(c, width, height, font, page_num)
                y = height - 60
            c.drawString(60, y, line)
            y -= 13

    # STRONA: STATYSTYKI
    c.showPage()
    page_num += 1
    _draw_page_header(c, width, height, font, page_num)

    y = height - 60
    c.setFont(font, 16)
    c.setFillColorRGB(0.13, 0.37, 0.65)
    c.drawString(50, y, "Wyniki analizy statystycznej")
    c.setFillColorRGB(0, 0, 0)
    c.line(50, y - 4, width - 50, y - 4)
    y -= 35

    if stats_text:
        c.setFont(font, 9)
        for line in stats_text.splitlines():
            if y < 60:
                c.showPage()
                page_num += 1
                _draw_page_header(c, width, height, font, page_num)
                y = height - 60
            c.drawString(50, y, line)
            y -= 13
    else:
        c.setFont(font, 11)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawString(50, y, "Brak statystyk — uruchom analize przed eksportem.")
        c.setFillColorRGB(0, 0, 0)
        y -= 30

    data_src = df_filtered if source == "csv" else sql_df
    if data_src is not None and not data_src.empty:
        num_cols = data_src.select_dtypes(include="number").columns.tolist()[:6]
        if num_cols:
            if y < 200:
                c.showPage()
                page_num += 1
                _draw_page_header(c, width, height, font, page_num)
                y = height - 60
            y -= 10
            c.setFont(font, 12)
            c.setFillColorRGB(0.13, 0.37, 0.65)
            c.drawString(50, y, f"Statystyki opisowe (pierwsze {len(num_cols)} kolumn numerycznych)")
            c.setFillColorRGB(0, 0, 0)
            c.line(50, y - 4, width - 50, y - 4)
            y -= 25

            desc = data_src[num_cols].describe().round(2)
            col_w = (width - 100) / (len(num_cols) + 1)

            c.setFont(font, 8)
            c.setFillColorRGB(0.13, 0.37, 0.65)
            c.drawString(55, y, "Metryka")
            for i, col in enumerate(num_cols):
                label = col[:10] + ".." if len(col) > 10 else col
                c.drawString(55 + (i + 1) * col_w, y, label)
            c.setFillColorRGB(0, 0, 0)
            y -= 5
            c.line(50, y, width - 50, y)
            y -= 14

            for idx, row_name in enumerate(desc.index):
                c.setFont(font, 8)
                if idx % 2 == 0:
                    c.setFillColorRGB(0.95, 0.97, 1.0)
                    c.rect(50, y - 4, width - 100, 16, fill=1, stroke=0)
                    c.setFillColorRGB(0, 0, 0)
                c.drawString(55, y, str(row_name))
                for i, col in enumerate(num_cols):
                    val = desc.loc[row_name, col]
                    c.drawString(55 + (i + 1) * col_w, y, f"{val:.2f}")
                y -= 16
            c.line(50, y, width - 50, y)

    # STRONA: WYKRES
    if plot_buf is not None:
        c.showPage()
        page_num += 1
        _draw_page_header(c, width, height, font, page_num)
        y = height - 60
        c.setFont(font, 16)
        c.setFillColorRGB(0.13, 0.37, 0.65)
        c.drawString(50, y, "Wizualizacja danych")
        c.setFillColorRGB(0, 0, 0)
        c.line(50, y - 4, width - 50, y - 4)
        plot_buf.seek(0)
        img = ImageReader(plot_buf)
        c.drawImage(img, 50, 100, width - 100, height - 220, preserveAspectRatio=True)

    # STRONA: WNIOSKI
    c.showPage()
    page_num += 1
    _draw_page_header(c, width, height, font, page_num)

    y = height - 60
    c.setFont(font, 16)
    c.setFillColorRGB(0.13, 0.37, 0.65)
    c.drawString(50, y, "Wnioski")
    c.setFillColorRGB(0, 0, 0)
    c.line(50, y - 4, width - 50, y - 4)
    y -= 35

    conclusions = _auto_conclusions(df, df_filtered, filters)
    for conclusion in conclusions:
        if y < 80:
            c.showPage()
            page_num += 1
            _draw_page_header(c, width, height, font, page_num)
            y = height - 60
        y = _wrap_text(c, f"• {conclusion}", 50, y, font, 11, width - 100, 18)
        y -= 6

    c.setFont(font, 9)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width / 2, 50,
        f"Raport wygenerowany: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

    c.save()
