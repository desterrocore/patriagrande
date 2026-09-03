#!/usr/bin/env python3
"""
Verificação do site — roda no CI antes de publicar e sai com código != 0 se
algo estiver errado.

Metade destas checagens é técnica (link quebrado, imagem sem alt, título
duplicado). A outra metade faz cumprir as regras editoriais do relatório-base,
que são a razão de o site existir na forma em que existe:

  - nada de 2026 em diante aparece como executado (§5, §18);
  - nenhum projeto da lista proibida vira página de portfólio (§18);
  - todo número publicado carrega a fonte do dado (§42);
  - nenhum dado pessoal sensível vai ao ar (§28.8).

    python3 tools/check-site.py
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"

# §18 — projetos que não podem virar página de portfólio executado.
FORBIDDEN_PROJECTS = [
    "cinemina",
    "cineclube fundação",
    "cine dandara",
    "colo de dandara",
    "cineclube amarildo",
    "cinegritude",
    "festival de hip-hop",
]

# §28.8 — dados que nunca devem ser publicados.
SENSITIVE = [
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "CNPJ"),
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "CPF"),
    (re.compile(r"MANOEL ISIDORO", re.I), "endereço do proponente"),
    (re.compile(r"meucnpj@", re.I), "e-mail contábil interno"),
]

# Diretórios que existem no repositório mas não são rotas do site. "_site" é o
# mais importante: o workflow monta a cópia a publicar ANTES de rodar esta
# verificação, e sem esta lista o verificador compara cada página com o clone
# dela mesma e acusa título duplicado.
NOT_ROUTES = {"_site", "assets", "source", "tools", "reference-content", "node_modules"}

# O histórico de um projeto só admite execução concluída. 2026 é o ano corrente,
# e o que acontece em 2026 vive no bloco "em andamento", nunca na linha do tempo.
FUTURE_FROM = 2026

problems: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


class PageParser(HTMLParser):
    """Coleta o que precisa ser verificado em cada página."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self._in_title = False
        self.description = None
        self.links: list[str] = []
        self.imgs: list[dict] = []
        self.h1_count = 0
        self.lang = None
        self.ids: list[str] = []
        self.buttons_without_type = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name") == "description":
            self.description = a.get("content")
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "button" and "type" not in a:
            self.buttons_without_type += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return "".join(self.title_parts).strip()


def check_data() -> None:
    projects = json.loads((SRC / "projetos.json").read_text(encoding="utf-8"))
    people = json.loads((SRC / "equipe.json").read_text(encoding="utf-8"))
    slugs = {p["slug"] for p in projects}

    for p in projects:
        where = f'projetos.json / {p["slug"]}'

        for name in FORBIDDEN_PROJECTS:
            if name in p["title"].lower():
                fail(f'{where}: "{p["title"]}" está na lista do §18 e não pode ser portfólio.')

        for h in p["history"]:
            if int(h["year"]) >= FUTURE_FROM:
                fail(
                    f'{where}: histórico traz {h["year"]} — o site só publica execução concluída '
                    f"(§5 e §18: {FUTURE_FROM}+ não entra)."
                )

        for m in p.get("metrics", []):
            if not m.get("source", "").strip():
                fail(f'{where}: métrica "{m.get("value")} {m.get("label")}" sem fonte (§42).')

        for rel in p.get("related", []):
            if rel not in slugs:
                fail(f"{where}: projeto relacionado inexistente: {rel}")
            if rel == p["slug"]:
                fail(f"{where}: projeto relacionado a si mesmo.")

        if not p.get("history"):
            fail(f"{where}: nenhuma execução registrada — um projeto sem execução não é portfólio.")

        # §31 e §78: previsão não é resultado. Um projeto em andamento pode ter
        # meta, mas ela nunca entra como métrica realizada.
        if p.get("ongoing"):
            o = p["ongoing"]
            for key in ("title", "text", "quando_onde"):
                if not o.get(key):
                    fail(f"{where}: bloco em andamento sem {key}.")
            blob = " ".join(str(o.get(k, "")) for k in o)
            for word in ("impactadas", "beneficiários", "alcançou"):
                if word in blob.lower() and "previst" not in blob.lower():
                    fail(f'{where}: bloco em andamento usa "{word}" sem marcar que é previsão (§31).')

        if not p.get("seo_description"):
            fail(f"{where}: falta seo_description.")
        elif len(p["seo_description"]) > 160:
            fail(f'{where}: seo_description com {len(p["seo_description"])} caracteres (máx. 160).')

    services = json.loads((SRC / "servicos.json").read_text(encoding="utf-8"))
    service_slugs = {s["slug"] for s in services}
    for sv in services:
        where = f'servicos.json / {sv["slug"]}'
        for key in ("title", "lede", "resumo", "entregas", "experiencia", "cta", "seo", "mailto_subject"):
            if not str(sv.get(key, "")).strip():
                fail(f"{where}: falta {key}.")
        if len(sv.get("seo", "")) > 160:
            fail(f'{where}: seo com {len(sv["seo"])} caracteres (máx. 160).')
        for rel in sv.get("related_projects", []):
            if rel not in slugs:
                fail(f"{where}: projeto relacionado inexistente: {rel}")
    if len(service_slugs) != len(services):
        fail("servicos.json: slug duplicado.")

    seen_people = set()
    for person in people:
        where = f'equipe.json / {person["slug"]}'
        if person["slug"] in seen_people:
            fail(f"{where}: slug duplicado.")
        seen_people.add(person["slug"])

        if person["tier"] not in ("nucleo", "rede"):
            fail(f'{where}: tier inválido "{person["tier"]}".')

        for s, _title in person.get("projects", []):
            if s not in slugs:
                fail(f"{where}: aponta para projeto inexistente: {s}")

        words = len(person.get("bio", "").split())
        if person["tier"] == "nucleo" and not 55 <= words <= 165:
            notes.append(f"{where}: bio do núcleo com {words} palavras (o alvo do §6 é 70–120).")

        if not person.get("bio_short"):
            fail(f"{where}: falta bio_short (usada nos cards compactos).")

    nucleo = [p for p in people if p["tier"] == "nucleo"]
    if not nucleo:
        fail("equipe.json: nenhum integrante marcado como núcleo.")
    # A v2 fecha o núcleo público em sete pessoas. Mais que isso é sinal de que
    # alguém voltou da rede sem decisão editorial.
    if len(nucleo) != 7:
        notes.append(f"equipe.json: {len(nucleo)} pessoas no núcleo — a v2 define sete.")


def check_pages() -> None:
    def is_route(path: Path) -> bool:
        top = path.relative_to(ROOT).parts[0]
        return top not in NOT_ROUTES and not top.startswith((".", "_"))

    pages = sorted(
        [ROOT / "index.html", ROOT / "404.html"]
        + [p for p in ROOT.glob("*/index.html") if is_route(p)]
        + [p for p in ROOT.glob("projetos/*/index.html") if is_route(p)]
        + [p for p in ROOT.glob("servicos/*/index.html") if is_route(p)]
    )
    if not pages:
        fail("Nenhuma página gerada — rode tools/build-site.py.")
        return

    titles: dict[str, str] = {}

    for page in pages:
        rel = page.relative_to(ROOT).as_posix()
        text = page.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)

        if parser.lang != "pt-BR":
            fail(f'{rel}: <html lang> é "{parser.lang}", deveria ser pt-BR.')
        if not parser.title:
            fail(f"{rel}: sem <title>.")
        elif parser.title in titles:
            fail(f'{rel}: título repetido de {titles[parser.title]} — "{parser.title}".')
        else:
            titles[parser.title] = rel

        if not parser.description:
            fail(f"{rel}: sem meta description.")
        elif len(parser.description) > 165:
            fail(f"{rel}: meta description com {len(parser.description)} caracteres.")

        if parser.h1_count != 1:
            fail(f"{rel}: {parser.h1_count} elementos <h1> (deve haver exatamente um).")

        if parser.buttons_without_type:
            fail(f"{rel}: {parser.buttons_without_type} <button> sem type explícito.")

        for img in parser.imgs:
            if img.get("alt") is None:
                fail(f'{rel}: <img src="{img.get("src")}"> sem atributo alt.')
            if not img.get("loading"):
                notes.append(f'{rel}: <img src="{img.get("src")}"> sem loading.')

        if "id=\"conteudo\"" not in text:
            fail(f"{rel}: falta o alvo #conteudo do link de pular navegação.")

        for pattern, label in SENSITIVE:
            if pattern.search(text):
                fail(f"{rel}: publica {label} — remover (§28.8).")

        # Links internos
        for href in parser.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
                continue
            target = (page.parent / href).resolve()
            if target.is_dir():
                target = target / "index.html"
            elif href.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                fail(f"{rel}: link quebrado → {href}")

    notes.append(f"{len(pages)} páginas verificadas.")


def check_brand() -> None:
    """A cartografia é inline em todas as páginas e o SVG é gerado por
    tools/trace-brand.py. Se ele sumir, o site perde o grafismo sem avisar."""
    svg = ROOT / "assets" / "img" / "marca" / "mapa-patria-grande.svg"
    if not svg.exists():
        fail("assets/img/marca/mapa-patria-grande.svg ausente — rode tools/trace-brand.py.")
    for name in ("wordmark-amarelo-450.png", "assinatura-amarela-600.png",
                 "favicon.ico", "favicon-96.png", "favicon-180.png",
                 "og-patria-grande.png", "logotipo-completo-800.webp"):
        if not (ROOT / "assets" / "img" / "marca" / name).exists():
            fail(f"assets/img/marca/{name} ausente — rode tools/build-brand.py.")

    # A Squarely do pacote é "free for personal use ONLY" e não pode ser servida.
    for font in (ROOT / "assets" / "fonts").glob("*"):
        if "squarely" in font.name.lower():
            fail(f"{font.name}: a Squarely não tem licença web — remover de assets/fonts/.")


def check_assets() -> None:
    """Cada entrada do manifesto tem de ter TODOS os arquivos que o srcset promete.

    Conferir só se "existe alguma saída" deixa passar o caso que de fato quebra:
    uma largura presente em WebP e ausente em JPEG. O navegador que não suporta
    WebP segue o srcset do <img> e recebe 404 — e a página fica com buraco no
    lugar da foto, sem nenhum aviso no build.
    """
    manifest = json.loads((SRC / "images.json").read_text(encoding="utf-8"))
    for group, entries in manifest.items():
        out_dir = ROOT / "assets" / "img" / group
        for entry in entries:
            src = ROOT / entry["src"]
            if not src.exists():
                notes.append(
                    f'images.json / {group} / {entry["name"]}: original ausente — '
                    "normal em clone sem reference-content/."
                )

            missing = []
            for width in entry["widths"]:
                stem = f'{entry["name"]}-{width}'
                for ext in ("webp", "jpg"):
                    if not (out_dir / f"{stem}.{ext}").exists():
                        missing.append(f"{stem}.{ext}")
            if missing:
                fail(
                    f'images.json / {group} / {entry["name"]}: faltam '
                    f'{len(missing)} arquivo(s) — {", ".join(missing[:4])}'
                    f'{"…" if len(missing) > 4 else ""}. Rode tools/build-images.py.'
                )

    # Arquivo em assets/img que nenhum manifesto reivindica é lixo de build
    # anterior: some do site sem ninguém perceber, e engorda o repositório.
    declared = set()
    for group, entries in manifest.items():
        for entry in entries:
            for width in entry["widths"]:
                for ext in ("webp", "jpg"):
                    declared.add(f'assets/img/{group}/{entry["name"]}-{width}.{ext}')

    for group in manifest:
        for f in sorted((ROOT / "assets" / "img" / group).glob("*")):
            rel = f.relative_to(ROOT).as_posix()
            if rel not in declared:
                notes.append(f"{rel}: não consta em images.json — órfão de build anterior?")


def main() -> int:
    check_data()
    check_pages()
    check_brand()
    check_assets()

    for n in notes:
        print(f"  · {n}")
    sys.stdout.flush()

    if problems:
        print("\nProblemas:", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        print(f"\n{len(problems)} problema(s).", file=sys.stderr)
        return 1

    print("\nTudo certo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
