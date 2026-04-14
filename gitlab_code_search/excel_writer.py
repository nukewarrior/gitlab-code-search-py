from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from .models import SearchResult

OUTPUT_COLUMNS = [
    ("关键字", "word"),
    ("分支", "branch"),
    ("项目ID", "project_id"),
    ("项目名", "project_name"),
    ("项目地址", "project_url"),
    ("文件名", "file_name"),
    ("代码地址", "line_url"),
    ("具体信息", "data"),
]


def build_output_basename() -> str:
    return datetime.now().strftime("%Y_%m_%d_%H_%M")


def _build_output_path(output_dir: str | Path, base_name: str, ext: str) -> Path:
    output_dir = Path(output_dir)
    return output_dir / f"{base_name}.{ext}"


def _result_to_row(result: SearchResult) -> list[object]:
    return [getattr(result, field_name) for _, field_name in OUTPUT_COLUMNS]


def _result_to_dict(result: SearchResult) -> dict[str, object]:
    return {header: getattr(result, field_name) for header, field_name in OUTPUT_COLUMNS}


def write_results_xlsx(results: list[SearchResult], output_dir: str | Path = ".", base_name: str | None = None) -> Path:
    base_name = base_name or build_output_basename()
    output_path = _build_output_path(output_dir, base_name, "xlsx")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"

    headers = [header for header, _ in OUTPUT_COLUMNS]
    sheet.append(headers)

    for result in results:
        sheet.append(_result_to_row(result))

    workbook.save(output_path)
    return output_path


def write_results_csv(results: list[SearchResult], output_dir: str | Path = ".", base_name: str | None = None) -> Path:
    base_name = base_name or build_output_basename()
    output_path = _build_output_path(output_dir, base_name, "csv")

    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow([header for header, _ in OUTPUT_COLUMNS])
        for result in results:
            writer.writerow(_result_to_row(result))
    return output_path


def write_results_json(results: list[SearchResult], output_dir: str | Path = ".", base_name: str | None = None) -> Path:
    base_name = base_name or build_output_basename()
    output_path = _build_output_path(output_dir, base_name, "json")

    data = [_result_to_dict(result) for result in results]
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
    return output_path


def write_results(
    results: list[SearchResult],
    formats: list[str],
    output_dir: str | Path = ".",
    base_name: str | None = None,
) -> list[Path]:
    base_name = base_name or build_output_basename()
    output_paths: list[Path] = []
    for fmt in formats:
        if fmt == "xlsx":
            output_paths.append(write_results_xlsx(results, output_dir=output_dir, base_name=base_name))
        elif fmt == "csv":
            output_paths.append(write_results_csv(results, output_dir=output_dir, base_name=base_name))
        elif fmt == "json":
            output_paths.append(write_results_json(results, output_dir=output_dir, base_name=base_name))
        else:
            raise ValueError(f"unsupported output format: {fmt}")
    return output_paths
