"""Frontend accessibility and cross-browser compatibility verification.

Parses index.html and validates WCAG 2.1 AA compliance markers,
semantic HTML structure, ARIA attributes, and cross-browser CSS patterns.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

INDEX_HTML = Path(__file__).resolve().parent.parent / "index.html"


class AccessibilityParser(HTMLParser):
    """Collects accessibility-relevant data from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.elements: list[dict[str, object]] = []
        self.headings: list[tuple[str, dict[str, str]]] = []
        self.aria_attrs: list[tuple[str, str, str]] = []  # (tag, attr, value)
        self.roles: list[tuple[str, str]] = []  # (tag, role)
        self.links: list[dict[str, str]] = []
        self.forms: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.inputs: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.landmarks: list[tuple[str, dict[str, str]]] = []
        self.has_lang = False
        self.has_viewport = False
        self.has_doctype = False
        self.has_skip_link = False
        self.style_content = ""
        self._in_style = False
        self._raw = ""

    def feed(self, data: str) -> None:
        self._raw = data
        if data.strip().startswith("<!DOCTYPE"):
            self.has_doctype = True
        super().feed(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v or "" for k, v in attrs}
        self.elements.append({"tag": tag, "attrs": attr_dict})

        if tag == "html" and "lang" in attr_dict:
            self.has_lang = True

        if tag == "meta" and attr_dict.get("name") == "viewport":
            self.has_viewport = True

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append((tag, attr_dict))

        for key, val in attr_dict.items():
            if key.startswith("aria-"):
                self.aria_attrs.append((tag, key, val or ""))
            if key == "role":
                self.roles.append((tag, val or ""))

        if tag == "a":
            self.links.append(attr_dict)
            if (
                "skip" in attr_dict.get("class", "").lower()
                and attr_dict.get("href", "").startswith("#")
            ):
                self.has_skip_link = True

        if tag == "form":
            self.forms.append(attr_dict)

        if tag == "img":
            self.images.append(attr_dict)

        if tag == "input":
            self.inputs.append(attr_dict)

        if tag == "button":
            self.buttons.append(attr_dict)

        if tag in ("header", "main", "nav", "footer", "aside"):
            self.landmarks.append((tag, attr_dict))

        if tag == "style":
            self._in_style = True
            self.style_content = ""

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.style_content += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False


@pytest.fixture(scope="module")
def html_content():
    return INDEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def parsed(html_content):
    parser = AccessibilityParser()
    parser.feed(html_content)
    return parser


class TestDocumentStructure:
    def test_has_doctype(self, parsed):
        assert parsed.has_doctype, "Missing <!DOCTYPE html>"

    def test_has_lang_attribute(self, parsed):
        assert parsed.has_lang, '<html> must have a lang attribute'

    def test_has_viewport_meta(self, parsed):
        assert parsed.has_viewport, "Missing viewport meta tag"

    def test_has_title(self, parsed):
        title_found = any(e["tag"] == "title" for e in parsed.elements)
        assert title_found, "Missing <title> element"


class TestSkipNavigation:
    def test_skip_link_exists(self, parsed):
        assert parsed.has_skip_link, "Missing skip-to-content link"

    def test_skip_link_target_exists(self, html_content):
        assert 'id="main-content"' in html_content, "Skip link target #main-content not found"


class TestHeadingHierarchy:
    def test_has_h1(self, parsed):
        h1_tags = [h for h in parsed.headings if h[0] == "h1"]
        assert len(h1_tags) >= 1, "Page must have at least one <h1> element"

    def test_no_heading_level_skip(self, parsed):
        levels = [int(h[0][1]) for h in parsed.headings]
        for i in range(1, len(levels)):
            gap = levels[i] - levels[i - 1]
            assert gap <= 1, (
                f"Heading level skip: {parsed.headings[i - 1][0]} → {parsed.headings[i][0]}"
            )


class TestLandmarks:
    def test_has_header(self, parsed):
        assert any(t == "header" for t, _ in parsed.landmarks), "Missing <header> landmark"

    def test_has_main(self, parsed):
        assert any(t == "main" for t, _ in parsed.landmarks), "Missing <main> landmark"

    def test_has_footer(self, parsed):
        assert any(t == "footer" for t, _ in parsed.landmarks), "Missing <footer> landmark"


class TestSearchForm:
    def test_search_form_has_role(self, parsed):
        search_forms = [f for f in parsed.forms if f.get("role") == "search"]
        assert len(search_forms) >= 1, "Search form must have role='search'"

    def test_search_input_has_label(self, parsed):
        search_inputs = [i for i in parsed.inputs if i.get("type") == "search"]
        assert len(search_inputs) >= 1, "Expected a search input"
        inp = search_inputs[0]
        assert "aria-label" in inp or "id" in inp, "Search input needs aria-label or associated label"

    def test_search_input_has_aria_autocomplete(self, parsed):
        search_inputs = [i for i in parsed.inputs if i.get("type") == "search"]
        assert len(search_inputs) >= 1
        assert search_inputs[0].get("aria-autocomplete") == "list"

    def test_search_input_has_aria_expanded(self, parsed):
        search_inputs = [i for i in parsed.inputs if i.get("type") == "search"]
        assert len(search_inputs) >= 1
        assert "aria-expanded" in search_inputs[0], "Search input needs aria-expanded for combobox pattern"

    def test_search_input_has_aria_controls(self, parsed):
        search_inputs = [i for i in parsed.inputs if i.get("type") == "search"]
        assert len(search_inputs) >= 1
        controls_id = search_inputs[0].get("aria-controls")
        assert controls_id, "Search input needs aria-controls pointing to dropdown"


class TestDropdown:
    def test_dropdown_has_listbox_role(self, html_content):
        assert 'role="listbox"' in html_content, "Dropdown must have role='listbox'"

    def test_dropdown_has_label(self, html_content):
        assert 'aria-label="City suggestions"' in html_content


class TestUnitToggle:
    def test_radiogroup_role(self, html_content):
        assert 'role="radiogroup"' in html_content, "Unit toggle must have role='radiogroup'"

    def test_radio_buttons_have_aria_checked(self, parsed):
        radio_buttons = [
            b for b in parsed.buttons if any(
                (t, k, v) for t, k, v in parsed.aria_attrs
                if k == "aria-checked"
            )
        ]
        assert len(radio_buttons) >= 2, "Radio buttons need aria-checked"

    def test_radiogroup_has_label(self, html_content):
        assert 'aria-label="Temperature unit"' in html_content


class TestAriaLiveRegions:
    def test_loading_state_has_aria_live(self, html_content):
        assert 'id="loading-state"' in html_content
        loading_match = re.search(r'id="loading-state"[^>]*aria-live', html_content)
        assert loading_match, "Loading state needs aria-live"

    def test_error_state_has_aria_live_assertive(self, html_content):
        error_match = re.search(r'id="error-state"[^>]*aria-live="assertive"', html_content)
        assert error_match, "Error state needs aria-live='assertive'"

    def test_weather_state_has_aria_live(self, html_content):
        weather_match = re.search(r'id="weather-state"[^>]*aria-live', html_content)
        assert weather_match, "Weather display needs aria-live"


class TestExternalLinks:
    def test_external_links_have_noopener(self, parsed):
        external = [link for link in parsed.links if link.get("target") == "_blank"]
        for link in external:
            rel = link.get("rel", "")
            assert "noopener" in rel, f"External link missing rel='noopener': {link.get('href')}"

    def test_external_links_have_new_tab_indication(self, html_content):
        assert "opens in new tab" in html_content, (
            "External links should indicate they open in a new tab for screen readers"
        )


class TestCrossBrowserCSS:
    def test_webkit_appearance_reset(self, parsed):
        assert "-webkit-appearance" in parsed.style_content, (
            "Search input should reset -webkit-appearance for Safari"
        )

    def test_webkit_search_decorations_removed(self, parsed):
        assert "webkit-search-cancel-button" in parsed.style_content, (
            "Safari search input cancel button should be removed"
        )

    def test_focus_visible_styles(self, parsed):
        assert "focus-visible" in parsed.style_content, (
            "Interactive elements need :focus-visible styles"
        )

    def test_prefers_reduced_motion(self, parsed):
        assert "prefers-reduced-motion" in parsed.style_content, (
            "Animations should respect prefers-reduced-motion"
        )

    def test_system_font_stack(self, parsed):
        assert "-apple-system" in parsed.style_content, "Should use system font stack"
        assert "BlinkMacSystemFont" in parsed.style_content, "Should include BlinkMacSystemFont"

    def test_css_custom_properties(self, parsed):
        assert "--bg-primary" in parsed.style_content, "Should use CSS custom properties"


class TestTouchTargets:
    def test_min_height_on_buttons(self, parsed):
        assert "min-height: 44px" in parsed.style_content, (
            "Interactive elements should have minimum 44px touch target"
        )


class TestResponsiveDesign:
    def test_has_mobile_breakpoint(self, parsed):
        assert "max-width: 640px" in parsed.style_content, "Missing mobile breakpoint"

    def test_has_small_mobile_breakpoint(self, parsed):
        assert "max-width: 400px" in parsed.style_content, "Missing small mobile breakpoint"


class TestXSSProtection:
    def test_escape_html_function_exists(self, html_content):
        assert "function escapeHtml" in html_content, "Must have XSS escaping function"

    def test_escape_html_handles_all_entities(self, html_content):
        for entity in ["&amp;", "&lt;", "&gt;", "&quot;", "&#39;"]:
            assert entity in html_content, f"escapeHtml must handle {entity}"


class TestRecentSearchAccessibility:
    def test_recent_section_has_role(self, html_content):
        match = re.search(r'id="recent-section"[^>]*role="region"', html_content)
        assert match, 'Recent section needs role="region" to pair with aria-label'


class TestScreenReaderUtility:
    def test_sr_only_class_exists(self, parsed):
        assert "sr-only" in parsed.style_content, "Missing .sr-only utility class"

    def test_decorative_icons_hidden(self, html_content):
        assert html_content.count('aria-hidden="true"') >= 3, (
            "Decorative icons should have aria-hidden='true'"
        )
