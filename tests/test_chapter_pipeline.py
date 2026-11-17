import base64
import zipfile

from core.chapter_pipeline import _parse_fb2, _parse_pdf, _representative_excerpts, segment_text

FB2_XML = """<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
  <description>
    <title-info>
      <author>
        <first-name>Чарльз</first-name>
        <last-name>Дарвин</last-name>
      </author>
      <book-title>Происхождение видов</book-title>
      <coverpage><image l:href="#cover.jpg"/></coverpage>
    </title-info>
  </description>
  <body>
    <section>
      <title><p>Глава первая</p></title>
      <p>Текст первой главы про изменчивость.</p>
    </section>
    <section>
      <title><p>Глава вторая</p></title>
      <p>Текст второй главы про отбор.</p>
    </section>
  </body>
  <binary id="cover.jpg" content-type="image/jpeg">%s</binary>
</FictionBook>
""" % base64.b64encode(b"fake-jpeg-bytes").decode()

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 300 144] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 40 >>
stream
BT /F1 18 Tf 10 100 Td (Test page content) Tj ET
endstream
endobj
trailer
<< /Size 6 /Root 1 0 R >>
%%EOF
"""


def test_parse_fb2_extracts_metadata_and_chapters(tmp_path, monkeypatch):
    import core.chapter_pipeline as cp

    monkeypatch.setattr(cp, "COVERS_DIR", tmp_path / "covers")
    fb2_path = tmp_path / "book.fb2"
    fb2_path.write_text(FB2_XML, encoding="utf-8")

    title, author, cover_path, chapters = _parse_fb2(fb2_path, book_id=1)

    assert title == "Происхождение видов"
    assert author == "Чарльз Дарвин"
    assert [c[0] for c in chapters] == ["Глава первая", "Глава вторая"]
    assert "изменчивость" in chapters[0][1]
    assert cover_path is not None and (tmp_path / "covers" / "1.jpg").exists()


def test_parse_fb2_zip_reads_inner_fb2(tmp_path, monkeypatch):
    import core.chapter_pipeline as cp

    monkeypatch.setattr(cp, "COVERS_DIR", tmp_path / "covers")
    fb2_path = tmp_path / "book.fb2"
    fb2_path.write_text(FB2_XML, encoding="utf-8")
    zip_path = tmp_path / "book.fb2.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.write(fb2_path, "book.fb2")

    title, _author, _cover, chapters = _parse_fb2(zip_path, book_id=1)

    assert title == "Происхождение видов"
    assert len(chapters) == 2


def test_parse_pdf_extracts_pages_as_chapters(tmp_path, monkeypatch):
    import core.chapter_pipeline as cp

    monkeypatch.setattr(cp, "COVERS_DIR", tmp_path / "covers")
    pdf_path = tmp_path / "book.pdf"
    pdf_path.write_bytes(MINIMAL_PDF)

    _title, _author, cover_path, chapters = _parse_pdf(pdf_path, book_id=1)

    assert chapters == [("Страница 1", "Test page content")]
    assert cover_path is not None and (tmp_path / "covers" / "1.png").exists()


def test_segment_text_keeps_paragraphs_whole():
    paragraphs = ["A" * 100, "B" * 2950, "C" * 100]
    full_text = "\n\n".join(paragraphs)

    segments = segment_text(full_text, chunk_size=3000)

    assert "".join(segments).replace("\n\n", "") == "".join(paragraphs)
    for segment in segments:
        assert len(segment) <= 3000 or "\n\n" not in segment


def test_segment_text_single_short_text_is_one_segment():
    assert segment_text("короткий текст", chunk_size=3000) == ["короткий текст"]


def test_segment_text_empty_text_gives_no_segments():
    assert segment_text("", chunk_size=3000) == []


def test_representative_excerpts_returns_all_when_fewer_than_count():
    segments = ["a", "b", "c"]
    assert _representative_excerpts(segments, count=5) == segments


def test_representative_excerpts_spreads_across_book():
    segments = [str(i) for i in range(10)]
    excerpts = _representative_excerpts(segments, count=5)

    assert excerpts[0] == "0"
    assert excerpts[-1] == "9"
    assert len(excerpts) == 5
