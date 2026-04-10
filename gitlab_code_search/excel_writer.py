from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from .models import SearchResult


def build_output_filename() -> str:
    return datetime.now().strftime("%Y_%m_%d_%H_%M") + ".xlsx"


def write_results_xlsx(results: list[SearchResult], output_dir: str | Path = ".") -> Path:
    output_dir = Path(output_dir)
    output_path = output_dir / build_output_filename()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"

    headers = ["关键字", "分支", "项目ID", "项目名", "项目地址", "文件名", "代码地址", "具体信息"]
    sheet.append(headers)

    for result in results:
        sheet.append(
            [
                result.word,
                result.branch,
                result.project_id,
                result.project_name,
                result.project_url,
                result.file_name,
                result.line_url,
                result.data,
            ]
        )

    workbook.save(output_path)
    return output_path
