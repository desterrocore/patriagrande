#!/usr/bin/env python3
"""
Deriva os arquivos de marca que o site usa a partir dos PNGs oficiais.

Os cinco logotipos entregues são quadrados de 3000 px, opacos e com muita
respiração em volta do desenho — feitos para papel, não para uma barra de
navegação de 60 px. Este script produz o que a web precisa:

  * a assinatura horizontal recortada no limite da arte, com fundo transparente,
    nas duas polaridades (amarela sobre vermelho, vermelha sobre amarelo);
  * o favicon, derivado da cartografia e não do logotipo inteiro — o §97 da
    especificação v2 pede exatamente isso, porque o logotipo completo vira
    borrão a 16 px;
  * a imagem de compartilhamento social, 1200×630.

As cores dos arquivos oficiais foram medidas, não estimadas: #690404, #5D0404 e
#FFCC00 aparecem chapadas, sem gradiente e sem canal alfa útil (todos os PNGs
vêm com alfa 255 em cada pixel). É por isso que dá para recortar por cor.

    python3 tools/build-brand.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LOGOS = ROOT / "reference-content" / "Site Pátria Grande 2026" / "patria-logos"
OUT = ROOT / "assets" / "img" / "marca"

RED = (0x69, 0x04, 0x04)
DEEP = (0x5D, 0x04, 0x04)
YELLOW = (0xFF, 0xCC, 0x00)

# Distância euclidiana máxima, no cubo RGB, para considerar um pixel "de fundo".
# Generosa o bastante para pegar o antisserrilhado do desenho, apertada o
# bastante para não comer a arte.
TOL = 90


def strip_background(path: Path, bg: tuple[int, int, int]) -> Image.Image:
    """Torna o fundo transparente, preservando a suavidade das bordas.

    O alfa sai da distância de cada pixel até a cor de fundo, em vez de um
    limiar duro — assim a arte não fica serrilhada quando reduzida para 40 px
    de altura no cabeçalho.
    """
    im = Image.open(path).convert("RGBA")
    px = im.load()
    w, h = im.size
    br, bg_, bb = bg
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            dist = ((r - br) ** 2 + (g - bg_) ** 2 + (b - bb) ** 2) ** 0.5
            if dist <= TOL:
                px[x, y] = (r, g, b, 0)
            elif dist < TOL * 2.2:
                # Faixa de transição: alfa proporcional, para a borda ficar limpa.
                a = round(255 * (dist - TOL) / (TOL * 1.2))
                px[x, y] = (r, g, b, max(0, min(255, a)))
    return im


def tight(im: Image.Image, pad: int = 12) -> Image.Image:
    box = im.getbbox()
    if not box:
        raise SystemExit("imagem vazia após remover o fundo")
    l, t, r, b = box
    w, h = im.size
    return im.crop((max(0, l - pad), max(0, t - pad), min(w, r + pad), min(h, b + pad)))


def save_widths(im: Image.Image, stem: str, widths: list[int]) -> None:
    for width in widths:
        scaled = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        path = OUT / f"{stem}-{width}.png"
        scaled.save(path, optimize=True)
        print(f"  {path.relative_to(ROOT)}  {scaled.width}×{scaled.height}  "
              f"{path.stat().st_size / 1024:.0f} KB")


def split_lockup(im: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Separa a assinatura em símbolo (cartografia) e wordmark.

    O cabeçalho precisa de uma faixa horizontal baixa; a assinatura entregue é
    quase quadrada porque empilha o mapa alto à esquerda e três linhas de tipo à
    direita. Separando as duas peças, o header pode compor símbolo + wordmark
    lado a lado, na altura que a barra permite, sem distorcer nada.

    A separação é por componente conexo do canal alfa: o contorno do mapa é uma
    única figura muito mais alta do que qualquer letra.
    """
    import numpy as np

    a = np.asarray(im.getchannel("A")) > 40
    h, w = a.shape
    seen = np.zeros_like(a)
    label = np.zeros(a.shape, dtype=np.int32)
    boxes = []
    next_id = 0

    from collections import deque
    for sy in range(h):
        for sx in range(w):
            if not a[sy, sx] or seen[sy, sx]:
                continue
            next_id += 1
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            label[sy, sx] = next_id
            y0 = y1 = sy
            x0 = x1 = sx
            n = 0
            while q:
                y, x = q.popleft()
                n += 1
                y0, y1 = min(y0, y), max(y1, y)
                x0, x1 = min(x0, x), max(x1, x)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and a[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            label[ny, nx] = next_id
                            q.append((ny, nx))
            boxes.append((y1 - y0, (x0, y0, x1 + 1, y1 + 1), n, next_id))

    boxes.sort(key=lambda b: b[0], reverse=True)
    symbol_id = boxes[0][3]
    symbol_box = boxes[0][1]
    rest = [b for b in boxes[1:]]
    wx0 = min(b[1][0] for b in rest); wy0 = min(b[1][1] for b in rest)
    wx1 = max(b[1][2] for b in rest); wy1 = max(b[1][3] for b in rest)

    # A caixa do mapa cobre parte do wordmark — o contorno é alto e largo, e as
    # letras caem dentro dele. Recortar pela caixa traria as letras junto, então
    # o símbolo sai com tudo que não é dele apagado, e só depois é recortado.
    only_symbol = im.copy()
    keep = label == symbol_id
    alpha = np.asarray(only_symbol.getchannel("A")).copy()
    alpha[~keep] = 0
    only_symbol.putalpha(Image.fromarray(alpha))

    return tight(only_symbol.crop(symbol_box), pad=0), im.crop((wx0, wy0, wx1, wy1))


# Vocabulário gráfico secundário do logotipo completo (§6.3): sol, lua com o
# Cruzeiro do Sul, veleiro sobre a cidade, peixe sobre a água. Caixas medidas
# no arquivo de 3000 px. Servem de separador de seção e detalhe de rodapé — o
# §96 pede exatamente isso no lugar do filete genérico, e o §6.3 proíbe
# substituí-los por ícone de biblioteca.
MOTIFS = {
    "sol":     (215, 125, 895, 715),
    "lua":     (1430, 170, 1965, 870),
    "navio":   (325, 655, 815, 915),
    "peixe":   (1535, 1075, 1945, 1315),
}


def build_motifs(im: Image.Image, polarity: str) -> None:
    for name, box in MOTIFS.items():
        piece = tight(im.crop(box), pad=6)
        save_widths(piece, f"motivo-{name}-{polarity}", [240])


def map_path() -> str:
    """O `d` do path cartográfico, do SVG que tools/trace-brand.py escreveu."""
    svg = (OUT / "mapa-patria-grande.svg").read_text(encoding="utf-8")
    start = svg.index('d="') + 3
    return svg[start: svg.index('"', start)]


def render_svg(svg: str, path: Path, size: tuple[int, int]) -> None:
    """Rasteriza um SVG simples desenhando o path com Pillow.

    Não há rasterizador de SVG nesta máquina, mas os desenhos aqui são um único
    polígono de cor chapada — o que o ImageDraw.polygon resolve exatamente.
    """
    from PIL import ImageDraw

    d = map_path()
    pts = []
    for seg in d.replace("M", "").replace("Z", "").split("L"):
        seg = seg.strip()
        if not seg:
            continue
        x, y = seg.split(",")
        pts.append((float(x), float(y)))

    # viewBox do traçado
    vb_w = max(p[0] for p in pts)
    vb_h = max(p[1] for p in pts)

    bg, fg, margin = svg  # (cor de fundo, cor do desenho, margem relativa)
    W, H = size
    im = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(im)

    avail_w, avail_h = W * (1 - 2 * margin), H * (1 - 2 * margin)
    scale = min(avail_w / vb_w, avail_h / vb_h)
    ox = (W - vb_w * scale) / 2
    oy = (H - vb_h * scale) / 2
    draw.polygon([(ox + x * scale, oy + y * scale) for x, y in pts], fill=fg)

    im.save(path, optimize=True)
    print(f"  {path.relative_to(ROOT)}  {W}×{H}  {path.stat().st_size / 1024:.0f} KB")


def main() -> int:
    if not LOGOS.exists():
        print(f"pasta de logotipos ausente: {LOGOS}", file=sys.stderr)
        print("Os arquivos em assets/img/marca/ já são o resultado deste script.",
              file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    print("Assinatura amarela (para fundo vermelho):")
    yellow_mark = tight(strip_background(LOGOS / "LOGOTIPO_PÁTRIA_GRANDE_fundo_vermelho.png", RED))
    save_widths(yellow_mark, "assinatura-amarela", [1200, 600, 300])

    print("\nAssinatura vermelha (para fundo amarelo ou claro):")
    red_mark = tight(strip_background(LOGOS / "LOGOTIPO_PÁTRIA_GRANDE_fundo_amarelo.png", YELLOW))
    save_widths(red_mark, "assinatura-vermelha", [1200, 600, 300])

    print("\nSímbolo e wordmark separados, para o cabeçalho:")
    sym_y, word_y = split_lockup(yellow_mark)
    sym_r, word_r = split_lockup(red_mark)
    save_widths(sym_y, "simbolo-amarelo", [320, 160])
    save_widths(word_y, "wordmark-amarelo", [900, 450])
    save_widths(sym_r, "simbolo-vermelho", [320, 160])
    save_widths(word_r, "wordmark-vermelho", [900, 450])

    print("\nLogotipo completo (uso editorial, tamanho grande):")
    full = Image.open(LOGOS / "LOGOTIPO_PÁTRIA_GRANDE_com_todos_elementos.png").convert("RGB")
    for width in (1400, 800, 480):
        scaled = full.resize((width, width), Image.LANCZOS)
        for ext, kw in (("webp", dict(format="WEBP", quality=88, method=6)),
                        ("png", dict(optimize=True))):
            p = OUT / f"logotipo-completo-{width}.{ext}"
            scaled.save(p, **kw)
        print(f"  logotipo-completo-{width}.(webp|png)  "
              f"{(OUT / f'logotipo-completo-{width}.webp').stat().st_size / 1024:.0f} KB (webp)")

    print("\nMotivos secundários do logotipo:")
    full_rgba = strip_background(LOGOS / "LOGOTIPO_PÁTRIA_GRANDE_com_todos_elementos.png", DEEP)
    build_motifs(full_rgba, "amarelo")

    print("\nFavicon — cartografia, não o logotipo inteiro (§97):")
    for size in (512, 192, 180, 96, 48, 32, 16):
        render_svg((DEEP, YELLOW, 0.10), OUT / f"favicon-{size}.png", (size, size))
    ico = Image.open(OUT / "favicon-48.png")
    ico.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"  {(OUT / 'favicon.ico').relative_to(ROOT)}")

    print("\nImagem de compartilhamento social:")
    og = Image.new("RGB", (1200, 630), DEEP)
    mark = yellow_mark.resize(
        (860, round(yellow_mark.height * 860 / yellow_mark.width)), Image.LANCZOS
    )
    og.paste(mark, ((1200 - mark.width) // 2, (630 - mark.height) // 2), mark)
    og.save(OUT / "og-patria-grande.png", optimize=True)
    print(f"  {(OUT / 'og-patria-grande.png').relative_to(ROOT)}  1200×630  "
          f"{(OUT / 'og-patria-grande.png').stat().st_size / 1024:.0f} KB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
