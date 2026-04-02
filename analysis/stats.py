import pandas as pd


def calculate_selected_stats(df_src, selected_cols, want, group_col=None, is_filtered=True):
    if df_src is None or df_src.empty:
        raise ValueError("Brak danych do analizy.")

    if not selected_cols:
        raise ValueError("Nie wybrano kolumn do analizy.")

    use_groupby = group_col is not None and group_col != "(brak)" and group_col in df_src.columns

    lines = []
    lines.append(f"Źródło: {'PRZEFILTROWANE' if is_filtered else 'CAŁE'}")
    if use_groupby:
        lines.append(f"Grupowanie po: {group_col}")
    lines.append(f"Kolumny: {', '.join(selected_cols)}")
    lines.append("Metryki: " + ", ".join([k for k, v in want.items() if v]))
    lines.append("—" * 60)

    def is_numeric_col(s):
        if pd.api.types.is_numeric_dtype(s):
            return True
        return pd.to_numeric(s, errors="coerce").notna().mean() > 0.5

    def summary_for_group(sub_df, group_name=None):
        header = f"[Grupa: {group_name}]" if group_name is not None else "[Całość]"
        out = [header]

        for col in selected_cols:
            s = sub_df[col]
            out.append(f"\nKolumna: {col}")

            n_missing = s.isna().sum()
            n_total = s.size
            if n_missing > 0:
                out.append(f"  braki danych: {n_missing} z {n_total} ({n_missing / n_total * 100:.1f}%)")

            if want.get("count"):
                out.append(f"  count: {s.count()}")

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
            else:
                s_clean = s.dropna().astype(str)
                n_unique = s_clean.nunique()
                out.append(f"  unikalne wartości: {n_unique}")

                vc = s_clean.value_counts()
                if n_unique <= 20:
                    out.append(f"  najczęstsze:")
                    for val, cnt in vc.head(5).items():
                        pct = cnt / s_clean.size * 100
                        out.append(f"    {val}: {cnt} ({pct:.1f}%)")
                else:
                    out.append(f"  najczęstsza: {vc.index[0]} ({vc.iloc[0]}x)")

        return "\n".join(out)

    if use_groupby:
        for gval, sub in df_src.groupby(group_col, dropna=False, sort=False):
            lines.append(summary_for_group(sub, group_name=str(gval)))
    else:
        lines.append(summary_for_group(df_src))

    return "\n".join(lines)


def compare_filter_impact(df_original, df_filtered):
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