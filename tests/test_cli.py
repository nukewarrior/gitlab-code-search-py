from urllib.parse import urlsplit
import unittest
from unittest.mock import patch

from gitlab_code_search.cli import build_line_url, configure_stdio_encoding


class FakeStream:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def reconfigure(self, *, encoding: str, errors: str) -> None:
        if self.fail:
            raise ValueError("stream is closed")
        self.calls.append((encoding, errors))


class ConfigureStdioEncodingTests(unittest.TestCase):
    def test_configure_stdio_encoding_sets_utf8_on_stdout_and_stderr(self) -> None:
        stdout = FakeStream()
        stderr = FakeStream()
        with patch("gitlab_code_search.cli.sys.stdout", stdout), patch("gitlab_code_search.cli.sys.stderr", stderr):
            configure_stdio_encoding()

        self.assertEqual(stdout.calls, [("utf-8", "replace")])
        self.assertEqual(stderr.calls, [("utf-8", "replace")])

    def test_configure_stdio_encoding_ignores_streams_that_cannot_reconfigure(self) -> None:
        stdout = FakeStream(fail=True)
        stderr = object()
        with patch("gitlab_code_search.cli.sys.stdout", stdout), patch("gitlab_code_search.cli.sys.stderr", stderr):
            configure_stdio_encoding()

        self.assertEqual(stdout.calls, [])


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
