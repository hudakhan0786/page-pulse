# tests/test_parsing.py
# Unit tests for the pure parsing/validation logic in app.py.
# These don't touch the network at all — just the functions that turn
# raw input / raw HTML into the values the API reports.

from bs4 import BeautifulSoup

from app import count_images_missing_alt, count_words, parse_and_validate_url


# ---- parse_and_validate_url -----------------------------------------------

class TestParseAndValidateUrl:
    def test_valid_https_url_is_returned_unchanged(self):
        assert parse_and_validate_url("https://example.com") == "https://example.com"

    def test_bare_domain_gets_https_prefix_added(self):
        # UX nicety: "example.com" should be treated as "https://example.com"
        assert parse_and_validate_url("example.com") == "https://example.com"

    def test_http_scheme_is_accepted(self):
        assert parse_and_validate_url("http://example.com") == "http://example.com"

    def test_whitespace_is_stripped(self):
        assert parse_and_validate_url("   https://example.com   ") == "https://example.com"

    # --- failure cases ---

    def test_empty_string_is_invalid(self):
        assert parse_and_validate_url("") is None

    def test_none_is_invalid(self):
        assert parse_and_validate_url(None) is None

    def test_gibberish_with_no_dot_is_invalid(self):
        # "garbage" has no TLD-like structure — shouldn't be treated as a domain
        assert parse_and_validate_url("garbage") is None

    def test_non_http_scheme_is_rejected(self):
        assert parse_and_validate_url("ftp://example.com") is None
        assert parse_and_validate_url("javascript:alert(1)") is None


# ---- count_words ------------------------------------------------------------

class TestCountWords:
    def test_counts_visible_text_only(self):
        soup = BeautifulSoup("<html><body><p>one two three</p></body></html>", "html.parser")
        assert count_words(soup) == 3

    def test_excludes_script_and_style_content(self):
        html = """
            <html><body>
                <script>var shouldNotCount = "one two three four";</script>
                <style>.a { content: "five six"; }</style>
                <p>real word count</p>
            </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        assert count_words(soup) == 3  # only "real word count"

    def test_empty_body_returns_zero(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert count_words(soup) == 0


# ---- count_images_missing_alt ------------------------------------------------

class TestCountImagesMissingAlt:
    def test_image_with_alt_text_is_not_counted(self):
        soup = BeautifulSoup('<img src="a.png" alt="a cat">', "html.parser")
        assert count_images_missing_alt(soup) == 0

    def test_image_with_no_alt_attribute_is_counted(self):
        soup = BeautifulSoup('<img src="a.png">', "html.parser")
        assert count_images_missing_alt(soup) == 1

    def test_image_with_empty_alt_is_counted(self):
        # alt="" is technically present but conveys nothing — still a miss
        soup = BeautifulSoup('<img src="a.png" alt="">', "html.parser")
        assert count_images_missing_alt(soup) == 1

    def test_mixed_images_counts_only_the_missing_ones(self):
        html = '<img src="a.png" alt="ok"><img src="b.png"><img src="c.png" alt="  ">'
        soup = BeautifulSoup(html, "html.parser")
        assert count_images_missing_alt(soup) == 2
