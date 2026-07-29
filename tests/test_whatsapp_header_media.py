#!/usr/bin/env python3
"""
Regression tests for Meta WhatsApp template header media support
(IMAGE / VIDEO / DOCUMENT).

Root cause covered by these tests: customer_retarget_en_v1 has a mandatory
VIDEO header, but the app only ever recognised IMAGE headers, so it silently
omitted the header component when sending — Meta rejected the send with
"#132012 Parameter format does not match format in the created template".
"""

import unittest

from app.modules.message_automation.service import (
    _header_component_from_template,
    _template_has_media_header,
    _template_header_format,
)


IMAGE_TEMPLATE = {
    "components": [
        {"type": "HEADER", "format": "IMAGE"},
        {"type": "BODY", "text": "Hi {{1}}"},
    ]
}
VIDEO_TEMPLATE = {
    "components": [
        {
            "type": "HEADER",
            "format": "VIDEO",
            "example": {"header_handle": ["https://scontent.example/sample.mp4"]},
        },
        {"type": "BODY", "text": "Hi {{1}}, check this out!"},
    ]
}
DOCUMENT_TEMPLATE = {
    "components": [
        {"type": "HEADER", "format": "DOCUMENT"},
        {"type": "BODY", "text": "Hi {{1}}"},
    ]
}
TEXT_ONLY_TEMPLATE = {
    "components": [
        {"type": "HEADER", "format": "TEXT", "text": "Hello"},
        {"type": "BODY", "text": "Hi {{1}}"},
    ]
}
NO_HEADER_TEMPLATE = {"components": [{"type": "BODY", "text": "Hi {{1}}"}]}


class TemplateHeaderFormatTests(unittest.TestCase):
    def test_detects_each_media_format(self):
        self.assertEqual(_template_header_format(IMAGE_TEMPLATE), "image")
        self.assertEqual(_template_header_format(VIDEO_TEMPLATE), "video")
        self.assertEqual(_template_header_format(DOCUMENT_TEMPLATE), "document")

    def test_text_header_is_not_a_media_header(self):
        self.assertIsNone(_template_header_format(TEXT_ONLY_TEMPLATE))

    def test_no_header_component_returns_none(self):
        self.assertIsNone(_template_header_format(NO_HEADER_TEMPLATE))

    def test_has_media_header_stays_backward_compatible(self):
        self.assertTrue(_template_has_media_header(VIDEO_TEMPLATE))
        self.assertTrue(_template_has_media_header(IMAGE_TEMPLATE))
        self.assertTrue(_template_has_media_header(DOCUMENT_TEMPLATE))
        self.assertFalse(_template_has_media_header(TEXT_ONLY_TEMPLATE))
        self.assertFalse(_template_has_media_header(NO_HEADER_TEMPLATE))


class HeaderComponentBuildingTests(unittest.TestCase):
    def test_video_header_uses_video_parameter_type(self):
        component = _header_component_from_template(
            VIDEO_TEMPLATE, media_url="https://cdn.example/product.mp4"
        )
        self.assertEqual(
            component,
            {
                "type": "header",
                "parameters": [
                    {"type": "video", "video": {"link": "https://cdn.example/product.mp4"}}
                ],
            },
        )

    def test_image_header_uses_image_parameter_type(self):
        component = _header_component_from_template(
            IMAGE_TEMPLATE, media_url="https://cdn.example/pic.jpg"
        )
        self.assertEqual(
            component,
            {
                "type": "header",
                "parameters": [
                    {"type": "image", "image": {"link": "https://cdn.example/pic.jpg"}}
                ],
            },
        )

    def test_document_header_uses_document_parameter_type(self):
        component = _header_component_from_template(
            DOCUMENT_TEMPLATE, media_url="https://cdn.example/catalog.pdf"
        )
        self.assertEqual(
            component,
            {
                "type": "header",
                "parameters": [
                    {"type": "document", "document": {"link": "https://cdn.example/catalog.pdf"}}
                ],
            },
        )

    def test_falls_back_to_template_example_handle_when_no_url_given(self):
        component = _header_component_from_template(VIDEO_TEMPLATE, media_url=None)
        self.assertEqual(
            component["parameters"][0]["video"]["link"],
            "https://scontent.example/sample.mp4",
        )

    def test_returns_none_when_no_url_and_no_example_handle(self):
        component = _header_component_from_template(IMAGE_TEMPLATE, media_url=None)
        self.assertIsNone(component)

    def test_returns_none_for_template_without_media_header(self):
        component = _header_component_from_template(
            NO_HEADER_TEMPLATE, media_url="https://cdn.example/unused.jpg"
        )
        self.assertIsNone(component)


if __name__ == "__main__":
    unittest.main()
