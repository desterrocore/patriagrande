#!/usr/bin/env python3
"""
Monta os arquivos de dados do site a partir das duas fontes de conteúdo.

    source/pesquisa-fontes.json   levantamento nos currículos, portfólios e
                                  apresentações — traz, para cada afirmação, de
                                  qual arquivo ela veio
    source/v2-conteudo.json       a redação feita para a versão 2 do site:
                                  serviços, "Quem somos", Calango, projetos em
                                  andamento, oficinas de dança, equipe e a
                                  atribuição das fotografias

e escreve source/site.json, servicos.json, projetos.json e equipe.json —
que são o que o gerador de páginas lê.

Este script roda quando o conteúdo bruto muda. No dia a dia, corrigir uma
biografia ou um crédito se faz direto no JSON de destino: rodá-lo de novo
SOBRESCREVE edições manuais.

    python3 tools/build-data.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"

RESEARCH = json.loads((SRC / "pesquisa-fontes.json").read_text(encoding="utf-8"))
V2 = json.loads((SRC / "v2-conteudo.json").read_text(encoding="utf-8"))["blocos"]
IMAGES = json.loads((SRC / "images.json").read_text(encoding="utf-8"))

RAW_PEOPLE = RESEARCH["pessoas"]
RAW_PROJECTS = RESEARCH["projetos"]


def b(key: str, default: str = "") -> str:
    return V2.get(key, default).strip()


def parse_fields(text: str) -> dict:
    """Lê um bloco em linhas "rótulo: valor" — o formato que a atribuição de
    fotografia usa."""
    out = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


# ==========================================================================
# 1. Serviços
# ==========================================================================

SERVICE_SLUGS = [
    "producao-executiva",
    "projecao-e-equipamentos",
    "traducao-e-legendagem",
    "oficinas-e-formacao",
]

# Limites que a especificação impõe e que o site precisa dizer em voz alta, em
# vez de fingir que a oferta é maior do que a decisão interna já tomada.
SERVICE_LIMITS = {
    "projecao-e-equipamentos":
        "O dimensionamento é feito caso a caso. Esta página não publica lista de "
        "equipamentos, potências ou dimensões de tela: a estrutura é montada a partir "
        "do local, do horário e do público de cada sessão, e o orçamento sai depois "
        "dessa conversa.",
    "traducao-e-legendagem":
        "Os pares de idiomas atendidos são definidos projeto a projeto. Antes de fechar "
        "escopo, vale conferir também se a demanda inclui legendagem descritiva, "
        "audiodescrição ou janela de Libras — recursos que a produtora já usou em "
        "programação própria e que entram por composição de equipe.",
}

SERVICE_PROOF = {
    "producao-executiva": ["fica-garopaba", "flaca", "cine-retrata"],
    "projecao-e-equipamentos": ["cineclube-marighella", "vozes-veladas", "cineclube-patria-grande"],
    "traducao-e-legendagem": ["fica-garopaba", "flaca"],
    "oficinas-e-formacao": ["abrindo-a-caixa-preta", "arte-para-voar", "educa-ambiental"],
}

MAILTO = {
    "producao-executiva": "Produção executiva — pedido de orçamento",
    "projecao-e-equipamentos": "Estrutura de projeção — pedido de orçamento",
    "traducao-e-legendagem": "Tradução e legendagem — pedido de orçamento",
    "oficinas-e-formacao": "Oficinas e formação — pedido de orçamento",
}

CTA_HELP = (
    "Escreva contando o que precisa, em que cidade, em que data e para que tamanho de "
    "público. Com essas informações o retorno já vem com orçamento."
)

services = []
for slug in SERVICE_SLUGS:
    services.append({
        "slug": slug,
        "title": b(f"servico.{slug}.titulo"),
        "lede": b(f"servico.{slug}.lede"),
        "resumo": b(f"servico.{slug}.resumo"),
        "entregas_titulo": "O que entra no serviço",
        "entregas": b(f"servico.{slug}.entregas"),
        "limites": SERVICE_LIMITS.get(slug, ""),
        "experiencia_titulo": "Onde isso já foi feito",
        "experiencia": b(f"servico.{slug}.experiencia"),
        "related_projects": SERVICE_PROOF[slug],
        "cta": b(f"servico.{slug}.cta", "Solicitar orçamento"),
        "cta_help": CTA_HELP,
        "mailto_subject": MAILTO[slug],
        "seo": b(f"servico.{slug}.seo"),
    })

(SRC / "servicos.json").write_text(
    json.dumps(services, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(f"servicos.json: {len(services)}")

# ==========================================================================
# 2. Projetos
# ==========================================================================

# Rotas do §91. Três projetos mudam de endereço em relação à versão anterior.
SLUG_MAP = {
    "fica": "fica-garopaba",
    "cine-patria-grande": "cineclube-patria-grande",
    "cine-marighella": "cineclube-marighella",
}

# A paleta institucional passou a ser só vermelho, vermelho profundo e amarelo.
# A alternância dá ritmo à grade sem inventar cor que a marca não tem.
BAND = {
    "fica-garopaba": "red",
    "flaca": "deep",
    "fica-calango": "red",
    "cineclube-patria-grande": "deep",
    "educa-ambiental": "red",
    "cine-retrata": "deep",
    "vozes-veladas": "red",
    "cineclube-marighella": "deep",
    "arte-para-voar": "yellow",
    "abrindo-a-caixa-preta": "deep",
    "oficinas-de-danca": "yellow",
}
PLATE = {
    "red": ("#690404", "#FFCC00"),
    "deep": ("#5D0404", "#FFCC00"),
    "yellow": ("#FFCC00", "#690404"),
}

ORDER = [
    "fica-garopaba", "flaca", "fica-calango", "cineclube-patria-grande",
    "educa-ambiental", "cine-retrata", "vozes-veladas", "cineclube-marighella",
    "abrindo-a-caixa-preta", "arte-para-voar", "oficinas-de-danca",
]

PLATE_TEXT = {
    "fica-garopaba": "FICA\nGaropaba",
    "flaca": "FLACA",
    "fica-calango": "Calango",
    "cineclube-patria-grande": "Cineclube\nPátria Grande",
    "educa-ambiental": "Educa\nAmbiental",
    "cine-retrata": "Cine\nRetrata",
    "vozes-veladas": "Vozes\nVeladas",
    "cineclube-marighella": "Cineclube\nMarighella",
    "abrindo-a-caixa-preta": "#Abrindo\nacaixapreta",
    "arte-para-voar": "Arte para\nVoar",
    "oficinas-de-danca": "Oficinas\nde dança",
}

SHORT = {
    "fica-garopaba": "FICA Garopaba",
    "flaca": "FLACA",
    "fica-calango": "FICA Calango",
    "cineclube-patria-grande": "Cineclube Pátria Grande",
    "educa-ambiental": "Cineclube Educa Ambiental",
    "cine-retrata": "Cine Retrata",
    "vozes-veladas": "Cineclube Vozes Veladas",
    "cineclube-marighella": "Cineclube Marighella",
    "abrindo-a-caixa-preta": "#Abrindoacaixapreta",
    "arte-para-voar": "Arte para Voar",
    "oficinas-de-danca": "Oficinas de dança",
}

# Fotografias atribuídas pela triagem. O manifesto de imagens é a autoridade
# sobre largura e proporção; aqui ficam só alt e legenda.
photo_blocks = {k[len("foto."):]: parse_fields(v) for k, v in V2.items() if k.startswith("foto.")}
by_slug_photo = {f["slug"]: {"file": name, **f} for name, f in photo_blocks.items() if f.get("slug")}


# Registros anteriores ao pacote 2026, que a triagem nova não cobre mas que
# continuam sendo os únicos publicáveis do seu projeto.
LEGACY_PHOTOS = {
    "flaca-libras": {
        "alt": "Auditório com palco de madeira; na tela à esquerda, um filme com janela de intérprete de Libras no canto inferior, e à direita o público sentado.",
        "legenda": "**FLACA** · Sessão com janela de Libras na projeção, 1ª edição, 2025. Foto: Flávio Veloso.",
    },
    "flaca-sala-cheia": {
        "alt": "Sala de cinema institucional cheia, com paredes de painéis acústicos; na tela larga, uma vista aérea de floresta com neblina.",
        "legenda": "**FLACA** · Sala pública cheia durante sessão do festival, Florianópolis, 2025. Foto: Flávio Veloso.",
    },
    "flaca-plateia-floresta": {
        "alt": "Auditório escuro visto de trás: fileiras de pessoas sentadas diante de uma tela grande onde se projeta uma floresta em contraluz.",
        "legenda": "**FLACA** · Plateia diante da projeção, 1ª edição, 2025. Foto: Flávio Veloso.",
    },
    "fica-salao-comunitario": {
        "alt": "Salão comunitário de telhado metálico com paredes cobertas de cartazes; dezenas de pessoas em cadeiras de praia assistem a um filme numa tela inflável vermelha com a marca da produtora.",
        "legenda": "**FICA Garopaba** · Sessão em salão comunitário, com a tela inflável da Pátria Grande Produções. Foto: Flávio Veloso.",
    },
    "fica-3a-edicao": {
        "alt": "Ambiente de teto de esteira e lâmpadas suspensas; público em cadeiras de praia diante de uma projeção com a marca do 3º FICA Garopaba.",
        "legenda": "**FICA Garopaba** · Abertura da 3ª edição, 2024. Foto: Flávio Veloso.",
    },
}


def photo(slug: str) -> dict | None:
    f = by_slug_photo.get(slug) or LEGACY_PHOTOS.get(slug)
    if not f:
        return None
    entry = next((i for i in IMAGES.get("fotos", []) if i["name"] == slug), None)
    if not entry:
        return None
    return {
        "name": slug,
        "widths": entry["widths"],
        "alt": f["alt"],
        "caption": f["legenda"],
        "group": "fotos",
    }


PROJECT_MEDIA = {
    "flaca": {
        "hero": "flaca-roda-de-conversa",
        "card": "flaca-sala-cheia",
        "gallery": ["flaca-plateia-vertical", "flaca-libras", "flaca-independente",
                    "flaca-sala-pequena", "flaca-plateia-floresta"],
    },
    "fica-garopaba": {"card": "fica-salao-comunitario",
                      "gallery": ["fica-salao-comunitario", "fica-3a-edicao"]},
}

# Edições correntes. O §31 é a regra: previsão nunca aparece como resultado, e
# por isso este bloco vive separado da linha do tempo e carrega selo próprio.
ONGOING = {
    "fica-garopaba": {
        "title": b("andamento.fica-garopaba.edicao") + " do FICA Garopaba",
        "text": b("andamento.fica-garopaba.descricao"),
        "quando_onde": b("andamento.fica-garopaba.quando_onde"),
        "status": b("andamento.fica-garopaba.status_texto"),
    },
    "flaca": {
        "title": b("andamento.flaca.edicao") + " do FLACA",
        "text": b("andamento.flaca.descricao"),
        "quando_onde": b("andamento.flaca.quando_onde"),
        "status": b("andamento.flaca.status_texto"),
    },
}

CONCEPT_TITLE = {
    "fica-garopaba": "Cinema ambiental como forma de olhar o território",
    "flaca": "América Latina e crise climática na mesma programação",
    "vozes-veladas": "Cinema na rua, debate depois",
    "cine-retrata": "O fato real como ponto de partida do debate",
    "educa-ambiental": "Educação ambiental que chega ao bairro",
    "cineclube-marighella": "Cinema dentro da ocupação",
    "cineclube-patria-grande": "A América Latina como linha curatorial",
    "arte-para-voar": "Formação cultural fora da tela",
    "abrindo-a-caixa-preta": "Abrir a câmera para abrir o olhar",
    "fica-calango": b("calango.concept_titulo"),
    "oficinas-de-danca": "Dança como ação formativa",
}

PULL = {
    "fica-garopaba": "Criado antes da formalização da Pátria Grande Produções, o FICA integra a trajetória do núcleo profissional que deu origem à produtora.",
    "flaca": "O mesmo filme pode ser visto por uma turma de estudantes numa manhã de escola e por um público adulto numa sessão noturna seguida de debate.",
    "fica-calango": "Realizado por profissionais que depois passaram a compor o núcleo da Pátria Grande, o Calango é a prova mais antiga de que a produtora não é um projeto de uma cidade só.",
    "cineclube-marighella": "O projeto não trata a Ocupação Carlos Marighella como cenário. Trata como território, com agência cultural própria.",
    "cineclube-patria-grande": "É o projeto que carrega o nome da produtora — e por isso funciona como síntese da sua filosofia cineclubista.",
}

RELATED = {
    "fica-garopaba": ["flaca", "fica-calango", "educa-ambiental"],
    "flaca": ["fica-garopaba", "fica-calango", "cineclube-patria-grande"],
    "fica-calango": ["fica-garopaba", "flaca", "educa-ambiental"],
    "cineclube-patria-grande": ["vozes-veladas", "educa-ambiental", "cine-retrata"],
    "educa-ambiental": ["cineclube-patria-grande", "vozes-veladas", "fica-garopaba"],
    "cine-retrata": ["cineclube-patria-grande", "vozes-veladas", "educa-ambiental"],
    "vozes-veladas": ["cineclube-patria-grande", "cineclube-marighella", "cine-retrata"],
    "cineclube-marighella": ["vozes-veladas", "cineclube-patria-grande", "educa-ambiental"],
    "abrindo-a-caixa-preta": ["arte-para-voar", "oficinas-de-danca", "cine-retrata"],
    "arte-para-voar": ["abrindo-a-caixa-preta", "oficinas-de-danca", "educa-ambiental"],
    "oficinas-de-danca": ["arte-para-voar", "abrindo-a-caixa-preta", "cineclube-patria-grande"],
}

CATEGORIES = {
    "fica-garopaba": ["festival"],
    "flaca": ["festival"],
    "fica-calango": ["festival"],
    "cineclube-patria-grande": ["cineclube"],
    "educa-ambiental": ["cineclube"],
    "cine-retrata": ["cineclube"],
    "vozes-veladas": ["cineclube"],
    "cineclube-marighella": ["cineclube"],
    "arte-para-voar": ["formacao"],
    "abrindo-a-caixa-preta": ["formacao", "fotografia"],
    "oficinas-de-danca": ["formacao", "danca"],
}


def years_label(years):
    ys = sorted(set(int(y) for y in years))
    if not ys:
        return "—"
    if len(ys) == 1:
        return str(ys[0])
    return f"{ys[0]}–{ys[-1]}" if ys == list(range(ys[0], ys[-1] + 1)) else " · ".join(map(str, ys))


def funding_short(items):
    out = []
    for text in items:
        head = re.split(r"\s+[—–(]\s*", text)[0].strip().rstrip(",;")
        head = re.sub(r"(?<=.),\s*edital n[ºo°].*$", "", head, flags=re.I).strip()
        head = re.sub(r"\s+(19|20)\d\d$", "", head)
        if head and head not in out:
            out.append(head)
    return out


# ---- projetos herdados do levantamento -----------------------------------

previous = json.loads((SRC / "projetos-v1.json").read_text(encoding="utf-8")) \
    if (SRC / "projetos-v1.json").exists() else None

projects = {}
for p in RAW_PROJECTS:
    slug = SLUG_MAP.get(p["slug"], p["slug"])
    projects[slug] = p

# ---- projetos novos, escritos para a v2 -----------------------------------

projects["fica-calango"] = {
    "slug": "fica-calango",
    "title": b("calango.titulo"),
    "years": [2022],
    "cities": ["Distrito Federal"],
    "lede": b("calango.lede"),
    "summary": b("calango.summary"),
    "concept": b("calango.concept"),
    "territory": b("calango.territory"),
    "history": [{"year": 2022, "label": "1ª edição — Distrito Federal", "text": b("calango.historia_2022")}],
    "credits": [
        dict(zip(("name", "role", "year"), [x.strip() for x in b(k).split("|")]))
        for k in sorted(V2) if k.startswith("calango.credito.")
    ],
    "metrics": [
        dict(zip(("value", "label", "source"), [x.strip() for x in b(k).split("|")]))
        for k in sorted(V2) if k.startswith("calango.metrica.")
    ],
    "funding": ["Fundo de Apoio à Cultura do Distrito Federal — edital Brasília Multicultural (2022)"],
    "seo_description": b("calango.seo"),
    "unverified": b("calango.pending"),
    "actions_text": b("calango.actions"),
}

projects["oficinas-de-danca"] = {
    "slug": "oficinas-de-danca",
    "title": b("danca.titulo"),
    "years": [2025],
    "cities": ["Santa Catarina"],
    "lede": b("danca.lede"),
    "summary": b("danca.summary"),
    "concept": b("danca.summary"),
    "territory": "Os locais das oficinas ainda não estão registrados nos materiais da produtora.",
    "history": [{"year": 2025, "label": "Ações formativas", "text": b("danca.summary").split("\n\n")[0]}],
    "credits": [],
    "metrics": [],
    "funding": [],
    "seo_description": b("danca.seo"),
    "unverified": b("danca.pending"),
    "actions_text": "",
}

# ---- normalização final ---------------------------------------------------

out_projects = []
for slug in ORDER:
    p = projects[slug]
    band = BAND[slug]
    plate_bg, plate_ink = PLATE[band]
    media = PROJECT_MEDIA.get(slug, {})

    entry = {
        "slug": slug,
        "title": p["title"],
        "short_title": SHORT[slug],
        "categories": CATEGORIES[slug],
        "years": sorted(set(int(y) for y in p["years"])),
        "years_label": years_label(p["years"]),
        "cities": p["cities"] or ["Santa Catarina"],
        "band": band,
        "plate_bg": plate_bg,
        "plate_ink": plate_ink,
        "plate_text": PLATE_TEXT[slug],
        "lede": p["lede"],
        "summary": p["summary"],
        "concept_title": CONCEPT_TITLE[slug],
        "concept": p["concept"],
        "actions_text": p.get("actions_text") or "\n".join(f"- {a}" for a in p.get("actions", [])),
        "history": [{"year": int(h["year"]), "label": h["label"], "text": h["text"]} for h in p["history"]],
        "territory": p["territory"],
        "credits": p.get("credits", []),
        "metrics": p.get("metrics", []),
        "funding": p.get("funding", []),
        "funding_short": funding_short(p.get("funding", [])),
        "related": [r for r in RELATED[slug] if r in ORDER][:3],
        "seo_description": p["seo_description"][:158],
        "pending": p.get("pending") or p.get("unverified", ""),
    }
    if PULL.get(slug):
        entry["pull"] = PULL[slug]
    if ONGOING.get(slug):
        entry["ongoing"] = ONGOING[slug]
    if media.get("hero") and photo(media["hero"]):
        entry["hero_image"] = photo(media["hero"])
    if media.get("card") and photo(media["card"]):
        entry["card_image"] = photo(media["card"])
    gal = [photo(g) for g in media.get("gallery", [])]
    gal = [g for g in gal if g]
    if gal:
        entry["gallery"] = gal
    out_projects.append(entry)

(SRC / "projetos.json").write_text(
    json.dumps(out_projects, ensure_ascii=False, indent=1), encoding="utf-8"
)
title_by_slug = {p["slug"]: p["short_title"] for p in out_projects}
print(f"projetos.json: {len(out_projects)} "
      f"({sum(1 for p in out_projects if p.get('ongoing'))} com edição em andamento)")

# ==========================================================================
# 3. Equipe
# ==========================================================================

# A v2 fecha o núcleo público em sete pessoas. Todo o resto do acervo continua
# no site, na Rede — sair do núcleo não é sair da produtora.
NUCLEO = [
    "flavio-veloso", "cristovam-muniz", "giulia-giacomolli", "thais-alemany",
    "eron-nascimento", "esteban-zapata", "lennon-da-silva-rocha",
]

HOLD = {"bruno-souza"}   # pasta sem foto, sem função e sem uma linha de bio

META = re.compile(
    r"[^.!?]*\b(o material (que ele enviou|dispon[íi]vel)|n[ãa]o h[áa] curr[íi]culo"
    r"|precisa[m]? ser (completada|confirmados)|antes da publica[çc][ãa]o"
    r"|antes de ir ao ar|[ée] a [úu]nica informa[çc][ãa]o documentada)[^.!?]*[.!?]\s*",
    re.I,
)

BIO_OVERRIDE = {
    "peri-dias-luersen": (
        "Peri Dias Luersen é produtor audiovisual, natural de Florianópolis, cidade onde "
        "também trabalha. Sua atuação transita entre gravação, edição e criação de "
        "conteúdos audiovisuais, com trabalhos que procuram unir técnica, estética e "
        "emoção para dialogar com públicos e contextos diferentes."
    ),
    "sarah-laranjeiras": (
        "Sarah Laranjeiras atua na direção criativa de roteiros e de conteúdos para redes "
        "sociais. Passou pelos setores de design, fotografia e audiovisual, repertório que "
        "sustenta seu trabalho de marketing para negócios e projetos culturais."
    ),
}

LINK_HOSTS = [
    ("youtube.com", "YouTube"), ("instagram.com", "Instagram"), ("facebook.com", "Facebook"),
    ("soundcloud.com", "SoundCloud"), ("spotify.com", "Spotify"), ("linkedin.com", "LinkedIn"),
    ("cnpq.br", "Lattes"), ("behance.net", "Behance"), ("vimeo.com", "Vimeo"),
    ("desterrocore.com.br", "desterrocore"),
]


def link_label(href):
    host = re.sub(r"^https?://(www\.)?", "", href).split("/")[0].lower()
    for needle, name in LINK_HOSTS:
        if host.endswith(needle):
            return name
    return host


have_photo = {e["name"]: e["widths"] for e in IMAGES["equipe"]}

people = []
for p in RAW_PEOPLE:
    slug = p["slug"]
    if slug == "giulia-valentina-giacomolli-gisler":
        slug = "giulia-giacomolli"
    if slug in HOLD:
        continue

    tier = "nucleo" if slug in NUCLEO else "rede"
    entry = {
        "slug": slug,
        "display_name": p["display_name"],
        "tier": tier,
        # Onde a v2 escreveu cargo e biografia novos, eles vencem: são a
        # redação feita para este site. Onde não escreveu, fica o levantamento.
        "role_line": b(f"equipe.{slug}.role") or p["role_line"],
        "bio": b(f"equipe.{slug}.bio") or BIO_OVERRIDE.get(slug) or META.sub("", p["bio"]).strip(),
        "bio_short": b(f"equipe.{slug}.bio_short") or META.sub("", p.get("bio_short") or p["bio"][:150]).strip(),
        "projects": [[SLUG_MAP.get(s, s), title_by_slug[SLUG_MAP.get(s, s)]]
                     for s in p.get("projects", []) if SLUG_MAP.get(s, s) in title_by_slug],
        "links": [{"href": h, "label": link_label(h)} for h in p.get("links", [])],
    }
    if (p.get("photo_credit") or "").strip():
        entry["photo_credit"] = p["photo_credit"].strip()
    if slug in have_photo:
        entry["photo"] = {"name": slug, "widths": have_photo[slug]}
    people.append(entry)

order = {s: i for i, s in enumerate(NUCLEO)}
nucleo = sorted([p for p in people if p["tier"] == "nucleo"], key=lambda p: order.get(p["slug"], 99))
rede = sorted([p for p in people if p["tier"] == "rede"],
              key=lambda p: unicodedata.normalize("NFKD", p["display_name"]).encode("ascii", "ignore"))

(SRC / "equipe.json").write_text(
    json.dumps(nucleo + rede, ensure_ascii=False, indent=1), encoding="utf-8"
)
print(f"equipe.json: {len(nucleo)} núcleo + {len(rede)} rede")

missing = [s for s in NUCLEO if s not in {p["slug"] for p in nucleo}]
if missing:
    print(f"  ATENÇÃO: núcleo previsto sem entrada no levantamento: {missing}")

# ==========================================================================
# 4. Cópia do site
# ==========================================================================

def linhas() -> list[dict]:
    slugs = ["cinema-e-audiovisual", "formacao", "artes-visuais",
             "producao-cultural", "territorio-e-socioambiental", "america-latina"]
    return [{"title": b(f"linha.{s}.titulo"), "text": b(f"linha.{s}.texto")} for s in slugs]


def foto_for(destino: str) -> dict | None:
    """A imagem que a triagem atribuiu a um destino de página."""
    for name, f in photo_blocks.items():
        if f.get("destino", "").startswith(destino) and f.get("slug"):
            got = photo(f["slug"])
            if got:
                return got
    return None


site = {
    "email": "patriagrandeproducoes@gmail.com",
    "instagram": "@patriagrandeproducoes",
    "instagram_url": "https://www.instagram.com/patriagrandeproducoes/",
    # Os dois números vieram do documento institucional. Qual é o principal e
    # qual é WhatsApp ainda não foi definido pela equipe, então nenhum dos dois
    # é apresentado como canal preferencial.
    "phones": [
        {"tel": "+5548996971772", "label": "(48) 99697-1772"},
        {"tel": "+5548999486832", "label": "(48) 99948-6832"},
    ],
    "footer_projects": [[s, title_by_slug[s]] for s in
                        ["fica-garopaba", "flaca", "fica-calango",
                         "cineclube-patria-grande", "cine-retrata"]],
    "footer_services": [[s["slug"], s["title"]] for s in services],

    "seo": {
        "home": b("seo.home"),
        "quem_somos": b("seo.quem_somos"),
        "projetos": b("seo.projetos"),
        "servicos": b("seo.servicos"),
        "equipe": b("seo.equipe"),
        "contato": b("seo.contato"),
        "404": "A página que você procurou não existe neste site da Pátria Grande Produções.",
    },

    "home": {
        "title": "Pátria Grande Produções — cultura para conectar territórios",
        "hero_title": b("home.hero_titulo"),
        "hero_lede": b("home.hero_lede"),
        "hero_image": foto_for("home.hero"),
        "manifesto": b("home.manifesto"),
        "about_title": b("home.quem_somos_titulo", "Uma produtora cultural com identidade latino-americana"),
        "about_text": b("home.quem_somos_curto"),
        "projects_title": b("home.projetos_titulo"),
        "projects_lede": b("home.projetos_lede"),
        "featured": ["fica-garopaba", "flaca", "cineclube-patria-grande", "cine-retrata"],
        "ongoing_title": b("home.andamento_titulo"),
        "ongoing_lede": b("home.andamento_lede"),
        "ongoing": ["fica-garopaba", "flaca"],
        "services_title": b("home.servicos_titulo"),
        "services_lede": b("home.servicos_lede"),
        "fullbleed_image": foto_for("home.fullbleed"),
        "axes_title": b("home.linhas_titulo", "Seis linhas que se atravessam"),
        "axes": linhas(),
        "territories_title": b("home.territorios_titulo"),
        "territories_text": b("home.territorios_texto"),
        "territories": [
            {"name": "Florianópolis", "text": "Base da produtora. Cineclubes no Centro, no Rio Vermelho e nos Ingleses, o Cine Retrata, o FLACA e o curso de fotografia."},
            {"name": "Garopaba", "text": "Casa do FICA desde 2022, com circulação por outras cidades do litoral catarinense."},
            {"name": "Palhoça", "text": "Ocupação Urbana Carlos Marighella, na região da Formiga do Aririu, onde funcionou o Cineclube Marighella."},
            {"name": "Distrito Federal", "text": "Escolas públicas e espaços culturais receberam a primeira edição do Calango, em 2022."},
        ],
        "team_title": b("home.equipe_titulo"),
        "team_text": b("home.equipe_texto"),
        "contact_title": b("home.contato_titulo"),
        "contact_text": b("home.contato_texto"),
    },

    "quem_somos": {
        "title": b("quem_somos.titulo"),
        "lede": b("quem_somos.lede"),
        "institucional": b("quem_somos.institucional"),
        "fecho": b("quem_somos.fecho"),
        "logo_caption": "**Logotipo Pátria Grande Produções** · A América Latina desenhada com o sul para cima, cercada por sol, lua, aves, peixe, água, cidade e a linha do Equador.",
        "conceito_titulo": b("quem_somos.conceito_titulo"),
        "conceito": b("quem_somos.conceito"),
        "cartografia_titulo": b("quem_somos.cartografia_titulo"),
        "cartografia": b("quem_somos.cartografia"),
        "fullbleed_image": foto_for("quem-somos.fullbleed") or foto_for("projetos.fullbleed"),
        "origem_titulo": b("quem_somos.origem_titulo"),
        "origem": b("quem_somos.origem"),
        "timeline": [
            {"year": "2022", "title": "Antes da empresa",
             "text": "A primeira edição do FICA acontece em Garopaba e a primeira edição do Calango, no Distrito Federal. Os dois festivais são realizados por profissionais que depois passariam a compor o núcleo da Pátria Grande. A empresa ainda não existe."},
            {"year": "2023", "title": "O festival ganha estrutura",
             "text": "A 2ª edição do FICA amplia a operação, com Giulia Giacomolli na produção executiva. No mesmo período começam a se formar as ações cineclubistas que depois integrariam o portfólio da produtora."},
            {"year": "2024", "title": "Formalização e linha cineclubista",
             "text": "A Pátria Grande Produções é constituída em Florianópolis. No mesmo ano são executados quatro cineclubes — Pátria Grande, Educa Ambiental, Marighella e Vozes Veladas — contemplados pelo Prêmio Catarinense de Cinema, e acontece a 3ª edição do FICA."},
            {"year": "2025", "title": "O portfólio se amplia",
             "text": "A 4ª edição do FICA, a 1ª edição do FLACA em Florianópolis, o Cine Retrata, a continuidade dos cineclubes por política pública estadual, a Oficina de Pandorga — Arte para Voar e o Curso Básico de Fotografia Digital #Abrindoacaixapreta."},
        ],
        "linhas_titulo": b("quem_somos.linhas_titulo", "Seis linhas de atuação"),
        "linhas": linhas(),
        "cta_titulo": b("quem_somos.cta_titulo"),
        "cta_texto": b("quem_somos.cta_texto"),
    },

    "projetos": {
        "title": "Arquivo de projetos",
        "lede": "Festivais, cineclubes, cursos e oficinas realizados desde 2022 em Florianópolis, Garopaba, Palhoça e no Distrito Federal — e as edições que estão acontecendo agora.",
        "tabs": [
            {"key": "executado", "label": "Realizados"},
            {"key": "andamento", "label": "Em andamento"},
        ],
        "filters": [
            {"key": "todos", "label": "Todos"},
            {"key": "festival", "label": "Festivais"},
            {"key": "cineclube", "label": "Cineclubes"},
            {"key": "formacao", "label": "Formação"},
            {"key": "fotografia", "label": "Fotografia"},
            {"key": "danca", "label": "Dança"},
        ],
        "note_label": "Realizado e em andamento",
        "note": b("andamento.aviso"),
    },

    "servicos": {
        "title": b("servicos.titulo"),
        "lede": b("servicos.lede"),
        "intro": b("servicos.intro"),
        "fullbleed_image": foto_for("servicos.hero"),
        "como_titulo": "Como pedir um orçamento",
        "como_texto": b("servicos.como_funciona"),
        "mailto_subject": "Pedido de orçamento — Pátria Grande Produções",
    },

    "equipe": {
        "title": b("equipe.titulo", "Quem faz a Pátria Grande"),
        "lede": "Cinema, fotografia, curadoria, produção executiva, tradução, jornalismo, acessibilidade, educação, música, dança e tecnologia. As funções se reorganizam conforme cada projeto.",
        "nucleo_title": b("equipe.nucleo_titulo"),
        "nucleo_text": b("equipe.nucleo_texto"),
        "rede_title": b("equipe.rede_titulo"),
        "rede_text": b("equipe.rede_texto"),
    },

    "contato": {
        "title": "Vamos conversar?",
        "lede": "Se você quer desenvolver um projeto cultural, organizar uma exibição, contratar produção executiva, realizar uma oficina ou propor uma parceria, escreva para a Pátria Grande.",
        "blocks": [
            {"title": "E-mail institucional",
             "value": "[patriagrandeproducoes@gmail.com](mailto:patriagrandeproducoes@gmail.com)",
             "note": "Canal principal. Orçamentos, pautas de imprensa, propostas e convites."},
            {"title": "Telefone",
             "value": "[(48) 99697-1772](tel:+5548996971772)<br>[(48) 99948-6832](tel:+5548999486832)",
             "note": "Dois números da produtora."},
            {"title": "Instagram",
             "value": "[@patriagrandeproducoes](https://www.instagram.com/patriagrandeproducoes/)",
             "note": "Programação, chamadas de sessão e registros das atividades."},
            {"title": "Onde estamos",
             "value": "Florianópolis · SC",
             "note": "Base da produtora, com atuação em diferentes regiões do Brasil."},
        ],
        "roteiro_titulo": "O que informar na primeira mensagem",
        "roteiro_intro": "Não há formulário neste site: o contato é direto, por e-mail, com a mesma equipe que executa o trabalho. Para o retorno já vir com orçamento em vez de perguntas, ajuda incluir:",
        "roteiro": (
            "- **Serviço de interesse** — produção executiva, estrutura de projeção, tradução e legendagem, oficina, parceria ou outro\n"
            "- **Quem está pedindo** — pessoa, coletivo, escola, organização ou projeto\n"
            "- **Cidade e local** — onde a atividade acontece, e em que tipo de espaço\n"
            "- **Data prevista**\n"
            "- **Público estimado**\n"
            "- **Edital, patrocínio ou prazo de prestação de contas**, se houver — isso muda o desenho da proposta"
        ),
        "mailto_subject": "Contato — Pátria Grande Produções",
        "reasons_title": "O que costuma chegar por aqui",
        "reasons_text": "Se a sua mensagem for sobre um destes assuntos, ajuda muito indicar isso na primeira linha.",
        "reasons": [
            "**Contratação de serviço** — produção executiva, estrutura de projeção, tradução e legendagem, oficinas.",
            "**Exibição** — propostas de sessão em escola, equipamento cultural, coletivo, ocupação ou espaço independente.",
            "**Realizadoras e realizadores** — filmes para curadoria dos festivais e cineclubes.",
            "**Editais e parcerias** — coprodução, cartas de anuência e articulação institucional.",
            "**Patrocínio** — apoio a projetos culturais, inclusive por mecanismos de incentivo fiscal.",
            "**Imprensa** — entrevistas, dados de projeto e material fotográfico com crédito.",
        ],
        "kit_titulo": "Material para imprensa",
        "kit_texto": "O kit está em organização e é enviado por e-mail mediante solicitação.",
        "kit": [
            {"title": "Logotipo", "text": "Versões oficiais da marca, com as cores corretas."},
            {"title": "Textos institucionais", "text": "Descrição curta e descrição longa da produtora, prontas para publicação."},
            {"title": "Fotografias", "text": "Registros dos projetos com crédito de fotografia e condições de uso definidas."},
            {"title": "Fichas técnicas", "text": "Créditos por edição, fomento, datas e territórios de cada projeto."},
        ],
    },
}

(SRC / "site.json").write_text(json.dumps(site, ensure_ascii=False, indent=1), encoding="utf-8")
print("site.json escrito")

empty = [k for k, v in site["seo"].items() if not v]
if empty:
    print(f"  ATENÇÃO: seo sem texto para {empty}")
