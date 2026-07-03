import tempfile
import unittest
import json
from pathlib import Path

from gitlab_code_search.excel_writer import build_output_basename, write_results
from gitlab_code_search.models import SearchResult


class ExcelWriterTests(unittest.TestCase):
    def test_build_output_basename_includes_seconds(self) -> None:
        basename = build_output_basename()
        self.assertRegex(basename, r"^\d{4}(?:_\d{2}){5}$")

    def test_write_results_reuses_same_basename_for_multiple_formats(self) -> None:
        result = SearchResult(
            word="needle",
            branch="main",
            project_id=1,
            project_name="demo",
            project_url="https://gitlab.example.com/group/project",
            file_name="file.py",
            line_url="https://gitlab.example.com/group/project/-/blob/main/file.py#L1",
            data="match",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_paths = write_results([result], ["csv", "json"], output_dir=tmpdir, base_name="report")

            self.assertEqual([path.suffix for path in output_paths], [".csv", ".json"])
            self.assertEqual({path.stem for path in output_paths}, {"report"})
            for path in output_paths:
                self.assertTrue(path.exists(), msg=str(path))

    def test_write_results_adds_suffix_when_target_exists(self) -> None:
        result = SearchResult(
            word="needle",
            branch="main",
            project_id=1,
            project_name="demo",
            project_url="https://gitlab.example.com/group/project",
            file_name="file.py",
            line_url="https://gitlab.example.com/group/project/-/blob/main/file.py#L1",
            data="match",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir) / "report.csv"
            existing.write_text("existing", encoding="utf-8")

            output_paths = write_results([result], ["csv", "json"], output_dir=tmpdir, base_name="report")

            self.assertEqual({path.stem for path in output_paths}, {"report_1"})
            self.assertTrue((Path(tmpdir) / "report_1.csv").exists())
            self.assertTrue((Path(tmpdir) / "report_1.json").exists())
            self.assertEqual(existing.read_text(encoding="utf-8"), "existing")

    def test_code_only_json_keeps_legacy_columns(self) -> None:
        result = SearchResult(
            word="needle",
            branch="main",
            project_id=1,
            project_name="demo",
            project_url="https://gitlab.example.com/group/project",
            file_name="file.py",
            line_url="https://gitlab.example.com/group/project/-/blob/main/file.py#L1",
            data="match",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = write_results([result], ["json"], output_dir=tmpdir, base_name="report")[0]
            data = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(
            list(data[0].keys()),
            ["关键字", "分支", "项目ID", "项目名", "项目地址", "文件名", "代码地址", "具体信息"],
        )

    def test_commit_rows_use_extended_columns(self) -> None:
        result = SearchResult(
            word="needle",
            branch="main",
            project_id=1,
            project_name="demo",
            project_url="https://gitlab.example.com/group/project",
            file_name="abcdef12",
            line_url="https://gitlab.example.com/group/project/-/commit/abcdef123456",
            data="Needle message",
            result_type="commit",
            commit_id="abcdef123456",
            commit_short_id="abcdef12",
            commit_title="Needle title",
            commit_author_name="Ada",
            commit_author_email="ada@example.com",
            commit_authored_date="2026-01-01T00:00:00+00:00",
            commit_committed_date="2026-01-01T00:01:00+00:00",
            commit_url="https://gitlab.example.com/group/project/-/commit/abcdef123456",
            commit_message="Needle message",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = write_results([result], ["json"], output_dir=tmpdir, base_name="report")[0]
            data = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(data[0]["结果类型"], "commit")
        self.assertEqual(data[0]["Commit SHA"], "abcdef123456")
        self.assertEqual(data[0]["Commit Message"], "Needle message")


if __name__ == "__main__":
    unittest.main()
