#!/usr/bin/env python3
"""
Extrai a silhueta cartográfica da marca do PNG do logotipo e escreve um SVG.

A América Latina invertida — sul para cima — é a tese visual da identidade
(§6 da especificação v2). No site ela é usada como marca d'água, máscara e
grafismo de seção, o que exige um traçado vetorial: PNG de 3000 px não escala,
não muda de cor por CSS e pesa.

O arquivo aberto do logotipo é `.cdr`, que nenhuma ferramenta desta máquina lê.
Então o caminho é traçar a partir do raster: a versão "com todos os elementos"
tem o mapa em amarelo chapado, o que dá um contorno limpo.

    python3 tools/trace-brand.py

Escreve assets/img/marca/mapa-patria-grande.svg.
Requer Pillow e numpy.
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "reference-content" / "Site Pátria Grande 2026" / "patria-logos" / \
    "LOGOTIPO_PÁTRIA_GRANDE_com_todos_elementos.png"
OUT = ROOT / "assets" / "img" / "marca" / "mapa-patria-grande.svg"

# Trabalhar em 1000 px de lado: resolução mais que suficiente para o contorno e
# rápida o bastante para o traçado em Python puro.
WORK = 1000
# Tolerância do Douglas-Peucker, em pixels do espaço de trabalho. Baixa demais
# gera um path de 200 KB; alta demais transforma a costa do Chile numa reta.
EPSILON = 0.85


def load_mask() -> np.ndarray:
    """Máscara booleana dos pixels amarelos, reamostrada para WORK×WORK."""
    im = Image.open(SRC).convert("RGB").resize((WORK, WORK), Image.LANCZOS)
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # Amarelo da marca: vermelho e verde altos, azul baixo. O fundo vinho tem
    # verde baixo, então a separação por g é o que faz o trabalho.
    return (r > 150) & (g > 110) & (b < 120)


def _shift_and(a: np.ndarray, r: int, op) -> np.ndarray:
    """Erosão (op=np.logical_and) ou dilatação (op=np.logical_or) com elemento
    quadrado de lado 2r+1, feita por deslocamentos — sem SciPy."""
    out = a.copy()
    pad = np.pad(a, r, mode="constant", constant_values=(op is np.logical_and))
    h, w = a.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out = op(out, pad[r + dy: r + dy + h, r + dx: r + dx + w])
    return out


def opening(mask: np.ndarray, r: int) -> np.ndarray:
    """Abertura morfológica: apaga traços finos e devolve as áreas cheias.

    É o que separa o mapa do resto do desenho. A linha do horizonte, o veleiro,
    a cidade e a linha do Equador encostam na silhueta e, sem isso, entrariam
    no mesmo contorno. Todos são traço de ~5 px na escala de trabalho; o mapa
    tem centenas. A erosão come os traços, a dilatação devolve o mapa."""
    return _shift_and(_shift_and(mask, r, np.logical_and), r, np.logical_or)


def drop_long_thin_horizontals(mask: np.ndarray, min_width: int = 130, thickness: int = 3) -> np.ndarray:
    """Apaga a linha do horizonte e a linha do Equador, preservando o istmo.

    Abrir só na vertical derruba tudo que é horizontalmente fino — inclusive a
    ponte estreita entre a América Central e o continente, que precisa ficar.
    O que separa os dois casos é o comprimento: as linhas do desenho atravessam
    centenas de pixels; o istmo tem algumas dezenas. Então marcamos o que é fino
    e removemos apenas as marcas largas o bastante para serem régua, não terra."""
    thin = mask & ~_shift_and(_shift_and(mask, thickness, np.logical_and), thickness, np.logical_or)

    h, w = mask.shape
    seen = np.zeros_like(thin, dtype=bool)
    out = mask.copy()
    removed = 0

    for sy in range(h):
        for sx in range(w):
            if not thin[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            cells = []
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and thin[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
            xs = [c[1] for c in cells]
            if max(xs) - min(xs) >= min_width:
                for y, x in cells:
                    out[y, x] = False
                removed += 1

    print(f"  linhas removidas: {removed}")
    return out


def largest_blob(mask: np.ndarray) -> np.ndarray:
    """A maior região conectada — o mapa. Descarta sol, lua, aves e wordmark."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best: np.ndarray | None = None
    best_size = 0

    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            cells = []
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(cells) > best_size:
                best_size = len(cells)
                blob = np.zeros_like(mask, dtype=bool)
                ys, xs = zip(*cells)
                blob[np.array(ys), np.array(xs)] = True
                best = blob

    if best is None:
        raise SystemExit("nenhuma região amarela encontrada — confira o limiar")
    print(f"  maior região: {best_size} px")
    return best


def trace(mask: np.ndarray) -> list[tuple[int, int]]:
    """Traçado de contorno de Moore, em sentido horário, a partir do pixel mais
    ao norte-oeste da região."""
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    start = (int(ys[0]), int(xs[np.argmin(xs[ys == ys[0]])]))

    # Vizinhança de Moore em ordem horária, começando a oeste.
    nbrs = [(0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1)]

    def solid(y, x):
        return 0 <= y < h and 0 <= x < w and mask[y, x]

    contour = [start]
    cur = start
    back = 0  # índice do vizinho de onde viemos
    guard = 0
    while True:
        guard += 1
        if guard > 4 * h * w:
            raise SystemExit("traçado não fechou — máscara provavelmente ruidosa")
        found = False
        for k in range(1, 9):
            i = (back + k) % 8
            dy, dx = nbrs[i]
            ny, nx = cur[0] + dy, cur[1] + dx
            if solid(ny, nx):
                back = (i + 5) % 8  # o vizinho oposto, menos um passo
                cur = (ny, nx)
                contour.append(cur)
                found = True
                break
        if not found:
            break
        if cur == start and len(contour) > 2:
            break
    print(f"  contorno: {len(contour)} pontos")
    return contour


def rdp(points: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    """Douglas-Peucker iterativo — a versão recursiva estoura a pilha aqui."""
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]

    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        ax, ay = points[first]
        bx, by = points[last]
        dx, dy = bx - ax, by - ay
        norm = (dx * dx + dy * dy) ** 0.5
        worst, worst_i = -1.0, first
        for i in range(first + 1, last):
            px, py = points[i]
            if norm == 0:
                d = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if d > worst:
                worst, worst_i = d, i
        if worst > eps:
            keep[worst_i] = True
            stack.append((first, worst_i))
            stack.append((worst_i, last))

    return [p for p, k in zip(points, keep) if k]


def main() -> int:
    if not SRC.exists():
        print(f"origem ausente: {SRC}", file=sys.stderr)
        print("O SVG versionado em assets/img/marca/ já é o resultado deste script.",
              file=sys.stderr)
        return 1

    print("Traçando a cartografia da marca:")
    mask = load_mask()
    # Raio 4: o traço do horizonte, do veleiro e da linha do Equador tem ~5 px
    # nesta escala e some; o istmo que liga a América Central ao continente tem
    # ~10 px e sobrevive, o que mantém a cartografia inteira da marca.
    # Primeiro saem as réguas horizontais do desenho — horizonte e linha do
    # Equador —, que encostam na costa e entrariam no mesmo contorno. Só depois
    # a abertura pequena limpa o veleiro, a cidade e os respingos de amostragem,
    # com raio baixo o bastante para o istmo da América Central sobreviver.
    mask = drop_long_thin_horizontals(mask)
    mask = opening(mask, 2)
    blob = largest_blob(mask)
    contour = trace(blob)

    pts = [(float(x), float(y)) for y, x in contour]
    simple = rdp(pts, EPSILON)
    print(f"  simplificado: {len(simple)} pontos")

    # Normaliza para uma viewBox de 1000 de largura, preservando a proporção.
    xs = [p[0] for p in simple]
    ys = [p[1] for p in simple]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span = max(maxx - minx, maxy - miny)
    scale = 1000 / span
    vb_w = round((maxx - minx) * scale)
    vb_h = round((maxy - miny) * scale)

    def fmt(v: float) -> str:
        return f"{v:.1f}".rstrip("0").rstrip(".")

    d = "M" + " L".join(
        f"{fmt((x - minx) * scale)},{fmt((y - miny) * scale)}" for x, y in simple
    ) + " Z"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb_w} {vb_h}" '
        f'role="img" aria-label="Silhueta da América Latina orientada com o sul para cima, '
        f'como no logotipo da Pátria Grande Produções">\n'
        f'<path fill="currentColor" d="{d}"/>\n'
        f"</svg>\n",
        encoding="utf-8",
    )
    print(f"\n{OUT.relative_to(ROOT)}  ({OUT.stat().st_size / 1024:.1f} KB, viewBox {vb_w}×{vb_h})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
