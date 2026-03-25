import pandas as pd


def calculate_selected_stats(df_src, selected_cols, want, group_col=None):
    if df_src is None or df_src.empty:
        raise ValueError("Brak danych do analizy.")

    if not selected_cols:
        raise ValueError("Nie wybrano kolumn do analizy.")

    use_groupby = group_col is not None and group_col != "(brak)" and group_col in df_src.columns

    lines = []
    lines.append(f"Źródło: {'PRZEFILTROWANE' if df_src is not None else 'BRAK'}")
    if use_groupby:
        lines.append(f"Grupowanie po: {group_col}")
    lines.append(f"Kolumny: {', '.join(selected_cols)}")
    lines.append("Metryki: " + ", ".join([k for k, v in want.items() if v]))
    lines.append("—" * 60)

    def numeric_series(s):
        return pd.to_numeric(s, errors="coerce")

    def summary_for_group(sub_df, group_name=None):
        header = f"[Grupa: {group_name}]" if group_name is not None else "[Całość]"
        out = [header]

        for col in selected_cols:
            s = sub_df[col]
            s_num = numeric_series(s)
            out.append(f"\nKolumna: {col}")

            if want.get("count"):
                out.append(f"  count: {s.size}")

            s_clean = s_num.dropna()
            if len(s_clean) == 0:
                if any([want.get("mean"), want.get("median"), want.get("min"), want.get("max"), want.get("std")]):
                    out.append("  (brak danych liczbowych do metryk numerycznych)")
            else:
                if want.get("mean"):
                    out.append(f"  mean: {s_clean.mean():.6g}")
                if want.get("median"):
                    out.append(f"  median: {s_clean.median():.6g}")
                if want.get("min"):
                    out.append(f"  min: {s_clean.min():.6g}")
                if want.get("max"):
                    out.append(f"  max: {s_clean.max():.6g}")
                if want.get("std"):
                    out.append(f"  std: {s_clean.std():.6g}")

        return "\n".join(out)

    if use_groupby:
        for gval, sub in df_src.groupby(group_col, dropna=False):
            lines.append(summary_for_group(sub, group_name=str(gval)))
    else:
        lines.append(summary_for_group(df_src))

    return "\n".join(lines)