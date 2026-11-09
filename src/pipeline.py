"""Turn captured listing text into versioned CSV batches and quality reports."""

import hashlib
import json
import re
import unicodedata
from numbers import Real

import pandas as pd

if __package__:
    from .storage import CloudStorage, csv_bytes
else:
    from storage import CloudStorage, csv_bytes

OUTPUT = "carros_dados_limpos.csv"
SCHEMA = ("Título", "Descrição", "Preço", "Local", "Ano", "KM Rodado")
COLUMNS = (*SCHEMA, "Cidade", "Estado", "Transmissão")
STATES = set(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)
PLACE = re.compile(r"(.+?)(?:,\s*|\s+-\s+)([A-Z]{2})")
YEAR = re.compile(r"((?:19|20)\d{2})(?:\s*/\s*(?:19|20)\d{2})?")
INTEGER = r"(?:\d+|\d{1,3}(?:\.\d{3})+)"
BRL = re.compile(rf"{INTEGER}(?:,\d{{2}})?")
MILEAGE = re.compile(rf"({INTEGER})(?:\s*km)?", re.IGNORECASE)
CSV = "text/csv; charset=utf-8"
JSON = "application/json; charset=utf-8"


def field(value) -> str:
    return "" if pd.isna(value) else " ".join(str(value).split())


def price_brl(value) -> float:
    text = field(value).removeprefix("R$").strip()
    if isinstance(value, Real):
        result = float(value)
    elif BRL.fullmatch(text):
        result = float(text.replace(".", "").replace(",", "."))
    else:
        raise ValueError("invalid_price")
    if not 0 < result < float("inf"):
        raise ValueError("invalid_price")
    return result


def mileage_km(value) -> int | None:
    text = field(value)
    if not text:
        return None
    if isinstance(value, Real) and float(value).is_integer():
        result = int(value)
    else:
        match = MILEAGE.fullmatch(text)
        if match is None:
            raise ValueError("invalid_mileage")
        result = int(match[1].replace(".", ""))
    if not 0 <= result <= 10_000_000:
        raise ValueError("invalid_mileage")
    return result


def transmission(description: str) -> str:
    plain = unicodedata.normalize("NFKD", description.casefold()).encode("ascii", "ignore").decode()
    automatic = re.search(r"\b(?:aut|at|automatic[oa]|cvt|dsg|dct)\b", plain)
    manual = re.search(r"\b(?:manual|mt)\b", plain)
    if bool(automatic) == bool(manual):
        return "Não informado"
    return "Automático" if automatic else "Manual"


def normalize(row: dict) -> dict:
    title, description = field(row["Título"]), field(row["Descrição"])
    if not title or not description:
        raise ValueError("missing_title_or_description")
    location = field(row["Local"])
    place = PLACE.fullmatch(location)
    if not place or place[2] not in STATES:
        raise ValueError("invalid_location")
    year = YEAR.fullmatch(field(row["Ano"]))
    if not year:
        raise ValueError("invalid_year")
    return {
        "Título": title,
        "Descrição": description,
        "Preço": price_brl(row["Preço"]),
        "Local": location,
        "Ano": int(year[1]),
        "KM Rodado": mileage_km(row["KM Rodado"]),
        "Cidade": place[1],
        "Estado": place[2],
        "Transmissão": transmission(description),
    }


def frame_from_rows(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame["KM Rodado"] = frame["KM Rodado"].astype("Int64")
    return frame


def limpar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a table with the original Portuguese input schema."""
    missing = set(SCHEMA) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    return frame_from_rows([normalize(row) for row in df.to_dict("records")])


def parse_card(text: str) -> dict:
    lines = [field(line) for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("missing_title_or_description")
    detail = lines[2:]
    return normalize(
        {
            "Título": lines[0],
            "Descrição": lines[1],
            "Preço": next((line for line in detail if line.startswith("R$")), ""),
            "Local": next((line for line in detail if PLACE.fullmatch(line)), ""),
            "Ano": next((line for line in detail if YEAR.fullmatch(line)), ""),
            "KM Rodado": next(
                (line for line in detail if re.search(r"\d.*\bkm\b", line, re.I)), ""
            ),
        }
    )


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def run_batch(capture: dict, storage: CloudStorage) -> dict:
    source, cards = capture.get("source"), capture.get("cards")
    if source not in {"synthetic", "icarros"} or not isinstance(cards, list):
        raise ValueError("Capture must specify source and a list of cards")
    rows, rejected, seen = [], [], set()
    duplicates = 0
    for index, card in enumerate(cards):
        if not isinstance(card, dict) or not isinstance(card.get("text"), str):
            raise ValueError(f"Invalid capture structure at card {index}")
        if type(card.get("page")) is not int or card["page"] < 1:
            raise ValueError(f"Invalid capture page at card {index}")
        try:
            row = parse_card(card["text"])
        except ValueError as exc:
            rejected.append({"card_index": index, "page": card["page"], "reason": str(exc)})
            continue
        identity = tuple(row[column] for column in COLUMNS)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        rows.append(row)
    if not rows:
        raise ValueError("No valid listings in the batch. Check the source layout and capture.")

    artifacts = {
        "raw.json": (json_bytes(capture), JSON),
        "curated.csv": (csv_bytes(frame_from_rows(rows)), CSV),
        "rejected.json": (json_bytes(rejected), JSON),
    }
    checksums = {name: hashlib.sha256(data).hexdigest() for name, (data, _) in artifacts.items()}
    batch_id = hashlib.sha256(json_bytes(checksums)).hexdigest()
    prefix = f"runs/{batch_id}"
    manifest = {
        "schema_version": 1,
        "batch_id": batch_id,
        "source": source,
        "captured": len(cards),
        "accepted": len(rows),
        "rejected": len(rejected),
        "duplicates": duplicates,
        "missing_mileage": sum(row["KM Rodado"] is None for row in rows),
        "artifacts_sha256": checksums,
    }
    for name, (data, content_type) in artifacts.items():
        storage.write_bytes(f"{prefix}/{name}", data, content_type)
    storage.write_bytes(f"{prefix}/manifest.json", json_bytes(manifest), JSON)
    storage.write_bytes(OUTPUT, artifacts["curated.csv"][0], CSV)
    return manifest
