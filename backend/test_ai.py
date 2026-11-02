"""AI boundary tests: no real Ollama process, model, GPU or downloads needed."""

from io import BytesIO
import json
import os
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from pydantic import ValidationError

from backend.ai import AIError, AIProvider, AISettings, Interpretation, create_provider
from backend.ai.ollama import OllamaProvider


def extraction(**overrides):
    return {"activities": ["bowling", "dinner"], "people": 4,
            "budget_per_person": 60, "date": None, "location": None,
            "preferences": [], **overrides}


class AITests(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaProvider(AISettings())
        self.open = Mock()
        self.provider._opener.open = self.open

    def respond(self, body):
        self.open.return_value = BytesIO(json.dumps(body).encode())

    def valid_response(self, **overrides):
        self.respond({"done": True, "message": {"content": json.dumps(extraction(**overrides))}})

    def test_schema_request_and_validated_response(self):
        self.valid_response()
        result = self.provider.interpret("Four people want bowling and dinner under $60 each.")
        self.assertEqual(result.people, 4)
        self.assertEqual(result.budget_per_person, 60)
        request = self.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        expected_schema = Interpretation.model_json_schema()
        for field in ("start_time", "end_time"):
            expected_schema["properties"].pop(field)
        expected_schema["required"].extend(["budget_group", "currency", "travel_total_minutes",
                                            "travel_leg_minutes", "transport", "cost", "journey"])
        expected_schema['properties']['journey'] = {'$ref':'#/$defs/Journey'}
        expected_schema['$defs']['Journey']['properties'].pop('order_conflict')
        expected_schema['$defs']['Journey']['required'] = list(expected_schema['$defs']['Journey']['properties'])
        expected_schema['$defs']['RequestedStop']['required'] = list(expected_schema['$defs']['RequestedStop']['properties'])
        expected_schema['$defs']['Duration']['required'] = ['minutes','relation','source']
        expected_schema['$defs']['Deadline']['properties'].pop('minute')
        expected_schema['$defs']['Deadline']['required'] = ['source','relation']
        self.assertEqual(payload["format"], expected_schema)
        self.assertNotIn('"$defs"', payload["messages"][0]["content"])
        self.assertEqual(result, Interpretation(**extraction()))
        self.assertIsNone(result.travel_total_minutes)
        self.assertEqual(result.time_expressions, [])
        self.assertFalse(payload["stream"])
        self.assertFalse(payload["think"])
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertEqual(self.open.call_args.kwargs["timeout"], 60)

    def test_configuration_is_read_from_environment(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "ollama", "AI_MODEL": "other-model",
                                    "AI_BASE_URL": "http://localhost:1234/",
                                    "AI_TIMEOUT_SECONDS": "12.5"}, clear=True):
            provider = create_provider()
        provider._opener.open = self.open
        self.valid_response()
        provider.interpret("bowling")
        self.assertEqual(self.open.call_args.args[0].full_url, "http://localhost:1234/api/chat")
        self.assertEqual(json.loads(self.open.call_args.args[0].data)["model"], "other-model")
        self.assertEqual(self.open.call_args.kwargs["timeout"], 12.5)

    def test_provider_can_be_substituted(self):
        class FakeProvider:
            def interpret(self, text: str) -> Interpretation:
                return Interpretation(**extraction(activities=[text], people=None))

        def consumer(provider: AIProvider) -> Interpretation:
            return provider.interpret("coffee")

        self.assertEqual(consumer(FakeProvider()).activities, ["coffee"])
        self.valid_response(activities=["coffee"], people=None)
        self.assertEqual(consumer(self.provider), consumer(FakeProvider()))

    def test_unknowns_and_zero_are_preserved(self):
        self.valid_response(people=None, budget_per_person=0)
        result = self.provider.interpret("A group wants free bowling")
        self.assertIsNone(result.people)
        self.assertIsNone(result.location)
        self.assertIsNone(result.date)
        self.assertEqual(result.budget_per_person, 0)

    def test_timeout_and_stopped_service_errors(self):
        for error, message in [(TimeoutError(), "timed out"),
                               (URLError(TimeoutError()), "timed out"),
                               (URLError(ConnectionRefusedError()), "Cannot reach Ollama"),
                               (ConnectionResetError(), "connection failed")]:
            with self.subTest(error=error):
                self.open.side_effect = error
                with self.assertRaisesRegex(AIError, message):
                    self.provider.interpret("coffee")

    def test_missing_model_and_service_http_errors(self):
        for status, message in [(404, "model or API not found"), (500, "HTTP 500")]:
            self.open.side_effect = HTTPError("http://localhost", status, "private server detail", {}, None)
            with self.assertRaisesRegex(AIError, message) as caught:
                self.provider.interpret("coffee")
            self.assertNotIn("private server detail", str(caught.exception))

    def test_malformed_outer_json(self):
        self.open.return_value = BytesIO(b"not json")
        with self.assertRaisesRegex(AIError, "invalid response JSON"):
            self.provider.interpret("coffee")

    def test_incomplete_or_invalid_content_is_rejected(self):
        for body in [[], {}, {"done": False}, {"done": True, "message": None},
                     {"done": True, "message": {"content": "not json"}},
                     {"done": True, "message": {"content": {}}},
                     {"done": True, "done_reason": "length",
                      "message": {"content": json.dumps(extraction())}}]:
            with self.subTest(body=body):
                self.respond(body)
                with self.assertRaisesRegex(AIError, "invalid structured output"):
                    self.provider.interpret("coffee")

    def test_invalid_extraction_is_rejected(self):
        for fields in [{"people": True}, {"people": 0}, {"people": "4"},
                       {"budget_per_person": -1}, {"budget_per_person": float("inf")},
                       {"activities": [""]}, {"date": "2026-02-30"},
                       {"invented_field": "value"}]:
            with self.subTest(fields=fields):
                self.valid_response(**fields)
                with self.assertRaises(AIError):
                    self.provider.interpret("coffee")
        self.respond({"done": True, "message": {"content": "{}"}})
        with self.assertRaises(AIError):
            self.provider.interpret("coffee")

    def test_invalid_configuration_fails_before_network(self):
        with self.assertRaisesRegex(AIError, "Unsupported AI_PROVIDER"):
            create_provider(AISettings(provider="unknown"))
        for timeout in [0, -1, "nan", "inf", "bad"]:
            with self.subTest(timeout=timeout), self.assertRaises(ValidationError):
                AISettings(timeout_seconds=timeout)
        for url in ["file:///tmp/socket", "http://user:secret@localhost", "http://localhost?token=x"]:
            with self.subTest(url=url), self.assertRaises(AIError):
                create_provider(AISettings(base_url=url))

    def test_blank_request_does_not_call_service(self):
        with self.assertRaises(ValueError):
            self.provider.interpret("  ")
        self.open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
