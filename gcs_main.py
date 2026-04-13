import multiprocessing

from gitlab_code_search.cli import main


if __name__ == "__main__":
    # Required for frozen binaries that implicitly touch multiprocessing internals.
    multiprocessing.freeze_support()
    raise SystemExit(main())
