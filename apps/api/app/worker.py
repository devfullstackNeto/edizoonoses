"""Redis/RQ OCR worker: original remains in MinIO; all pages use local Tesseract."""

import io
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps, ImageStat
import pytesseract
from .core import SessionLocal, s3
from .models import AuditEvent, Document, OCRJob, OccurrenceEvent
from .settings import settings

LABELS = {
    "protocolo": "protocolo",
    "data": "data",
    "tipo": "tipo",
    "endereco": "endereco",
    "endereço": "endereco",
    "territorio": "territorio",
    "território": "territorio",
    "bairro": "bairro",
    "observacoes": "observacoes",
    "observações": "observacoes",
    "responsavel": "responsavel",
    "responsável": "responsavel",
    "telefone": "telefone",
    "documento": "documento",
}


class OCRProvider:
    def extract(self, image: Image.Image):
        raise NotImplementedError


class TesseractProvider(OCRProvider):
    def extract(self, image: Image.Image):
        text = pytesseract.image_to_string(image, lang="por+eng", config="--psm 6")
        data = pytesseract.image_to_data(
            image, lang="por+eng", config="--psm 6", output_type=pytesseract.Output.DICT
        )
        confidence = [float(v) for v in data["conf"] if float(v) >= 0]
        return text, round(sum(confidence) / len(confidence), 1) if confidence else 0.0


def preprocess(image: Image.Image):
    steps = ["exif_transpose", "grayscale", "autocontrast", "median_filter"]
    image = ImageOps.exif_transpose(image).convert("RGB")
    try:
        osd = pytesseract.image_to_osd(image, lang="eng")
        match = re.search(r"Rotate:\s*(90|180|270)", osd)
        if match:
            image = image.rotate(int(match.group(1)), expand=True)
            steps.append("orientation")
    except pytesseract.TesseractError:
        pass
    image = ImageOps.autocontrast(ImageOps.grayscale(image))
    image = image.filter(ImageFilter.MedianFilter(size=3))
    if ImageStat.Stat(image).stddev[0] < 35:
        image = image.point(lambda pixel: 255 if pixel >= 160 else 0)
        steps.append("threshold_low_contrast")
    if image.width < 1200:
        ratio = 1200 / image.width
        image = image.resize(
            (1200, int(image.height * ratio)), Image.Resampling.LANCZOS
        )
        steps.append("resize")
    return image, steps


def parse_fields(text: str):
    """Parse labelled synthetic forms, including labels followed by a value on the next line."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields = {}
    for index, line in enumerate(lines):
        match = re.match(r"^([A-Za-zÀ-ÿ ]{3,24})\s*[:\-]\s*(.*)$", line)
        label, value = (match.group(1), match.group(2)) if match else (line, "")
        name = LABELS.get(label.strip().lower())
        if not name:
            continue
        value = value.strip(" :-")
        if not value and index + 1 < len(lines):
            value = lines[index + 1]
        if value and value.lower() not in LABELS:
            fields[name] = value[:500]
    return fields


def pdf_images(data: bytes, folder: str):
    source = Path(folder) / "input.pdf"
    source.write_bytes(data)
    info = subprocess.run(
        ["pdfinfo", str(source)], capture_output=True, text=True, check=True, timeout=20
    ).stdout
    match = re.search(r"^Pages:\s*(\d+)", info, re.M)
    count = int(match.group(1)) if match else 0
    if count < 1 or count > 10:
        raise ValueError("PDF deve conter de 1 a 10 páginas")
    prefix = str(Path(folder) / "page")
    subprocess.run(
        [
            "pdftoppm",
            "-r",
            "180",
            "-f",
            "1",
            "-l",
            str(count),
            "-png",
            str(source),
            prefix,
        ],
        check=True,
        timeout=180,
    )
    paths = sorted(Path(folder).glob("page-*.png"))
    if len(paths) != count:
        raise ValueError("Falha ao converter todas as páginas do PDF")
    return [Image.open(path).copy() for path in paths]


def process_ocr(job_id: str):
    with SessionLocal() as db:
        job = db.get(OCRJob, job_id)
        if not job:
            return
        job.status = "processing"
        db.commit()
        try:
            doc = db.get(Document, job.document_id)
            data = (
                s3()
                .get_object(Bucket=settings.s3_bucket, Key=doc.object_key)["Body"]
                .read()
            )
            with tempfile.TemporaryDirectory() as folder:
                images = (
                    pdf_images(data, folder)
                    if doc.mime == "application/pdf"
                    else [Image.open(io.BytesIO(data)).copy()]
                )
                pages, merged, details = [], {}, []
                for page_number, original in enumerate(images, 1):
                    enhanced, steps = preprocess(original)
                    raw, confidence = TesseractProvider().extract(enhanced)
                    detected = parse_fields(raw)
                    pages.append(
                        {
                            "page": page_number,
                            "raw_text": raw,
                            "confidence": confidence,
                            "preprocessing": steps,
                            "fields": detected,
                        }
                    )
                    for name, value in detected.items():
                        if name not in merged:
                            merged[name] = value
                            details.append(
                                {
                                    "name": name,
                                    "value": value,
                                    "confidence": confidence,
                                    "page": page_number,
                                    "reviewed_value": None,
                                    "status": "detected",
                                }
                            )
                job.pages = pages
                job.field_details = details
                job.raw_text = "\n\n".join(
                    f"--- Página {p['page']} ---\n{p['raw_text']}" for p in pages
                )
                job.fields = merged
                job.confidence = round(
                    sum(p["confidence"] for p in pages) / len(pages), 1
                )
                job.status = "needs_review"
                if doc.occurrence_id:
                    db.add(
                        OccurrenceEvent(
                            occurrence_id=doc.occurrence_id,
                            action="ocr_extracted",
                            payload={"job_id": job.id, "pages": len(pages)},
                        )
                    )
                db.add(
                    AuditEvent(
                        action="ocr_extracted",
                        entity="ocr_job",
                        entity_id=job.id,
                        details={"pages": len(pages), "provider": "tesseract"},
                    )
                )
        except Exception as exc:
            job.status = "failed"
            job.raw_text = str(exc)[:300]
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
