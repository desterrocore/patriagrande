#!/usr/bin/env python3
"""
Monta o site a partir dos arquivos de dados em source/.

O que o GitHub Pages publica é HTML estático — não há build no servidor e não
há framework. Este gerador existe porque vinte páginas dividem o mesmo
cabeçalho, o mesmo rodapé e a mesma ficha de metadados, e manter isso à mão é
como se introduz divergência. O HTML gerado É COMMITADO junto com o gerador:
quem clona serve os arquivos direto, e quem edita conteúdo mexe nos JSON e roda

    python3 tools/build-site.py

Duas regras do documento-fonte v2 são feitas cumprir aqui, e não deixadas ao
cuidado de quem escreve:

  * número sem fonte não vira página (§78 e §105) — toda métrica precisa de
    "source", e tools/check-site.py falha se faltar;
  * previsão não é resultado (§31) — o que está em andamento carrega selo, vive
    numa aba própria e nunca soma aos números do que foi executado.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"

BASE_URL = "https://patriagrande.com.br"

# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------


def e(text) -> str:
    """Escapa para HTML. Todo dado vindo do JSON passa por aqui."""
    return html.escape(str(text if text is not None else ""), quote=True)


# O 404 é a única página servida em endereço que ela não conhece: o GitHub
# Pages devolve o mesmo arquivo para /qualquer/coisa/funda/, e ali um caminho
# relativo resolve para /qualquer/coisa/funda/assets/… — a página aparece sem
# estilo. Num domínio de ápice dá para usar caminho de raiz, que é sempre
# válido. Num subcaminho não dá, e o relativo continua sendo o certo.
_ABS_ROOT = False


def up(depth: int) -> str:
    """Prefixo até a raiz do site.

    Relativo por padrão — é o que permite o mesmo build funcionar num
    subcaminho como usuario.github.io/repo/ e num domínio próprio, sem
    reescrever nada. Só o 404, e só quando o site está num ápice, usa raiz.
    """
    if _ABS_ROOT:
        return "/"
    return "../" * depth


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
STRONG_RE = re.compile(r"\*\*([^*]+)\*\*")


def external(href: str) -> str:
    return ' target="_blank" rel="noopener"' if href.startswith("http") else ""


def inline(text: str) -> str:
    """Escapa e devolve apenas dois marcadores: **negrito** e [texto](url).
    Nada mais de markdown — o conteúdo é editorial, não um blog."""
    out = e(text)
    out = STRONG_RE.sub(r"<strong>\1</strong>", out)
    return LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}"{external(m.group(2))}>{m.group(1)}</a>', out
    )


def paras(text: str, cls: str = "") -> str:
    if not text:
        return ""
    attr = f' class="{cls}"' if cls else ""
    return "\n".join(
        f"<p{attr}>{inline(b.strip())}</p>" for b in re.split(r"\n\s*\n", text.strip())
    )


def bullets(text: str) -> str:
    """Uma lista a partir de linhas que começam com "- ". Lista de um item só
    não é lista — nesse caso vira parágrafo."""
    items = [ln.strip()[2:].strip() for ln in (text or "").splitlines() if ln.strip().startswith("- ")]
    if not items:
        return ""
    if len(items) == 1:
        return f"<p>{inline(items[0])}</p>"
    return "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"


def picture(img: dict, depth: int, sizes: str = "100vw", loading: str = "lazy",
            ratio: str | None = None, group: str = "fotos") -> str:
    """<picture> com WebP e JPEG, srcset completo e dimensões explícitas, para
    o navegador reservar o espaço certo antes de a imagem chegar."""
    widths = img["widths"]
    base = f'{up(depth)}assets/img/{img.get("group", group)}/{img["name"]}'

    def src(w, ext):
        return f"{base}-{w}.{ext}"

    webp = ", ".join(f"{src(w, 'webp')} {w}w" for w in widths)
    jpg = ", ".join(f"{src(w, 'jpg')} {w}w" for w in widths)
    big = max(widths)

    dim = ""
    r = ratio or img.get("ratio")
    if r:
        rw, rh = (float(x) for x in r.split(":"))
        dim = f' width="{big}" height="{round(big * rh / rw)}"'

    prio = ' fetchpriority="high"' if loading == "eager" else ""
    return (
        "<picture>"
        f'<source type="image/webp" srcset="{webp}" sizes="{sizes}">'
        f'<img src="{src(big, "jpg")}" srcset="{jpg}" sizes="{sizes}" alt="{e(img["alt"])}" '
        f'loading="{loading}" decoding="async"{prio}{dim}>'
        "</picture>"
    )


# A cartografia é inline — assim herda a cor da faixa por currentColor e não
# custa uma requisição. Mas ela aparece até dez vezes numa página, e repetir o
# path dez vezes custaria 30 KB de HTML por página. O desenho entra uma vez, num
# <symbol> no topo do body, e cada aparição vira um <use> de algumas dezenas de
# bytes. O arquivo é o mesmo que tools/trace-brand.py escreve.
_MAP_CACHE: dict[str, str] = {}


def _map() -> dict[str, str]:
    if not _MAP_CACHE:
        svg = (ROOT / "assets" / "img" / "marca" / "mapa-patria-grande.svg").read_text(encoding="utf-8")
        _MAP_CACHE["viewbox"] = re.search(r'viewBox="([^"]+)"', svg).group(1)
        _MAP_CACHE["path"] = re.search(r"<path[^>]*/>", svg).group(0)
    return _MAP_CACHE


def map_sprite() -> str:
    """O desenho, uma vez por página. Fora do fluxo e fora da árvore de acessibilidade."""
    m = _map()
    return ('<svg class="sprite" aria-hidden="true" focusable="false" width="0" height="0">'
            f'<symbol id="pg-mapa" viewBox="{m["viewbox"]}">{m["path"]}</symbol></svg>')


def map_use(extra: str = "") -> str:
    m = _map()
    return f'<svg viewBox="{m["viewbox"]}" focusable="false"{extra}><use href="#pg-mapa"/></svg>'


def cartografia(cls: str = "cartografia cartografia--canto") -> str:
    """Silhueta decorativa: ornamento, não conteúdo."""
    return f'<span class="{cls}" aria-hidden="true">{map_use()}</span>'


def eyebrow(num: str, label: str) -> str:
    return (f'<p class="eyebrow"><span class="eyebrow__num">{e(num)}</span>'
            f"<span>{e(label)}</span></p>")


def write(path: str, content: str) -> None:
    out = ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"  {path}  ({len(content.encode('utf-8')) / 1024:.1f} KB)")


# --------------------------------------------------------------------------
# chrome
# --------------------------------------------------------------------------

NAV = [
    ("quem-somos/", "Quem somos", False),
    ("projetos/", "Projetos", False),
    ("servicos/", "Serviços", False),
    ("equipe/", "Equipe", False),
    ("contato/", "Contato", True),
]


def head(title: str, description: str, path: str, depth: int, og_image: str | None = None) -> str:
    canonical = f"{BASE_URL}/{path}" if path else f"{BASE_URL}/"
    og = og_image or f"{BASE_URL}/assets/img/marca/og-patria-grande.png"
    r = up(depth)
    return f"""<!DOCTYPE html>
<html lang="pt-BR" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{canonical}">

<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="Pátria Grande Produções">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og}">
<meta name="twitter:card" content="summary_large_image">

<meta name="theme-color" content="#690404">
<link rel="icon" href="{r}assets/img/marca/favicon.ico" sizes="any">
<link rel="icon" href="{r}assets/img/marca/favicon-96.png" type="image/png" sizes="96x96">
<link rel="apple-touch-icon" href="{r}assets/img/marca/favicon-180.png">
<link rel="manifest" href="{r}site.webmanifest">

<link rel="preload" href="{r}assets/fonts/archivo-black-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{r}assets/fonts/archivo-400-800-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{r}assets/css/patria-grande.css">
</head>
<body>
{map_sprite()}
<a class="skip-link" href="#conteudo">Ir para o conteúdo</a>
"""


def header(active: str, depth: int) -> str:
    r = up(depth)
    items = []
    for href, label, is_cta in NAV:
        current = ' aria-current="page"' if href == active else ""
        cls = "nav__link nav__cta" if is_cta else "nav__link"
        items.append(f'<li><a class="{cls}" href="{r}{href}"{current}>{label}</a></li>')

    return f"""<header class="header">
<div class="shell header__inner">
<a class="brand" href="{r}" aria-label="Pátria Grande Produções — página inicial">
<span class="brand__symbol" aria-hidden="true"><svg viewBox="{_map()["viewbox"]}" focusable="false"><use href="#pg-mapa"/></svg></span>
<img class="brand__word" src="{r}assets/img/marca/wordmark-amarelo-450.png" width="450" height="293" alt="Pátria Grande Produções" loading="eager" decoding="async">
</a>
<nav class="nav" aria-label="Principal">
<button class="nav__toggle" type="button" aria-expanded="false" aria-controls="nav-list">
<span class="nav__bars" aria-hidden="true"><i></i><i></i><i></i></span>Menu
</button>
<ul class="nav__list" id="nav-list">
{chr(10).join(items)}
</ul>
</nav>
</div>
</header>
<main id="conteudo">
"""


def footer(site: dict, depth: int) -> str:
    r = up(depth)
    nav_links = "".join(f'<li><a href="{r}{href}">{label}</a></li>' for href, label, _ in NAV)
    proj_links = "".join(
        f'<li><a href="{r}projetos/{slug}/">{title}</a></li>' for slug, title in site["footer_projects"]
    )
    serv_links = "".join(
        f'<li><a href="{r}servicos/{slug}/">{title}</a></li>' for slug, title in site["footer_services"]
    )
    phones = "".join(
        f'<li><a class="footer__plain" href="tel:{p["tel"]}">{e(p["label"])}</a></li>'
        for p in site["phones"]
    )
    return f"""</main>
<footer class="footer">
{cartografia("cartografia")}
<div class="shell">
<div class="footer__top">
<div>
<h2 class="visually-hidden">Pátria Grande Produções</h2>
<img class="footer__mark" src="{r}assets/img/marca/assinatura-amarela-600.png" width="600" height="517" alt="Pátria Grande Produções" loading="lazy" decoding="async">
<p class="meta">Produtora cultural<br>Florianópolis · Santa Catarina<br>Atuação em diferentes regiões do Brasil</p>
</div>
<nav aria-label="Rodapé">
<h3>Navegar</h3>
<ul class="footer__list">{nav_links}</ul>
</nav>
<div>
<h3>Projetos</h3>
<ul class="footer__list">{proj_links}</ul>
</div>
<div>
<h3>Serviços</h3>
<ul class="footer__list">{serv_links}</ul>
</div>
<div>
<h3>Contato</h3>
<ul class="footer__list">
<li><a class="footer__plain" href="mailto:{site["email"]}">{site["email"]}</a></li>
{phones}
<li><a href="{site["instagram_url"]}" target="_blank" rel="noopener">Instagram {site["instagram"]}</a></li>
</ul>
</div>
</div>
<div class="footer__bottom">
<span>© 2022–2026 Pátria Grande Produções · Textos e fotografias de seus autores</span>
<span>Site por <a href="https://desterrocore.com.br" target="_blank" rel="noopener">desterrocore</a></span>
</div>
</div>
</footer>
<script src="{r}assets/js/main.js" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# componentes
# --------------------------------------------------------------------------

CATEGORY_LABEL = {
    "festival": "Festival",
    "cineclube": "Cineclube",
    "formacao": "Formação",
    "fotografia": "Fotografia",
    "artes-visuais": "Artes visuais",
    "danca": "Dança",
}


def badge(text: str) -> str:
    return f'<span class="badge">{e(text)}</span>'


def project_card(p: dict, depth: int, feature: bool = False) -> str:
    """Card do arquivo. Sem foto documental o card recebe uma placa de cor da
    marca com a cartografia atrás — nunca imagem de banco, nunca gerada, nunca
    emprestada de outro projeto."""
    href = f'{up(depth)}projetos/{p["slug"]}/'
    cats = " ".join(p["categories"])
    years = " ".join(str(y) for y in p["years"])
    # Um projeto com edições realizadas E uma edição corrente pertence às duas
    # abas: some da aba "Realizados" seria apagar quatro edições do FICA.
    status = "executado andamento" if p.get("ongoing") else "executado"

    if p.get("card_image"):
        sizes = "(min-width: 900px) 42vw, 100vw" if feature else "(min-width: 900px) 30vw, 100vw"
        media = f'<div class="pcard__media">{picture(p["card_image"], depth, sizes=sizes, ratio="3:2")}</div>'
    else:
        media = (
            f'<div class="pcard__plate plate--{p["band"]}">'
            f'{cartografia("cartografia")}'
            f'<span aria-hidden="true">{e(p["plate_text"])}</span></div>'
        )

    # "Edição em andamento" e não "Em andamento": o projeto já aconteceu, o que
    # está correndo agora é uma edição nova. A diferença é o ponto inteiro.
    flag = f'<span class="pcard__flag">{badge("Edição em andamento")}</span>' if p.get("ongoing") else ""
    kicker = " · ".join(CATEGORY_LABEL.get(c, c) for c in p["categories"])
    foot = "".join(
        f"<span>{e(v)}</span>"
        for v in (p["years_label"] if p["years"] else "", " · ".join(p["cities"]))
        if v
    ) or '<span>Sem data confirmada</span>' 

    return f"""<li data-category="{cats}" data-status="{status}" data-years="{years}">
<article class="pcard{' pcard--feature' if feature else ''}">
{media}{flag}
<div class="pcard__body">
<p class="pcard__kicker">{e(kicker)}</p>
<h3 class="pcard__title"><a href="{href}">{e(p["short_title"])}</a></h3>
<p class="pcard__desc">{inline(p["lede"])}</p>
<p class="pcard__foot">{foot}</p>
</div>
</article>
</li>"""


def ongoing_card(p: dict, depth: int) -> str:
    """A edição corrente não é o projeto: reaproveitar o card do histórico dizia
    "2022–2025 · Garopaba" numa seção sobre o que ainda vai acontecer. Este card
    fala só da edição em curso — e não imprime data, porque não há data
    anunciada; a janela do PRONAC é prazo de projeto, não de festival."""
    o = p["ongoing"]
    href = f'{up(depth)}projetos/{p["slug"]}/'
    return f"""<li>
<article class="pcard pcard--ongoing">
<div class="pcard__plate plate--{p["band"]}">
{cartografia("cartografia")}
<span aria-hidden="true">{e(p["plate_text"])}</span>
</div>
<span class="pcard__flag">{badge("Edição em andamento")}</span>
<div class="pcard__body">
<p class="pcard__kicker">{e(o.get("edicao") or "Nova edição")}</p>
<h3 class="pcard__title"><a href="{href}">{e(p["short_title"])}</a></h3>
<p class="pcard__desc">{inline(o["status"])}</p>
<p class="pcard__foot"><span>{e(o.get("territorio", ""))}</span><span>Sem data anunciada</span></p>
</div>
</article>
</li>"""


def service_card(s: dict, depth: int, num: int) -> str:
    return f"""<li>
<article class="scard">
{cartografia("cartografia")}
<p class="scard__num">{num:02d}</p>
<h3 class="scard__title"><a href="{up(depth)}servicos/{s["slug"]}/">{e(s["title"])}</a></h3>
<p class="scard__desc">{inline(s["lede"])}</p>
<p class="scard__more">{e(s["cta"])} <span aria-hidden="true">→</span></p>
</article>
</li>"""


def team_card(person: dict, depth: int, compact: bool = False) -> str:
    r = up(depth)
    if person.get("photo"):
        media = picture(
            {**person["photo"], "group": "equipe", "alt": f'Retrato de {person["display_name"]}'},
            depth, sizes="(min-width: 900px) 22vw, 45vw", ratio="1:1",
        )
    else:
        initials = "".join(w[0] for w in person["display_name"].split()[:2]).upper()
        media = (f'<div class="tcard__initials">{cartografia("cartografia")}'
                 f'<span aria-hidden="true">{e(initials)}</span>'
                 f'<span class="visually-hidden">Sem retrato disponível</span></div>')

    credit = ""
    if person.get("photo") and person.get("photo_credit"):
        credit = f'<p class="tcard__credit meta">Foto: {e(person["photo_credit"])}</p>'

    # A lista de projetos só aparece no card completo. No compacto ela
    # desequilibra a grade — quem assina nove projetos ganharia um card três
    # vezes mais alto que o do vizinho — e está a um clique em /equipe.
    tags = ""
    if person.get("projects") and not compact:
        items = "".join(
            f'<li><a class="tag" href="{r}projetos/{s}/">{e(t)}</a></li>' for s, t in person["projects"]
        )
        tags = f'<ul class="taglist">{items}</ul>'

    links = ""
    if person.get("links"):
        items = " · ".join(
            f'<a href="{l["href"]}" target="_blank" rel="noopener">{e(l["label"])}&nbsp;↗</a>'
            for l in person["links"]
        )
        links = f'<p class="tcard__links">{items}</p>'

    bio = person["bio_short"] if compact else person["bio"]
    return f"""<li>
<article class="tcard{' tcard--compact' if compact else ''}">
<div class="tcard__photo">{media}{credit}</div>
<h3 class="tcard__name">{e(person["display_name"])}</h3>
<p class="tcard__role">{e(person["role_line"])}</p>
<p class="tcard__bio">{inline(bio)}</p>
{tags}
{links}
</article>
</li>"""


def stats_block(metrics: list[dict]) -> str:
    if not metrics:
        return ""
    items = "".join(
        f'<li><span class="stat__v">{e(m["value"])}</span>'
        f'<span class="stat__k">{e(m["label"])}</span>'
        f'<span class="stat__src">{inline(m["source"])}</span></li>'
        for m in metrics
    )
    return f'<ul class="stats">{items}</ul>'


def note(label: str, body: str) -> str:
    return f'<aside class="note"><b class="note__label">{e(label)}</b>{paras(body)}</aside>'


def gallery(images: list[dict], depth: int) -> str:
    if not images:
        return ""
    items = []
    for img in images:
        big = max(img["widths"])
        full = f'{up(depth)}assets/img/fotos/{img["name"]}-{big}.jpg'
        items.append(
            "<li><figure>"
            f'<a href="{full}" data-full>'
            + picture(img, depth, sizes="(min-width: 900px) 32vw, 100vw", ratio="3:2")
            + "</a>"
            f'<figcaption class="archivecaption">{inline(img["caption"])}</figcaption>'
            "</figure></li>"
        )
    return f'<ul class="gallery" data-gallery>{"".join(items)}</ul>'


def fullbleed(img: dict, depth: int) -> str:
    if not img:
        return ""
    return (
        '<figure class="fullbleed">'
        + picture(img, depth, sizes="100vw", ratio="21:9")
        + f'<figcaption>{inline(img["caption"])}</figcaption></figure>'
    )


def axes_cols(n: int) -> str:
    """Colunas de uma grade de divisórias, escolhidas para não sobrar célula:
    o maior divisor de n até 4 (4 itens → 4 colunas; 6 → 3; 5 → 1)."""
    wide = next((c for c in (4, 3, 2) if n % c == 0), 1)
    return f'--cols-lg:{wide};--cols-sm:{2 if n % 2 == 0 else 1}'


# --------------------------------------------------------------------------
# páginas
# --------------------------------------------------------------------------


def build() -> None:
    site = json.loads((SRC / "site.json").read_text(encoding="utf-8"))
    projects = json.loads((SRC / "projetos.json").read_text(encoding="utf-8"))
    people = json.loads((SRC / "equipe.json").read_text(encoding="utf-8"))
    services = json.loads((SRC / "servicos.json").read_text(encoding="utf-8"))

    by_slug = {p["slug"]: p for p in projects}

    print("Gerando páginas:")
    page_home(site, projects, people, services, by_slug)
    page_quem_somos(site, people)
    page_projetos(site, projects)
    for p in projects:
        page_projeto(site, p, by_slug)
    page_servicos(site, services, by_slug)
    for i, s in enumerate(services, 1):
        page_servico(site, s, i, services, by_slug)
    page_equipe(site, people)
    page_contato(site, services)
    page_404(site)
    page_sitemap(projects, services)
    print("\nPronto.")


# ---- home -----------------------------------------------------------------


def page_home(site, projects, people, services, by_slug) -> None:
    h = site["home"]
    depth = 0

    featured = "".join(project_card(by_slug[s], depth, feature=True) for s in h["featured"])
    ongoing = "".join(ongoing_card(by_slug[s], depth) for s in h["ongoing"])
    service_cards = "".join(service_card(s, depth, i) for i, s in enumerate(services, 1))
    nucleo = [p for p in people if p["tier"] == "nucleo"]
    team_cards = "".join(team_card(p, depth, compact=True) for p in nucleo)

    axes = "".join(
        f'<li><span class="axes__num">{i + 1:02d}</span><h3>{e(a["title"])}</h3>'
        f'<p>{inline(a["text"])}</p></li>'
        for i, a in enumerate(h["axes"])
    )
    territories = "".join(
        f'<li><h3>{e(t["name"])}</h3><p>{inline(t["text"])}</p></li>' for t in h["territories"]
    )

    out = head(h["title"], site["seo"]["home"], "", depth)
    out += header("", depth)
    out += f"""
<section class="hero">
<div class="hero__panel">
{cartografia("cartografia cartografia--canto")}
<div class="hero__inner">
<h1 class="hero__title">{inline(h["hero_title"])}</h1>
<p class="hero__lede">{inline(h["hero_lede"])}</p>
<p class="btnrow">
<a class="btn btn--primary" href="projetos/">Conheça nossos projetos <span class="btn__arrow" aria-hidden="true">→</span></a>
<a class="btn btn--ghost" href="servicos/">Serviços</a>
</p>
</div>
</div>
<div class="hero__media">
{picture(h["hero_image"], depth, sizes="(min-width: 900px) 55vw, 100vw", loading="eager", ratio="3:2")}
<p class="hero__caption">{inline(h["hero_image"]["caption"])}</p>
</div>
</section>

<section class="band band--yellow" aria-labelledby="manifesto">
<div class="shell">
<h2 class="visually-hidden" id="manifesto">Manifesto</h2>
<p class="manifesto" data-reveal>{inline(h["manifesto"])}</p>
</div>
</section>

<section class="band band--paper" aria-labelledby="quem-somos-home">
<div class="shell">
{eyebrow("01", "Quem somos")}
<div class="split">
<div data-reveal><h2 id="quem-somos-home">{inline(h["about_title"])}</h2></div>
<div class="prose" data-reveal>
{paras(h["about_text"])}
<p class="btnrow" style="margin-top:1.6em">
<a class="btn btn--primary" href="quem-somos/">Conheça a Pátria Grande <span class="btn__arrow" aria-hidden="true">→</span></a>
</p>
</div>
</div>
</div>
</section>

<section class="band band--paper band--tight" aria-labelledby="realizados">
<div class="shell">
{eyebrow("02", "Projetos realizados")}
<h2 id="realizados" data-reveal>{inline(h["projects_title"])}</h2>
<p class="lede" style="margin-top:1em" data-reveal>{inline(h["projects_lede"])}</p>
<ul class="projectgrid projectgrid--feature" style="margin-top:clamp(26px,3.2vw,48px)" data-reveal>
{featured}
</ul>
<p class="btnrow" style="margin-top:clamp(26px,3vw,42px)">
<a class="btn btn--ghost" href="projetos/">Ver todos os projetos realizados <span class="btn__arrow" aria-hidden="true">→</span></a>
</p>
</div>
</section>

<section class="band band--deep" aria-labelledby="em-andamento">
<div class="shell">
{eyebrow("03", "Em andamento")}
<div class="split">
<div data-reveal><h2 id="em-andamento">{inline(h["ongoing_title"])}</h2></div>
<div data-reveal>{paras(h["ongoing_lede"], "lede")}</div>
</div>
<ul class="projectgrid" style="margin-top:clamp(28px,3.4vw,50px)" data-reveal>
{ongoing}
</ul>
</div>
</section>

<section class="band band--paper" aria-labelledby="servicos-home">
<div class="shell">
{eyebrow("04", "O que fazemos")}
<div class="split">
<div data-reveal><h2 id="servicos-home">{inline(h["services_title"])}</h2></div>
<div data-reveal>{paras(h["services_lede"], "lede")}</div>
</div>
<ul class="services" style="margin-top:clamp(28px,3.4vw,50px)" data-reveal>
{service_cards}
</ul>
<p class="btnrow" style="margin-top:clamp(26px,3vw,42px)">
<a class="btn btn--primary" href="servicos/">Conheça nossos serviços <span class="btn__arrow" aria-hidden="true">→</span></a>
</p>
</div>
</section>

{fullbleed(h.get("fullbleed_image"), depth)}

<section class="band band--paper" aria-labelledby="eixos">
<div class="shell">
{eyebrow("05", "Linhas de atuação")}
<h2 id="eixos" data-reveal>{inline(h["axes_title"])}</h2>
<ul class="axes" style="margin-top:clamp(26px,3.2vw,46px);{axes_cols(len(h["axes"]))}" data-reveal>
{axes}
</ul>
</div>
</section>

<section class="band band--paper band--tight" aria-labelledby="territorios">
<div class="shell">
{eyebrow("06", "Territórios")}
<div class="split">
<div data-reveal><h2 id="territorios">{inline(h["territories_title"])}</h2></div>
<div data-reveal>
{paras(h["territories_text"], "lede")}
<ul class="territories" style="margin-top:clamp(22px,2.8vw,38px)">{territories}</ul>
</div>
</div>
</div>
</section>

<section class="band band--red" aria-labelledby="equipe-home">
<div class="shell">
{eyebrow("07", "Equipe")}
<div class="split">
<div data-reveal><h2 id="equipe-home">{inline(h["team_title"])}</h2></div>
<div data-reveal>{paras(h["team_text"], "lede")}</div>
</div>
<ul class="teamgrid teamgrid--compact" style="margin-top:clamp(30px,3.8vw,54px)" data-reveal>
{team_cards}
</ul>
<p class="btnrow" style="margin-top:clamp(26px,3vw,42px)">
<a class="btn btn--primary" href="equipe/">Conheça a equipe <span class="btn__arrow" aria-hidden="true">→</span></a>
</p>
</div>
</section>

<section class="band band--yellow" aria-labelledby="contato-home">
<div class="shell">
<div class="split" style="align-items:center">
<div data-reveal><h2 id="contato-home">{inline(h["contact_title"])}</h2></div>
<div data-reveal>
{paras(h["contact_text"], "lede")}
<p class="contact__value" style="margin-top:1.1em"><a href="mailto:{site["email"]}">{site["email"]}</a></p>
<p class="btnrow" style="margin-top:1.5em">
<a class="btn btn--primary" href="contato/">Entrar em contato <span class="btn__arrow" aria-hidden="true">→</span></a>
</p>
</div>
</div>
</div>
</section>
"""
    out += footer(site, depth)
    write("index.html", out)


# ---- quem somos -----------------------------------------------------------


def page_quem_somos(site, people) -> None:
    depth = 1
    s = site["quem_somos"]

    linhas = "".join(
        f'<li><span class="axes__num">{i + 1:02d}</span><h3>{e(l["title"])}</h3>'
        f'<p>{inline(l["text"])}</p></li>'
        for i, l in enumerate(s["linhas"])
    )
    timeline = "".join(
        f'<li><span class="timeline__year">{e(t["year"])}</span>'
        f'<h3 class="timeline__title">{e(t["title"])}</h3>'
        f'<div class="timeline__body">{paras(t["text"])}</div></li>'
        for t in s["timeline"]
    )

    out = head(s["title"] + " — Pátria Grande Produções", site["seo"]["quem_somos"], "quem-somos/", depth)
    out += header("quem-somos/", depth)
    out += f"""
<section class="band band--red pagehead">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("Quem somos", "A produtora")}
<h1 class="pagehead__title">{inline(s["title"])}</h1>
<p class="pagehead__lede">{inline(s["lede"])}</p>
</div>
</section>

<section class="band band--paper">
<div class="shell">
<div class="split split--aside">
<div class="prose prose--wide" data-reveal>{paras(s["institucional"])}</div>
<aside class="split__sticky" data-reveal>
<img src="{up(depth)}assets/img/marca/logotipo-completo-800.webp" width="800" height="800" alt="Logotipo completo da Pátria Grande Produções: a América Latina desenhada com o sul para cima, cercada por sol, lua, aves, peixe, água e cidade." loading="lazy" decoding="async">
<p class="archivecaption">{inline(s["logo_caption"])}</p>
</aside>
</div>
<p class="manifesto" style="margin-top:clamp(36px,4.4vw,64px);color:var(--pg-red)" data-reveal>{inline(s["fecho"])}</p>
</div>
</section>

<section class="band band--deep">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("01", "O conceito")}
<div class="split">
<div data-reveal><h2>{inline(s["conceito_titulo"])}</h2></div>
<div class="prose" data-reveal>{paras(s["conceito"])}</div>
</div>
</div>
</section>

<section class="band band--paper">
<div class="shell">
{eyebrow("02", "A marca")}
<div class="split">
<div data-reveal><h2>{inline(s["cartografia_titulo"])}</h2></div>
<div class="prose" data-reveal>{paras(s["cartografia"])}</div>
</div>
</div>
</section>

{fullbleed(s.get("fullbleed_image"), depth)}

<section class="band band--paper">
<div class="shell">
{eyebrow("03", "Origem")}
<div class="split">
<div data-reveal><h2>{inline(s["origem_titulo"])}</h2></div>
<div class="prose" data-reveal>{paras(s["origem"])}</div>
</div>
<ol class="timeline" style="margin-top:clamp(30px,3.6vw,52px)" data-reveal>{timeline}</ol>
</div>
</section>

<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("04", "Linhas de atuação")}
<h2 data-reveal>{inline(s["linhas_titulo"])}</h2>
<ul class="axes" style="margin-top:clamp(26px,3.2vw,46px);{axes_cols(len(s["linhas"]))}" data-reveal>{linhas}</ul>
</div>
</section>

<section class="band band--yellow band--tight">
<div class="shell">
<div class="split" style="align-items:center">
<div data-reveal><h2>{inline(s["cta_titulo"])}</h2></div>
<div data-reveal>
{paras(s["cta_texto"], "lede")}
<p class="btnrow" style="margin-top:1.5em">
<a class="btn btn--primary" href="../projetos/">Projetos <span class="btn__arrow" aria-hidden="true">→</span></a>
<a class="btn btn--ghost" href="../equipe/">Equipe</a>
</p>
</div>
</div>
</div>
</section>
"""
    out += footer(site, depth)
    write("quem-somos/index.html", out)


# ---- arquivo de projetos --------------------------------------------------


def page_projetos(site, projects) -> None:
    depth = 1
    s = site["projetos"]

    executed = [p for p in projects
                if "executado" in ("executado andamento" if p.get("ongoing") else "executado")]
    ongoing = [p for p in projects if p.get("ongoing")]

    filters = "".join(
        f'<button class="filters__btn" type="button" data-filter="{e(f["key"])}" aria-pressed="false">{e(f["label"])}</button>'
        for f in s["filters"]
    )
    tabs = "".join(
        f'<button class="tabs__btn" type="button" role="tab" id="tab-{e(t["key"])}" '
        f'aria-controls="painel-projetos" data-tab="{e(t["key"])}" aria-selected="false">{e(t["label"])}</button>'
        for t in s["tabs"]
    )
    cards = "".join(project_card(p, depth) for p in projects)

    out = head("Projetos — Pátria Grande Produções", site["seo"]["projetos"], "projetos/", depth)
    out += header("projetos/", depth)
    out += f"""
<section class="band band--deep pagehead">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("Projetos", "Arquivo vivo")}
<h1 class="pagehead__title">{inline(s["title"])}</h1>
<p class="pagehead__lede">{inline(s["lede"])}</p>
</div>
</section>

<section class="band band--paper">
<div class="shell">
<div class="tabs" role="tablist" aria-label="Situação dos projetos" data-tabs>{tabs}</div>
<fieldset class="filters" data-filters>
<legend class="meta">Filtrar por tipo de projeto</legend>
{filters}
</fieldset>
<h2 class="visually-hidden">Projetos</h2>
<p class="meta" data-filter-count aria-live="polite">{len(executed)} projetos realizados</p>
<div id="painel-projetos" role="tabpanel" tabindex="0" style="margin-top:clamp(20px,2.4vw,32px)">
<ul class="projectgrid">
{cards}
</ul>
</div>
{note(s["note_label"], s["note"])}
</div>
</section>
"""
    out += footer(site, depth)
    write("projetos/index.html", out)


# ---- página de projeto ----------------------------------------------------


def page_projeto(site, p, by_slug) -> None:
    depth = 2

    # Campo sem dado sai da ficha. O §78 é explícito: onde não há informação,
    # ocultar o campo — nunca imprimir zero, travessão ou território inventado.
    meta_items = [
        ("Situação", "Realizado" if p["history"] else "Sem data confirmada"),
        ("Categoria", " · ".join(CATEGORY_LABEL.get(c, c) for c in p["categories"])),
    ]
    if p["years"]:
        meta_items.append(("Execução", p["years_label"]))
    if p["cities"]:
        meta_items.append(("Território", " · ".join(p["cities"])))
    if p.get("funding_short"):
        meta_items.append(("Fomento", " · ".join(p["funding_short"])))
    metastrip = "".join(
        f'<div><span class="metastrip__k">{e(k)}</span><span class="metastrip__v">{e(v)}</span></div>'
        for k, v in meta_items
    )

    hero_media = ""
    if p.get("hero_image"):
        hero_media = (
            f'<div class="projecthead__media">'
            + picture(p["hero_image"], depth, sizes="100vw", loading="eager", ratio="16:9")
            + "</div>"
            + f'<div class="shell" style="padding-top:.9em"><p class="archivecaption">{inline(p["hero_image"]["caption"])}</p></div>'
        )

    history = "".join(
        f'<li><span class="timeline__year">{e(h["year"])}</span>'
        f'<h3 class="timeline__title">{e(h["label"])}</h3>'
        f'<div class="timeline__body">{paras(h["text"])}</div></li>'
        for h in p["history"]
    )

    credit_rows = "".join(
        f'<div class="credits__row"><dt>{e(c["role"])}</dt><dd>{e(c["name"])}'
        + (f' <span class="meta" style="text-transform:none">({e(c["year"])})</span>' if c.get("year") else "")
        + "</dd></div>"
        for c in p.get("credits", [])
    )
    for i, f in enumerate(p.get("funding", [])):
        credit_rows += (
            f'<div class="credits__row"><dt>{"Fomento" if i == 0 else "&nbsp;"}</dt>'
            f'<dd style="font-weight:500">{inline(f)}</dd></div>'
        )
    credits = f'<dl class="credits">{credit_rows}</dl>' if credit_rows else ""

    # Bloco da edição em andamento — separado do histórico, com selo, e sem
    # nenhum número previsto apresentado como resultado.
    ongoing_section = ""
    if p.get("ongoing"):
        o = p["ongoing"]
        ongoing_section = f"""
<section class="band band--yellow">
<div class="shell">
{eyebrow("Agora", "Edição em andamento")}
<div class="split">
<div data-reveal>
<p style="margin-bottom:1em">{badge("Edição em andamento")}</p>
<h2>{inline(o["title"])}</h2>
</div>
<div class="prose" data-reveal>
{paras(o["text"])}
<p class="meta" style="margin-top:1.4em">{inline(o["quando_onde"])}</p>
</div>
</div>
</div>
</section>"""

    stats = stats_block(p.get("metrics", []))
    stats_section = ""
    if stats:
        stats_section = f"""
<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("Registro", "Números com fonte")}
<div class="split">
<div data-reveal>
<h2>O que está documentado</h2>
<p class="meta" style="margin-top:1.1em;max-width:34ch">Cada número traz a origem do dado. Onde não há registro consolidado, o site não apresenta número.</p>
</div>
<div data-reveal>{stats}</div>
</div>
</div>
</section>"""

    gal = gallery(p.get("gallery", []), depth)
    gallery_section = ""
    if gal:
        gallery_section = f"""
<section class="band band--deep">
<div class="shell">
{eyebrow("Galeria", "Registros do projeto")}
<h2 data-reveal>{e(p["short_title"])} em imagens</h2>
<div style="margin-top:clamp(22px,2.8vw,40px)" data-reveal>{gal}</div>
</div>
</section>"""

    pending = ""
    if p.get("pending"):
        pending = f"""
<section class="band band--paper band--tight">
<div class="shell">{note("Em aberto", p["pending"])}</div>
</section>"""

    related = ""
    if p.get("related"):
        items = "".join(project_card(by_slug[s], depth) for s in p["related"] if s in by_slug)
        related = f"""
<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("Relacionados", "No mesmo eixo")}
<h2 data-reveal>Outros projetos</h2>
<ul class="projectgrid" style="margin-top:clamp(20px,2.4vw,32px)" data-reveal>{items}</ul>
</div>
</section>"""

    og = None
    if p.get("hero_image"):
        big = max(p["hero_image"]["widths"])
        og = f'{BASE_URL}/assets/img/fotos/{p["hero_image"]["name"]}-{big}.jpg'

    out = head(f'{p["short_title"]} — Pátria Grande Produções', p["seo_description"],
               f'projetos/{p["slug"]}/', depth, og_image=og)
    out += header("projetos/", depth)
    out += f"""
<article class="projecthead">
{hero_media}
<div class="band band--{p["band"]} projecthead__body">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
<p class="eyebrow"><span class="eyebrow__num"><a href="../" style="color:inherit">Projetos</a></span><span>{e(CATEGORY_LABEL.get(p["categories"][0], p["categories"][0]))}</span></p>
<div class="projecthead__flags">{badge("Edição em andamento") if p.get("ongoing") else ""}</div>
<h1 class="projecthead__title">{inline(p["title"])}</h1>
<p class="projecthead__lede">{inline(p["lede"])}</p>
<div class="metastrip">{metastrip}</div>
</div>
</div>
</article>

<section class="band band--paper">
<div class="shell">
<div class="split split--aside">
<div class="prose prose--wide" data-reveal>
{eyebrow("01", "O projeto")}
{paras(p["summary"])}
</div>
<aside class="split__sticky" data-reveal>
{f'<blockquote class="pull">{inline(p["pull"])}</blockquote>' if p.get("pull") else ""}
</aside>
</div>
</div>
</section>
{ongoing_section}
<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("02", "Conceito")}
<div class="split">
<div data-reveal><h2>{inline(p["concept_title"])}</h2></div>
<div class="prose" data-reveal>{paras(p["concept"])}{bullets(p.get("actions_text", ""))}</div>
</div>
</div>
</section>

<section class="band band--paper">
<div class="shell">
{eyebrow("03", "Execução")}
<div class="split">
<div data-reveal>
<h2>O que já aconteceu</h2>
<p class="meta" style="margin-top:1.1em;max-width:34ch">Só entram aqui edições e ações efetivamente realizadas.</p>
</div>
<ol class="timeline" data-reveal>{history}</ol>
</div>
</div>
</section>
{stats_section}
<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("04", "Território")}
<div class="split">
<div data-reveal><h2>Onde aconteceu</h2></div>
<div class="prose" data-reveal>{paras(p["territory"])}</div>
</div>
</div>
</section>
{gallery_section}
<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("05", "Ficha técnica")}
<div class="split">
<div data-reveal>
<h2>Equipe e fomento</h2>
<p class="meta" style="margin-top:1.1em;max-width:34ch">Créditos documentados. Os créditos completos por edição estão em consolidação.</p>
</div>
<div data-reveal>{credits}</div>
</div>
</div>
</section>
{pending}{related}
"""
    out += footer(site, depth)
    write(f'projetos/{p["slug"]}/index.html', out)


# ---- serviços -------------------------------------------------------------


def page_servicos(site, services, by_slug) -> None:
    depth = 1
    s = site["servicos"]
    cards = "".join(service_card(sv, depth, i) for i, sv in enumerate(services, 1))

    out = head("Serviços — Pátria Grande Produções", site["seo"]["servicos"], "servicos/", depth)
    out += header("servicos/", depth)
    out += f"""
<section class="band band--red pagehead">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("Serviços", "O que fazemos")}
<h1 class="pagehead__title">{inline(s["title"])}</h1>
<p class="pagehead__lede">{inline(s["lede"])}</p>
</div>
</section>

<section class="band band--paper">
<div class="shell">
<div class="prose prose--wide" data-reveal>{paras(s["intro"])}</div>
<h2 class="visually-hidden">Os quatro serviços</h2>
<ul class="services" style="margin-top:clamp(28px,3.4vw,52px)" data-reveal>{cards}</ul>
</div>
</section>

{fullbleed(s.get("fullbleed_image"), depth)}

<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("Como funciona", "Pedir um orçamento")}
<div class="split">
<div data-reveal><h2>{inline(s["como_titulo"])}</h2></div>
<div class="prose" data-reveal>
{paras(s["como_texto"])}
<p class="btnrow" style="margin-top:1.6em">
<a class="btn btn--primary" href="mailto:{site["email"]}?subject={e(s["mailto_subject"])}">Solicitar orçamento <span class="btn__arrow" aria-hidden="true">→</span></a>
<a class="btn btn--ghost" href="../contato/">Outras formas de contato</a>
</p>
</div>
</div>
</div>
</section>
"""
    out += footer(site, depth)
    write("servicos/index.html", out)


def page_servico(site, s, num, services, by_slug) -> None:
    depth = 2

    proof = ""
    if s.get("related_projects"):
        items = "".join(project_card(by_slug[x], depth) for x in s["related_projects"] if x in by_slug)
        proof = f"""
<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("Prova", "Projetos que sustentam")}
<h2 data-reveal>Projetos que comprovam</h2>
<ul class="projectgrid" style="margin-top:clamp(20px,2.4vw,32px)" data-reveal>{items}</ul>
</div>
</section>"""

    others = "".join(
        service_card(o, depth, i) for i, o in enumerate(services, 1) if o["slug"] != s["slug"]
    )

    out = head(f'{s["title"]} — Pátria Grande Produções', s["seo"], f'servicos/{s["slug"]}/', depth)
    out += header("servicos/", depth)
    out += f"""
<section class="band band--red pagehead">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
<p class="eyebrow"><span class="eyebrow__num"><a href="../" style="color:inherit">Serviços</a></span><span>{num:02d}</span></p>
<h1 class="pagehead__title">{inline(s["title"])}</h1>
<p class="pagehead__lede">{inline(s["lede"])}</p>
</div>
</section>

<section class="band band--paper">
<div class="shell">
<div class="split split--aside">
<div class="prose prose--wide" data-reveal>{paras(s["resumo"])}</div>
<aside class="split__sticky" data-reveal>
<div class="note">
<b class="note__label">Solicitar orçamento</b>
<p>{inline(s["cta_help"])}</p>
<p class="btnrow" style="margin-top:1.2em">
<a class="btn btn--primary" href="mailto:{site["email"]}?subject={e(s["mailto_subject"])}">{e(s["cta"])} <span class="btn__arrow" aria-hidden="true">→</span></a>
</p>
</div>
</aside>
</div>
</div>
</section>

<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("01", "O que entra")}
<div class="split">
<div data-reveal><h2>{inline(s["entregas_titulo"])}</h2></div>
<div class="prose" data-reveal>
{bullets(s["entregas"]).replace('<ul>', '<ul class="deliverables">')}
{note("Antes de fechar escopo", s["limites"]) if s.get("limites") else ""}
</div>
</div>
</div>
</section>

<section class="band band--deep">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("02", "Experiência")}
<div class="split">
<div data-reveal><h2>{inline(s["experiencia_titulo"])}</h2></div>
<div class="prose" data-reveal>{paras(s["experiencia"])}</div>
</div>
</div>
</section>
{proof}
<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("Serviços", "Outros")}
<ul class="services" style="margin-top:clamp(20px,2.4vw,32px)" data-reveal>{others}</ul>
</div>
</section>
"""
    out += footer(site, depth)
    write(f'servicos/{s["slug"]}/index.html', out)


# ---- equipe ---------------------------------------------------------------


def page_equipe(site, people) -> None:
    depth = 1
    s = site["equipe"]
    nucleo = [p for p in people if p["tier"] == "nucleo"]
    rede = [p for p in people if p["tier"] != "nucleo"]

    out = head("Equipe — Pátria Grande Produções", site["seo"]["equipe"], "equipe/", depth)
    out += header("equipe/", depth)
    out += f"""
<section class="band band--red pagehead">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("Equipe", "Quem faz a Pátria Grande")}
<h1 class="pagehead__title">{inline(s["title"])}</h1>
<p class="pagehead__lede">{inline(s["lede"])}</p>
</div>
</section>

<section class="band band--paper">
<div class="shell">
{eyebrow("01", "Núcleo")}
<div class="split">
<div data-reveal><h2>{inline(s["nucleo_title"])}</h2></div>
<div class="prose" data-reveal>{paras(s["nucleo_text"])}</div>
</div>
<ul class="teamgrid" style="margin-top:clamp(32px,3.8vw,58px)" data-reveal>
{"".join(team_card(p, depth) for p in nucleo)}
</ul>
</div>
</section>

<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("02", "Rede")}
<div class="split">
<div data-reveal><h2>{inline(s["rede_title"])}</h2></div>
<div class="prose" data-reveal>{paras(s["rede_text"])}</div>
</div>
<ul class="teamgrid teamgrid--compact" style="margin-top:clamp(32px,3.8vw,58px)" data-reveal>
{"".join(team_card(p, depth, compact=True) for p in rede)}
</ul>
</div>
</section>
"""
    out += footer(site, depth)
    write("equipe/index.html", out)


# ---- contato --------------------------------------------------------------


def page_contato(site, services) -> None:
    depth = 1
    s = site["contato"]

    def contact_block(b: dict) -> str:
        # "values" vira uma linha por item. O dado não carrega marcação: <br>
        # dentro do JSON seria escapado por inline() e apareceria como texto.
        vals = b.get("values") or [b["value"]]
        body = "".join(f'<p class="contact__value">{inline(v)}</p>' for v in vals)
        return (f'<div class="contact__block"><h3>{e(b["title"])}</h3>{body}'
                f'<p class="meta" style="margin-top:.8em">{inline(b["note"])}</p></div>')

    blocks = "".join(contact_block(b) for b in s["blocks"])
    reasons = "".join(f"<li>{inline(r)}</li>" for r in s["reasons"])
    roteiro = bullets(s["roteiro"])
    kit = "".join(
        f'<div class="contact__block"><h3>{e(k["title"])}</h3><p>{inline(k["text"])}</p></div>'
        for k in s["kit"]
    )

    out = head("Contato — Pátria Grande Produções", site["seo"]["contato"], "contato/", depth)
    out += header("contato/", depth)
    out += f"""
<section class="band band--red pagehead">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("Contato", "Falar com a produtora")}
<h1 class="pagehead__title">{inline(s["title"])}</h1>
<p class="pagehead__lede">{inline(s["lede"])}</p>
</div>
</section>

<section class="band band--paper">
<div class="shell">
<h2 class="visually-hidden">Canais de contato</h2>
<div class="contact" data-reveal>{blocks}</div>
</div>
</section>

<section class="band band--yellow">
<div class="shell">
{eyebrow("Orçamento", "O que informar")}
<div class="split">
<div data-reveal><h2>{inline(s["roteiro_titulo"])}</h2></div>
<div class="prose" data-reveal>
{paras(s["roteiro_intro"])}
{roteiro}
<p class="btnrow" style="margin-top:1.6em">
<a class="btn btn--primary" href="mailto:{site["email"]}?subject={e(s["mailto_subject"])}">Escrever para a produtora <span class="btn__arrow" aria-hidden="true">→</span></a>
</p>
</div>
</div>
</div>
</section>

<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("01", "O que costuma chegar por aqui")}
<div class="split">
<div data-reveal><h2>{inline(s["reasons_title"])}</h2></div>
<div class="prose" data-reveal>{paras(s["reasons_text"])}<ul>{reasons}</ul></div>
</div>
</div>
</section>

<section class="band band--paper band--tight">
<div class="shell">
{eyebrow("02", "Imprensa")}
<div class="split">
<div data-reveal><h2>{inline(s["kit_titulo"])}</h2></div>
<div data-reveal>
{paras(s["kit_texto"], "lede")}
<div class="contact" style="margin-top:clamp(22px,2.8vw,38px)">{kit}</div>
</div>
</div>
</div>
</section>
"""
    out += footer(site, depth)
    write("contato/index.html", out)


# ---- 404 ------------------------------------------------------------------


def page_404(site) -> None:
    global _ABS_ROOT
    depth = 0
    # Caminho de raiz só é seguro quando o site vive no ápice do domínio.
    _ABS_ROOT = "/" not in BASE_URL.split("://", 1)[-1]
    out = head("Página não encontrada — Pátria Grande Produções", site["seo"]["404"], "404.html", depth)
    out += header("__none__", depth)
    out += f"""
<section class="band band--deep pagehead" style="min-height:62svh;display:flex;align-items:center">
{cartografia("cartografia cartografia--canto")}
<div class="shell">
{eyebrow("404", "Página não encontrada")}
<h1 class="pagehead__title">Esta sessão não está em cartaz.</h1>
<p class="pagehead__lede">O endereço que você abriu não existe, ou mudou de lugar. Os projetos, os serviços e a equipe continuam todos no site.</p>
<p class="btnrow" style="margin-top:clamp(26px,3vw,42px)">
<a class="btn btn--primary" href="projetos/">Ver os projetos <span class="btn__arrow" aria-hidden="true">→</span></a>
<a class="btn btn--ghost" href="./">Voltar ao início</a>
</p>
</div>
</section>
"""
    out += footer(site, depth)
    write("404.html", out)
    _ABS_ROOT = False


# ---- sitemap --------------------------------------------------------------


def page_sitemap(projects, services) -> None:
    paths = ["", "quem-somos/", "projetos/", "servicos/", "equipe/", "contato/"]
    paths += [f'projetos/{p["slug"]}/' for p in projects]
    paths += [f'servicos/{s["slug"]}/' for s in services]
    urls = "\n".join(
        f"  <url><loc>{BASE_URL}/{p}</loc>"
        f"<priority>{'1.0' if p == '' else '0.8' if p.count('/') <= 1 else '0.6'}</priority></url>"
        for p in paths
    )
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{urls}\n</urlset>\n")


if __name__ == "__main__":
    build()
