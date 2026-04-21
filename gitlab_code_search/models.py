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
class SearchResult:
    word: str
    branch: str
    project_id: int
    project_name: str
    project_url: str
    file_name: str
    line_url: str
    data: str


@dataclass
class AuthenticatedUser:
    id: int
    username: str
    name: str
