"""Optional smoke test for an OpenAI-compatible endpoint; never prints credentials."""

from types import SimpleNamespace
from .main import OpenAICompatibleProvider
from .settings import settings


def main():
    if not all((settings.ai_base_url, settings.ai_api_key, settings.ai_model)):
        raise SystemExit(
            "Configure AI_BASE_URL, AI_API_KEY e AI_MODEL para o smoke opcional"
        )
    item = SimpleNamespace(
        id="smoke",
        title="Teste sintético",
        tags=["teste"],
        body="Este é um teste sintético do EDI Zoonoses.",
        source="smoke-local",
        version=1,
    )
    answer = OpenAICompatibleProvider().answer("Explique o teste sintético", [item])
    if answer["response_type"] != "knowledge_ai" or not answer["source_refs"]:
        raise SystemExit("Provider indisponível; fallback local permaneceu ativo")
    print("Provider externo respondeu com fonte local controlada")


if __name__ == "__main__":
    main()
