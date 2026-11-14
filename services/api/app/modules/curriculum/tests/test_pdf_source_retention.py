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


def test_blank_pdf_does_not_publish_page_numbers_as_teaching_text():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = io.BytesIO()
    writer.write(output)
    assert _file_text(".pdf", output.getvalue()) is None


def test_file_selection_reserves_current_chapters_and_lectures_not_old_exams():
    from app.modules.curriculum.retrieval import teaching_file_ids

    sources = [
        ResolvedSource(
            "assignment",
            "course",
            "Ch. 17 Homework",
            "assignment",
            "canvas",
            "Ch. 17 Homework | Due: 2099-11-18T23:00:00Z",
        ),
        *[
            ResolvedSource(str(index), "course", title, "file", "canvas", None)
            for index, title in enumerate(
                [
                    "williams_finman_chap01.pptx",
                    "williams_finman_chap17.pptx",
                    "Lecture14.pdf",
                    "Lecture15.pdf",
                    "Midterm-Fall24.pdf",
                    "Lecture16-Solutions.pdf",
                    "syllabus.pdf",
                ]
            )
        ],
        ResolvedSource("foreign", "other", "Lecture90.pdf", "file", "canvas", None),
    ]

    class Resolver:
        def can_open_file(self, course_id, source_id):
            return True

    assert teaching_file_ids("course", Resolver(), sources) == ["1", "3", "2"]
    bare = replace(sources[2], source_id="bare-chapter", title="ch17.pdf")
    assert teaching_file_ids("course", Resolver(), [sources[0], bare]) == ["bare-chapter"]


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
