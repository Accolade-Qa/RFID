from printer.tag_file import TagFile


def test_read_tags_returns_non_empty_lines_in_file_order(tmp_path):
    source = tmp_path / "scanned_tags.txt"
    source.write_text("\ufeff  A1B2C3  \n\nD4E5F6\n", encoding="utf-8")

    assert TagFile(source).read_tags() == ["A1B2C3", "D4E5F6"]


def test_read_tags_returns_empty_list_when_file_is_missing(tmp_path):
    assert TagFile(tmp_path / "missing.txt").read_tags() == []
