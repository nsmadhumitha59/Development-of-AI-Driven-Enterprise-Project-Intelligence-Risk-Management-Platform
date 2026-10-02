"""
CSV Document Parser using pandas and standard csv handling.
"""
from pathlib import Path
from typing import Optional, List
import logging
import pandas as pd

from ..base import BaseParser, FileType, DocumentMetadata, ParsedDocument, DocumentSection
from ..normalizer import ContentNormalizer

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """
    Parses structured tabular CSV files.
    Converts tabular data into rich semantic text representation suitable for RAG chunking and indexing.
    """

    @property
    def supported_type(self) -> FileType:
        return FileType.CSV

    def parse(self, file_path: Path, metadata: Optional[DocumentMetadata] = None) -> ParsedDocument:
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        file_stat = file_path.stat()
        file_hash = self.calculate_file_hash(file_path)

        if metadata is None:
            metadata = DocumentMetadata(
                filename=file_path.name,
                original_name=file_path.name,
                file_type=FileType.CSV,
                file_size_bytes=file_stat.st_size,
                file_hash=file_hash,
            )
        else:
            metadata.file_size_bytes = file_stat.st_size
            metadata.file_hash = file_hash

        sections: List[DocumentSection] = []
        raw_rows: List[str] = []
        normalized_rows: List[str] = []

        try:
            # Try reading with pandas, auto-detecting separator if needed
            try:
                df = pd.read_csv(str(file_path), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(str(file_path), encoding="latin1")

            total_rows, total_cols = df.shape
            metadata.row_count = total_rows
            columns = [str(col).strip() for col in df.columns]
            
            metadata.custom_metadata["columns"] = columns
            metadata.custom_metadata["total_columns"] = total_cols
            metadata.custom_metadata["total_rows"] = total_rows

            # 1. Add schema / summary section
            summary_text = (
                f"CSV Dataset: {file_path.name}\n"
                f"Total Records: {total_rows}, Total Columns: {total_cols}\n"
                f"Column Headers: {', '.join(columns)}"
            )
            sections.append(
                DocumentSection(
                    section_index=0,
                    section_title="Dataset Summary & Schema",
                    row_number=0,
                    raw_text=summary_text,
                    normalized_text=ContentNormalizer.normalize(summary_text)
                )
            )
            raw_rows.append(summary_text)
            normalized_rows.append(ContentNormalizer.normalize(summary_text))

            # 2. Process each data row into contextual text representation
            # Example: "Record 1 -> Task: Fix Auth Bug, Assignee: Alice, Status: In Progress, Priority: High"
            for row_idx, row in df.iterrows():
                row_num = row_idx + 1
                row_items = []
                for col in columns:
                    val = row[col]
                    if pd.notna(val) and str(val).strip() != "":
                        cleaned_val = ContentNormalizer.clean_table_text(str(val))
                        row_items.append(f"{col}: {cleaned_val}")

                if row_items:
                    row_text = f"Row {row_num}: {'; '.join(row_items)}"
                    norm_row_text = ContentNormalizer.normalize(row_text)

                    raw_rows.append(row_text)
                    normalized_rows.append(norm_row_text)

                    sections.append(
                        DocumentSection(
                            section_index=len(sections),
                            section_title=f"Record {row_num}",
                            row_number=row_num,
                            raw_text=row_text,
                            normalized_text=norm_row_text
                        )
                    )

            full_raw_text = "\n".join(raw_rows)
            full_norm_text = "\n".join(normalized_rows)

            metadata.char_count = len(full_norm_text)
            metadata.word_count = len(full_norm_text.split()) if full_norm_text else 0
            metadata.status = "parsed"

            return ParsedDocument(
                metadata=metadata,
                raw_text=full_raw_text,
                normalized_text=full_norm_text,
                sections=sections
            )

        except Exception as e:
            metadata.status = "failed"
            metadata.error_message = f"Failed to parse CSV: {str(e)}"
            logger.error(f"Failed to parse CSV {file_path}: {e}", exc_info=True)
            raise ValueError(f"Error parsing CSV file {file_path.name}: {str(e)}") from e
