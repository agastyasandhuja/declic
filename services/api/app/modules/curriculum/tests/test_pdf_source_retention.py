import io
from dataclasses import asdict, replace

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.modules.canvas.ingestion.resources import _file_text
from app.modules.curriculum.extract import _course_fingerprint
from app.modules.curriculum.sources import CanvasSourceResolver, ResolvedSource


def test_real_pdf_text_is_available_for_later_quiz_generation():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 40 700 Td (A stack removes the most recently added item first.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    assert "most recently added item first" in _file_text(".pdf", output.getvalue())


def resolver_with(source):
    resolver = CanvasSourceResolver(None, owner_user_id="owner")
    resolver._cache = [source]
    return resolver


def test_unchanged_inventory_restores_text_without_cross_course_sources():
    source = ResolvedSource(
        "lecture",
        "course",
        "Stacks.pdf",
        "file",
        "canvas",
        None,
        source_updated_at="2026-11-14T12:00:00Z",
    )
    resolver = resolver_with(source)
    original = _course_fingerprint(resolver, "course")
    cached = asdict(
        replace(
            source,
            text="Push adds an item. Pop removes the top item.",
            content_hash="downloaded-bytes-digest",
        )
    )
    resolver.restore_extracted_sources(
        "course",
        [
            {**cached, "source_id": "foreign"},
            {**cached, "course_id": "other"},
        ],
    )
    assert resolver.list_sources()[0].text is None
    resolver.restore_extracted_sources("course", [cached])
    assert resolver.sources_for_planning("course")[0].text == cached["text"]
    changed = resolver_with(replace(source, source_updated_at="2026-11-14T13:00:00Z"))
    assert _course_fingerprint(changed, "course") != original
