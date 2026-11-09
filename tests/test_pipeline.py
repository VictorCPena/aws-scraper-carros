import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline import OUTPUT, limpar_dados, parse_card, run_batch
from src.storage import CloudStorage

FIXTURE = Path(__file__).parent / "fixtures" / "listings.json"


@pytest.fixture
def capture():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def storage(tmp_path):
    return CloudStorage(ambiente="LOCAL", local_path=tmp_path)


def test_replay_checksums_and_idempotence(capture, storage, tmp_path):
    manifest = run_batch(capture, storage)
    assert (manifest["captured"], manifest["accepted"], manifest["rejected"]) == (
        15,
        12,
        2,
    )
    assert manifest["duplicates"] == manifest["missing_mileage"] == 1
    run_dir = tmp_path / "runs" / manifest["batch_id"]
    assert json.loads((run_dir / "manifest.json").read_text()) == manifest
    for filename, expected in manifest["artifacts_sha256"].items():
        assert hashlib.sha256((run_dir / filename).read_bytes()).hexdigest() == expected
    assert (tmp_path / OUTPUT).read_bytes() == (run_dir / "curated.csv").read_bytes()

    rows = storage.ler_csv(OUTPUT)
    assert len(rows) == 12
    assert rows.loc[0, "Preço"] == 55_990.90
    assert rows.loc[0, "KM Rodado"] == 61_500
    assert rows.loc[0, "Ano"] == 2020
    assert rows.loc[1, "Transmissão"] == "Automático"
    assert pd.isna(rows.loc[2, "KM Rodado"])
    assert rows.loc[2, "Transmissão"] == "Não informado"
    assert [row["reason"] for row in json.loads((run_dir / "rejected.json").read_text())] == [
        "invalid_price",
        "invalid_location",
    ]
    assert run_batch(capture, storage) == manifest
    assert list((tmp_path / "runs").iterdir()) == [run_dir]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Sedã\n1.8 prata\nR$ 1.000\nFortaleza, CE\n2010/2011\n0 km", "Não informado"),
        ("Sedã\n1.8 AUT.\nR$ 1000,00\nFortaleza, CE\n2010\n10 km", "Automático"),
        ("Sedã\n1.8 MT\nR$ 1.000\nFortaleza, CE\n2010\n5 km", "Manual"),
    ],
)
def test_transmission_matches_words(text, expected):
    assert parse_card(text)["Transmissão"] == expected


def test_historical_dataframe_input_accepts_numbers():
    frame = pd.DataFrame(
        [
            {
                "Título": "Carro A",
                "Descrição": "1.5 CVT",
                "Preço": 62900.50,
                "Local": "Fortaleza, CE",
                "Ano": 2020,
                "KM Rodado": 0,
            }
        ]
    )
    row = limpar_dados(frame).iloc[0]
    assert row["Preço"] == 62_900.50
    assert row["KM Rodado"] == 0
    assert row["Transmissão"] == "Automático"


def test_rejected_batch_keeps_previous_csv(capture, storage, tmp_path):
    run_batch(capture, storage)
    before = (tmp_path / OUTPUT).read_bytes()
    with pytest.raises(ValueError, match="No valid listings"):
        run_batch(
            {"source": "icarros", "cards": [{"page": 1, "text": "layout alterado"}]},
            storage,
        )
    assert (tmp_path / OUTPUT).read_bytes() == before
    assert len(list((tmp_path / "runs").iterdir())) == 1


def test_partial_batch_cannot_replace_latest(capture, storage, tmp_path, monkeypatch):
    run_batch(capture, storage)
    before = (tmp_path / OUTPUT).read_bytes()
    write = storage.write_bytes

    def fail_on_rejects(name, content, content_type):
        if name.endswith("rejected.json"):
            raise OSError("injected write failure")
        write(name, content, content_type)

    monkeypatch.setattr(storage, "write_bytes", fail_on_rejects)
    capture["cards"].pop(1)
    with pytest.raises(OSError, match="injected"):
        run_batch(capture, storage)
    assert (tmp_path / OUTPUT).read_bytes() == before
    assert len(list((tmp_path / "runs").glob("*/manifest.json"))) == 1
