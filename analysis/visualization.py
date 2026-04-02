import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

SCATTER_MAX_POINTS = 5000


def _detect_type(series):
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    converted = pd.to_datetime(series, errors="coerce", format="mixed")
    if converted.notna().mean() > 0.5:
        return "datetime"
    return "text"


def create_plot(df, col_x, col_y=None, chart_type="Auto", y_min=None, y_max=None):
    if df is None or df.empty:
        raise ValueError("Brak danych do wizualizacji.")
    if not col_x:
        raise ValueError("Nie wybrano kolumny X.")

    has_y = col_y and col_y != "(brak)"

    type_x = _detect_type(df[col_x])
    type_y = _detect_type(df[col_y]) if has_y else None

    if chart_type == "Auto":
        if has_y:
            if type_x == "text" and type_y == "numeric":
                chart_type = "Box plot"
            elif type_x == "numeric" and type_y == "numeric":
                chart_type = "Wykres rozrzutu"
            elif type_x == "datetime" and type_y == "numeric":
                chart_type = "Wykres liniowy"
            else:
                chart_type = "Histogram"
        else:
            if type_x == "numeric":
                chart_type = "Histogram"
            else:
                chart_type = "Bar chart"

    plt.style.use("seaborn-v0_8")
    fig, ax = plt.subplots(figsize=(9, 5))

    # HISTOGRAM
    if chart_type == "Histogram":
        x = pd.to_numeric(df[col_x], errors="coerce").dropna()
        if x.empty:
            raise ValueError(f"Kolumna '{col_x}' nie zawiera danych liczbowych.")
        n_bins = min(50, max(10, len(x) // 50))
        ax.hist(x, bins=n_bins, color="skyblue", edgecolor="black", alpha=0.7)
        ax.set_title(f"Histogram: {col_x}")
        ax.set_xlabel(col_x)
        ax.set_ylabel("Liczba wystąpień")

    # BAR CHART
    elif chart_type == "Bar chart":
        counts = df[col_x].value_counts().head(20)
        if counts.empty:
            raise ValueError(f"Kolumna '{col_x}' jest pusta.")
        ax.bar(counts.index.astype(str), counts.values,
               color="steelblue", edgecolor="black", alpha=0.8)
        ax.set_title(f"Liczba wystąpień: {col_x} (top 20)")
        ax.set_xlabel(col_x)
        ax.set_ylabel("Liczba")
        ax.tick_params(axis="x", rotation=45)

    # BOX PLOT ze strip plotem
    elif chart_type == "Box plot":
        if not has_y:
            raise ValueError("Box plot wymaga kolumny Y.")

        y = pd.to_numeric(df[col_y], errors="coerce")
        combined = pd.DataFrame({"x": df[col_x], "y": y}).dropna()
        if combined.empty:
            raise ValueError("Brak danych do narysowania box plotu.")

        top_cats = combined["x"].value_counts().head(15).index
        combined = combined[combined["x"].isin(top_cats)]

        multi = [cat for cat in top_cats if len(combined[combined["x"] == cat]) >= 3]
        single = [cat for cat in top_cats if len(combined[combined["x"] == cat]) < 3]
        all_cats = list(multi) + list(single)

        positions = list(range(len(all_cats)))
        cat_to_pos = {cat: i for i, cat in enumerate(all_cats)}

        if multi:
            groups = [combined["y"][combined["x"] == cat].values for cat in multi]
            multi_pos = [cat_to_pos[cat] for cat in multi]
            ax.boxplot(
                groups,
                positions=multi_pos,
                widths=0.4,
                patch_artist=True,
                boxprops=dict(facecolor="lightblue", color="steelblue", alpha=0.4),
                medianprops=dict(color="tomato", linewidth=2),
                whiskerprops=dict(color="steelblue"),
                capprops=dict(color="steelblue"),
                flierprops=dict(marker="", markersize=0)
            )

        rng = np.random.default_rng(42)
        for cat in all_cats:
            vals = combined["y"][combined["x"] == cat].values
            pos = cat_to_pos[cat]
            n = len(vals)
            jitter = rng.uniform(-0.15, 0.15, size=n) if n > 1 else [0]
            color = "steelblue" if cat in multi else "tomato"
            ax.scatter(
                [pos + j for j in jitter],
                vals,
                alpha=0.7,
                color=color,
                edgecolors="white",
                linewidths=0.5,
                s=30,
                zorder=3
            )

        ax.set_xticks(positions)
        ax.set_xticklabels(all_cats, rotation=45, ha="right", fontsize=9)
        ax.set_title(f"Rozkład {col_y} według {col_x}")
        ax.set_xlabel(col_x)
        ax.set_ylabel(col_y)

    # SCATTER PLOT
    elif chart_type == "Wykres rozrzutu":
        if not has_y:
            raise ValueError("Wykres rozrzutu wymaga kolumny Y.")
        x = pd.to_numeric(df[col_x], errors="coerce")
        y = pd.to_numeric(df[col_y], errors="coerce")
        combined = pd.DataFrame({"x": x, "y": y}).dropna()
        if combined.empty:
            raise ValueError("Brak danych liczbowych do wykresu rozrzutu.")

        sampled = False
        if len(combined) > SCATTER_MAX_POINTS:
            combined = combined.sample(n=SCATTER_MAX_POINTS, random_state=42)
            sampled = True

        ax.scatter(combined["x"], combined["y"],
                   alpha=0.5, color="teal", edgecolors="none", s=20)
        title = f"Wykres rozrzutu: {col_x} vs {col_y}"
        if sampled:
            title += f" (próbka {SCATTER_MAX_POINTS} pkt)"
        ax.set_title(title)
        ax.set_xlabel(col_x)
        ax.set_ylabel(col_y)

    # WYKRES LINIOWY
    elif chart_type == "Wykres liniowy":
        if not has_y:
            raise ValueError("Wykres liniowy wymaga kolumny Y.")
        x = pd.to_datetime(df[col_x], errors="coerce")
        y = pd.to_numeric(df[col_y], errors="coerce")
        combined = pd.DataFrame({"x": x, "y": y}).dropna().sort_values("x")
        if combined.empty:
            raise ValueError("Brak danych do wykresu liniowego.")

        ax.plot(combined["x"], combined["y"],
                color="steelblue", linewidth=1.5, alpha=0.8)
        ax.set_title(f"Wykres liniowy: {col_y} w czasie ({col_x})")
        ax.set_xlabel(col_x)
        ax.set_ylabel(col_y)
        fig.autofmt_xdate()

    else:
        raise ValueError(f"Nieznany typ wykresu: {chart_type}")

    ax.grid(True, linestyle="--", alpha=0.5)

    if y_min is not None and y_max is not None:
        ax.set_ylim(y_min, y_max)

        # Policz punkty poza zakresem
        try:
            all_y = combined["y"] if "combined" in dir() else x
            out_below = int((all_y < y_min).sum())
            out_above = int((all_y > y_max).sum())
            out_total = out_below + out_above
        except Exception:
            out_total = out_below = out_above = 0

        info = f"Zakres osi Y: {y_min} – {y_max}"
        if out_total > 0:
            info += f"\n{out_total} pkt poza zakresem"
            if out_below > 0:
                info += f"  (poniżej: {out_below})"
            if out_above > 0:
                info += f"  (powyżej: {out_above})"

        ax.annotate(
            info,
            xy=(0.01, 0.99), xycoords="axes fraction",
            va="top", ha="left", fontsize=8,
            color="tomato" if out_total > 0 else "gray",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="tomato" if out_total > 0 else "gray",
                      alpha=0.8)
        )

    fig.tight_layout()
    return fig, chart_type