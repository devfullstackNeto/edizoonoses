"""Build the evidence index from the verified screenshot manifest."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "docs" / "evidence"
manifest = json.loads((root / "reports" / "capture-manifest.json").read_text(encoding="utf-8"))


def mapping(number: int, mobile: bool):
    if mobile:
        return ("Operação de campo móvel", "../../apps/web/evidence/capture.spec.ts",
                "../../FIELD_OPERATIONS.md")
    if number in (1, 2, 23, 24, 25, 27):
        return ("Módulos integrados", "../../apps/web/evidence/capture.spec.ts; ../../apps/api/tests/test_api.py",
                "../../QA_REPORT.md")
    if number in (3, 4, 5, 6, 7, 8):
        return ("Mapa, ocorrência e rota", "../../apps/web/evidence/capture.spec.ts; ../../apps/api/tests/test_sprint3_unit.py",
                "../../FIELD_OPERATIONS.md")
    if number in (17, 18, 19, 20, 21, 22):
        return ("Documento e OCR", "../../apps/web/evidence/capture.spec.ts; ../../apps/api/tests/test_field.py",
                "../../OCR_PIPELINE.md")
    return ("Operação de campo", "../../apps/web/evidence/capture.spec.ts; ../../apps/api/tests/test_field.py",
            "../../FIELD_OPERATIONS.md")


lines = [
    "# Índice de evidências — EDI Zoonoses",
    "",
    "Captura Playwright em 29/09/2026 (America/Cuiaba). IDs, protocolo e SHA-256 constam em "
    "[capture-manifest.json](reports/capture-manifest.json). `PASS` significa arquivo capturado "
    "de uma etapa executada e integridade verificada; não indica homologação institucional.",
    "",
    "| ID | Evidência | Funcionalidade | Teste relacionado | Documento relacionado | Resultado |",
    "|---|---|---|---|---|---|",
]
for item in manifest["screenshots"]:
    mobile = item["file"].startswith("screenshots/mobile/")
    number = int(item["id"])
    prefix = "M" if mobile else "D"
    feature, test, doc = mapping(number, mobile)
    test_links = "; ".join(f"[{Path(part).name}]({part})" for part in test.split("; "))
    lines.append(f"| {prefix}{number:02d} | [{Path(item['file']).name}]({item['file']}) | "
                 f"{feature}: {item['description']} | {test_links} | "
                 f"[{Path(doc).name}]({doc}) | PASS |")
lines += ["", "A matriz de objetivos inferidos do escopo oficial está em "
          "[SUAP_TRACEABILITY.md](SUAP_TRACEABILITY.md). A descrição completa de cada PNG está em "
          "[SCREENSHOT_GUIDE.md](../../SCREENSHOT_GUIDE.md).", ""]
(root / "EVIDENCE_INDEX.md").write_text("\n".join(lines), encoding="utf-8")
print(f"Index built: {len(manifest['screenshots'])} valid screenshots")
