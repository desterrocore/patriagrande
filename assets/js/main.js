/* ===========================================================================
   PÁTRIA GRANDE PRODUÇÕES — comportamento
   ---------------------------------------------------------------------------
   Quatro coisas, nesta ordem de importância:

     1. o menu no celular;
     2. as abas e os filtros do arquivo de projetos;
     3. a ampliação de fotografias na galeria;
     4. uma revelação curta na rolagem.

   Nada aqui é necessário para ler o site. Sem JavaScript o menu fica aberto
   como lista, o portfólio mostra todos os projetos, a galeria abre a imagem
   em cheio no próprio navegador e nada fica escondido — por isso a classe
   `no-js` sai do <html> só depois que este arquivo executa.
   =========================================================================== */

(function () {
  'use strict';

  document.documentElement.classList.remove('no-js');

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* -------------------------------------------------------------------------
     1. Menu
     O botão só existe abaixo de 901px. Acima disso a lista é sempre visível,
     então o estado aria-expanded é irrelevante e o botão sai da árvore.
     ------------------------------------------------------------------------- */

  var toggle = document.querySelector('.nav__toggle');
  var list = document.getElementById('nav-list');

  if (toggle && list) {
    var setOpen = function (open) {
      list.dataset.open = open ? 'true' : 'false';
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    };

    setOpen(false);

    toggle.addEventListener('click', function () {
      setOpen(list.dataset.open !== 'true');
    });

    // Fecha ao escolher um destino, ao apertar Esc e ao clicar fora.
    list.addEventListener('click', function (e) {
      if (e.target.closest('a')) setOpen(false);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && list.dataset.open === 'true') {
        setOpen(false);
        toggle.focus();
      }
    });

    document.addEventListener('click', function (e) {
      if (list.dataset.open !== 'true') return;
      if (!e.target.closest('.header')) setOpen(false);
    });

    // Ao voltar para o desktop o estado do celular não pode ficar preso.
    window.matchMedia('(min-width: 901px)').addEventListener('change', function (e) {
      if (e.matches) setOpen(false);
    });
  }

  /* -------------------------------------------------------------------------
     2. Arquivo de projetos: abas de situação + filtros de categoria

     A lista já vem inteira no HTML, e a seleção é feita no cliente. Sem
     JavaScript a página é o arquivo completo — que é exatamente o
     comportamento correto para um arquivo. As duas dimensões são
     independentes: a aba diz se o projeto foi realizado ou está em andamento,
     o filtro diz de que tipo ele é, e elas se combinam.
     ------------------------------------------------------------------------- */

  var filterBar = document.querySelector('[data-filters]');
  var tabBar = document.querySelector('[data-tabs]');

  if (filterBar || tabBar) {
    var cards = Array.prototype.slice.call(document.querySelectorAll('[data-status]'));
    var count = document.querySelector('[data-filter-count]');
    var panel = document.getElementById('painel-projetos');
    var fButtons = filterBar
      ? Array.prototype.slice.call(filterBar.querySelectorAll('.filters__btn'))
      : [];
    var tButtons = tabBar
      ? Array.prototype.slice.call(tabBar.querySelectorAll('.tabs__btn'))
      : [];

    var state = { tab: 'executado', filtro: 'todos' };

    var label = function (n, tab) {
      var noun = n === 1 ? 'projeto' : 'projetos';
      return n + ' ' + noun + (tab === 'andamento' ? ' em andamento' : ' realizados');
    };

    var apply = function () {
      var shown = 0;
      var inTab = 0;

      cards.forEach(function (card) {
        // O status é uma lista: um projeto com histórico e edição corrente
        // aparece nas duas abas.
        var okTab = (card.dataset.status || '').split(/\s+/).indexOf(state.tab) !== -1;
        if (okTab) inTab++;
        var cats = (card.dataset.category || '').split(/\s+/);
        var okCat = state.filtro === 'todos' || cats.indexOf(state.filtro) !== -1;
        var match = okTab && okCat;
        card.hidden = !match;
        if (match) shown++;
      });

      fButtons.forEach(function (b) {
        b.setAttribute('aria-pressed', b.dataset.filter === state.filtro ? 'true' : 'false');
      });
      tButtons.forEach(function (b) {
        var on = b.dataset.tab === state.tab;
        b.setAttribute('aria-selected', on ? 'true' : 'false');
        b.tabIndex = on ? 0 : -1;
        // O painel é um só e muda de dono conforme a aba: sem isso o leitor de
        // tela anuncia sempre o mesmo rótulo, qualquer que seja a aba ativa.
        if (on && panel) panel.setAttribute('aria-labelledby', b.id);
      });

      if (count) {
        count.textContent =
          shown === inTab ? label(shown, state.tab) : shown + ' de ' + label(inTab, state.tab);
      }

      // A seleção sobrevive a um recarregamento e é compartilhável por link.
      var url = new URL(window.location.href);
      if (state.tab === 'executado') url.searchParams.delete('situacao');
      else url.searchParams.set('situacao', state.tab);
      if (state.filtro === 'todos') url.searchParams.delete('filtro');
      else url.searchParams.set('filtro', state.filtro);
      history.replaceState(null, '', url);
    };

    if (filterBar) {
      filterBar.addEventListener('click', function (e) {
        var btn = e.target.closest('.filters__btn');
        if (!btn) return;
        state.filtro = btn.dataset.filter;
        apply();
      });
    }

    if (tabBar) {
      tabBar.addEventListener('click', function (e) {
        var btn = e.target.closest('.tabs__btn');
        if (!btn) return;
        state.tab = btn.dataset.tab;
        apply();
      });

      // Setas percorrem as abas, como manda o padrão de tablist.
      tabBar.addEventListener('keydown', function (e) {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        var i = tButtons.findIndex(function (b) { return b.dataset.tab === state.tab; });
        var next = (i + (e.key === 'ArrowRight' ? 1 : -1) + tButtons.length) % tButtons.length;
        state.tab = tButtons[next].dataset.tab;
        apply();
        tButtons[next].focus();
        e.preventDefault();
      });
    }

    var params = new URL(window.location.href).searchParams;
    var wantTab = params.get('situacao');
    var wantFiltro = params.get('filtro');
    if (wantTab && tButtons.some(function (b) { return b.dataset.tab === wantTab; })) state.tab = wantTab;
    if (wantFiltro && fButtons.some(function (b) { return b.dataset.filter === wantFiltro; })) state.filtro = wantFiltro;
    apply();
  }

  /* -------------------------------------------------------------------------
     3. Galeria
     Cada figura da galeria é um link para a imagem grande. Com JavaScript o
     link vira um <dialog> nativo — que já traz foco preso, Esc e camada de
     topo de graça — com navegação por seta entre as fotos da mesma galeria.
     ------------------------------------------------------------------------- */

  var galleries = Array.prototype.slice.call(document.querySelectorAll('[data-gallery]'));

  if (galleries.length && typeof HTMLDialogElement === 'function') {
    var dialog = document.createElement('dialog');
    dialog.className = 'lightbox';
    dialog.innerHTML =
      '<figure class="lightbox__fig">' +
      '<img class="lightbox__img" alt="">' +
      '<figcaption class="lightbox__cap archivecaption"></figcaption>' +
      '</figure>' +
      '<div class="lightbox__ui">' +
      '<button type="button" class="lightbox__btn" data-step="-1">← Anterior</button>' +
      '<span class="lightbox__pos" aria-live="polite"></span>' +
      '<button type="button" class="lightbox__btn" data-step="1">Próxima →</button>' +
      '<button type="button" class="lightbox__btn lightbox__close">Fechar ✕</button>' +
      '</div>';
    document.body.appendChild(dialog);

    var dImg = dialog.querySelector('.lightbox__img');
    var dCap = dialog.querySelector('.lightbox__cap');
    var dPos = dialog.querySelector('.lightbox__pos');

    var current = { items: [], index: 0 };

    var show = function (i) {
      var items = current.items;
      if (!items.length) return;
      current.index = (i + items.length) % items.length;
      var it = items[current.index];
      dImg.src = it.href;
      dImg.alt = it.alt;
      dCap.innerHTML = it.caption;
      dCap.hidden = !it.caption;
      dPos.textContent = current.index + 1 + ' de ' + items.length;
    };

    galleries.forEach(function (gal) {
      gal.addEventListener('click', function (e) {
        var link = e.target.closest('a[data-full]');
        if (!link) return;
        e.preventDefault();

        current.items = Array.prototype.slice.call(gal.querySelectorAll('a[data-full]')).map(function (a) {
          var fig = a.closest('figure');
          var cap = fig && fig.querySelector('figcaption');
          var img = a.querySelector('img');
          return {
            href: a.getAttribute('href'),
            alt: img ? img.alt : '',
            caption: cap ? cap.innerHTML : ''
          };
        });

        show(current.items.findIndex(function (it) { return it.href === link.getAttribute('href'); }));
        dialog.showModal();
      });
    });

    dialog.addEventListener('click', function (e) {
      var step = e.target.closest('[data-step]');
      if (step) { show(current.index + Number(step.dataset.step)); return; }
      if (e.target.closest('.lightbox__close')) { dialog.close(); return; }
      // Clique no fundo (fora da figura e fora dos controles) fecha.
      if (e.target === dialog) dialog.close();
    });

    dialog.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); show(current.index + 1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(current.index - 1); }
    });

    // Libera a memória da imagem grande quando o diálogo fecha.
    dialog.addEventListener('close', function () { dImg.removeAttribute('src'); });
  }

  /* -------------------------------------------------------------------------
     4. Revelação na rolagem
     Uma vez por elemento, e nunca quando o sistema pede menos movimento.
     ------------------------------------------------------------------------- */

  var revealables = document.querySelectorAll('[data-reveal]');

  if (!revealables.length) return;

  if (reduced || !('IntersectionObserver' in window)) {
    revealables.forEach(function (el) { el.classList.add('is-in'); });
    return;
  }

  var io = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      });
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.06 }
  );

  revealables.forEach(function (el) { io.observe(el); });
})();
