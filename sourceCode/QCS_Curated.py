# -*- coding: utf-8 -*-
"""Read-only catalog and export engine for the qualified QCS corpus.

The corpus contains three incompatible table layouts.  A curated database is
therefore one workbook with one data sheet per selected layout, plus an
included-products sheet that keeps every row traceable to its source product.
Each layout is unified only through :func:`QCS_DataHandler.build_database`.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Iterable
from itertools import product as itertools_product
from pathlib import Path

import pandas as pd

import QCS_DataHandler as data


DEFAULT_CORPUS_ROOT = r"\\Abrolhos\Projetos\Seaguard & HOBO\DATABASE"
INSTRUMENT_ORDER = ("Seaguard", "Doppler", "HOBO")
INSTRUMENT_LABELS = {
    "Seaguard": "Seaguard",
    "Doppler": "Seaguard current profiler (Doppler)",
    "HOBO": "HOBO",
}
_FAMILY_FOLDERS = (("SEAGUARD", "Seaguard"), ("HOBO", "HOBO"))
_QUALIFIED_SUFFIXES = ("_qlf.csv", "_qlf.xlsx")
_EXCLUDED_COLLECTION_FOLDERS = frozenset({
    "_EXPERIMENTOS", "_PISCINAS", "_SEM_SITIO",
})
_EXCLUDED_SITE_PREFIXES = ("PISCINA_",)


class CuratedDatabaseError(ValueError):
    """A self-localizing corpus selection or export error."""


class CuratedOperationCancelled(Exception):
    """Cooperative cancellation requested by the Curated Database tab."""


def _check_cancel(should_cancel):
    if should_cancel and should_cancel():
        raise CuratedOperationCancelled("Curated database operation canceled.")


def _is_excluded_corpus_path(path: Path) -> bool:
    """Keep special-purpose and pool deployments outside the curated corpus."""
    upper_parts = tuple(part.upper() for part in path.parts)
    return (bool(_EXCLUDED_COLLECTION_FOLDERS.intersection(upper_parts))
            or any(part.startswith(_EXCLUDED_SITE_PREFIXES)
                   for part in upper_parts))


def _read_identity_columns(path: Path) -> pd.DataFrame:
    """Read only the two columns needed to catalog a qualified product."""
    try:
        if path.suffix.lower() == ".xlsx":
            frame = pd.read_excel(path, usecols=lambda col: col in ("Datetime", "Site"))
        else:
            frame = pd.read_csv(path, usecols=lambda col: col in ("Datetime", "Site"),
                                low_memory=False)
    except Exception as exc:
        raise CuratedDatabaseError(
            "Curated database: could not read %s:\n%s" % (path, exc)) from exc
    missing = [col for col in ("Datetime", "Site") if col not in frame.columns]
    if missing:
        raise CuratedDatabaseError(
            "Curated database: %s is missing column(s): %s"
            % (path.name, ", ".join(missing)))
    return frame


def _product_context(root: Path, path: Path, family_instrument: str) -> dict:
    """Metadata encoded by the qualified corpus folder and file names."""
    relative = path.relative_to(root)
    parts = relative.parts
    if len(parts) < 5 or parts[1].lower() != "qualified":
        raise CuratedDatabaseError(
            "Curated database: unexpected qualified-product path: %s" % path)
    semester = parts[2]
    folders = parts[3:-1]
    bucket = folders[0] if len(folders) > 1 and folders[0].startswith("_") else ""
    path_site = folders[-1]
    instrument = family_instrument
    if family_instrument == "Seaguard" and "_DOPPLER_" in path.stem.upper():
        instrument = "Doppler"
    return {
        "product": path.stem,
        "source_file": path.name,
        "instrument": instrument,
        "semester": semester,
        "bucket": bucket,
        "path_site": path_site,
        "path": str(path),
        "relative_path": str(relative),
    }


def discover_qualified_corpus(
        corpus_root: str | os.PathLike,
        progress: Callable[[str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Catalog every qualified product below a corpus root without writing it.

    Calendar years and sites come from the data rows, not the campaign folder:
    a recovered deployment may start in an earlier calendar year.  Unreadable
    products are reported and excluded rather than represented as valid data.
    """
    root = Path(corpus_root).expanduser()
    if not root.is_dir():
        raise CuratedDatabaseError(
            "Curated database: corpus folder does not exist or is unavailable:\n%s"
            % root)

    candidates: list[tuple[Path, str]] = []
    for folder, family_instrument in _FAMILY_FOLDERS:
        _check_cancel(should_cancel)
        qualified = root / folder / "qualified"
        if not qualified.is_dir():
            continue
        for path in qualified.rglob("*"):
            _check_cancel(should_cancel)
            if (path.is_file()
                    and path.name.lower().endswith(_QUALIFIED_SUFFIXES)
                    and not _is_excluded_corpus_path(path)):
                candidates.append((path, family_instrument))
    candidates.sort(key=lambda item: str(item[0]).lower())
    if not candidates:
        raise CuratedDatabaseError(
            "Curated database: no *_QLF.csv or *_QLF.xlsx products were found under:\n%s"
            % root)

    rows = []
    messages = []
    total = len(candidates)
    for number, (path, family_instrument) in enumerate(candidates, start=1):
        _check_cancel(should_cancel)
        if progress and (number == 1 or number == total or number % 10 == 0):
            progress("Reading qualified product %d/%d..." % (number, total))
        try:
            frame = _read_identity_columns(path)
            context = _product_context(root, path, family_instrument)
        except CuratedDatabaseError as exc:
            messages.append("Warning: %s" % exc)
            continue
        _check_cancel(should_cancel)
        timestamps = data.parse_qualified_datetimes(frame["Datetime"])
        valid = timestamps.notna()
        site_values = frame["Site"].astype("string").str.strip()
        pair_rows = valid & site_values.notna() & site_values.ne("")
        site_years = tuple(sorted({
            (str(site_values.loc[index]), int(timestamps.loc[index].year))
            for index in frame.index[pair_rows]
        }))
        sites = tuple(sorted({site for site, _year in site_years}))
        years = tuple(sorted({year for _site, year in site_years}))
        if not site_years:
            messages.append(
                "Warning: Curated database: %s has no usable Site/Datetime rows and was excluded."
                % path.name)
            continue
        rows.append({
            **context,
            "sites": sites,
            "years": years,
            "site_years": site_years,
            "n_rows": int(len(frame)),
            "invalid_datetimes": int((~valid).sum()),
            "t_start": timestamps.loc[valid].min(),
            "t_end": timestamps.loc[valid].max(),
        })

    if not rows:
        raise CuratedDatabaseError(
            "Curated database: qualified products were found, but none had usable Site/Datetime rows.")
    catalog = pd.DataFrame(rows)
    order = {name: index for index, name in enumerate(INSTRUMENT_ORDER)}
    catalog["_instrument_order"] = catalog["instrument"].map(order)
    catalog = catalog.sort_values(
        ["_instrument_order", "path_site", "semester", "product"], kind="stable")
    catalog = catalog.drop(columns="_instrument_order").reset_index(drop=True)
    if catalog["path"].duplicated().any():
        raise CuratedDatabaseError("Curated database: duplicate product paths were discovered.")
    if catalog.duplicated(subset=["instrument", "source_file"]).any():
        raise CuratedDatabaseError(
            "Curated database: duplicate filenames exist within one instrument layout; "
            "row provenance would be ambiguous.")
    messages.append(
        "Info: curated corpus catalog: %d product(s), %d source row(s)."
        % (len(catalog), int(catalog["n_rows"].sum())))
    return catalog, messages


def _catalog_site_years(row) -> tuple[tuple[str, int], ...]:
    """Return exact row-level pairs, with a fallback for old in-memory catalogs."""
    pairs = row.get("site_years")
    if isinstance(pairs, (tuple, list, set)):
        return tuple((str(site), int(year)) for site, year in pairs)
    return tuple(itertools_product(
        (str(site) for site in row["sites"]),
        (int(year) for year in row["years"])))


def available_filters(
        catalog: pd.DataFrame,
        instruments: Iterable[str] = (),
        sites: Iterable[str] = (),
        years: Iterable[int] = (),
) -> dict[str, list]:
    """Return faceted options, constraining each dimension by the other two.

    An empty selection is treated as no constraint so that clearing one list
    leaves valid choices available in it. Site/year pairs are exact data-row
    combinations rather than the Cartesian product of product-level labels.
    """
    selected_instruments = {str(value) for value in instruments}
    selected_sites = {str(value) for value in sites}
    selected_years = {int(value) for value in years}
    triples = {
        (str(row["instrument"]), site, year)
        for _index, row in catalog.iterrows()
        for site, year in _catalog_site_years(row)
    }
    available_instruments = {
        instrument for instrument, site, year in triples
        if (not selected_sites or site in selected_sites)
        and (not selected_years or year in selected_years)
    }
    available_sites = {
        site for instrument, site, year in triples
        if (not selected_instruments or instrument in selected_instruments)
        and (not selected_years or year in selected_years)
    }
    available_years = {
        year for instrument, site, year in triples
        if (not selected_instruments or instrument in selected_instruments)
        and (not selected_sites or site in selected_sites)
    }
    return {
        "instruments": [name for name in INSTRUMENT_ORDER
                        if name in available_instruments],
        "sites": sorted(available_sites),
        "years": sorted(available_years),
    }


def select_catalog(
        catalog: pd.DataFrame,
        instruments: Iterable[str],
        sites: Iterable[str],
        years: Iterable[int],
) -> pd.DataFrame:
    """Select products intersecting all three filter dimensions."""
    instruments = {str(value) for value in instruments}
    sites = {str(value) for value in sites}
    years = {int(value) for value in years}
    if not instruments or not sites or not years:
        return catalog.iloc[0:0].copy()
    mask = (
        catalog["instrument"].isin(instruments)
        & catalog.apply(
            lambda row: any(site in sites and year in years
                            for site, year in _catalog_site_years(row)), axis=1)
    )
    return catalog.loc[mask].copy().reset_index(drop=True)


def _included_products(
        selected: pd.DataFrame,
        selected_rows: dict[tuple[str, str], int],
) -> pd.DataFrame:
    included = selected.copy()
    included["sites"] = included["sites"].map(lambda values: ", ".join(values))
    included["years"] = included["years"].map(
        lambda values: ", ".join(str(value) for value in values))
    included["selected_rows"] = [
        selected_rows.get((row.instrument, row.source_file), 0)
        for row in included.itertuples(index=False)
    ]
    included["contribution"] = included["selected_rows"].map(
        lambda count: "Included" if count > 0
        else "No unique rows after unification/filter")
    included = included.rename(columns={
        "product": "Product",
        "instrument": "Instrument",
        "semester": "Campaign semester",
        "bucket": "Bucket",
        "path_site": "Path site",
        "sites": "Data sites",
        "years": "Calendar years",
        "n_rows": "Source rows",
        "selected_rows": "Selected rows",
        "contribution": "Contribution",
        "invalid_datetimes": "Invalid datetimes",
        "t_start": "Data start",
        "t_end": "Data end",
        "relative_path": "Corpus path",
    })
    return included[[
        "Product", "Instrument", "Campaign semester", "Bucket", "Path site",
        "Data sites", "Calendar years", "Source rows", "Selected rows",
        "Contribution", "Invalid datetimes", "Data start", "Data end", "Corpus path",
    ]].reset_index(drop=True)


def build_curated_tables(
        catalog: pd.DataFrame,
        instruments: Iterable[str],
        sites: Iterable[str],
        years: Iterable[int],
        progress: Callable[[str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame, dict, list[str]]:
    """Build selected layout tables through the official unification engine."""
    _check_cancel(should_cancel)
    requested_instruments = set(instruments)
    instruments = [name for name in INSTRUMENT_ORDER if name in requested_instruments]
    sites = sorted({str(value) for value in sites})
    years = sorted({int(value) for value in years})
    selected = select_catalog(catalog, instruments, sites, years)
    if selected.empty:
        raise CuratedDatabaseError(
            "Curated database: no qualified products match the selected instruments, sites and years.")

    tables: dict[str, pd.DataFrame] = {}
    messages: list[str] = []
    selected_rows: dict[tuple[str, str], int] = {}
    for instrument in instruments:
        _check_cancel(should_cancel)
        group = selected[selected["instrument"] == instrument]
        if group.empty:
            continue
        if progress:
            progress("Unifying %s: %d product(s)..." % (INSTRUMENT_LABELS[instrument], len(group)))
        frame, build_messages = data.build_database(
            instrument, file_list=group["path"].astype(str).tolist(),
            should_cancel=should_cancel)
        _check_cancel(should_cancel)
        messages.extend(build_messages)
        before = len(frame)
        frame["Datetime"] = data.parse_qualified_datetimes(frame["Datetime"])
        frame = frame[
            frame["Site"].astype(str).isin(sites)
            & frame["Datetime"].dt.year.isin(years)
        ].copy()
        frame = frame.sort_values(["Site", "Datetime"], kind="stable").reset_index(drop=True)
        messages.append(
            "Info: %s calendar/site filter: %d -> %d row(s); %d outside selection."
            % (instrument, before, len(frame), before - len(frame)))
        if frame.empty:
            continue
        tables[instrument] = frame
        counts = frame["Source file"].value_counts()
        for product in group.itertuples(index=False):
            selected_rows[(instrument, product.source_file)] = int(
                counts.get(product.source_file, 0))

    if not tables:
        raise CuratedDatabaseError(
            "Curated database: matching products were found, but no data rows remain after the calendar-year filter.")
    included = _included_products(selected, selected_rows)
    summary = {
        "products": int(len(included)),
        "contributing_products": int((included["Selected rows"] > 0).sum()),
        "rows": int(sum(len(frame) for frame in tables.values())),
        "rows_by_instrument": {name: int(len(frame)) for name, frame in tables.items()},
        "instruments": list(tables),
        "sites": sites,
        "years": years,
    }
    return tables, included, summary, messages


def _readme_table(corpus_root: str, summary: dict) -> pd.DataFrame:
    rows = [
        ("QCS version", data.QCS_VERSION),
        ("Generated", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Corpus root", str(corpus_root)),
        ("Instruments", ", ".join(INSTRUMENT_LABELS[name]
                                   for name in summary["instruments"])),
        ("Sites", ", ".join(summary["sites"])),
        ("Calendar years", ", ".join(str(year) for year in summary["years"])),
        ("Included products", str(summary["products"])),
        ("Contributing products", str(summary["contributing_products"])),
        ("Selected rows", str(summary["rows"])),
        ("Structure", "One data sheet per instrument layout; incompatible flag and column layouts are never stacked."),
        ("Year filter", "Rows are selected by Datetime calendar year, not by the campaign-semester folder."),
        ("Provenance", "Included products maps every data sheet back to its qualified corpus product."),
        ("Flags", "1 = good; 2 = not evaluated; 3 = suspect; 4 = bad; 5 = dismissed; 9 = missing."),
    ]
    return pd.DataFrame(rows, columns=["Field", "Value"])


def write_curated_workbook(
        output_path: str | os.PathLike,
        corpus_root: str | os.PathLike,
        tables: dict[str, pd.DataFrame],
        included: pd.DataFrame,
        summary: dict,
        progress: Callable[[str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
) -> str:
    """Write a curated workbook.  The caller owns overwrite confirmation."""
    path = Path(output_path)
    if path.suffix.lower() != ".xlsx":
        raise CuratedDatabaseError("Curated database: output file must end in .xlsx.")
    if not path.parent.is_dir():
        raise CuratedDatabaseError(
            "Curated database: output folder does not exist:\n%s" % path.parent)
    if progress:
        progress("Writing curated workbook...")
    _check_cancel(should_cancel)
    sheets = {name: tables[name] for name in INSTRUMENT_ORDER if name in tables}
    sheets["Included products"] = included
    sheets["Read me"] = _readme_table(str(corpus_root), summary)
    temp_handle = tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=".%s-" % path.stem,
        suffix=".tmp.xlsx", delete=False)
    temp_path = Path(temp_handle.name)
    temp_handle.close()
    try:
        data.save_excel_sheets(
            sheets, temp_path, index=False, should_cancel=should_cancel)
        _check_cancel(should_cancel)
        os.replace(temp_path, path)
    except (CuratedOperationCancelled, InterruptedError):
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    except Exception as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise CuratedDatabaseError(
            "Curated database: could not write %s:\n%s" % (path, exc)) from exc
    return str(path)
