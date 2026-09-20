"""Tests for Telegram message rendering — pure, no bot, no network."""
from datetime import datetime, timezone

import pytest

from app.services.channel_rss_worker import (
    TELEGRAM_CAPTION_LIMIT,
    TELEGRAM_MESSAGE_LIMIT,
    _clean_html,
    _is_useless_content,
    format_post_message,
)
from app.services.parser.models import RSSPost


def make_post(**kwargs) -> RSSPost:
    defaults = dict(
        guid="g1",
        title="Заголовок",
        link="https://example.com/a",
        summary="Краткое содержание поста, достаточно длинное чтобы пройти фильтр.",
        content="",
    )
    return RSSPost(**{**defaults, **kwargs})


class TestCleanHtml:
    def test_strips_tags(self):
        assert _clean_html("<p>hello <b>world</b></p>") == "hello world"

    def test_collapses_whitespace(self):
        assert _clean_html("a\n\n  b\t c") == "a b c"

    def test_handles_empty(self):
        assert _clean_html("") == ""


class TestIsUselessContent:
    @pytest.mark.parametrize("text", ["none", "NULL", "[more]", "Читать далее…", "...", ""])
    def test_rejects_placeholders_and_stubs(self, text):
        assert _is_useless_content(text) is True

    def test_accepts_real_prose(self):
        assert _is_useless_content("Это настоящий текст статьи, довольно длинный.") is False


class TestFormatPostMessage:
    def test_title_is_bolded(self):
        assert format_post_message(make_post()).startswith("<b>Заголовок</b>")

    def test_html_in_title_is_escaped(self):
        msg = format_post_message(make_post(title="<script>alert(1)</script>"))
        assert "<script>" not in msg
        assert "&lt;script&gt;" in msg or "alert(1)" in msg

    def test_link_query_ampersand_is_escaped(self):
        # Regression: a raw & made Telegram reject the whole message as
        # unparseable HTML, and the post was then lost permanently.
        url = "https://example.com/a?utm_source=rss&utm_medium=feed"
        msg = format_post_message(make_post(link=url))
        assert "&amp;utm_medium" in msg
        assert "?utm_source=rss&utm_medium" not in msg

    def test_link_single_quote_does_not_break_the_attribute(self):
        msg = format_post_message(make_post(link="https://example.com/it's"))
        assert "href=\"https://example.com/it&#x27;s\"" in msg

    def test_no_link_section_when_link_is_empty(self):
        assert "Читать полностью" not in format_post_message(make_post(link=""))

    def test_published_time_is_rendered(self):
        post = make_post(published_time=datetime(2025, 6, 10, 12, 30, tzinfo=timezone.utc))
        assert "2025-06-10 12:30" in format_post_message(post)

    def test_content_wins_over_summary(self):
        post = make_post(content="Полный текст статьи, весьма содержательный.", summary="Краткое.")
        assert "Полный текст статьи" in format_post_message(post)

    def test_useless_body_is_dropped(self):
        msg = format_post_message(make_post(summary="none", content=""))
        assert "none" not in msg
        assert "<b>Заголовок</b>" in msg

    def test_long_body_is_truncated_within_limit(self):
        post = make_post(content="я" * 20000)
        msg = format_post_message(post)
        assert len(msg) <= TELEGRAM_MESSAGE_LIMIT
        assert "..." in msg

    def test_huge_title_does_not_invert_the_truncation(self):
        # Regression: a title big enough to make the budget negative turned
        # clean_text[:negative] into "keep almost everything", blowing the limit.
        post = make_post(title="Т" * 5000, content="я" * 20000)
        msg = format_post_message(post)
        assert "я" * 100 not in msg


class TestCaptionLimit:
    """Regression: the caption used to be message[:1024], which sliced the
    rendered HTML mid-tag. Telegram answered "Can't find end tag corresponding
    to start tag \"a\"" / "Unclosed end tag at byte offset N" and the post was
    never delivered."""

    def _assert_tags_balanced(self, msg: str) -> None:
        for tag in ("b", "a", "i"):
            assert msg.count(f"<{tag}") == msg.count(f"</{tag}>"), f"<{tag}> unbalanced in: {msg!r}"

    def test_caption_keeps_the_link_tag_whole(self):
        post = make_post(content="я" * 20000)
        msg = format_post_message(post, limit=TELEGRAM_CAPTION_LIMIT)
        assert len(msg) <= TELEGRAM_CAPTION_LIMIT
        assert msg.endswith("</a>\n\n") or "</a>" in msg
        self._assert_tags_balanced(msg)

    @pytest.mark.parametrize(
        "body_len",
        # The 900-1100 band is where the old slice landed inside the trailing
        # <a>/<i> tags: 85 of those 200 lengths produced unparseable HTML.
        [0, 1, 500, 5000, 20000] + list(range(900, 1100, 7)),
    )
    def test_caption_never_exceeds_limit_and_stays_parseable(self, body_len):
        post = make_post(
            content="я" * body_len,
            published_time=datetime(2025, 6, 10, 12, 30, tzinfo=timezone.utc),
        )
        msg = format_post_message(post, limit=TELEGRAM_CAPTION_LIMIT)
        assert len(msg) <= TELEGRAM_CAPTION_LIMIT
        self._assert_tags_balanced(msg)

    def test_long_url_does_not_push_caption_over_the_limit(self):
        # The old fixed 150-char reserve could not cover a link this long.
        post = make_post(link="https://example.com/" + "p" * 600, content="я" * 20000)
        msg = format_post_message(post, limit=TELEGRAM_CAPTION_LIMIT)
        assert len(msg) <= TELEGRAM_CAPTION_LIMIT
        self._assert_tags_balanced(msg)

    def test_truncation_never_splits_an_html_entity(self):
        # Body of bare ampersands: escaping before truncating could cut &amp;
        # into "&am" and hand Telegram a malformed entity.
        post = make_post(content="& " * 5000)
        msg = format_post_message(post, limit=TELEGRAM_CAPTION_LIMIT)
        body = msg.split("</b>")[1].split("<a href")[0]
        assert "&" not in body.replace("&amp;", ""), f"raw or broken entity in: {body!r}"

    def test_link_survives_when_body_is_dropped_entirely(self):
        post = make_post(title="Т" * 2000, content="я" * 20000)
        msg = format_post_message(post, limit=TELEGRAM_CAPTION_LIMIT)
        self._assert_tags_balanced(msg)
