"""Tests for file generation (CSV and XLSX writers)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from openpyxl import load_workbook

from b2b_data_bridge.config import FileConfig
from b2b_data_bridge.models import ExternalPricingRow, ExternalProductRow, ExternalStockRow
from b2b_data_bridge.files import write_csv, write_xlsx


@pytest.fixture
def file_config() -> FileConfig:
    return FileConfig(encoding="utf-8", csv_delimiter=";", csv_quotechar='"')


@pytest.fixture
def sample_product_rows() -> list[ExternalProductRow]:
    return [
        ExternalProductRow(
            ArticleNumber="SKU-001", ArticleName="Mouse", EAN="4006381333931",
            Description="Wireless mouse", Category="Peripherals", Brand="TechCorp",
            WeightKG="0.12", LastUpdate="2026-03-30T10:00:00",
        ),
        ExternalProductRow(
            ArticleNumber="SKU-002", ArticleName="Hub", EAN="4006381333948",
            Description="USB-C hub", Category="Accessories", Brand="TechCorp",
            WeightKG="0.25", LastUpdate="2026-03-30T10:00:00",
        ),
    ]


class TestCsvWriter:
    def test_write_csv_creates_file(
        self, tmp_path: Path, sample_product_rows: list[ExternalProductRow], file_config: FileConfig,
    ) -> None:
        out = tmp_path / "test.csv"
        result = write_csv(sample_product_rows, out, file_config)
        assert result.exists()
        assert result == out

    def test_csv_content_correct(
        self, tmp_path: Path, sample_product_rows: list[ExternalProductRow], file_config: FileConfig,
    ) -> None:
        out = tmp_path / "test.csv"
        write_csv(sample_product_rows, out, file_config)

        with open(out, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["ArticleNumber"] == "SKU-001"
        assert rows[1]["EAN"] == "4006381333948"

    def test_csv_utf8_encoding(
        self, tmp_path: Path, file_config: FileConfig,
    ) -> None:
        rows = [
            ExternalProductRow(
                ArticleNumber="SKU-Ü01", ArticleName="Ärmel Mütze", EAN="4006381333931",
            ),
        ]
        out = tmp_path / "utf8.csv"
        write_csv(rows, out, file_config)
        content = out.read_text(encoding="utf-8")
        assert "Ärmel Mütze" in content

    def test_csv_empty_rows_raises(
        self, tmp_path: Path, file_config: FileConfig,
    ) -> None:
        with pytest.raises(ValueError, match="zero rows"):
            write_csv([], tmp_path / "empty.csv", file_config)


class TestXlsxWriter:
    def test_write_xlsx_creates_file(
        self, tmp_path: Path, sample_product_rows: list[ExternalProductRow],
    ) -> None:
        out = tmp_path / "test.xlsx"
        result = write_xlsx(sample_product_rows, out)
        assert result.exists()

    def test_xlsx_content_correct(
        self, tmp_path: Path, sample_product_rows: list[ExternalProductRow],
    ) -> None:
        out = tmp_path / "test.xlsx"
        write_xlsx(sample_product_rows, out)

        wb = load_workbook(str(out))
        ws = wb.active
        assert ws is not None
        rows = list(ws.iter_rows(values_only=True))
        # Header + 2 data rows
        assert len(rows) == 3
        assert rows[0][0] == "ArticleNumber"
        assert rows[1][0] == "SKU-001"
        wb.close()

    def test_xlsx_empty_rows_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="zero rows"):
            write_xlsx([], tmp_path / "empty.xlsx")
