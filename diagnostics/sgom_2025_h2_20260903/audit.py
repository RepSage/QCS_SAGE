"""Read-only SGOM temperature-disagreement audit.

Dependencies: Python, pandas, numpy, openpyxl (versions recorded in output).
Inputs are never modified. Archive location is supplied on the command line.
"""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import sys

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sourceCode"))


def profile(frame):
    numeric = frame.select_dtypes(include="number")
    return {
        "rows": len(frame),
        "columns": len(frame.columns),
        "dtypes": {str(k): str(v) for k, v in frame.dtypes.items()},
        "missing": {str(k): int(v) for k, v in frame.isna().sum().items()},
        "duplicate_rows": int(frame.duplicated().sum()),
        "numeric_ranges": {
            str(c): [numeric[c].min(), numeric[c].max()] for c in numeric
        },
    }


def file_info(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def analyse(args):
    import matplotlib
    matplotlib.use("Agg")
    import QCS_DataHandler as data
    import QCS_DataView as view
    import QCS_Theme as theme
    import QCS_Tests as tests
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    product_path = args.archive / "HOBO/qualified/2026S1/SGOM/SGOM_2026S1_HOBO_QLF.csv"
    product = pd.read_csv(product_path, parse_dates=["Datetime"])
    paired = product.copy()
    details = {"reader_version": data.QCS_VERSION, "reader_messages": {}, "joins": [],
               "runtime": {"python": platform.python_version(), "pandas": pd.__version__,
                           "numpy": np.__version__, "openpyxl": openpyxl.__version__}}
    for number, filename in ((1, "HOBO1_SGOM_A2_110925_ERRO.xlsx"),
                             (2, "HOBO2_SGOM_A2_110925.xlsx")):
        path = args.archive / "HOBO/raw/2026S1/SGOM/planilha" / filename
        raw = pd.read_excel(path, header=1)
        messages = []
        stamps = data._hobo_datetimes(raw.iloc[:, 1], messages.append)
        temperatures, scale_message = data._hobo_fix_temp_scale(raw.iloc[:, 2], filename)
        if scale_message:
            messages.append(scale_message)
        assert stamps.notna().all(), "Missing raw timestamps must be reviewed."
        assert not stamps.duplicated().any(), "Ambiguous timestamps must be reviewed."
        source = pd.DataFrame({
            f"HOBO{number} datetime": stamps,
            f"HOBO{number} temperature (degC)": temperatures,
            f"HOBO{number} Excel row": raw.index + 3,
        }).sort_values(f"HOBO{number} datetime")
        details["reader_messages"][filename] = messages
        details.setdefault("raw_normalized", {})[filename] = {
            **profile(source),
            "datetime_range": [stamps.min(), stamps.max()],
            "duplicate_timestamps": int(stamps.duplicated().sum()),
        }
        before = len(paired)
        paired = pd.merge_asof(paired.sort_values("Datetime"), source,
                               left_on="Datetime", right_on=f"HOBO{number} datetime",
                               direction="nearest", tolerance=pd.Timedelta(hours=1))
        details["joins"].append({
            "source": filename, "left_rows_before": before, "left_rows_after": len(paired),
            "right_rows": len(source),
            "unmatched": int(paired[f"HOBO{number} datetime"].isna().sum()),
            "time_offset_seconds_range": [
                (paired.Datetime - paired[f"HOBO{number} datetime"]).dt.total_seconds().min(),
                (paired.Datetime - paired[f"HOBO{number} datetime"]).dt.total_seconds().max()],
        })
        assert len(paired) == before and paired[f"HOBO{number} datetime"].notna().all()
    t1, t2 = paired["HOBO1 temperature (degC)"], paired["HOBO2 temperature (degC)"]
    paired["Raw pair mean (degC)"] = (t1 + t2) / 2
    paired["Raw pair spread (degC)"] = (t1 - t2).abs()
    mean_matches = np.isclose(paired["Temperature (degC)"], paired["Raw pair mean (degC)"], atol=0.00006, rtol=0)
    spread_matches = np.isclose(paired["Temperature spread (degC)"], paired["Raw pair spread (degC)"], atol=0.00006, rtol=0)
    both = mean_matches & spread_matches
    only2 = np.isclose(paired["Temperature (degC)"], t2, atol=0.00006, rtol=0) & paired["Temperature spread (degC)"].eq(0)
    only1 = np.isclose(paired["Temperature (degC)"], t1, atol=0.00006, rtol=0) & paired["Temperature spread (degC)"].eq(0)
    paired["Reconstructed source"] = np.select([both, only2, only1], ["Both", "HOBO2 only", "HOBO1 only"], default="Unexplained")
    paired["Archive CSV line"] = paired.index + 2
    details["reconstruction_counts"] = paired["Reconstructed source"].value_counts().to_dict()
    details["maximum"] = paired.loc[paired["Temperature spread (degC)"].idxmax()].to_dict()
    h2 = paired.loc[paired.Datetime.ge("2025-07-01") & paired.Datetime.lt("2026-01-01")].copy()
    details["calendar_filter"] = {"before": len(paired), "after": len(h2),
                                  "removed": len(paired) - len(h2), "criterion": "2025-07-01 <= Datetime < 2026-01-01"}
    for label, subset in (("full_deployment", paired), ("calendar_2025_h2", h2)):
        suspect = subset.loc[subset.Flag_T.eq(3)]
        details[label] = {
            "rows": len(subset), "suspect_rows": len(suspect),
            "suspect_fraction": len(suspect) / len(subset),
            "suspect_datetime_range": [suspect.Datetime.min(), suspect.Datetime.max()],
            "spread_over_5degC": int(subset["Temperature spread (degC)"].gt(5).sum()),
            "reconstructed_sources": subset["Reconstructed source"].value_counts().to_dict(),
        }
    details["paired_HOBO1_range_by_source"] = paired.groupby("Reconstructed source")["HOBO1 temperature (degC)"].agg(["count", "min", "max"]).to_dict("index")
    details["suspect_months"] = h2.assign(Month=h2.Datetime.dt.to_period("M").astype(str)).groupby("Month").agg(
        rows=("Flag_T", "size"), suspect=("Flag_T", lambda x: int(x.eq(3).sum())),
        max_spread=("Temperature spread (degC)", "max")).to_dict("index")

    # Exercise the current referee with the same independent-reference recipe
    # used by the corpus batch. Contribution masks reconstructed above stand in
    # for the archived per-replicate Flag_T values, which were not preserved.
    t0 = product.Datetime.min() - pd.Timedelta(days=1)
    t1 = product.Datetime.min() + pd.Timedelta(days=400)
    reference_columns = []
    reference_products = []
    qualified_root = args.archive / "HOBO" / "qualified"
    for candidate in sorted(qualified_root.glob("*/**/*_HOBO*_QLF.csv")):
        if candidate.name.startswith("SGOM_"):
            continue
        try:
            candidate_data = pd.read_csv(
                candidate,
                usecols=lambda c: c in ("Datetime", "Temperature (degC)", "Flag_T"),
            )
        except Exception as error:
            reference_products.append({"path": str(candidate), "read_error": str(error)})
            continue
        original_rows = len(candidate_data)
        candidate_data["Datetime"] = pd.to_datetime(candidate_data["Datetime"], errors="coerce")
        missing_datetime = int(candidate_data.Datetime.isna().sum())
        candidate_data = candidate_data.loc[candidate_data.Datetime.between(t0, t1)].copy()
        rows_in_window = len(candidate_data)
        if "Flag_T" in candidate_data:
            candidate_data = candidate_data.loc[pd.to_numeric(candidate_data.Flag_T, errors="coerce").le(2)].copy()
        acceptable_rows = len(candidate_data)
        included = acceptable_rows >= 200
        reference_products.append({
            "path": str(candidate), "original_rows": original_rows,
            "missing_datetime": missing_datetime, "rows_in_window": rows_in_window,
            "acceptable_rows": acceptable_rows, "included": included,
        })
        if included:
            reference_columns.append(candidate_data.set_index("Datetime")["Temperature (degC)"].resample("D").mean())
    reference_frame = pd.concat(reference_columns, axis=1) if reference_columns else pd.DataFrame()
    reference = reference_frame.mean(axis=1) if not reference_frame.empty else None
    replica2 = pd.DataFrame({"Datetime": paired.Datetime,
                             "Temperature (degC)": paired["HOBO2 temperature (degC)"],
                             "Flag_T": 1})
    replica1 = pd.DataFrame({"Datetime": paired.Datetime,
                             "Temperature (degC)": paired["HOBO1 temperature (degC)"],
                             "Flag_T": np.where(paired["Reconstructed source"].eq("Both"), 1, 3)})
    referee = tests.replicate_referee([replica2, replica1], reference=reference)
    diagnostic_replica2 = replica2.drop(columns="Flag_T")
    diagnostic_replica1 = replica1.drop(columns="Flag_T")
    referee_all_finite = tests.replicate_referee(
        [diagnostic_replica2, diagnostic_replica1], reference=reference
    )
    cadence = tests._referee_cadence(pd.DatetimeIndex(paired.Datetime))
    reference_changes = reference.sort_index().resample(cadence).mean().diff().dropna()

    def comparison_count(frame):
        values = pd.Series(pd.to_numeric(frame["Temperature (degC)"], errors="coerce").to_numpy(),
                           index=pd.DatetimeIndex(frame.Datetime)).sort_index()
        if "Flag_T" in frame:
            values = values.where(pd.to_numeric(frame.Flag_T, errors="coerce").to_numpy() <= 2)
        changes = values.resample(cadence).mean().diff().dropna()
        return len(reference_changes.index.intersection(changes.index))
    details["retrospective_referee"] = {
        "reference_window": [t0, t1],
        "products_inspected": len(reference_products),
        "products_included": int(sum(item.get("included", False) for item in reference_products)),
        "reference_daily_rows": len(reference_frame),
        "reference_daily_missing": int(reference.isna().sum()) if reference is not None else None,
        "reference_daily_range_degC": [reference.min(), reference.max()] if reference is not None else None,
        "products": reference_products,
        "replicate_order": ["HOBO2_SGOM_A2_110925.xlsx", "HOBO1_SGOM_A2_110925_ERRO.xlsx"],
        "cadence": cadence,
        "comparison_change_counts_output_eligible": [comparison_count(replica2), comparison_count(replica1)],
        "comparison_change_counts_all_finite": [comparison_count(diagnostic_replica2), comparison_count(diagnostic_replica1)],
        "result": referee,
        "diagnostic_result_all_finite": referee_all_finite,
        "limitation": "Archived per-replicate Flag_T was not retained; its contribution to the archived combined product was reconstructed.",
    }

    spread_rows = []
    for candidate in sorted(qualified_root.glob("*/**/*_HOBO*_QLF.csv")):
        candidate_data = pd.read_csv(candidate)
        timestamp = pd.to_datetime(candidate_data.get("Datetime"), errors="coerce")
        temperature = pd.to_numeric(candidate_data.get("Temperature (degC)"), errors="coerce")
        spread = (pd.to_numeric(candidate_data["Temperature spread (degC)"], errors="coerce")
                  if "Temperature spread (degC)" in candidate_data else pd.Series(np.nan, index=candidate_data.index))
        flag_t = (pd.to_numeric(candidate_data["Flag_T"], errors="coerce")
                  if "Flag_T" in candidate_data else pd.Series(np.nan, index=candidate_data.index))
        spread_rows.append({
            "path": str(candidate), "product": candidate.stem,
            "rows": len(candidate_data), "columns": len(candidate_data.columns),
            "missing_datetime": int(timestamp.isna().sum()),
            "duplicate_timestamps": int(timestamp.duplicated().sum()),
            "missing_temperature": int(temperature.isna().sum()),
            "temperature_min_degC": temperature.min(), "temperature_max_degC": temperature.max(),
            "spread_nonmissing": int(spread.notna().sum()), "spread_max_degC": spread.max(),
            "spread_over_0_5": int(spread.gt(0.5).sum()),
            "spread_over_2": int(spread.gt(2).sum()), "spread_over_5": int(spread.gt(5).sum()),
            "flag_T_suspect": int(flag_t.eq(3).sum()),
            "qcs_versions": " | ".join(sorted(map(str, candidate_data.get("QCS version", pd.Series(dtype=str)).dropna().unique()))),
        })
    spread_sweep = pd.DataFrame(spread_rows).sort_values(
        ["spread_max_degC", "product"], ascending=[False, True], na_position="last")
    spread_sweep.to_csv(args.output / "corpus_spread_sweep.csv", index=False)
    details["corpus_spread_sweep"] = {
        "products_inspected": len(spread_sweep),
        "products_with_spread": int(spread_sweep.spread_nonmissing.gt(0).sum()),
        "products_over_0_5_degC": int(spread_sweep.spread_over_0_5.gt(0).sum()),
        "products_over_2_degC": int(spread_sweep.spread_over_2.gt(0).sum()),
        "products_over_5_degC": int(spread_sweep.spread_over_5.gt(0).sum()),
        "largest": spread_sweep.head(10).to_dict("records"),
    }
    assert (paired["Reconstructed source"] != "Unexplained").all(), details["reconstruction_counts"]
    assert paired.Flag_T.eq(3).equals(paired["Temperature spread (degC)"].gt(0.5))
    last_pair = paired.loc[paired["Reconstructed source"].eq("Both"), "Datetime"].max()
    after = paired.loc[paired.Datetime.gt(last_pair)]
    details["after_last_pair"] = {"last_pair": last_pair, "before_filter": len(paired),
                                  "after_filter": len(after),
                                  "source_counts": after["Reconstructed source"].value_counts().to_dict()}
    assert after["Reconstructed source"].eq("HOBO2 only").all()
    proposed = paired["HOBO2 temperature (degC)"]
    absolute_change = (proposed - paired["Temperature (degC)"]).abs()
    changed = absolute_change.gt(0.00006)
    details["dry_run_exclude_entire_HOBO1"] = {
        "decision_status": "simulation only; not authorized or applied",
        "rows_before": len(paired), "rows_after": len(paired),
        "temperature_rows_changed": int(changed.sum()),
        "temperature_rows_unchanged": int((~changed).sum()),
        "change_datetime_range": [paired.loc[changed, "Datetime"].min(),
                                  paired.loc[changed, "Datetime"].max()],
        "mean_absolute_change_degC": absolute_change.loc[changed].mean(),
        "max_absolute_change_degC": absolute_change.max(),
        "existing_suspect_rows_among_changed": int(paired.loc[changed, "Flag_T"].eq(3).sum()),
        "note": "Flags and light must be regenerated by the real pipeline; this dry run changes temperature values only.",
    }
    paired.to_csv(args.output / "paired_evidence.csv", index=False)
    (args.output / "analysis.json").write_text(json.dumps(details, indent=2, default=str), encoding="utf-8")
    colors = view.getSiteColors(["HOBO1", "HOBO2", "Qualified product"])
    with plt.rc_context({"font.family": theme.FONT_FAMILY}):
        fig, axes = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]}, layout="constrained")
        for number in (1, 2):
            axes[0].plot(h2.Datetime, h2[f"HOBO{number} temperature (degC)"],
                         color=colors[f"HOBO{number}"], linewidth=0.8,
                         label=f"HOBO{number}: source export")
        axes[0].plot(h2.Datetime, h2["Temperature (degC)"], color=colors["Qualified product"],
                     linewidth=1.0, label="Archived qualified product")
        axes[0].set_ylabel("Temperature (°C)")
        axes[0].set_title("SGOM: September–December 2025 | archived product SGOM_2026S1 (v11.0)")
        axes[0].legend(loc="upper left", ncol=3)
        axes[1].vlines(h2.Datetime, 0, h2["Temperature spread (degC)"],
                       colors=colors["Qualified product"], linewidth=0.65)
        axes[1].set_ylabel("Archived spread (°C)")
        peak = details["maximum"]
        axes[1].annotate("30 Oct: 9.750 °C\nmean retained, Flag_T = 3",
                         xy=(peak["Datetime"], peak["Temperature spread (degC)"]),
                         xytext=(pd.Timestamp("2025-11-11"), 6.5),
                         arrowprops={"arrowstyle": "->"})
        axes[1].text(pd.Timestamp("2025-11-06"), 1.2,
                     "After the last paired value on 30 Oct:\nproduct uses HOBO2 alone (source sensors still disagree).")
        axes[1].set_ylim(0, 11)
        axes[1].xaxis.set_major_locator(mdates.MonthLocator())
        axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        for ax in axes:
            ax.grid(axis="y", alpha=0.2)
            ax.spines[["top", "right"]].set_visible(False)
        fig.savefig(args.output / "sgom_disagreement.png", dpi=170)
        plt.close(fig)
    print(json.dumps(details, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analyse", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.analyse:
        analyse(args)
        return
    result = {
        "versions": {"python": platform.python_version(), "pandas": pd.__version__,
                     "numpy": np.__version__, "openpyxl": openpyxl.__version__},
        "products": {}, "raw": {},
    }
    for semester in ("2025S2", "2026S1"):
        path = args.archive / "HOBO" / "qualified" / semester / "SGOM" / f"SGOM_{semester}_HOBO_QLF.csv"
        frame = pd.read_csv(path)
        frame["Datetime"] = pd.to_datetime(frame["Datetime"])
        entry = {**file_info(path), **profile(frame)}
        entry["datetime_range"] = [frame.Datetime.min(), frame.Datetime.max()]
        entry["duplicate_timestamps"] = int(frame.Datetime.duplicated().sum())
        entry["flag_counts"] = frame.Flag_T.value_counts(dropna=False).to_dict()
        entry["qcs_versions"] = frame["QCS version"].unique().tolist()
        if "Temperature spread (degC)" in frame:
            entry["largest_spreads"] = frame.nlargest(5, "Temperature spread (degC)").to_dict("records")
        result["products"][semester] = entry
    raw_folder = args.archive / "HOBO" / "raw" / "2026S1" / "SGOM" / "planilha"
    for path in sorted(raw_folder.glob("*.xlsx")):
        sample = pd.read_excel(path, header=None, nrows=20)
        header = next(i for i, row in sample.iterrows()
                      if re.search(r"data\s*hora|date\s*time", " ".join(map(str, row)).lower())
                      and re.search(r"temp", " ".join(map(str, row)).lower()))
        frame = pd.read_excel(path, header=header)
        result["raw"][path.name] = {
            **file_info(path), **profile(frame),
            "header_excel_row": header + 1,
            "first_rows": frame.head(4).to_dict("records"),
            "last_rows": frame.tail(4).to_dict("records"),
        }
    destination = args.output / "inspection.json"
    destination.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
