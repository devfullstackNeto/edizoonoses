"""Create printable, wholly synthetic zoonoses forms for the pilot OCR demonstration."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "apps" / "api" / "fixtures"
FONT = "C:/Windows/Fonts/arial.ttf"
BOLD = "C:/Windows/Fonts/arialbd.ttf"


def form(filename, title, subtitle, fields, observations, footer):
    image = Image.new("RGB", (1500, 1950), "#ffffff")
    draw = ImageDraw.Draw(image)
    navy, teal, grey = "#17365d", "#287a9a", "#576979"
    f_big = ImageFont.truetype(BOLD, 55)
    f_med = ImageFont.truetype(BOLD, 31)
    f_text = ImageFont.truetype(FONT, 30)
    f_small = ImageFont.truetype(FONT, 24)
    draw.rectangle((0, 0, 1500, 235), fill=navy)
    draw.rounded_rectangle((64, 54, 170, 160), radius=18, fill="white")
    draw.text((86, 82), "EDI", font=f_med, fill=navy)
    draw.text((200, 61), "EDI ZOONOSES", font=f_big, fill="white")
    draw.text((202, 134), "FORMULÁRIO SINTÉTICO PARA DEMONSTRAÇÃO", font=f_small, fill="#dceaf1")
    draw.text((65, 295), title, font=f_big, fill=navy)
    draw.text((67, 375), subtitle, font=f_text, fill=grey)
    draw.line((65, 435, 1435, 435), fill=teal, width=5)
    y = 485
    for label, value in fields:
        draw.text((70, y), label.upper(), font=f_small, fill=grey)
        draw.rounded_rectangle((65, y + 38, 1435, y + 111), radius=9, outline="#cbd9e1", width=2)
        draw.text((83, y + 52), value, font=f_text, fill="#17202a")
        y += 155
    draw.text((70, y + 10), "OBSERVAÇÕES", font=f_small, fill=grey)
    draw.rounded_rectangle((65, y + 48, 1435, y + 236), radius=9, outline="#cbd9e1", width=2)
    for line_no, line in enumerate(observations):
        draw.text((83, y + 65 + 48 * line_no), line, font=f_text, fill="#17202a")
    draw.line((65, 1780, 1435, 1780), fill="#cbd9e1", width=2)
    draw.text((70, 1810), footer, font=f_small, fill=grey)
    draw.text((70, 1860), "DADOS SINTÉTICOS / DEMONSTRAÇÃO — SEM VALIDADE INSTITUCIONAL", font=f_small, fill=navy)
    image.save(OUT / filename, optimize=True)
    return image


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    first = form("ficha_atendimento_sintetica.png", "Ficha de atendimento", "Vigilância em zoonoses · registro de ocorrência",
         [("Protocolo", "DEMO-OCR-PILOT-001"), ("Data", "29/09/2026"),
          ("Tipo", "Morcego"), ("Endereco", "Rua Exemplo, 120 - Centro Demo"),
          ("Territorio", "Centro Demo")],
         ["Animal observado em área externa. Equipe orientada para", "vistoria do local. Nenhuma pessoa real identificada."],
         "Registro preenchido exclusivamente para teste de OCR local.")
    form("vistoria_sintetica.png", "Formulário de vistoria", "Vigilância em zoonoses · inspeção de campo",
         [("Protocolo", "DEMO-OCR-PILOT-002"), ("Data", "28/09/2026"),
          ("Tipo", "Escorpião"), ("Endereco", "Avenida Modelo, 450 - Norte Demo"),
          ("Territorio", "Norte Demo")],
         ["Inspeção visual em imóvel sintético. Orientação sobre", "limpeza e vedação de frestas; retorno recomendado."],
         "Formulário demonstrativo sem dados pessoais ou epidemiológicos reais.")
    third = form("relatorio_visita_sintetico.png", "Relatório de visita", "Operação de campo · registro técnico demonstrativo",
         [("Protocolo", "DEMO-OCR-PILOT-003"), ("Data", "29/09/2026"),
          ("Tipo", "Roedor"), ("Endereco", "Rua Modelo, 300 - Sul Demo"),
          ("Responsavel", "Equipe Demo de Campo")],
         ["Vistoria sintética concluída. Pendência identificada para", "reavaliação de abrigo e acondicionamento de resíduos."],
         "Relatório sintético de visita para validação do OCR multipágina.")
    first.save(OUT / "dossie_visita_sintetico.pdf", save_all=True,
               append_images=[third], resolution=150)
