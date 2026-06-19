from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.qagent.paper_fetcher import (
    _candidate_pdf_urls,
    _discover_pdf_urls_from_html,
    _local_pdf_path_candidates,
    _repository_priority_pdf_urls,
    _source_cache_key,
    fetch_best_source,
)
from src.qagent.paper_text_extractor import _confidence_from_text, _looks_like_full_text, extract_paper_text
import src.qagent.paper_text_extractor as paper_text_extractor


class PaperFetchAndTextTests(unittest.TestCase):
    def test_arxiv_abs_url_becomes_pdf_candidate(self) -> None:
        urls = _candidate_pdf_urls({"url": "https://arxiv.org/abs/2505.08959"})

        self.assertIn("https://arxiv.org/pdf/2505.08959.pdf", urls)
        self.assertIn("https://export.arxiv.org/pdf/2505.08959.pdf", urls)

    def test_arxiv_url_is_repository_priority_over_publisher_doi(self) -> None:
        source, urls = _repository_priority_pdf_urls(
            {
                "url": "https://arxiv.org/abs/2505.08959",
                "doi": "10.1007/s00205-016-1040-9",
            }
        )

        self.assertEqual(source, "arXiv")
        self.assertEqual(urls[0], "https://arxiv.org/pdf/2505.08959")
        self.assertNotIn("link.springer.com", "\n".join(urls))

    def test_arxiv_doi_becomes_pdf_candidate_and_cache_key(self) -> None:
        entry = {"doi": "10.48550/arxiv.2508.01811", "title": "Example"}

        self.assertIn("https://arxiv.org/pdf/2508.01811.pdf", _candidate_pdf_urls(entry))
        self.assertEqual(_source_cache_key(entry), "arxiv_2508_01811")

    def test_cvgmt_id_adds_cvgmt_candidates(self) -> None:
        urls = _candidate_pdf_urls({"cvgmt_id": "1234"})

        self.assertTrue(any("cvgmt.sns.it/paper/1234" in url for url in urls))
        self.assertTrue(any(url.endswith(".pdf") for url in urls))

    def test_cvgmt_url_adds_cvgmt_candidates(self) -> None:
        urls = _candidate_pdf_urls({"url": "https://cvgmt.sns.it/paper/5678/"})

        self.assertIn("https://cvgmt.sns.it/paper/5678/", urls)
        self.assertIn("https://cvgmt.sns.it/media/doc/paper/5678/main.pdf", urls)

    def test_cvgmt_url_is_repository_priority(self) -> None:
        source, urls = _repository_priority_pdf_urls({"url": "https://cvgmt.sns.it/paper/5678/"})

        self.assertEqual(source, "CVGMT")
        self.assertEqual(urls[0], "https://cvgmt.sns.it/paper/5678/")
        self.assertIn("https://cvgmt.sns.it/media/doc/paper/5678/main.pdf", urls)

    def test_publisher_doi_adds_common_pdf_candidates(self) -> None:
        springer = _candidate_pdf_urls({"doi": "10.1007/s00205-016-1040-9"})
        degruyter = _candidate_pdf_urls({"doi": "10.1515/acv-2023-0064"})

        self.assertIn("https://link.springer.com/content/pdf/10.1007/s00205-016-1040-9.pdf", springer)
        self.assertIn("https://www.degruyter.com/document/doi/10.1515/acv-2023-0064/pdf", degruyter)

    def test_local_pdf_path_is_used_before_online_fetch(self) -> None:
        with TemporaryDirectory() as tmp:
            import src.qagent.paper_fetcher as paper_fetcher

            old_pdf_dir = paper_fetcher.PDF_DIR
            paper_fetcher.PDF_DIR = Path(tmp) / "pdfs"
            try:
                local = Path(tmp) / "local.pdf"
                local.write_bytes(b"%PDF" + b"x" * 20_000)

                result = fetch_best_source(
                    {"paper_id": "paper_001", "pdf_path": str(local), "title": "Local PDF"},
                    try_online=False,
                    cache_key="local_pdf",
                )

                self.assertEqual(result.source_type, "pdf")
                self.assertTrue(Path(result.pdf_path).is_file())
                self.assertIn("Using local PDF", "\n".join(result.log))
            finally:
                paper_fetcher.PDF_DIR = old_pdf_dir

    def test_local_pdf_url_field_is_used_before_online_fetch(self) -> None:
        with TemporaryDirectory() as tmp:
            import src.qagent.paper_fetcher as paper_fetcher

            old_pdf_dir = paper_fetcher.PDF_DIR
            paper_fetcher.PDF_DIR = Path(tmp) / "pdfs"
            try:
                local = Path(tmp) / "local.pdf"
                local.write_bytes(b"%PDF" + b"x" * 20_000)

                result = fetch_best_source(
                    {"paper_id": "paper_001", "url": str(local), "doi": "10.1007/s00205-018-1296-3"},
                    try_online=True,
                    cache_key="local_url_pdf",
                )

                self.assertEqual(result.source_type, "pdf")
                self.assertEqual(result.source_url, local.as_posix())
                self.assertIn("Using local PDF", "\n".join(result.log))
            finally:
                paper_fetcher.PDF_DIR = old_pdf_dir

    def test_windows_local_pdf_path_candidates_include_wsl_mount(self) -> None:
        candidates = _local_pdf_path_candidates(r"C:\Users\19891\Desktop\papers\paper.pdf")

        self.assertIn(r"C:\Users\19891\Desktop\papers\paper.pdf", candidates)
        self.assertIn("/mnt/c/Users/19891/Desktop/papers/paper.pdf", candidates)

    def test_file_url_local_pdf_path_candidates_include_wsl_mount(self) -> None:
        candidates = _local_pdf_path_candidates("file:///C:/Users/19891/Desktop/papers/paper.pdf")

        self.assertIn(r"C:\Users\19891\Desktop\papers\paper.pdf", candidates)
        self.assertIn("/mnt/c/Users/19891/Desktop/papers/paper.pdf", candidates)

    def test_repository_pdf_has_priority_over_local_pdf(self) -> None:
        with TemporaryDirectory() as tmp:
            import src.qagent.paper_fetcher as paper_fetcher

            old_pdf_dir = paper_fetcher.PDF_DIR
            old_download = paper_fetcher._download_first_valid_pdf
            paper_fetcher.PDF_DIR = Path(tmp) / "pdfs"

            def fake_download(_requests, urls, pdf_path, _timeout, _log, discovery_pool=None):
                pdf_path.write_bytes(b"%PDF" + b"x" * 20_000)
                return urls[0]

            paper_fetcher._download_first_valid_pdf = fake_download
            try:
                local = Path(tmp) / "local.pdf"
                local.write_bytes(b"%PDF" + b"y" * 20_000)

                result = fetch_best_source(
                    {
                        "paper_id": "paper_001",
                        "url": "https://arxiv.org/abs/2505.08959",
                        "pdf_path": str(local),
                        "title": "Repository beats local",
                    },
                    try_online=True,
                    cache_key="repo_priority",
                )

                self.assertEqual(result.source_url, "https://arxiv.org/pdf/2505.08959")
                self.assertIn("Repository priority source: arXiv", "\n".join(result.log))
                self.assertNotIn("Using local PDF", "\n".join(result.log))
            finally:
                paper_fetcher._download_first_valid_pdf = old_download
                paper_fetcher.PDF_DIR = old_pdf_dir

    def test_html_pdf_discovery_uses_relative_links_and_labels(self) -> None:
        html = """
        <html><body>
        <a href="/media/doc/paper/1234/main.pdf">Download PDF</a>
        <a href="details.html">Details</a>
        </body></html>
        """

        urls = _discover_pdf_urls_from_html(html, "https://cvgmt.sns.it/paper/1234/")

        self.assertEqual(urls, ["https://cvgmt.sns.it/media/doc/paper/1234/main.pdf"])

    def test_full_text_detection_requires_more_than_short_abstract(self) -> None:
        short = "Abstract. We prove a theorem."
        full = (
            "Abstract. We prove a theorem. Introduction. "
            + "This section contains mathematical context. " * 80
            + "Theorem. Let u solve an equation. Proof. The proof follows. References."
        )

        self.assertFalse(_looks_like_full_text(short))
        self.assertTrue(_looks_like_full_text(full))
        self.assertEqual(_confidence_from_text(short, "pdf"), "low")
        self.assertIn(_confidence_from_text(full, "pdf"), {"medium", "high"})

    def test_cached_pdf_source_reextracts_short_cached_text(self) -> None:
        with TemporaryDirectory() as tmp:
            original_text_dir = paper_text_extractor.TEXT_DIR
            paper_text_extractor.TEXT_DIR = Path(tmp)
            try:
                text_path = Path(tmp) / "arxiv_2508_01811.txt"
                text_path.write_text("Short stale metadata cache.", encoding="utf-8")
                pdf_path = Path(tmp) / "paper_001.pdf"
                pdf_path.write_bytes(b"%PDF placeholder")

                full = (
                    "Abstract. We prove a theorem. Introduction. "
                    + "This section contains mathematical context. " * 80
                    + "Theorem. Let u solve an equation. Proof. The proof follows. References."
                )
                original_extract = paper_text_extractor._extract_pdf_text
                paper_text_extractor._extract_pdf_text = lambda _: (full, ["fake PDF extraction"])
                try:
                    result = extract_paper_text(
                        {
                            "paper_id": "paper_001",
                            "cache_key": "arxiv_2508_01811",
                            "source": "cached_pdf",
                            "pdf_path": str(pdf_path),
                        },
                        {"title": "T"},
                    )
                finally:
                    paper_text_extractor._extract_pdf_text = original_extract

                self.assertTrue(result.full_text_read)
                self.assertIn("re-extracting from PDF", "\n".join(result.log))
                self.assertGreater(len(text_path.read_text(encoding="utf-8")), 1500)
            finally:
                paper_text_extractor.TEXT_DIR = original_text_dir

    def test_pdf_source_reextracts_even_when_cached_html_looks_long(self) -> None:
        with TemporaryDirectory() as tmp:
            original_text_dir = paper_text_extractor.TEXT_DIR
            paper_text_extractor.TEXT_DIR = Path(tmp)
            try:
                text_path = Path(tmp) / "doi_example.txt"
                text_path.write_text(
                    "Abstract. Introduction. " + "publisher html navigation " * 400 + "References.",
                    encoding="utf-8",
                )
                pdf_path = Path(tmp) / "paper.pdf"
                pdf_path.write_bytes(b"%PDF placeholder")

                full = (
                    "Abstract. PDF text. Introduction. "
                    + "This section contains mathematical context. " * 80
                    + "Theorem. Let u solve an equation. Proof. The proof follows. References."
                )
                original_extract = paper_text_extractor._extract_pdf_text
                paper_text_extractor._extract_pdf_text = lambda _: (full, ["fake PDF extraction"])
                try:
                    result = extract_paper_text(
                        {
                            "paper_id": "paper_001",
                            "cache_key": "doi_example",
                            "source_type": "pdf",
                            "pdf_path": str(pdf_path),
                        },
                        {"title": "T"},
                    )
                finally:
                    paper_text_extractor._extract_pdf_text = original_extract

                self.assertTrue(result.full_text_read)
                self.assertIn("re-extracting from PDF", "\n".join(result.log))
                self.assertIn("PDF text", text_path.read_text(encoding="utf-8"))
            finally:
                paper_text_extractor.TEXT_DIR = original_text_dir


if __name__ == "__main__":
    unittest.main()
