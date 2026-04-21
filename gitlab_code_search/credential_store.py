from __future__ import annotations

from .serve_store import ServeStore


class CredentialStoreError(RuntimeError):
    pass


class LocalCredentialStore:
    def __init__(self, store: ServeStore) -> None:
        self.store = store

    def set_secret(self, account: str, secret: str) -> None:
        if not account:
            raise CredentialStoreError("credential key cannot be empty")
        self.store.upsert_credential(account, secret)

    def get_secret(self, account: str) -> str | None:
        if not account:
            return None
        return self.store.get_credential(account)

    def delete_secret(self, account: str) -> None:
        if not account:
            return
        self.store.delete_credential(account)
