import pandas as pd
import matplotlib.pyplot as plt


def create_plot(df, col_x, col_y=None, chart_type="Auto"):
    if df is None or df.empty:
        raise ValueError("Brak danych do wizualizacji.")

    if not col_x:
        raise ValueError("Nie wybrano kolumny X.")

    x = pd.to_numeric(df[col_x], errors="coerce")

    y = None
    if col_y and col_y != "(brak)":
        y = pd.to_numeric(df[col_y], errors="coerce")

    if chart_type == "Auto":
        if y is not None:
            chart_type = "Wykres rozrzutu"
        else:
            chart_type = "Histogram"

    fig, ax = plt.subplots(figsize=(8, 5))
    plt.style.use("seaborn-v0_8")

    if chart_type == "Histogram":
        ax.hist(x.dropna(), bins=20, color="skyblue", edgecolor="black", alpha=0.7)
        ax.set_title(f"Histogram kolumny: {col_x}")
        ax.set_xlabel(col_x)
        ax.set_ylabel("Liczba wystąpień")

    elif chart_type == "Wykres rozrzutu":
        if y is None:
            raise ValueError("Dla wykresu rozrzutu wybierz kolumnę Y.")
        ax.scatter(x, y, alpha=0.7, color="teal", edgecolors="black")
        ax.set_title(f"Wykres rozrzutu: {col_x} vs {col_y}")
        ax.set_xlabel(col_x)
        ax.set_ylabel(col_y)

    else:
        raise ValueError(f"Nieznany typ wykresu: {chart_type}")

    ax.grid(True, linestyle="--", alpha=0.6)

    return fig, chart_type