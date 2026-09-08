import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("build_docs", Path(__file__).parents[1] / "build_docs.py")
docs_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs_builder)


class DocumentBuildTests(unittest.TestCase):
    def test_build_delegates_once_per_topic_and_checks_local_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            docs = Path(temporary)
            topic = docs / "topic"
            topic.mkdir()
            (docs / "navigation.tex").write_text(r"\DocPDF{en}{topic/en.pdf}")
            entries = {"en": topic / "en.tex", "zh": topic / "zh.tex"}
            with patch.object(docs_builder, "DOCS", docs), patch.object(docs_builder.subprocess, "run") as run:
                with self.assertRaises(FileNotFoundError):
                    docs_builder.build(entries)
                run.assert_called_once_with(["make", "-C", str(topic), "pdf"], check=True)
                (topic / "en.pdf").touch()
                docs_builder.build(entries)
            self.assertFalse((docs / "build").exists())

    def test_registry_rejects_pdf_outside_topic(self):
        with tempfile.TemporaryDirectory() as temporary:
            docs = Path(temporary)
            (docs / "topic").mkdir()
            (docs / "topic/main.tex").touch()
            (docs / "topic/Makefile").touch()
            (docs / "navigation.tex").write_text("\\DocEntry{main}{topic/main.tex}\n\\DocPDF{main}{build/main.pdf}\n")
            for language in ("en", "zh"):
                (docs / f"index_{language}.tex").write_text(r"\Read{main}{Main}")
            with patch.object(docs_builder, "DOCS", docs):
                with self.assertRaisesRegex(ValueError, "beside its source"):
                    docs_builder.registry()


if __name__ == "__main__":
    unittest.main()
