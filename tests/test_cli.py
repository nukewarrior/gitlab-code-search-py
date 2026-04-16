from urllib.parse import urlsplit
import unittest

from gitlab_code_search.cli import build_line_url


class BuildLineUrlTests(unittest.TestCase):
    def test_build_line_url_encodes_special_characters_in_branch_and_filename(self) -> None:
        url = build_line_url(
            "https://gitlab.example.com/group/project",
            "feature/test",
            "dir with space/中文#a?.py",
            12,
        )

        parsed = urlsplit(url)
        self.assertEqual(parsed.fragment, "L12")
        self.assertEqual(
            parsed.path,
            "/group/project/-/blob/feature%2Ftest/dir%20with%20space/%E4%B8%AD%E6%96%87%23a%3F.py",
        )

    def test_build_line_url_preserves_directory_separators(self) -> None:
        url = build_line_url(
            "https://gitlab.example.com/group/project",
            "main",
            "nested/path/file.py",
            3,
        )

        parsed = urlsplit(url)
        self.assertIn("/nested/path/file.py", parsed.path)


if __name__ == "__main__":
    unittest.main()
