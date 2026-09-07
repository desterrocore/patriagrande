# Estado do projeto e fila de trabalho

Documento de passagem de bastão. O `README.md` explica **como o repositório funciona**;
este aqui registra **onde as coisas estão, o que já foi decidido e por quê, e o que falta** —
para que uma sessão futura não reabra discussão já encerrada nem repita erro já pago.

Última atualização: **7 de setembro de 2026** · alterações ainda não commitadas.

---

## 1. Onde o site está

**No ar em <https://patriagrande.com.br>** — HTTPS válido, certificado emitido em 3/9/2026,
`http://` redireciona para `https://`. Vinte e uma páginas (eram 22 até a retirada do
Cineclube Vozes Veladas), e a árvore de imagens segue abaixo de 3,5 MB de WebP.

O DNS está completo no Registro.br: quatro registros A, quatro AAAA, `www` como CNAME para
`desterrocore.github.io` e o TXT de verificação de domínio publicado — o Registro.br **aceitou**
o underscore em `_github-pages-challenge-desterrocore`, ao contrário do que a documentação
sugeria.

### ⚠️ O www ainda não funciona por HTTPS

`https://www.patriagrande.com.br` devolve **erro de certificado**, que para o visitante é pior
que um 404 — o navegador mostra aviso de site inseguro.

O certificado emitido cobre só o ápice:

```
subject=CN = patriagrande.com.br
X509v3 Subject Alternative Name: DNS:patriagrande.com.br
```

No `www` o GitHub serve o curinga `*.github.io`, que não bate com o nome pedido. O CNAME de
`www` provavelmente entrou depois da emissão. Em `http://` o `www` já redireciona certo para
`https://patriagrande.com.br/`.

**Como resolver:** em Settings → Pages, apagar o domínio próprio, salvar, e cadastrá-lo de
novo. Isso força nova emissão, agora com o `www` resolvendo. Conferir depois com:

```bash
echo | openssl s_client -servername www.patriagrande.com.br \
  -connect www.patriagrande.com.br:443 2>/dev/null | openssl x509 -noout -ext subjectAltName
```

O SAN precisa listar `patriagrande.com.br` **e** `www.patriagrande.com.br`. Enquanto não
listar, o `www` fica quebrado para quem digita `https://`.

---

## 2. Decisões já tomadas — não reabrir sem motivo novo

| Assunto | Decisão | Por quê |
| --- | --- | --- |
| Grafia dos nomes | **Thais Alemany** (sem acento), **Giulia Giacomolli**, **Esteban Zapata** | Cada um segue o currículo assinado pela própria pessoa. O pacote 2026 escreve "Thaís Alemany ?" — com interrogação — e "Giulia Valentina Gisler", suprimindo um sobrenome. Documento assinado vence anotação de rascunho. **Ainda assim, confirmar com as três antes do lançamento.** |
| Núcleo da equipe | **Sete pessoas**, conforme a spec v2 | Luna Vanzella, Tayná Oliveira e Sara Santos saíram do núcleo para a Rede, apesar de terem curadoria e direção documentadas em projeto nomeado. É decisão editorial da produtora, não falta de evidência. Reverter é trocar `"tier"` em `source/equipe.json`. |
| Fonte Squarely | **Não é servida** | A licença no pacote diz "free for personal use ONLY". O wordmark entra como arte, não como texto. `check-site.py` falha se ela aparecer em `assets/fonts/`. |
| Cartografia | **Traçada do PNG**, não do `.cdr` | Nenhuma ferramenta livre lê CorelDRAW. `tools/trace-brand.py` faz limiar de cor, remove as réguas horizontais do desenho, abertura morfológica, contorno de Moore e Douglas-Peucker. Se a produtora exportar um SVG do Corel, ele substitui o traçado com ganho de fidelidade. |
| Favicon | **Cartografia, não o logotipo** | O logotipo completo vira borrão a 16 px. §97 da spec pede exatamente isso. |
| Formulário de orçamento | **Não existe** | GitHub Pages é estático. Os CTAs abrem `mailto:` com assunto pronto. Decisão do usuário; alternativa era Formspree. |
| Arquivo `CNAME` | **Fica, mesmo sendo ignorado** | Publicando via Actions, o GitHub ignora o arquivo — quem manda é Settings → Pages. Ele permanece como declaração versionada do domínio, e é o que `check-site.py` usa para cobrar coerência com `BASE_URL` e `robots.txt`. |
| Fotos com menores | **Três bloqueadas** | `251113_8051.jpg`, `251113_8019.jpg` e `20251104_155037-2.jpg` têm crianças e adolescentes identificáveis em primeiro plano. Uma delas é a **única** evidência gráfica do 4º FICA (camiseta legível) e outra a única que mostra a tela inflável com a marca. Liberam com autorização de uso de imagem. |
| Números agregados | **Não existem no site** | Nada de "+20 projetos" ou "+10 mil pessoas". Seis métricas acumuladas do FICA foram removidas por não terem fonte conferida. |
| Cineclube Vozes Veladas | **Fora do site, inteiro** | Decisão da produtora em 7/9/2026. Saíram a página, o card, o rodapé, a linha do tempo, as provas de serviço, as etiquetas e toda menção em bio. `check-site.py` reprova qualquer página que escreva o nome (lista `RETIRED`). Os registros continuam em `source/pesquisa-fontes.json` — foi retirada de publicação, não apagamento de arquivo. |
| Quem sai da página de equipe | **Set `HOLD` em `tools/build-data.py`** | Carolina Rögelin, Denise de Castro, Marcela Guitarrarra e Peri Dias Luersen saíram em 7/9/2026 a pedido da produtora. A Rede foi de 18 para 14, e o texto de abertura da seção precisou perder acessibilidade/Libras, música, tradução e produção audiovisual — eram as especialidades das quatro. |
| Vínculo de pessoa com projeto | **A produtora vence a apuração** | `PROJECTS_ADD` em `tools/build-data.py` acrescenta vínculos que os currículos não registram (Lennon no FICA e no FLACA, Thais no FLACA e no Cineclube Pátria Grande, Eron no Cineclube Pátria Grande). O levantamento em `pesquisa-fontes.json` fica intacto: o override é acréscimo, não reescrita da fonte. |
| Oficinas de dança | **São da produtora** | A spec §44 dizia "produzidas e apoiadas pela Pátria Grande em colaboração com profissionais e projetos da área". Corrigido em 7/9/2026: as oficinas são dela. O texto publicado diz "realizadas pela Pátria Grande, conduzidas com profissionais da própria rede da produtora". Não reintroduzir "apoiadas". |
| Logotipo de projeto | **Fora do `images.json`** | O logotipo do Cineclube Pátria Grande vem de PDF vetorial (CorelDRAW), não de fotografia. `tools/build-brand.py` rasteriza com `pdftoppm` (poppler-utils), recorta o disco por geometria — não por cor, porque "CINECLUBE" é branco e sairia junto com o fundo — e escreve PNG com alfa + WebP em `assets/img/projetos/`. Servido por `<picture>` com PNG no `<img>`: JPEG não tem canal alfa e devolveria um quadrado branco. `check_brand()` cobra os seis arquivos. |
| Placas de marca | **Quatro, compostas no build** | `assets/img/projetos/<slug>-<largura>.(webp\|png)`, em 3:2, com fundo e arte no mesmo arquivo. Fontes: Cineclube Pátria Grande (PDF vetorial do CorelDRAW), FICA Garopaba (`FICA_Garopaba_logo_evergreen.png`), FLACA e FICA Calango (recortados de `imagens-festivais.png`, folha de 2048×768 com os três lado a lado). As caixas de recorte foram medidas varrendo a folha por coluna de conteúdo — estão em `SHEET_BOX`, em `tools/build-brand.py`. |
| Por que compor no build e não no CSS | **Cada marca pede um fundo diferente** | Amarelo da casa atrás do cineclube (decisão da produtora), a cor da própria arte atrás do FLACA (`#000C2A`) e do Calango (`#85082C`), e o desenho de ondas do festival atrás do FICA. Nenhuma cor da casa serve às quatro. Compondo no build, o CSS fica com três linhas e a marca encosta na moldura com precisão de pixel. |
| Como cada marca é recortada | **Por cor ou por geometria, conforme o que a arte tem de branco** | FICA e FLACA saem por cor: nada na arte deles é branco. Cineclube Pátria Grande e Calango saem por geometria — o "CINECLUBE" é branco e o "CALANGO" é creme, e tirar branco por cor comeria as letras. Errar isso não dá erro de build: dá buraco no logotipo. O Calango ainda precisa de 2 px de recuo em cada lado, senão a linha de transição contra o branco da folha vira moldura sobre a placa da mesma cor. |
| Desenho de ondas do FICA | **Retraçado, não recortado** | A fonte é `3o_FICA_GAROPABA.jpg`, cartaz de uma edição: traz numeral, datas, lista de cidades e reivindicações de programação, nada publicável. Em vez de apagar tipo de um raster, `trace_waves()` classifica cada pixel entre os cinco azuis chapados, acha a linha de topo de cada tom, fecha verticalmente (peixe e tipo são buracos no meio da faixa, não no topo) e despica. O desenho sai limpo, sem uma letra, e em coordenadas 0..1 — serve a qualquer tamanho. |
| Composição da placa do FICA | **Dois tons pálidos altos, três escuros rasos** | O logotipo é 1,45:1 e a placa é 1,5:1 — quase a mesma proporção, então marca e ondas disputam o mesmo espaço. Os dois tons pálidos sobem a 46% da placa e passam por trás da linha "Festival Internacional de Cinema Ambiental", onde o preto ainda tem 14:1; os três escuros ficam numa faixa d'água de 10%, abaixo do logotipo. Foram testadas quatro composições antes desta. |
| Tamanho da marca na placa | **90% da altura, teto de 93% na largura** | "Quase tangente à moldura", como pedido. A altura é o lado curto de uma placa 3:2, então ela é que manda; o teto de largura só entra para o FICA, que é deitado. |
| PNG das placas | **Reduzido a 256 cores (octree)** | O PNG é o ramo do `srcset` para quem não tem WebP. Em cor cheia o ladrilho do Calango saía a 405 KB; quantizado dá 40 KB, e o alfa mantém mais de cem níveis, então a borda não serrilha. A arte é chapada — em vários tamanhos o PNG fica MENOR que o WebP. |
| Logotipo × fotografia no card | **A marca ganha** | Um festival se reconhece primeiro pela marca. As fotos que serviam de capa desceram para a galeria: `fica-salao-comunitario` já estava lá, e `flaca-sala-cheia` foi acrescentada para não sumir do site. |
| Marcas de projeto | **Sete das dez** | FICA Garopaba, FLACA, FICA Calango, Cineclube Pátria Grande, Cine Retrata, Cineclube Educa Ambiental e Cineclube Marighella. Seguem com placa de tipo: #Abrindoacaixapreta, Arte para Voar e Oficinas de dança — não há marca para eles. |
| Cada marca pede um tratamento | **Chapado, alfa ou textura** | Educa Ambiental é ladrilho de cor chapada: `mark_box()` recorta a arte da margem verde e a placa repete o mesmo `#053305`. Marighella já chega com alfa e só foi assentado sobre branco. Cine Retrata tem fundo de TEXTURA com degradê de cima para baixo — cor chapada deixaria costura, então `bleed_tile()` escala o ladrilho pela marca e ESPELHA a textura nos ~5% de cada lado que ele não cobre. Escolher errado não quebra o build: estraga o logotipo em silêncio. |
| Grão do Cine Retrata | **Desfocado só no fundo** | O grão do papel é ruído de alta frequência: sozinho triplicava o arquivo e some na tela no tamanho servido. `_smooth_ground()` desfoca com a marca protegida por máscara — WebP de 654 para 198 KB no 1500, sem tirar um fio da linha preta. |
| Telefone | **Não é mais canal publicado** | Retirados em 7/9/2026 do bloco de contato e do rodapé das 21 páginas. Ficam e-mail e Instagram, e o bloco do Instagram passou a dizer que aceita mensagem direta. Os números seguem em `source/pesquisa-fontes.json` como registro. Para voltar atrás: reintroduzir a lista `phones` em `build-data.py` e o `<li>` no rodapé em `build-site.py`. |
| `sizes` dos cards | **Derivado da grade, não chutado** | `.projectgrid` é `auto-fill / minmax(min(100%,290px),1fr)` dentro de `.shell`: vira duas colunas em **656px** e três em **1003px**, e não existe media query nenhuma nesses pontos. O antigo `(min-width:900px) 30vw` subdeclarava **1,45×** entre 900 e 1002px — o navegador buscava o arquivo de 300px para uma caixa de 445px — e sobredeclarava 2,3× abaixo. Os valores em `SIZES_CARD` / `SIZES_CARD_FEATURE` foram conferidos largura a largura de 320 a 2560: nunca subdeclaram, sobram no máximo 1,13×. |
| Primeira placa de /projetos | **`loading="eager"` + `fetchpriority="high"`** | Ali a grade abre logo abaixo do cabeçalho, e a primeira placa é o maior elemento pintado da página. Preguiçosa, custava ~450 ms de LCP porque o pré-varredor não podia começar a busca. Em toda outra página as placas ficam abaixo da dobra e seguem preguiçosas. |
| Retrato de quem saiu da página | **Sai também do manifesto e do disco** | O `images.json` é catraca de mão única: obriga o arquivo a existir mas nada liga a entrada a um consumidor. Quatro pessoas retiradas em 7/9/2026 continuavam com o retrato publicado em URL estável e adivinhável, 403 KB, depois de sumirem do site. `check_assets()` agora reprova entrada de `equipe` que não corresponda a alguém em `equipe.json`. |
| Ficha técnica | **Sem ano, uma linha por pessoa** | Decisão de 7/9/2026. A ficha diz quem faz o quê no projeto, não em qual edição — Cristovam aparecia quatro vezes seguidas no FICA. As fichas do FICA e do FLACA são escritas à mão em `CREDITS_PUBLIC` (`tools/build-data.py`); as demais são fundidas automaticamente. A atribuição edição a edição continua em `source/pesquisa-fontes.json`. As linhas de **Fomento** mantêm o ano, que é o nome do edital, não crédito de equipe. |
| Onde o logotipo aparece | **Só na placa do card** | Decisão de 7/9/2026: nada de logotipo no cabeçalho da página do projeto. O card é o mesmo componente em toda parte, então ele aparece na grade de /projetos, na home e nos blocos de "projetos relacionados" — mudar isso por contexto faria o mesmo projeto ter card diferente em cada página. |
| Tamanho do logotipo na placa | **Por porcentagem da largura, nunca da altura** | A placa é 3:2, então a altura é 0,667 da largura. `min(52%, 168px)` dá 78% da altura disponível em qualquer tamanho e não depende de porcentagem de altura resolver dentro do grid — foi assim que o disco apareceu cortado na primeira tentativa. |
| Foto de abertura em página de projeto | **Não existe mais** | Removida em 7/9/2026 a pedido da produtora. O cabeçalho é tipografia sobre a faixa da marca. Só o FLACA tinha uma — `flaca-roda-de-conversa` —, e ela desceu para a **primeira posição da galeria**, onde continua sendo a imagem que abre o registro do projeto. |
| `og:image` de projeto | **Foto de abertura, senão a primeira da galeria com 1200 px ou mais** | Abaixo de 1200 px vale mais o cartão da marca: as redes pedem 1200 px e um arquivo de 640 px chegaria borrado. Hoje só o FLACA tem foto na prévia de link; o FICA Garopaba cai no cartão porque as duas fotos dele são de 640 px. |
| Manchete da home | "Cultura para conectar territórios." | É **sugestão** do §19, não assinatura aprovada. A alternativa é "Cinema, arte e encontro.". O §115 proíbe fixar slogan sem decisão interna. |

---

## 3. Armadilhas — erros que já custaram caro aqui

Coisas que pareciam certas e não eram. Vale reler antes de mexer nas áreas correspondentes.

1. **`pending` era a caderneta de apuração e estava sendo publicado.** Em todas as 11 páginas
   de projeto, imprimindo as metas que o próprio site declara proibidas (`4.070 pessoas`,
   `R$ 627.672,38`), nomes de arquivo interno e frases dirigidas ao editor. Hoje há dois
   campos: `pending` (público) e `notes_internal` (**nunca renderizado**). Se você reescrever
   `build-data.py`, não volte a copiar `unverified` para `pending`.

2. **Estilo em linha vence regra de folha.** As cores das placas vinham num `style=` inline, e
   a variação por faixa que eu escrevera nunca chegou a valer. Cor de componente vai por
   classe (`.plate--red` etc.), não por atributo.

3. **Faixa colorida precisa declarar os cinco tokens.** `.header` e `.scard` não declaravam, e
   o `:focus-visible` herdava o acento de `:root` — vermelho sobre vermelho, 1,00:1. Ao criar
   qualquer superfície de cor, copie o conjunto completo que `.band--red` usa.

4. **`vw` não serve para dimensionar tipo dentro de coluna estreita.** O `h1` do hero vive num
   painel com menos da metade da janela; entre 900 e 1199 px "TERRITÓRIOS." partia no meio.
   Agora usa `cqi` com `container-type: inline-size` no painel.

5. **O workflow copia diretórios inteiros.** `cp -r projetos _site/` publica qualquer arquivo
   dentro de uma rota. Um HTML de sonda de 41 KB chegou a ser commitado e enviado. O
   verificador agora recusa arquivo inesperado em diretório de rota.

6. **Sufixo de largura condicional é armadilha.** Antes, imagem com uma única largura saía sem
   sufixo no nome — acrescentar uma segunda largura renomeava arquivos já publicados. Hoje a
   largura entra sempre no nome.

7. **`srcset` promete arquivo que pode não existir.** Dois retratos anunciavam 640 px sem que
   o recorte chegasse a isso, e quem não tem WebP recebia 404. O verificador confere cada
   candidato de `srcset` e cada `src`.

8. **O verificador rodava depois da montagem** e comparava cada página com a cópia em `_site/`,
   acusando título duplicado. Hoje roda antes, e `_site` está na lista de não-rotas.

9. **Agentes de auditoria deixam resíduo.** Além do HTML de sonda, um deles renomeou
   `cristovam-muniz-640.jpg` para testar o verificador e não desfez. Depois de qualquer rodada
   com subagentes, rodar `git status` e `python3 tools/check-site.py`.

---

- **Recortar arte clara por cor sobre fundo escuro deixa halo.** O `strip_white` dá alfa
  proporcional à distância do branco, então o pixel a meio caminho entre a arte e o papel
  fica OPACO e cinza-claro. Sobre branco não se vê; sobre o azul-marinho do FLACA virava um
  anel luminoso de 4 px em volta do disco — o "recorte colado" que a cor medida existe para
  evitar. Disco vai de máscara geométrica, com recuo de 4 px. Só o FICA sai por cor, e pode:
  a placa dele é branca.
- **Mediana com borda replicada não enxerga discrepância na ponta.** `_median` enche a borda
  com cópias do próprio valor da extremidade, então o ponto discrepante vira a sua própria
  mediana e o despique nunca o aponta. No traçado das ondas isso deixava uma lasca pálida de
  1 a 3 px descendo as duas laterais da placa do FICA. Há uma guarda explícita para as pontas
  antes do despique.
- **`sizes` inventado é blur invisível no desenvolvimento.** Sai da grade, não do palpite —
  e a grade desta folha de estilo muda de coluna em pontos que não têm media query.

## 4. Fila de trabalho

### 4.1. Bloqueia o lançamento

- [ ] **Certificado do `www`** — ver seção 1. É a única coisa quebrada para o visitante.

### 4.2. Decisões que só a produtora pode tomar

- [ ] Confirmar a grafia com **Thais Alemany**, **Giulia Giacomolli** e **Esteban Zapata**
      (o currículo dele traz "Esteban Gabriel Mederos Zapata").
- [ ] Aprovar ou trocar a **manchete da home**.
- [ ] **Cristovam e a direção do FICA**: a bio agora diz "é diretor geral do FICA Garopaba
      desde a primeira edição", redação ditada pela produtora em 7/9/2026. O currículo dele
      dizia "dirigiu as três primeiras edições e assumiu a direção de curadoria da quarta" —
      a direção de curadoria da 4ª edição saiu do texto. Confirmar se deve voltar.
- [ ] **Bios da Rede**: as 14 pessoas que restaram nunca tiveram bio revisada. As de
      Sara Santos e Tayná Oliveira foram reescritas em 7/9/2026 só para tirar o nome do
      cineclube retirado — vale uma leitura delas.
- [ ] Definir **qual telefone é o principal** e qual é WhatsApp. Hoje os dois aparecem sem
      distinção.
- [x] ~~**Numeração das edições em andamento**~~ — RESOLVIDO em 07/09/2026 pelo produtor:
      os cards passam a dizer **"5ª edição"** (FICA) e **"2ª edição"** (FLACA), seguindo a
      contagem do portfólio (quatro edições do FICA, uma do FLACA). O título registrado na
      Lei Rouanet continua citado como está no PRONAC ("6º FICA", "III FLACA") e o texto de
      cada projeto explica a divergência em uma frase. Fonte da decisão: instrução do produtor,
      coerente com os CVs de Cristovam Muniz e Thais Alemany, que já falavam em 5ª edição.
- [x] ~~**Foto de capa**~~ — RESOLVIDO em 07/09/2026: a capa passou a ser `251115_8122.jpg`
      (`sessao-ao-ar-livre-conversa`, sessão ao ar livre à noite), e a antiga capa
      `casa-cheia-debate` desceu para o full-bleed de /quem-somos. O corte virou 3:2 porque o
      original 2040×1361 já é 3:2 — a capa usa o quadro inteiro, sem perda.
- [ ] **Foto na rua com o telão**: pedida em 07/09/2026 e não existe no material. As 13 fotos
      de "Site Pátria Grande 2026" e as 8 legadas são todas internas ou cobertas. O telão
      inflável só aparece em `20251104_155037-2.jpg` (ginásio, crianças em primeiro plano —
      bloqueada por direito de imagem), `flaca-6.jpg` (mesma situação) e
      `fica-salao-comunitario.jpg` (salão comunitário, 700×525 — pequena demais para capa).
      Se o arquivo aparecer, é trocar `destino: home.hero` em `source/v2-conteudo.json`.
- [ ] **Inventário de projeção** e **pares de idiomas** da tradução: as páginas de serviço
      declaram que o escopo é definido caso a caso, conforme §48 e §49. Fechar internamente.
- [ ] **Oficinas de dança**: falta nome oficial, datas, responsáveis, público e financiamento.
      A página está deliberadamente curta e sem ano.
- [ ] **Autorização de uso de imagem** para as três fotos bloqueadas.

### 4.3. Achados de auditoria ainda abertos

Da verificação adversarial (46 confirmados de 78 brutos), **14 seguem abertos**. Nenhum impede
publicar. O relatório completo, com evidência e correção prescrita para cada um, está em
`/tmp/…/tasks/w9x0q2msk.output` — **volátil**; se for preciso, refazer com o workflow
`patria-grande-v2-verify`.

**Média**

- [ ] `/servicos/producao-executiva` publica como fato assentado dados que as páginas de
      projeto registram como disputados.
- [ ] Abas e filtros de `/projetos/` ficam sem estado e sem função quando o JS não roda.
- [ ] A guarda do §31 em `check-site.py` está desarmada nos dois projetos que deveria vigiar —
      a busca por palavra de resultado não casa com o texto real dos blocos.
- [ ] O hero de tela dividida descarta 51% da foto e corta o assunto descrito no `alt`.
- [ ] A aba se chama "Realizados" e a nota logo abaixo fala em "Executados".
- [ ] `/projetos/oficinas-de-danca/` publica o mesmo parágrafo três vezes — `summary` e
      `concept` são o mesmo texto em `build-data.py`.

**Baixa**

- [ ] Créditos que `/equipe` atribui a FICA e FLACA não constam nas fichas técnicas desses
      projetos.
- [ ] Sem JavaScript o menu fica inacessível abaixo de 901 px — e o comentário no topo do
      `main.js` afirma o contrário do que o código faz.
- [ ] Sete campos dos JSON chegam ao HTML sem passar por `e()` nem `inline()` (e-mail,
      Instagram, telefones — todos dado interno, não entrada de usuário).
- [ ] Código morto nos geradores.
- [ ] A galeria não aceita swipe, exigido pelo §75.
- [ ] `"044.000/SMLCP/2024"` extrapola a coluna na ficha do projeto.
- [ ] "Guaporé (RO)" publicado com UF numa página e sem UF em outra, apesar de a apuração
      registrar dúvida.
- [ ] `role_line` de Jia ("Produção Assistente") e de Luna Vanzella ("Curadoria · Coordenação
      de Curadoria", que se repete).

### 4.4. Conteúdo que falta

- [ ] **Clipping** — não há página de imprensa nesta versão, por decisão do §16. O material
      entra nas páginas dos próprios projetos.
- [ ] **Créditos completos por edição** de FICA, FLACA, Educa Ambiental e
      Cineclube Pátria Grande.
- [ ] **Fotografia**: seis dos onze projetos não têm nenhuma e usam placa de cor. O FICA tem
      só dois registros publicáveis, ambos em baixa resolução, extraídos de apresentações.
- [ ] **Retratos**: Thais Alemany, Jia e Bruno Souza estão sem foto (Bruno está fora do site,
      pasta vazia). Flávio Veloso usa um registro de celular de 2023 — é o card do fundador.
- [ ] **Métricas acumuladas do FICA** só voltam depois de conferidas contra o clipping final.

---

## 5. Como retomar

```bash
cd /home/userntt/Documentos/patriagrande
python3 -m http.server 8000        # preview
python3 tools/check-site.py        # tem de dizer "Tudo certo."
```

Editar conteúdo é mexer nos JSON de `source/` e rodar `tools/build-site.py`. **`build-data.py`
sobrescreve** `projetos.json`, `equipe.json`, `servicos.json` e `site.json` a partir de
`pesquisa-fontes.json` + `v2-conteudo.json` — no dia a dia, edite o arquivo de destino; só rode
o `build-data.py` quando o conteúdo bruto mudar.

Regenerar imagem ou marca exige `reference-content/`, que não está no repositório (115 MB de
PDFs, currículos, logotipos e fotografias em resolução integral, na máquina de quem edita).

**As duas regras que o CI faz cumprir** — e que são a razão de o site ter a forma que tem:
só aparece como realizado o que já foi executado; e previsão nunca é resultado. Ver `README.md`.

## 6. Fontes

| Arquivo | O que é |
| --- | --- |
| `source/patria-grande-producoes-site-source-v2.md` | A especificação editorial. Autoridade. |
| `source/patria-grande-producoes-relatorio-site.md` | A versão anterior, mantida por referência. |
| `source/pesquisa-fontes.json` | Procedência de cada fato: de qual currículo ou apresentação veio, e o que não pôde ser confirmado. |
| `source/v2-conteudo.json` | A redação feita para esta versão do site. |
| `reference-content/Site Pátria Grande 2026/` | O pacote da produtora: logotipos, 13 fotografias e quatro documentos. **Dois deles são formulários em branco** — `Roteiro projetos para site.docx` e `Equipe para site.docx` definem campos, não conteúdo. O único com texto acabado é `estrutura site pátria 2026.docx`. |
