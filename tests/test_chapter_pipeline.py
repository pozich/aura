from core.chapter_pipeline import _representative_excerpts, segment_text


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
