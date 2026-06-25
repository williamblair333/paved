from paved.llm._base import LLMResult, PROMPTS, LLMProvider


def test_llm_result_defaults():
    r = LLMResult(mode="clean", ok=True, text="hello")
    assert r.warning == ""


def test_prompts_has_clean_and_summary():
    assert "clean" in PROMPTS
    assert "summary" in PROMPTS
    assert "{text}" in PROMPTS["clean"]
    assert "{text}" in PROMPTS["summary"]


def test_provider_helpers():
    class DummyProvider(LLMProvider):
        name = "dummy"
        def is_available(self): return True
        def process(self, text, mode, model=None, timeout=600.0):
            return self._ok(mode, text)

    p = DummyProvider()
    r = p._ok("clean", "out")
    assert r.ok is True and r.text == "out"
    r2 = p._fail("clean", "orig", "oops")
    assert r2.ok is False and r2.text == "orig" and r2.warning == "oops"
