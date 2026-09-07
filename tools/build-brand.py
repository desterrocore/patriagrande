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
  * a imagem de compartilhamento social, 1200×630;
  * as placas de projeto — a marca de cada festival já composta sobre o fundo
    que ela pede, em 3:2, prontas para o card. A do Cineclube Pátria Grande vem
    de um PDF vetorial do CorelDRAW e precisa do `pdftoppm` (poppler-utils).

As cores dos arquivos oficiais foram medidas, não estimadas: #690404, #5D0404 e
#FFCC00 aparecem chapadas, sem gradiente e sem canal alfa útil (todos os PNGs
vêm com alfa 255 em cada pixel). É por isso que dá para recortar por cor.

    python3 tools/build-brand.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
LOGOS = ROOT / "reference-content" / "Site Pátria Grande 2026" / "patria-logos"
OUT = ROOT / "assets" / "img" / "marca"
OUT_PROJETOS = ROOT / "assets" / "img" / "projetos"

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


# A marca do cineclube é um disco: arte circular centrada num quadrado branco.
# Recortar por cor não serve aqui — "CINECLUBE" é branco e sairia junto com o
# fundo. O recorte é geométrico: acha-se a caixa do que não é branco (que é
# exatamente o quadrado circunscrito ao disco) e apaga-se o lado de fora do
# círculo inscrito nela.
CINECLUBE_PDF = ROOT / "reference-content" / "Cineclube PÁTRIA GRANDE Logo .pdf"


def disc_alpha(im: Image.Image, inset: float = 0.0) -> Image.Image:
    """Alfa circular, com borda suavizada por supersampling do próprio raio.

    `inset` encolhe o raio em pixels. Serve para engolir a faixa de
    antisserrilhado que o disco tem contra o branco da folha: sem ela, os pixels
    a meio caminho entre a arte e o branco ficam OPACOS e cinza-claros, e sobre
    um fundo escuro isso vira um anel luminoso em volta do disco — exatamente o
    "recorte colado" que a cor de fundo medida existe para evitar.
    """
    import numpy as np

    a = np.asarray(im.convert("RGB")).astype(int)
    ys, xs = np.nonzero(a.sum(2) < 720)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0 + y1 - y0 + 2) / 4 - inset

    yy, xx = np.mgrid[0:im.height, 0:im.width]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    # Uma faixa de dois pixels entre opaco e transparente tira o serrilhado sem
    # comer a borda do disco.
    alpha = np.clip((r - dist) + 1, 0, 1) * 255
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(alpha.astype("uint8")))
    return out.crop((round(cx - r), round(cy - r), round(cx + r), round(cy + r)))


# ---------------------------------------------------------------------------
# Placas de projeto
# ---------------------------------------------------------------------------
# Cada projeto com marca própria recebe uma placa 3:2 pronta — fundo e marca já
# compostos num arquivo só. Compor aqui, e não no CSS, é o que permite dar a
# cada marca o fundo que ela pede sem espalhar quatro exceções pela folha de
# estilo: o amarelo da casa atrás do cineclube, a cor da própria arte atrás do
# FLACA e do Calango, e o desenho de ondas do festival atrás do FICA. Também é
# o que permite encostar a marca quase na moldura com precisão de pixel.
FESTIVAIS = ROOT / "reference-content" / "Site Pátria Grande 2026" / "festivais-logos"

PLATE_WIDTHS = (1500, 900, 600, 300)   # múltiplos de 3: a altura 3:2 fecha exata
PLATE_TANGENT = 0.90                   # altura da arte sobre a altura da placa
PLATE_MAX_WIDTH = 0.93                 # e um teto na largura, para o FICA deitado


def plate_size(width: int) -> tuple[int, int]:
    return width, width * 2 // 3


def strip_white(im: Image.Image, hard: float = 28.0, soft: float = 70.0) -> Image.Image:
    """Fundo branco vira transparência, com uma faixa curta de transição.

    A tolerância é bem mais apertada que a de strip_background: aqui o que está
    perto do branco é papel de fundo, e o azul mais claro do círculo do FICA
    está a menos de 100 de distância do branco. Uma tolerância generosa o
    apagaria pela metade.
    """
    import numpy as np

    a = np.asarray(im.convert("RGB")).astype(float)
    dist = np.sqrt(((a - 255.0) ** 2).sum(2))
    alpha = np.clip((dist - hard) / (soft - hard), 0, 1) * 255
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(alpha.astype("uint8")))
    return out


# --- o desenho de ondas do FICA --------------------------------------------
# A chave de arte do festival é uma pilha de cinco azuis chapados em silhueta de
# onda. O arquivo de origem é um cartaz de edição: traz numeral da edição, datas
# e lista de cidades, nada disso publicável. Em vez de apagar tipo de um raster,
# o desenho é RETRAÇADO — para cada tom, a linha de topo da região daquele tom
# ou mais escuro — e redesenhado limpo. Peixe e tipo são buracos no meio da
# faixa, não no topo dela, e por isso somem no fechamento vertical.
WAVE_SRC = FESTIVAIS / "3o_FICA_GAROPABA.jpg"
WAVE_Y0 = 500          # acima disso é o lockup do cartaz, que não interessa
WAVE_CLOSE = 91        # mais alto que o maior peixe e que uma linha de tipo
WAVE_PAL = [(0xD8, 0xEF, 0xFA), (0x9C, 0xD2, 0xEE), (0x5B, 0xAB, 0xD0),
            (0x34, 0x8F, 0xBB), (0x20, 0x7F, 0xAB)]
WAVE_DESPIKE = [61, 61, 61, 81, 121]


def _vroll(m, k: int, op: str):
    import numpy as np
    pad = np.pad(m, ((k // 2, k // 2), (0, 0)), mode="edge")
    win = np.lib.stride_tricks.sliding_window_view(pad, k, axis=0)
    return win.max(2) if op == "max" else win.min(2)


def _median(v, k: int):
    import numpy as np
    pad = np.pad(v, (k // 2, k // 2), mode="edge")
    return np.array([np.median(pad[i:i + k]) for i in range(len(v))])


def _smooth(v, k: int):
    import numpy as np
    return np.convolve(np.pad(v, (k // 2, k // 2), mode="edge"),
                       np.ones(k) / k, mode="valid")[:len(v)]


def trace_waves():
    """Uma curva de topo por tom, em coordenadas 0..1 — serve a qualquer tamanho."""
    import numpy as np

    a = np.asarray(ImageOps.exif_transpose(Image.open(WAVE_SRC)).convert("RGB")).astype(int)
    reg = a[WAVE_Y0:]
    h, w, _ = reg.shape
    pal = np.array(WAVE_PAL)
    dist = np.sqrt(((reg[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(3))
    nearest, belongs = dist.argmin(2), dist.min(2) < 30

    curves = []
    for i in range(len(WAVE_PAL)):
        mask = (belongs & (nearest >= i)).astype("uint8")
        # Fechamento vertical: tapa peixe e tipo, que são buracos dentro da faixa.
        mask = _vroll(_vroll(mask, WAVE_CLOSE, "max"), WAVE_CLOSE, "min")
        top = np.array([(np.nonzero(mask[:, x])[0][0] if mask[:, x].any() else h)
                        for x in range(w)], float)
        # Uma discrepância nas duas pontas escapa do despique: _median enche a
        # borda com cópias do próprio valor da ponta, então o ponto discrepante
        # vira a sua própria mediana e nunca é apontado. Sem esta guarda sobra
        # uma lasca pálida de 1 a 3 px descendo as duas laterais da placa.
        guard = WAVE_DESPIKE[i] // 2
        for lo, hi, sl in ((0, guard, slice(guard, 3 * guard)),
                           (w - guard, w, slice(w - 3 * guard, w - guard))):
            inner = np.median(top[sl])
            if abs(top[lo if lo == 0 else hi - 1] - inner) > 6:
                top[lo:hi] = inner
        # Despique: crista de verdade tem mais de cem pixels de largura e
        # sobrevive à mediana larga; o que se afasta dela é resíduo de desenho.
        ref = _median(top, WAVE_DESPIKE[i])
        top = np.where(np.abs(top - ref) > 6, ref, top)
        curves.append(_smooth(_median(top, 21), 9) / h)
    return np.array(curves)


def draw_waves(canvas: Image.Image, band_h: int, curves, bands=None, ss: int = 3) -> None:
    """Desenha a pilha de ondas ocupando band_h pixels na base de canvas."""
    from PIL import ImageDraw

    w, h = canvas.size
    n = curves.shape[1]
    big = Image.new("RGBA", (w * ss, band_h * ss), (0, 0, 0, 0))
    pen = ImageDraw.Draw(big)
    for i in (range(len(WAVE_PAL)) if bands is None else bands):
        pts = [(round(x * (w * ss - 1) / (n - 1)), round(curves[i][x] * band_h * ss))
               for x in range(n)]
        pen.polygon(pts + [(w * ss, band_h * ss), (0, band_h * ss)], fill=WAVE_PAL[i])
    canvas.alpha_composite(big.resize((w, band_h), Image.LANCZOS), (0, h - band_h))


# --- as quatro artes --------------------------------------------------------
# O recorte de cada uma depende da forma da arte e do que ela tem de branco.
# O FICA sai por cor, e pode: nenhum pixel da arte dele é branco, e a placa dele
# é branca, então nem um resto de branco apareceria. Cineclube, FLACA e Calango
# saem por geometria — os dois primeiros são discos, o último é um ladrilho —,
# porque cada um deles seria estragado por um recorte de cor: o "CINECLUBE" é
# branco, o "CALANGO" é creme, e o disco do FLACA vai para cima de fundo escuro,
# onde a faixa de antisserrilhado do recorte de cor vira anel luminoso. Errar
# isso não quebra o build: faz buraco no logotipo, ou halo em volta dele.
def mark_box(im: Image.Image, background, tol: float = 60.0, inset: int = 6):
    """A caixa da arte dentro de um ladrilho de fundo chapado.

    Vale a pena recortar por ela e não pelo ladrilho inteiro: como a placa vai
    receber a MESMA cor de fundo, a margem do ladrilho é indistinguível da
    placa, e mantê-la só faria a marca aparecer menor do que podia. O recuo
    descarta a borda do arquivo, onde JPEG e PNG costumam deixar uma linha de
    pixels que não é nem fundo nem arte.
    """
    import numpy as np

    a = np.asarray(im.convert("RGB")).astype(int)[inset:-inset, inset:-inset]
    ys, xs = np.nonzero(np.sqrt(((a - np.array(background)) ** 2).sum(2)) > tol)
    return inset + xs.min(), inset + ys.min(), inset + xs.max() + 1, inset + ys.max() + 1


def _smooth_ground(im: Image.Image, radius: float = 2.4) -> Image.Image:
    """Desfoca o fundo de um ladrilho, preservando a arte."""
    import numpy as np
    from PIL import ImageFilter

    a = np.asarray(im.convert("RGB")).astype(int)
    arte = ((a.mean(2) < 140) | ((a.max(2) - a.min(2)) > 50)).astype("uint8") * 255
    mask = (Image.fromarray(arte)
            .filter(ImageFilter.MaxFilter(5))
            .filter(ImageFilter.GaussianBlur(1.5)))
    return Image.composite(im, im.filter(ImageFilter.GaussianBlur(radius)), mask)


def bleed_tile(tile: Image.Image, box, w: int, h: int,
               tangent: float = PLATE_TANGENT) -> Image.Image:
    """Estica um ladrilho quadrado até cobrir a placa, espelhando a textura.

    É o caso do Cine Retrata: o fundo dele não é cor chapada, é uma textura com
    degradê de cima para baixo. Pintar a placa de uma cor média deixaria costura
    visível onde a textura encontra o liso. Escalando o ladrilho pela marca, ele
    sobra na vertical e falta uns 5% de cada lado na horizontal — e espelhar a
    própria textura nessas faixas é invisível, porque o grão não tem direção.
    """
    mw, mh = box[2] - box[0], box[3] - box[1]
    k = tangent * h / mh
    if mw * k > PLATE_MAX_WIDTH * w:
        k = PLATE_MAX_WIDTH * w / mw
    tw, th = round(tile.width * k), round(tile.height * k)
    big = tile.resize((tw, th), Image.LANCZOS)

    # O grão do papel é ruído de alta frequência: sozinho ele triplica o peso do
    # arquivo e some na tela, no tamanho em que a placa é servida. Desfocar só
    # o FUNDO, com a marca protegida por máscara, corta o WebP de 654 para 172 KB
    # sem tirar um fio da linha preta.
    big = _smooth_ground(big)

    ox = round(w / 2 - (box[0] + box[2]) / 2 * k)
    oy = round(h / 2 - (box[1] + box[3]) / 2 * k)
    out = Image.new("RGB", (w, h))
    out.paste(big, (ox, oy))
    if ox > 0:
        out.paste(big.crop((0, 0, min(ox, tw), th)).transpose(Image.FLIP_LEFT_RIGHT), (0, oy))
    if ox + tw < w:
        n = min(w - (ox + tw), tw)
        out.paste(big.crop((tw - n, 0, tw, th)).transpose(Image.FLIP_LEFT_RIGHT), (ox + tw, oy))
    return out


SHEET_BOX = {                      # caixas medidas varrendo imagens-festivais.png
    "flaca": (724, 37, 1343, 666),
    # Dois pixels para dentro: a borda do ladrilho tem uma linha de transição
    # clara contra o branco da folha, e ela apareceria como moldura sobre a
    # placa da mesma cor.
    "fica-calango": (1370, 39, 2013, 680),
}


def art_cineclube() -> Image.Image | None:
    import subprocess
    import tempfile

    if not CINECLUBE_PDF.exists():
        print(f"  {CINECLUBE_PDF.name} ausente — placa do cineclube pulada.")
        return None
    with tempfile.TemporaryDirectory() as tmp:
        stem = Path(tmp) / "marca"
        try:
            subprocess.run(["pdftoppm", "-r", "300", "-png", "-singlefile",
                            str(CINECLUBE_PDF), str(stem)],
                           check=True, capture_output=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            print(f"  pdftoppm indisponível ({exc}) — instale poppler-utils.")
            return None
        return disc_alpha(Image.open(stem.with_suffix(".png")))


def compose_plate(art: Image.Image, bg, width: int, curves=None,
                  tile_box=None) -> Image.Image:
    """Uma placa 3:2: fundo, o desenho de ondas quando houver, e a marca."""
    w, h = plate_size(width)
    if tile_box is not None:
        return bleed_tile(art, tile_box, w, h).convert("RGBA")
    plate = Image.new("RGBA", (w, h), bg)

    if curves is not None:
        # Os dois tons pálidos ocupam quase metade da placa e passam por trás da
        # linha "Festival Internacional de Cinema Ambiental" do logotipo, onde o
        # preto ainda tem 14:1. Os três tons escuros ficam numa faixa d'água
        # rasa, abaixo do logotipo, onde não disputam legibilidade com o tipo.
        draw_waves(plate, round(h * 0.46), curves, bands=[0, 1])
        draw_waves(plate, round(h * 0.10), curves, bands=[2, 3, 4])
        art_h = round(h * 0.86)
        art_w = round(art.width * art_h / art.height)
        top = round(h * 0.05)
    else:
        art_h = round(h * PLATE_TANGENT)
        art_w = round(art.width * art_h / art.height)
        if art_w > round(w * PLATE_MAX_WIDTH):
            art_w = round(w * PLATE_MAX_WIDTH)
            art_h = round(art.height * art_w / art.width)
        top = (h - art_h) // 2

    # .convert("RGBA"): recorte de ladrilho chega em RGB, e alpha_composite exige
    # os dois lados com canal alfa.
    plate.alpha_composite(art.convert("RGBA").resize((art_w, art_h), Image.LANCZOS),
                          ((w - art_w) // 2, top))
    return plate


def save_plate(slug: str, art: Image.Image, bg, curves=None, tile_box=None) -> None:
    """Grava a placa em WebP e PNG, nas larguras que o card usa.

    O PNG é o ramo do srcset para quem não tem WebP, e em cor cheia uma placa
    com degradê passa de 400 KB. Reduzir a 256 cores por octree corta isso em
    dez vezes sem diferença visível: a arte é chapada.
    """
    OUT_PROJETOS.mkdir(parents=True, exist_ok=True)
    for width in PLATE_WIDTHS:
        plate = compose_plate(art, bg, width, curves, tile_box).convert("RGB")
        plate.save(OUT_PROJETOS / f"{slug}-{width}.webp",
                   format="WEBP", quality=90, method=6)
        plate.quantize(colors=256, method=Image.FASTOCTREE).save(
            OUT_PROJETOS / f"{slug}-{width}.png", optimize=True)
    total = sum((OUT_PROJETOS / f"{slug}-{w}.{ext}").stat().st_size
                for w in PLATE_WIDTHS for ext in ("webp", "png"))
    print(f"  {slug}  {'|'.join(str(w) for w in PLATE_WIDTHS)}  "
          f"{total / 1024:.0f} KB no total")


# Fundo de cada placa. O do cineclube é cor da casa, por decisão da produtora;
# os do FLACA e do Calango são a cor de fundo da própria arte, medida no
# arquivo — assim o disco e o ladrilho não aparecem como recorte colado.
PLATE_BG = {
    "cineclube-patria-grande": "#FFCC00",
    "flaca": "#000C2A",
    "fica-calango": "#85082C",
    "fica-garopaba": "#FFFFFF",
    "educa-ambiental": "#053305",
    # O disco do Marighella já vem recortado, com alfa, e é branco por dentro:
    # a placa repete o branco da própria arte, e o filete vermelho do disco é
    # que dá a forma. Sobre o vermelho da marca ficaria mais forte, mas aí o
    # card brigaria com a faixa vermelha da casa quando caísse sobre uma.
    "cineclube-marighella": "#FFFFFF",
    # O Cine Retrata não tem cor de fundo: o dele é textura, e a placa inteira
    # é o próprio ladrilho espelhado. Ver bleed_tile.
    "cine-retrata": None,
}

# Ladrilhos que já vêm com o fundo dentro, um arquivo por projeto.
TILE = {
    "educa-ambiental": "Cineclube EDUCA AMBIENTAL LOGO.jpg",
    "cine-retrata": "AVATAR CINE RETRATA.png",
    "cineclube-marighella": "CCCM Logo.png",
}


def build_project_plates() -> None:
    sheet = FESTIVAIS / "imagens-festivais.png"
    cine = art_cineclube()
    if cine is not None:
        save_plate("cineclube-patria-grande", cine, PLATE_BG["cineclube-patria-grande"])
    else:
        print("  ATENÇÃO: a placa do cineclube NÃO foi regravada. A que está no "
              "disco continua sendo a de antes — confira antes de publicar.")

    if not sheet.exists():
        print(f"  {sheet.name} ausente — FLACA e Calango pulados.")
    else:
        folha = Image.open(sheet).convert("RGB")
        # 4 px de recuo: é a largura da faixa de antisserrilhado do disco.
        save_plate("flaca", disc_alpha(folha.crop(SHEET_BOX["flaca"]), inset=4),
                   PLATE_BG["flaca"])
        save_plate("fica-calango", folha.crop(SHEET_BOX["fica-calango"]).convert("RGBA"),
                   PLATE_BG["fica-calango"])

    # O Educa Ambiental é ladrilho de cor chapada: recorta-se a marca e a placa
    # repete o mesmo verde, então a moldura do ladrilho desaparece.
    educa = FESTIVAIS / TILE["educa-ambiental"]
    if educa.exists():
        im = ImageOps.exif_transpose(Image.open(educa)).convert("RGB")
        save_plate("educa-ambiental", im.crop(mark_box(im, (5, 51, 5))),
                   PLATE_BG["educa-ambiental"])
    else:
        print(f"  {TILE['educa-ambiental']} ausente — Educa Ambiental pulado.")

    # O Cine Retrata é ladrilho de textura: a placa é o próprio ladrilho.
    retrata = FESTIVAIS / TILE["cine-retrata"]
    if retrata.exists():
        im = ImageOps.exif_transpose(Image.open(retrata)).convert("RGB")
        import numpy as np
        a = np.asarray(im).astype(int)
        arte = (a.mean(2) < 110) | ((a.max(2) - a.min(2)) > 60)
        ys, xs = np.nonzero(arte)
        save_plate("cine-retrata", im, None,
                   tile_box=(xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    else:
        print(f"  {TILE['cine-retrata']} ausente — Cine Retrata pulado.")

    # O Marighella é o único que já chega recortado: PNG com alfa, disco branco
    # de filete vermelho. Não há o que cortar, só o que assentar.
    cccm = FESTIVAIS / TILE["cineclube-marighella"]
    if cccm.exists():
        save_plate("cineclube-marighella",
                   tight(ImageOps.exif_transpose(Image.open(cccm)).convert("RGBA"), pad=0),
                   PLATE_BG["cineclube-marighella"])
    else:
        print(f"  {TILE['cineclube-marighella']} ausente — Marighella pulado.")

    evergreen = FESTIVAIS / "FICA_Garopaba_logo_evergreen.png"
    if not evergreen.exists() or not WAVE_SRC.exists():
        print("  arte do FICA ausente — pulado.")
        return
    save_plate("fica-garopaba", tight(strip_white(Image.open(evergreen)), pad=0),
               PLATE_BG["fica-garopaba"], curves=trace_waves())


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

    print("\nPlacas de projeto — marca sobre o fundo que ela pede:")
    build_project_plates()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
