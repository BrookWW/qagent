from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from src.qagent.input_resolver import resolve_paper_entries


class InputResolverTests(unittest.TestCase):
    def test_single_markdown_heading_is_one_entry(self) -> None:
        markdown = """## Asymptotics for 2-dimensional vectorial Allen-Cahn systems

- **Authors:** Fabrice Bethuel
- **Year:** 2025
- **DOI:** 10.4310/acta.2025.v234.n2.a1
- **URL:** https://doi.org/10.4310/acta.2025.v234.n2.a1

**Abstract:**

not provided
"""

        resolved = resolve_paper_entries(markdown, try_online=False)

        self.assertEqual(len(resolved["entries"]), 1)
        self.assertEqual(resolved["entries"][0]["title"], "Asymptotics for 2-dimensional vectorial Allen-Cahn systems")
        self.assertEqual(resolved["entries"][0]["doi"], "10.4310/acta.2025.v234.n2.a1")

    def test_numbered_title_prefix_is_removed(self) -> None:
        markdown = "## 2.Landau-de Gennes model with sextic potentials: asymptotic behavior of minimizers"

        resolved = resolve_paper_entries(markdown, try_online=False)

        self.assertEqual(
            resolved["entries"][0]["title"],
            "Landau-de Gennes model with sextic potentials: asymptotic behavior of minimizers",
        )

    def test_pdf_url_and_path_fields_are_preserved(self) -> None:
        markdown = """## Paper with local PDF

- **PDF URL:** https://example.org/paper.pdf
- **PDF Path:** C:\\papers\\paper.pdf
"""

        resolved = resolve_paper_entries(markdown, try_online=False)

        self.assertEqual(resolved["entries"][0]["pdf_url"], "https://example.org/paper.pdf")
        self.assertEqual(resolved["entries"][0]["pdf_path"], "C:\\papers\\paper.pdf")
        self.assertIn("PDF URL", resolved["normalized_markdown"])

    def test_local_pdf_link_skips_online_enrichment(self) -> None:
        markdown = """## Paper with local PDF

DOI: 10.1007/s00205-018-1296-3
PDF: C:\\papers\\local-paper.pdf
"""

        resolved = resolve_paper_entries(markdown, try_online=True)

        self.assertEqual(resolved["entries"][0]["pdf_path"], "C:\\papers\\local-paper.pdf")
        self.assertEqual(resolved["entries"][0]["source"], "user+local-pdf")
        self.assertEqual(resolved["entries"][0]["url"], "not provided")
        self.assertIn("Local PDF path provided", "\n".join(resolved["resolver_log"]))

    def test_file_url_is_normalized_as_local_pdf_path(self) -> None:
        markdown = """## Paper with file URL

URL: file:///C:/papers/local-paper.pdf
"""

        resolved = resolve_paper_entries(markdown, try_online=True)

        self.assertEqual(resolved["entries"][0]["pdf_path"], "C:\\papers\\local-paper.pdf")
        self.assertEqual(resolved["entries"][0]["source"], "user+local-pdf")

    def test_arxiv_url_is_preserved_over_online_enrichment(self) -> None:
        markdown = """## Published paper with arXiv

URL: https://arxiv.org/abs/1803.01331
DOI: 10.1007/s00205-018-1296-3
"""

        resolved = resolve_paper_entries(markdown, try_online=True)

        self.assertEqual(resolved["entries"][0]["url"], "https://arxiv.org/abs/1803.01331")
        self.assertEqual(resolved["entries"][0]["pdf_url"], "https://arxiv.org/pdf/1803.01331.pdf")
        self.assertEqual(resolved["entries"][0]["source"], "user+repository")
        self.assertIn("arXiv", resolved["normalized_markdown"])

    def test_arxiv_title_match_is_preferred_before_openalex_doi(self) -> None:
        arxiv_response = Mock()
        arxiv_response.status_code = 200
        arxiv_response.text = """
        <feed>
          <entry>
            <id>https://arxiv.org/abs/1803.01331</id>
            <published>2018-03-04T00:00:00Z</published>
            <title>Asymptotics for the Fractional Allen-Cahn Equation and Stationary Nonlocal Minimal Surfaces</title>
            <author><name>Vincent Millot</name></author>
            <author><name>Yannick Sire</name></author>
            <author><name>Kelei Wang</name></author>
          </entry>
        </feed>
        """
        requests = Mock()
        requests.get.return_value = arxiv_response

        with patch.dict("sys.modules", {"requests": requests}):
            resolved = resolve_paper_entries(
                "## Asymptotics for the Fractional Allen-Cahn Equation and Stationary Nonlocal Minimal Surfaces",
                try_online=True,
            )

        self.assertEqual(resolved["entries"][0]["source"], "arxiv")
        self.assertEqual(resolved["entries"][0]["url"], "https://arxiv.org/abs/1803.01331")
        self.assertEqual(resolved["entries"][0]["pdf_url"], "https://arxiv.org/pdf/1803.01331.pdf")


if __name__ == "__main__":
    unittest.main()
