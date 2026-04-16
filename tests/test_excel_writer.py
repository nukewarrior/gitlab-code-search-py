import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
