from dataclasses import dataclass


@dataclass
class Project:
    id: int
    name: str
    web_url: str
    default_branch: str | None = None


@dataclass
class BranchRef:
    name: str
    search_ref: str


@dataclass
class BlobSearchResult:
    filename: str
    startline: int
    data: str


@dataclass
class CommitSearchResult:
    commit_id: str
    short_id: str
    title: str
    author_name: str
    author_email: str
    authored_date: str
    committed_date: str
    web_url: str
    message: str


@dataclass
class SearchResult:
    word: str
    branch: str
    project_id: int
    project_name: str
    project_url: str
    file_name: str
    line_url: str
    data: str
    result_type: str = "code"
    commit_id: str = ""
    commit_short_id: str = ""
    commit_title: str = ""
    commit_author_name: str = ""
    commit_author_email: str = ""
    commit_authored_date: str = ""
    commit_committed_date: str = ""
    commit_url: str = ""
    commit_message: str = ""


@dataclass
class AuthenticatedUser:
    id: int
    username: str
    name: str
