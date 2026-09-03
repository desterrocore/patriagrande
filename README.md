# patriagrande

Site institucional da **Pátria Grande Produções** — produtora cultural de Florianópolis,
com atuação em diferentes regiões do Brasil.

No ar: <https://desterrocore.com.br/patriagrande/> — migrando para <https://patriagrande.com.br>

---

## As duas regras que governam este site

O conteúdo vem de `source/patria-grande-producoes-site-source-v2.md`, a especificação
editorial da produtora. Duas regras dela atravessam tudo, e nenhuma é confiada à boa vontade
de quem escreve — as duas são verificadas no CI:

> **Só aparece como realizado o que já foi executado.**
> Aprovação em edital, orçamento, identidade visual ou programação futura não transformam
> um projeto em portfólio.

> **Previsão não é resultado.**
> FICA Garopaba e FLACA têm edições realizadas *e* uma edição correndo agora. As duas coisas
> convivem no site, em blocos separados, com selo próprio — e as metas da edição corrente
> nunca somam aos números do que já aconteceu.

Consequências concretas no código:

- `tools/check-site.py` **falha o build** se a linha do tempo de um projeto trouxer 2026 ou
  depois, se um projeto da lista vetada aparecer, ou se um bloco "em andamento" usar palavra
  de resultado sem marcar que é previsão;
- toda métrica publicada precisa do campo `source`, e a fonte aparece impressa ao lado do
  número na página — sem fonte, o build quebra;
- números agregados que ainda não foram auditados por projeto simplesmente não existem no
  site. Não há "+20 projetos" nem "+10 mil pessoas" em lugar nenhum;
- nenhuma imagem gerada por IA ou de banco entra. Das 88 imagens encontradas no material de
  origem, 57 foram descartadas por esse motivo e 3 por conterem crianças identificáveis sem
  autorização de uso. Projeto sem registro publicável recebe uma placa de cor da marca com a
  cartografia — nunca uma foto emprestada de outro projeto.

## Como funciona

Site estático: HTML, CSS e um arquivo de JavaScript. Sem framework, sem bundler, sem
dependência de terceiros em tempo de execução. As fontes são hospedadas aqui, então a página
não faz nenhuma requisição para fora do próprio domínio.

O HTML **é gerado e é commitado**. Vinte e duas páginas dividem o mesmo cabeçalho, rodapé e
ficha de metadados; manter isso à mão é como se introduz divergência. Quem clona serve os
arquivos direto; quem edita conteúdo mexe nos JSON e roda o gerador.

```
source/*.json          conteúdo — é aqui que se edita
tools/build-site.py    gera todo o HTML + sitemap.xml
tools/build-data.py    remonta os JSON de destino a partir do conteúdo bruto
tools/build-images.py  gera assets/img/equipe e /fotos a partir dos originais
tools/build-brand.py   gera assets/img/marca a partir dos logotipos oficiais
tools/trace-brand.py   traça a cartografia da marca em SVG
tools/check-site.py    verificação técnica e editorial (roda no CI)

source/patria-grande-producoes-site-source-v2.md   a especificação editorial
source/patria-grande-producoes-relatorio-site.md   a versão anterior, mantida por referência
source/pesquisa-fontes.json                        procedência de cada fato apurado
source/v2-conteudo.json                            a redação feita para esta versão
```

### Editar o conteúdo

| Para mudar | Edite |
| --- | --- |
| Texto da home, do Quem somos, do Contato, SEO | `source/site.json` |
| Um projeto — resumo, execução, créditos, números, edição em andamento | `source/projetos.json` |
| Um serviço — descrição, entregas, experiência | `source/servicos.json` |
| Uma pessoa — cargo, biografia, projetos, links | `source/equipe.json` |
| Quais imagens existem e como são recortadas | `source/images.json` |

Depois:

```bash
python3 tools/build-site.py     # regenera o HTML
python3 tools/check-site.py     # confere antes de commitar
```

O texto dos JSON aceita dois marcadores e nada mais: `**negrito**` e `[texto](url)`.
Parágrafos são separados por linha em branco (`\n\n`); listas, por linhas começando com `- `.

`tools/build-data.py` remonta `projetos.json`, `equipe.json`, `servicos.json` e `site.json`
a partir de `source/pesquisa-fontes.json` e `source/v2-conteudo.json`. Rodá-lo **sobrescreve
edições manuais** — no dia a dia, edite o JSON de destino.

### Regenerar imagens e marca

```bash
python3 -m pip install Pillow pillow-heif numpy
python3 tools/build-images.py
python3 tools/build-brand.py
python3 tools/trace-brand.py
```

Só funciona com `reference-content/` presente — a pasta de originais, que não vai para o
repositório (115 MB de PDFs, currículos, logotipos e fotografias em resolução integral). O que
está versionado é o resultado: `assets/img/`, do qual o navegador baixa apenas os WebP.

`source/images.json` é o manifesto. Cada entrada diz de onde vem a imagem, em que proporção é
recortada, onde está o assunto (`focus_x` / `focus_y`) e em que larguras sair. Nenhum recorte
é feito à mão: o enquadramento é dado, versionado e reproduzível.

### Preview local

```bash
python3 -m http.server 8000
```

## Publicação

`.github/workflows/deploy-pages.yml` publica no GitHub Pages a cada push na `main`. O workflow
monta o artefato apenas com o que vai ao ar — a especificação, as ferramentas e os JSON ficam
no repositório mas fora do site — e roda `tools/check-site.py` antes de enviar. Verificação
reprovada, publicação não sai.

### Domínio

O site vai para **patriagrande.com.br**. Quem define isso é **Settings → Pages → Custom
domain** no repositório, e só isso: quando a publicação sai de um workflow do Actions, como
aqui, o GitHub ignora o arquivo `CNAME`. O arquivo continua no repositório por outro motivo —
é a declaração versionada do domínio, e é o que permite verificar que o resto concorda com ele:

| Onde | O quê |
| --- | --- |
| `CNAME` | o domínio, sozinho, numa linha |
| `BASE_URL` em `tools/build-site.py` | tags canônicas, `og:url` e `sitemap.xml` |
| `Sitemap:` em `robots.txt` | o único arquivo com o domínio escrito à mão — `build-site.py` não gera o robots |
| `index.html` | a canônica publicada tem de bater com o `BASE_URL` atual |
| `deploy-pages.yml` | copia o `CNAME` para o artefato |

`tools/check-site.py` confere os cinco e falha se divergirem. Não é zelo: divergência aqui não
quebra nada visivelmente — o site abre e publica canônicas apontando para outro endereço, o
buscador segue a canônica e indexa o domínio errado. Trocar o `BASE_URL` e esquecer de rodar
`build-site.py` também é pego, comparando a canônica do `index.html` com o valor atual.

Todos os caminhos internos são relativos, então o mesmo build funciona no ápice e num
subcaminho. A exceção é o `404.html`: o Pages devolve esse arquivo para qualquer endereço
inexistente, inclusive `/projetos/algo/inexistente/`, e ali um caminho relativo resolveria para
`/projetos/algo/inexistente/assets/…` — a página apareceria sem estilo. Por isso o 404, e só
ele, sai com caminho de raiz, e só quando o `BASE_URL` não tem subcaminho. Voltando para um
subcaminho, o gerador devolve o relativo sozinho.

## Design

### Cor

Três cores, medidas pixel a pixel nos arquivos oficiais do logotipo — não estimadas:

| | | |
| --- | --- | --- |
| `#690404` | vermelho | fundos institucionais, cabeçalho, cards de serviço |
| `#5D0404` | vermelho profundo | rodapé, faixas de variação, overlays |
| `#FFCC00` | amarelo | tipo sobre vermelho, botões, selos, acentos |

Mais preto e branco como utilitários e `#F7F4EE` como papel de leitura longa. **Azul e verde
não são cores da identidade** e não aparecem no site — só dentro de fotografias.

A composição alterna três condições e nunca fica no meio-termo: papel para ler, faixa
vermelha para as afirmações institucionais, cartaz amarelo para o volume máximo. Cada faixa
redefine quatro tokens (`--band-bg`, `--band-ink`, `--band-dim`, `--band-accent`) e os
componentes só conversam com eles — é o que faz o mesmo card funcionar sobre papel, sobre
vermelho e sobre amarelo.

Todo par de cor usado para texto foi medido. Os números estão comentados ao lado dos tokens
em `assets/css/patria-grande.css`; o menor da casa é 5,19:1 e os pares principais passam de
8:1.

### Cartografia

A América Latina desenhada com o sul para cima é a tese visual da marca, e no site ela é
vetorial: `tools/trace-brand.py` traça a silhueta a partir do PNG do logotipo — limiar de cor,
remoção das réguas horizontais do desenho, abertura morfológica, traçado de contorno de Moore
e simplificação de Douglas-Peucker — e escreve um SVG de 3 KB. Como é inline e usa
`currentColor`, ele muda de cor com a faixa, escala sem perder nitidez e não custa requisição.

O arquivo aberto do logotipo é `.cdr`, que nenhuma ferramenta livre desta máquina lê. Se a
produtora conseguir exportar um SVG a partir do CorelDRAW, ele substitui o traçado com ganho
de fidelidade.

`tools/build-brand.py` deriva o resto: a assinatura recortada em duas polaridades, o símbolo e
o wordmark separados para o cabeçalho, o favicon (feito da cartografia, não do logotipo
inteiro, que vira borrão a 16 px), a imagem de compartilhamento social e os quatro motivos
secundários — sol, lua com o Cruzeiro do Sul, veleiro sobre a cidade, peixe sobre a água.

### Tipografia

**Archivo Black** nos títulos, **Archivo** variável no texto, **IBM Plex Mono** apenas em
metadado — data, cidade, crédito, status, número de seção. Todas em `assets/fonts/`, sob SIL
Open Font License.

A **Squarely**, que desenha o wordmark da marca, vem no pacote com licença "free for personal
use ONLY" e por isso **não é carregada pelo site**: o wordmark entra como arte, não como
texto. `tools/check-site.py` falha se ela aparecer em `assets/fonts/`.

### Acessibilidade

HTML semântico, um `<h1>` por página, link de pular navegação, foco visível, `aria-current` na
navegação, `role="tablist"` com navegação por seta nas abas do arquivo, `aria-pressed` nos
filtros, região viva no contador, `alt` em todas as imagens, cartografia decorativa marcada
`aria-hidden`, `prefers-reduced-motion` respeitado, galeria em `<dialog>` nativo e nenhuma
informação transmitida só por cor. Sem JavaScript o site funciona inteiro: o menu vira lista,
o arquivo mostra todos os projetos e a galeria abre a imagem no próprio navegador.

## Estrutura

```
/                           home
/quem-somos/                institucional, conceito, cartografia, origem, linhas de atuação
/projetos/                  arquivo com abas Realizados / Em andamento e filtros
/projetos/<slug>/           onze páginas de projeto
/servicos/                  índice
/servicos/<slug>/           quatro páginas de serviço
/equipe/                    núcleo + rede
/contato/                   canais, roteiro de orçamento e material para imprensa
```

---

## Pendências

Nada aqui impede o site de ir ao ar. São lacunas do material de origem e decisões que cabem à
produtora — o site as declara em vez de preenchê-las.

### Decisões da produtora

- **A manchete da home não é assinatura aprovada.** "Cultura para conectar territórios." é uma
  das duas sugestões do §19 da especificação, que proíbe fixar slogan sem decisão interna. A
  alternativa é "Cinema, arte e encontro.". Trocar é uma linha em `source/site.json`.
- **Telefone principal e WhatsApp.** Os dois números estão publicados, sem distinção. Falta
  definir qual é o principal, qual é WhatsApp e se ambos devem mesmo aparecer.
- **Composição do núcleo.** A especificação fecha a equipe pública em sete pessoas. Com isso,
  **Luna Vanzella**, **Tayná Oliveira** e **Sara Santos** — que na versão anterior do site
  estavam no núcleo, com curadoria e direção documentadas em projeto nomeado — passaram para a
  Rede. Reverter é trocar `"tier"` em `source/equipe.json`.
- **Grafia de nomes.** O site usa **Thais Alemany** (sem acento), **Giulia Giacomolli** e
  **Esteban Zapata**, seguindo os currículos assinados por cada um. O pacote 2026 escreve
  "Thaís Alemany ?" e "Giulia Valentina Gisler"; o currículo do Esteban traz "Esteban Gabriel
  Mederos Zapata". Confirmar com as três pessoas antes do lançamento.
- **Numeração das edições em andamento.** Os cards dizem "6ª edição" (FICA) e "3ª edição"
  (FLACA) porque é assim que os projetos se chamam no registro federal — PRONAC 261904 e
  262096. Mas o portfólio publica quatro edições do FICA e uma do FLACA. Se as edições de 2026
  já aconteceram, o histórico precisa ganhá-las e a diferença deixa de existir.
- **Serviços: escopo real.** A página de projeção não publica inventário de equipamento e a de
  tradução não publica pares de idiomas — as duas coisas dependem de decisão interna, conforme
  §48 e §49. Libras não entra como oferta enquanto não houver projeto executado que a comprove.

### Fotografia

- **Três fotos estão bloqueadas** por conterem crianças ou adolescentes identificáveis em
  primeiro plano: `251113_8051.jpg` e `251113_8019.jpg` (a única evidência gráfica do 4º FICA
  Garopaba, com a camiseta do festival legível) e `20251104_155037-2.jpg` (a única que mostra a
  estrutura móvel de projeção com a marca da produtora). Liberam com autorização de uso de
  imagem dos responsáveis ou autorização coletiva da escola. Enquanto isso, o eixo escolar do
  FICA fica sem fotografia.
- **FICA Garopaba** tem apenas dois registros publicáveis, ambos extraídos das apresentações
  institucionais, em 700 e 640 px. Por isso a página não tem hero fotográfico.
- **Seis dos onze projetos não têm nenhuma fotografia** e usam placa de cor: os cineclubes, o
  curso de fotografia, a oficina de pandorgas e as oficinas de dança.
- **Retratos.** Três pessoas aparecem com iniciais em vez de foto: **Thais Alemany** (a pasta
  tem só currículo e portfólio), **Jia** (os arquivos da pasta retratam alguém que não foi
  possível identificar com segurança) e **Bruno Souza**, que está fora do site porque a pasta
  dele está inteiramente vazia. **Flávio Veloso** não tem retrato profissional recente — a foto
  em uso é um registro de celular de 2023, e é o card do fundador.
- **Créditos de fotografia** estão publicados onde são conhecidos: Flávio Veloso, Maurício
  Garcias e Antonio Husadel. Os demais retratos seguem sem crédito documentado.

### Conteúdo

- **Oficinas de dança** entram como página deliberadamente curta: a lista institucional as
  registra como executadas, mas não há nome oficial, datas, responsáveis, público nem
  financiamento. Nada disso foi estimado.
- **FICA Calango** publica apenas o que dois currículos e o registro no Salic sustentam: ano,
  território, fomento e dois créditos. Calendário, número de sessões e público seguem sem
  conferência.
- **Créditos completos por edição** de FICA, FLACA, Vozes Veladas, Educa Ambiental e Cineclube
  Pátria Grande seguem em consolidação.
- **Clipping.** Não existe página de imprensa nesta versão, por decisão do §16: o material de
  imprensa vive em `/contato` e o clipping entrará nas páginas dos próprios projetos.
- **Métricas acumuladas do FICA** ("mais de 68 filmes", "≈6 mil pessoas") continuam fora do ar
  até serem conferidas contra o clipping final.

---

## Licença

Código sob MIT. Textos, fotografias, logotipos e identidade visual da Pátria Grande Produções
não — ver `LICENSE`.

Site por [desterrocore](https://desterrocore.com.br).
