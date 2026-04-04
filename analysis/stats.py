# =============================================================================
# IMPORT BIBLIOTEK
# =============================================================================
import pandas as pd


# =============================================================================
# FUNKCJA GŁÓWNA — OBLICZANIE STATYSTYK DLA WYBRANYCH KOLUMN
# Obsługuje zarówno dane przefiltrowane, jak i całkowite.
# Umożliwia grupowanie wyników po wybranej kolumnie.
# =============================================================================
def calculate_selected_stats(df_src, selected_cols, want, group_col=None, is_filtered=True):

    # --- WALIDACJA DANYCH WEJŚCIOWYCH ---
    if df_src is None or df_src.empty:
        raise ValueError("Brak danych do analizy.")

    if not selected_cols:
        raise ValueError("Nie wybrano kolumn do analizy.")

    # --- USTALENIE TRYBU GRUPOWANIA ---
    # Grupowanie jest aktywne tylko jeśli użytkownik wybrał kolumnę inną niż "(brak)"
    # i kolumna ta faktycznie istnieje w zbiorze danych.
    use_groupby = group_col is not None and group_col != "(brak)" and group_col in df_src.columns

    # --- BUDOWANIE NAGŁÓWKA RAPORTU ---
    lines = []
    lines.append(f"Źródło: {'PRZEFILTROWANE' if is_filtered else 'CAŁE'}")
    if use_groupby:
        lines.append(f"Grupowanie po: {group_col}")
    lines.append(f"Kolumny: {', '.join(selected_cols)}")
    lines.append("Metryki: " + ", ".join([k for k, v in want.items() if v]))
    lines.append("—" * 60)

    # --- POMOCNICZA FUNKCJA: AUTO-DETEKCJA KOLUMNY NUMERYCZNEJ ---
    # Uznaje kolumnę za numeryczną jeśli pandas oznacza ją jako liczbową
    # lub jeśli ponad 50% wartości da się skonwertować do liczb.
    def is_numeric_col(s):
        if pd.api.types.is_numeric_dtype(s):
            return True
        return pd.to_numeric(s, errors="coerce").notna().mean() > 0.5

    # --- POMOCNICZA FUNKCJA: OBLICZANIE STATYSTYK DLA PODZBIORU DANYCH ---
    # Generuje blok tekstowy z metrykami dla pojedynczej grupy (lub całości).
    # Dla kolumn numerycznych: count/mean/median/min/max/std.
    # Dla kolumn tekstowych: liczba unikalnych wartości + najczęstsze wystąpienia.
    def summary_for_group(sub_df, group_name=None):
        header = f"[Grupa: {group_name}]" if group_name is not None else "[Całość]"
        out = [header]

        for col in selected_cols:
            s = sub_df[col]
            out.append(f"\nKolumna: {col}")

            # Informacja o brakach danych
            n_missing = s.isna().sum()
            n_total = s.size
            if n_missing > 0:
                out.append(f"  braki danych: {n_missing} z {n_total} ({n_missing / n_total * 100:.1f}%)")

            if want.get("count"):
                out.append(f"  count: {s.count()}")

            # Gałąź numeryczna
            if is_numeric_col(s):
                s_clean = pd.to_numeric(s, errors="coerce").dropna()
                if want.get("mean"):
                    out.append(f"  mean:   {s_clean.mean():.6g}")
                if want.get("median"):
                    out.append(f"  median: {s_clean.median():.6g}")
                if want.get("min"):
                    out.append(f"  min:    {s_clean.min():.6g}")
                if want.get("max"):
                    out.append(f"  max:    {s_clean.max():.6g}")
                if want.get("std"):
                    out.append(f"  std:    {s_clean.std():.6g}")

            # Gałąź tekstowa / kategoryczna
            else:
                s_clean = s.dropna().astype(str)
                n_unique = s_clean.nunique()
                out.append(f"  unikalne wartości: {n_unique}")

                vc = s_clean.value_counts()
                # Do 20 unikalnych wartości — pokazuje top 5 z procentami
                if n_unique <= 20:
                    out.append(f"  najczęstsze:")
                    for val, cnt in vc.head(5).items():
                        pct = cnt / s_clean.size * 100
                        out.append(f"    {val}: {cnt} ({pct:.1f}%)")
                # Powyżej 20 — pokazuje tylko najczęstszą wartość
                else:
                    out.append(f"  najczęstsza: {vc.index[0]} ({vc.iloc[0]}x)")

        return "\n".join(out)

    # --- GŁÓWNA LOGIKA: GRUPOWANIE LUB ANALIZA CAŁOŚCI ---
    if use_groupby:
        # Iteracja po każdej grupie — dropna=False uwzględnia też wartości NaN jako grupę
        for gval, sub in df_src.groupby(group_col, dropna=False, sort=False):
            lines.append(summary_for_group(sub, group_name=str(gval)))
    else:
        lines.append(summary_for_group(df_src))

    return "\n".join(lines)


# =============================================================================
# FUNKCJA POMOCNICZA — SZYBKIE PORÓWNANIE LICZBY REKORDÓW PRZED I PO FILTRZE
# Zwraca uproszczony raport tekstowy z procentowym ubytkiem danych.
# =============================================================================
def compare_filter_impact(df_original, df_filtered):

    # --- WALIDACJA DANYCH WEJŚCIOWYCH ---
    if df_original is None or df_filtered is None:
        raise ValueError("Brak danych do porównania")

    lines = []
    lines.append("=== ANALIZA WPŁYWU FILTRÓW ===")

    total = len(df_original)
    filtered = len(df_filtered)

    lines.append(f"Liczba rekordów przed filtrem: {total}")
    lines.append(f"Liczba rekordów po filtrze: {filtered}")

    if total > 0:
        percent = (filtered / total) * 100
        lines.append(f"Pozostało: {percent:.2f}% danych")

    lines.append("—" * 40)

    return "\n".join(lines)


# =============================================================================
# FUNKCJA ZAAWANSOWANA — ANALIZA WPŁYWU FILTRÓW NA STATYSTYKI KOLUMN NUMERYCZNYCH
# Porównuje średnie i mediany każdej kolumny numerycznej przed i po zastosowaniu filtrów.
# Wyświetla bezwzględną i procentową zmianę wartości.
# =============================================================================
def analyze_filter_impact(df_original, df_filtered, numeric_cols=None):

    # --- WALIDACJA DANYCH WEJŚCIOWYCH ---
    if df_original is None or df_filtered is None:
        raise ValueError("Brak danych do porównania.")

    # --- AUTO-DETEKCJA KOLUMN NUMERYCZNYCH ---
    # Jeśli lista kolumn nie została podana, wybierane są wszystkie kolumny numeryczne z oryginału.
    if numeric_cols is None:
        numeric_cols = df_original.select_dtypes(include="number").columns.tolist()

    if not numeric_cols:
        raise ValueError("Brak kolumn numerycznych do analizy.")

    lines = []
    lines.append("=== ANALIZA WPŁYWU PARAMETRÓW FILTROWANIA ===\n")

    # --- PODSUMOWANIE LICZBY REKORDÓW ---
    total = len(df_original)
    filtered = len(df_filtered)
    pct = filtered / total * 100 if total > 0 else 0

    lines.append(f"Rekordów przed filtrem: {total:,}")
    lines.append(f"Rekordów po filtrze:    {filtered:,}")
    lines.append(f"Pozostało:              {pct:.1f}% danych")
    lines.append("—" * 55)

    # --- TABELA PORÓWNAWCZA ŚREDNICH ---
    lines.append(f"\n{'Kolumna':<20} {'Przed':>10} {'Po':>10} {'Zmiana':>10} {'%':>8}")
    lines.append("—" * 55)

    for col in numeric_cols:
        try:
            s_before = pd.to_numeric(df_original[col], errors="coerce").dropna()
            s_after  = pd.to_numeric(df_filtered[col],  errors="coerce").dropna()

            if s_before.empty or s_after.empty:
                continue

            mean_before = s_before.mean()
            mean_after  = s_after.mean()
            delta       = mean_after - mean_before
            delta_pct   = (delta / mean_before * 100) if mean_before != 0 else 0
            sign        = "+" if delta >= 0 else ""

            lines.append(
                f"{col:<20} {mean_before:>10.3g} {mean_after:>10.3g} "
                f"{sign}{delta:>9.3g} {sign}{delta_pct:>6.1f}%"
            )
        except Exception:
            continue

    # --- TABELA PORÓWNAWCZA MEDIAN ---
    lines.append("—" * 55)
    lines.append("\nMediany:")
    lines.append(f"\n{'Kolumna':<20} {'Przed':>10} {'Po':>10} {'Zmiana':>10}")
    lines.append("—" * 45)

    for col in numeric_cols:
        try:
            s_before = pd.to_numeric(df_original[col], errors="coerce").dropna()
            s_after  = pd.to_numeric(df_filtered[col],  errors="coerce").dropna()

            if s_before.empty or s_after.empty:
                continue

            med_before = s_before.median()
            med_after  = s_after.median()
            delta      = med_after - med_before
            sign       = "+" if delta >= 0 else ""

            lines.append(
                f"{col:<20} {med_before:>10.3g} {med_after:>10.3g} {sign}{delta:>9.3g}"
            )
        except Exception:
            continue

    return "\n".join(lines)
