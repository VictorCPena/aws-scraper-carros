"""CSV storage for notebooks and batch artifacts for the CLI."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import boto3
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def object_key(value: str) -> str:
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts) or "\\" in value:
        raise ValueError("Invalid storage key")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Invalid storage key")
    return value


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


class CloudStorage:
    def __init__(
        self,
        *,
        ambiente: str | None = None,
        local_path: str | Path | None = None,
        s3_client=None,
    ):
        load_dotenv(ROOT / ".env")
        self.env = (ambiente or os.environ.get("AMBIENTE", "LOCAL")).strip().upper()
        if self.env not in {"LOCAL", "PROD"}:
            raise ValueError("AMBIENTE must be LOCAL or PROD")

        self.local_path = Path(local_path or os.environ.get("DATA_DIR") or ROOT / "data").resolve()
        self.bucket_name = os.environ.get("BUCKET_NAME", "").strip()
        self.prefix = os.environ.get("S3_PREFIX", "").strip()
        if self.env == "PROD":
            if not self.bucket_name:
                raise ValueError("BUCKET_NAME is required in PROD")
            if self.prefix:
                object_key(self.prefix)
            self.s3_client = (
                s3_client
                if s3_client is not None
                else boto3.client("s3", region_name=os.environ.get("AWS_REGION") or None)
            )

    def _local_file(self, key: str) -> Path:
        path = (self.local_path / object_key(key)).resolve()
        if not path.is_relative_to(self.local_path):
            raise ValueError("Storage path escapes DATA_DIR")
        return path

    def _s3_key(self, key: str) -> str:
        key = object_key(key)
        return f"{self.prefix}/{key}" if self.prefix else key

    def write_bytes(self, name: str, content: bytes, content_type: str) -> None:
        if self.env == "PROD":
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self._s3_key(name),
                Body=content,
                ContentType=content_type,
            )
            return

        path = self._local_file(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=path.parent, delete=False) as file:
            temp = Path(file.name)
            try:
                file.write(content)
                file.flush()
                file.close()
                os.replace(temp, path)
            finally:
                temp.unlink(missing_ok=True)

    def salvar(self, df: pd.DataFrame, nome_arquivo: str) -> None:
        self.write_bytes(nome_arquivo, csv_bytes(df), "text/csv; charset=utf-8")

    def ler_csv(self, nome_arquivo: str) -> pd.DataFrame:
        if self.env == "PROD":
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=self._s3_key(nome_arquivo)
            )
            with response["Body"] as body:
                return pd.read_csv(body)
        return pd.read_csv(self._local_file(nome_arquivo))
