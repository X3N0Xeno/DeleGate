/* DeleGate UI behaviour. Vanilla, no dependencies.
   Everything is wired through data-* attributes so the templates stay declarative:

   data-theme-set="aether"         theme switcher buttons
   data-sun-set="auto|dawn|day|golden|night"   time-of-day preview pills
   data-open-drawer="tpl-id"       open the slide-over with the contents of <template id="tpl-id">
   data-drawer-close               close the slide-over
   <form data-confirm="...">       ask in-app instead of window.confirm()
   <form data-reopen>              inside a drawer: reopen the same drawer after the page reloads
   data-toggle-password="input-id" show / hide a password
   data-nav-template="?x=__v__"    <select> that navigates on change
   data-shortcut="c"               click this element when the key is pressed
*/
(function () {
  'use strict';

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var signedIn = !!$('meta[name="dg-auth"]');
  var csrf = function () { var m = $('meta[name="csrf-token"]'); return m ? m.content : ''; };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    sget: function (k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
    sset: function (k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} },
    sdel: function (k) { try { sessionStorage.removeItem(k); } catch (e) {} }
  };

  /* ---------------------------------------------------------------- toasts */
  var toastHost = $('#toasts');

  function dismissToast(el) {
    if (!el.parentNode) return;
    el.classList.add('is-leaving');
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, reduceMotion ? 0 : 240);
  }

  function armToast(el, ms) {
    var tone = el.getAttribute('data-tone');
    var life = ms || (tone === 'error' || tone === 'warning' ? 7000 : 4200);
    var timer = setTimeout(function () { dismissToast(el); }, life);
    el.addEventListener('mouseenter', function () { clearTimeout(timer); });
    el.addEventListener('mouseleave', function () { timer = setTimeout(function () { dismissToast(el); }, 1800); });
    el.addEventListener('click', function () { dismissToast(el); });
  }

  function toast(message, tone) {
    if (!toastHost) return;
    var el = document.createElement('div');
    el.className = 'toast';
    el.setAttribute('data-tone', tone || 'info');
    el.setAttribute('role', tone === 'error' ? 'alert' : 'status');
    el.textContent = message;
    toastHost.appendChild(el);
    armToast(el);
  }

  $$('.toast', toastHost || document).forEach(function (el) { armToast(el); });
  window.dgToast = toast;

  /* ----------------------------------------------------------------- theme */
  var THEMES = ['aether', 'terrace', 'mist'];

  // circadian.js owns the colours; this only keeps the pickers in step with it.
  function paintTheme(theme) {
    $$('[data-theme-set]').forEach(function (btn) {
      var on = btn.getAttribute('data-theme-set') === theme;
      btn.setAttribute('aria-checked', on ? 'true' : 'false');
      btn.tabIndex = on ? 0 : -1;
    });
  }

  function chooseTheme(theme, url) {
    if (THEMES.indexOf(theme) === -1) return;
    if (window.Circadian) window.Circadian.setTheme(theme);   // instant, client side
    paintTheme(theme);
    if (!signedIn || !url) return;   // signed-out pages only remember it locally
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      keepalive: true,
      headers: { 'X-CSRFToken': csrf(), 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'fetch' },
      body: 'theme=' + encodeURIComponent(theme)
    }).then(function (res) {
      if (!res.ok) throw new Error('bad status');
    }).catch(function () {
      toast('Theme changed here, but it could not be saved to your account.', 'warning');
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-theme-set]');
    if (!btn) return;
    var host = btn.closest('[data-theme-url]');
    chooseTheme(btn.getAttribute('data-theme-set'), host ? host.getAttribute('data-theme-url') : '');
  });

  // Compact density previews instantly
  document.addEventListener('change', function (e) {
    if (!e.target.matches || !e.target.matches('[data-density-toggle]')) return;
    if (e.target.checked) document.documentElement.setAttribute('data-density', 'compact');
    else document.documentElement.removeAttribute('data-density');
  });

  // Arrow keys move through a radio group of themes
  document.addEventListener('keydown', function (e) {
    var btn = e.target.closest && e.target.closest('[data-theme-set]');
    if (!btn || ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].indexOf(e.key) === -1) return;
    var group = $$('[data-theme-set]', btn.closest('[role="radiogroup"]') || document);
    var i = group.indexOf(btn);
    var next = group[(i + (e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? group.length - 1 : 1)) % group.length];
    e.preventDefault();
    next.focus();
    next.click();
  });

  paintTheme(document.documentElement.getAttribute('data-solarpunk-theme') || 'aether');

  // ------------------------------------------------------------- time of day
  var SUN_DETAIL = {
    auto: 'Following your local sun',
    dawn: 'Previewing dawn',
    day: 'Previewing solar day',
    golden: 'Previewing golden hour',
    night: 'Previewing night'
  };

  function paintSun() {
    if (!window.Circadian) return;
    var st = window.Circadian.getState();
    $$('[data-sun-set]').forEach(function (btn) {
      var on = btn.getAttribute('data-sun-set') === st.mode;
      btn.setAttribute('aria-checked', on ? 'true' : 'false');
      btn.tabIndex = on ? 0 : -1;
    });
    $$('[data-sun-label]').forEach(function (el) { el.textContent = st.label; });
    $$('[data-sun-detail]').forEach(function (el) {
      if (el.closest('.sun-panel')) el.textContent = SUN_DETAIL[st.mode];
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-sun-set]');
    if (btn && window.Circadian) window.Circadian.setMode(btn.getAttribute('data-sun-set'));
  });
  document.addEventListener('keydown', function (e) {
    var btn = e.target.closest && e.target.closest('[data-sun-set]');
    if (!btn || ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].indexOf(e.key) === -1) return;
    var group = $$('[data-sun-set]', btn.closest('[role="radiogroup"]'));
    var i = group.indexOf(btn);
    var next = group[(i + (e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? group.length - 1 : 1)) % group.length];
    e.preventDefault();
    next.focus();
    next.click();
  });
  window.addEventListener('circadian:change', paintSun);
  paintSun();

  /* ---------------------------------------------------------------- drawer */
  var drawer = $('#drawer');
  var drawerBody = $('#drawer-body');
  var closing = null;

  function openDrawer(tplId) {
    var tpl = document.getElementById(tplId);
    if (!drawer || !tpl) return;
    clearTimeout(closing);
    drawerBody.replaceChildren(tpl.content.cloneNode(true));
    $('#drawer-title').textContent = tpl.getAttribute('data-title') || '';
    $('#drawer-kicker').textContent = tpl.getAttribute('data-kicker') || '';
    drawer.setAttribute('data-tpl', tplId);
    drawerBody.scrollTop = 0;
    document.documentElement.classList.add('drawer-open');
    document.body.classList.add('drawer-open');
    if (!drawer.open) drawer.show();
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { drawer.classList.add('is-open'); });
    });
    var first = $('[autofocus]', drawerBody) || $('[data-drawer-close]', drawer);
    if (first) first.focus({ preventScroll: true });
  }

  function closeDrawer() {
    if (!drawer || !drawer.open) return;
    drawer.classList.remove('is-open');
    document.documentElement.classList.remove('drawer-open');
    document.body.classList.remove('drawer-open');
    clearTimeout(closing);
    closing = setTimeout(function () { if (drawer.open) drawer.close(); }, reduceMotion ? 0 : 300);
  }

  if (drawer) {
    drawer.addEventListener('cancel', function (e) { e.preventDefault(); closeDrawer(); });
    drawer.addEventListener('close', function () {
      drawer.classList.remove('is-open');
      document.documentElement.classList.remove('drawer-open');
      document.body.classList.remove('drawer-open');
      drawer.removeAttribute('data-tpl');
      drawerBody.replaceChildren();
    });
    drawer.addEventListener('click', function (e) {
      if (e.target === drawer) closeDrawer();   // click on the dimmed area
    });
  }

  document.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-open-drawer]');
    if (opener) { e.preventDefault(); openDrawer(opener.getAttribute('data-open-drawer')); return; }
    if (e.target.closest('[data-drawer-close]')) closeDrawer();
  });

  // Reopen the drawer after a note / comment / blocker save, or from a #task-12 link
  var reopen = store.sget('dg-reopen');
  if (reopen) { store.sdel('dg-reopen'); openDrawer(reopen); }
  else if (/^#task-\d+$/.test(location.hash)) openDrawer('tpl-' + location.hash.slice(1));

  /* ---------------------------------------------------------------- confirm */
  var dialog = $('#confirm');
  var pendingResolve = null;

  function settle(result) {
    if (!dialog || !dialog.open) return;
    dialog.classList.remove('is-open');
    document.documentElement.classList.remove('drawer-open');
    document.body.classList.remove('drawer-open');
    var resolve = pendingResolve;
    pendingResolve = null;
    setTimeout(function () { if (dialog.open) dialog.close(); }, reduceMotion ? 0 : 200);
    if (resolve) resolve(result);
  }

  function ask(opts) {
    return new Promise(function (resolve) {
      if (!dialog) { resolve(true); return; }
      pendingResolve = resolve;
      $('#confirm-title').textContent = opts.title || 'Are you sure?';
      $('#confirm-message').textContent = opts.message || '';
      var ok = $('#confirm-ok');
      ok.textContent = opts.label || 'Confirm';
      ok.className = 'btn ' + (opts.tone === 'danger' ? 'btn-critical' : '');
      document.documentElement.classList.add('drawer-open');
      document.body.classList.add('drawer-open');
      if (!dialog.open) dialog.show();
      requestAnimationFrame(function () { dialog.classList.add('is-open'); });
      (opts.tone === 'danger' ? $('#confirm-cancel') : ok).focus();
    });
  }

  if (dialog) {
    $('#confirm-ok').addEventListener('click', function () { settle(true); });
    $('#confirm-cancel').addEventListener('click', function () { settle(false); });
    dialog.addEventListener('cancel', function (e) { e.preventDefault(); settle(false); });
    dialog.addEventListener('click', function (e) { if (e.target === dialog) settle(false); });
  }

  /* ----------------------------------------------------------- form submits */
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!(form instanceof HTMLFormElement)) return;

    if (form.hasAttribute('data-confirm') && !form.hasAttribute('data-confirmed')) {
      e.preventDefault();
      ask({
        message: form.getAttribute('data-confirm'),
        title: form.getAttribute('data-confirm-title'),
        label: form.getAttribute('data-confirm-label'),
        tone: form.getAttribute('data-confirm-tone')
      }).then(function (ok) {
        if (!ok) return;
        form.setAttribute('data-confirmed', '');
        form.requestSubmit();
      });
      return;
    }

    if (form.hasAttribute('data-reopen') && drawer && drawer.open && drawer.getAttribute('data-tpl')) {
      store.sset('dg-reopen', drawer.getAttribute('data-tpl'));
    }

    // Optimistic UI feedback for mining and gate pass actions
    var submitBtn = $('button[type="submit"]', form);
    if (submitBtn) {
      var btnText = submitBtn.textContent.trim();
      if (btnText === 'Mine!') {
        submitBtn.innerHTML = '<span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:currentColor;margin-right:4px;animation:pulseGlow 0.8s infinite;"></span> Mining...';
        var row = form.closest('.row');
        if (row) {
          row.style.transition = 'all 0.3s ease';
          row.style.background = 'color-mix(in srgb, var(--accent) 12%, var(--surface))';
          row.style.borderColor = 'var(--accent)';
        }
      } else if (btnText.indexOf('Pass Gate') !== -1 || btnText.indexOf('Approve') !== -1) {
        submitBtn.textContent = 'Passing Gate...';
      }
    }

    // One click, one action: stops a double-click mining or approving twice
    setTimeout(function () {
      $$('button[type="submit"]', form).forEach(function (b) {
        b.disabled = true;
        b.setAttribute('aria-busy', 'true');
      });
    }, 0);
  });

  // Back/forward cache can restore a page with its buttons still disabled
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    $$('button[aria-busy="true"]').forEach(function (b) { b.disabled = false; b.removeAttribute('aria-busy'); });
    $$('form[data-confirmed]').forEach(function (f) { f.removeAttribute('data-confirmed'); });
  });

  /* ------------------------------------------------------------ gate stepper */
  // Reveal the rail once, then play any lock / unlock that happened since the
  // last visit: the gate is first drawn in its old state and flips to the new one.
  $$('.gates').forEach(function (rail) {
    var project = rail.getAttribute('data-project');
    var flips = [];

    if (project) {
      var key = 'dg-gates-' + project;
      var before = {};
      try { before = JSON.parse(store.get(key) || '{}'); } catch (err) { before = {}; }
      var now = {};
      $$('.gate', rail).forEach(function (gate) {
        var id = gate.getAttribute('data-gate');
        var state = gate.getAttribute('data-state');
        now[id] = state;
        if (before[id] && before[id] !== state && !reduceMotion) {
          flips.push({ gate: gate, to: state });
          gate.setAttribute('data-state', before[id]);
        }
      });
      store.set(key, JSON.stringify(now));
    }

    // Decorative gates (sign-in page) carry data-then="active|passed"
    $$('.gate[data-then]', rail).forEach(function (gate) {
      flips.push({ gate: gate, to: gate.getAttribute('data-then') });
    });

    requestAnimationFrame(function () { rail.classList.add('is-ready'); });
    flips.forEach(function (flip, i) {
      setTimeout(function () { flip.gate.setAttribute('data-state', flip.to); }, (reduceMotion ? 0 : 900) + i * 420);
    });
  });

  /* -------------------------------------------------------- small behaviours */
  // Password show / hide
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-toggle-password]');
    if (!btn) return;
    var input = document.getElementById(btn.getAttribute('data-toggle-password'));
    if (!input) return;
    var show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.setAttribute('aria-pressed', show ? 'true' : 'false');
    btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    var icons = $$('svg', btn);
    if (icons[0]) icons[0].hidden = show;
    if (icons[1]) icons[1].hidden = !show;
  });

  // Selects that navigate (bypassed if instant client-side filter is present)
  document.addEventListener('change', function (e) {
    var sel = e.target.closest && e.target.closest('select[data-nav-template]');
    if (sel && !sel.hasAttribute('data-instant-gate-filter')) {
      location.href = sel.getAttribute('data-nav-template').replace('__v__', encodeURIComponent(sel.value));
    }
  });

  // ------------------------------------------ Instant client-side tab filtering
  // Claimant queue instant tab filter (zero page reload)
  document.addEventListener('click', function (e) {
    var tab = e.target.closest && e.target.closest('[data-instant-filter="claimant-queue"] a.tab');
    if (!tab) return;
    e.preventDefault();
    var nav = tab.closest('[data-instant-filter]');
    var key = tab.getAttribute('data-filter-tab') || 'all';
    $$('.tab', nav).forEach(function (t) {
      if (t === tab) t.setAttribute('aria-current', 'page');
      else t.removeAttribute('aria-current');
    });

    var rows = $$('#claimant-queue-list > li.row');
    var visible = 0;
    rows.forEach(function (row) {
      var status = (row.getAttribute('data-task-status') || '').toLowerCase();
      var match = (key === 'all') || (status === key);
      row.style.display = match ? '' : 'none';
      if (match) visible++;
    });

    var countBadge = $('#claimant-queue-count');
    if (countBadge) countBadge.textContent = visible;

    var empty = $('#claimant-queue-empty');
    if (empty) empty.style.display = (visible === 0) ? '' : 'none';

    try { history.replaceState(null, '', tab.href); } catch (err) {}
  });

  // Assigner board instant tab + gate filter (zero page reload)
  function applyAssignerFilters() {
    var nav = $('[data-instant-filter="assigner-board"]');
    var activeTab = nav ? $('a.tab[aria-current="page"]', nav) : null;
    var statusKey = activeTab ? (activeTab.getAttribute('data-filter-tab') || 'all') : 'all';

    var gateSel = $('select[data-instant-gate-filter]');
    var gateKey = gateSel ? gateSel.value : 'all';

    var containers = $$('.gate-group-container');
    var totalVisible = 0;

    containers.forEach(function (container) {
      var groupGate = container.getAttribute('data-gate-group');
      var gateMatch = (gateKey === 'all') || (groupGate === gateKey);

      if (!gateMatch) {
        container.style.display = 'none';
        return;
      }

      var rows = $$('li.row', container);
      var groupVisible = 0;

      rows.forEach(function (row) {
        var status = (row.getAttribute('data-task-status') || '').toLowerCase();
        var blocked = row.getAttribute('data-task-blocked') === '1';

        var statusMatch = false;
        if (statusKey === 'all') statusMatch = true;
        else if (statusKey === 'open') statusMatch = (status === 'open');
        else if (statusKey === 'mined') statusMatch = (status === 'claimed' || status === 'in_progress');
        else if (statusKey === 'review') statusMatch = (status === 'in_review');
        else if (statusKey === 'blocked') statusMatch = blocked;
        else if (statusKey === 'completed') statusMatch = (status === 'completed');

        row.style.display = statusMatch ? '' : 'none';
        if (statusMatch) groupVisible++;
      });

      var countEl = $('[data-group-count]', container);
      if (countEl) countEl.textContent = groupVisible + ' task' + (groupVisible === 1 ? '' : 's');

      container.style.display = (groupVisible > 0) ? '' : 'none';
      totalVisible += groupVisible;
    });

    var empty = $('#assigner-empty-filter');
    if (empty) empty.style.display = (totalVisible === 0) ? '' : 'none';
  }

  document.addEventListener('click', function (e) {
    var tab = e.target.closest && e.target.closest('[data-instant-filter="assigner-board"] a.tab');
    if (!tab) return;
    e.preventDefault();
    var nav = tab.closest('[data-instant-filter]');
    $$('.tab', nav).forEach(function (t) {
      if (t === tab) t.setAttribute('aria-current', 'page');
      else t.removeAttribute('aria-current');
    });
    applyAssignerFilters();
    try { history.replaceState(null, '', tab.href); } catch (err) {}
  });

  document.addEventListener('change', function (e) {
    var sel = e.target.closest && e.target.closest('select[data-instant-gate-filter]');
    if (!sel) return;
    applyAssignerFilters();
    var template = sel.getAttribute('data-nav-template');
    if (template) {
      try { history.replaceState(null, '', template.replace('__v__', encodeURIComponent(sel.value))); } catch (err) {}
    }
  });

  // Account menu: close on outside click / Escape
  function closeMenus(except) {
    $$('details.menu[open]').forEach(function (m) { if (m !== except) m.removeAttribute('open'); });
  }
  document.addEventListener('click', function (e) { closeMenus(e.target.closest('details.menu')); });

  // ------------------------------------------------ Direct toast feedback handlers
  // Universal feedback on click (replaces hover-only tooltips)
  document.addEventListener('click', function (e) {
    var trigger = e.target.closest && e.target.closest('[data-toast-warning], [data-toast-info], [data-toast-success], [data-toast-error]');
    if (!trigger) return;
    if (trigger.tagName === 'BUTTON' && trigger.type === 'submit' && !trigger.classList.contains('is-disabled') && !trigger.hasAttribute('aria-disabled')) return;
    e.preventDefault();
    if (trigger.hasAttribute('data-toast-warning')) {
      toast(trigger.getAttribute('data-toast-warning'), 'warning');
    } else if (trigger.hasAttribute('data-toast-info')) {
      toast(trigger.getAttribute('data-toast-info'), 'info');
    } else if (trigger.hasAttribute('data-toast-success')) {
      toast(trigger.getAttribute('data-toast-success'), 'success');
    } else if (trigger.hasAttribute('data-toast-error')) {
      toast(trigger.getAttribute('data-toast-error'), 'error');
    }
  });

  // Clipboard copy with direct feedback toast
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('[data-copy-link]');
    if (!btn) return;
    e.preventDefault();
    var text = btn.getAttribute('data-copy-link');
    if (!text) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        toast('Link copied to clipboard', 'success');
      }).catch(function () {
        toast('Link copied to clipboard', 'success');
      });
    } else {
      var ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        toast('Link copied to clipboard', 'success');
      } catch (err) {}
      document.body.removeChild(ta);
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeMenus(); if (window.innerWidth <= 900) document.body.classList.remove('nav-open'); return; }

    // Single-key shortcuts, ignored while typing or when a dialog is open
    if (e.metaKey || e.ctrlKey || e.altKey || e.key.length !== 1) return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    if ($('dialog[open]')) return;
    var target = $('[data-shortcut="' + e.key.toLowerCase() + '"]');
    if (target) { e.preventDefault(); target.click(); }
  });

  /* ------------------------------------------------- custom dot & spotlight */
  (function () {
    if (reduceMotion || !window.matchMedia('(hover: hover)').matches) return;
    var root = document.documentElement;
    var body = document.body;
    var dot = $('#cursor-dot');
    var rafId = null;
    var mouseX = -1000, mouseY = -1000;

    function updateGlow() {
      root.style.setProperty('--cursor-x', mouseX + 'px');
      root.style.setProperty('--cursor-y', mouseY + 'px');
      rafId = null;
    }

    window.addEventListener('pointermove', function (e) {
      if (e.pointerType === 'touch') return;
      mouseX = e.clientX;
      mouseY = e.clientY;

      if (!body.classList.contains('has-cursor')) {
        body.classList.add('has-cursor');
      }

      if (dot) {
        dot.style.transform = 'translate3d(' + mouseX + 'px, ' + mouseY + 'px, 0)';
      }

      var target = e.target;
      var isTextInput = target && (
        target.matches && target.matches('input:not([type="checkbox"]):not([type="radio"]):not([type="submit"]):not([type="button"]), textarea, [contenteditable]')
      );
      var isInteractive = !isTextInput && target && target.closest && target.closest(
        'a, button, [role="button"], [role="radio"], summary, label, input[type="checkbox"], input[type="radio"], select, .pill, .gate-pill, .seg-opt, .row-title, [data-open-drawer], [data-drawer-close], [data-copy-link]'
      );

      if (isTextInput) {
        body.classList.add('cursor-is-text');
        body.classList.remove('cursor-is-hover');
      } else if (isInteractive) {
        body.classList.add('cursor-is-hover');
        body.classList.remove('cursor-is-text');
      } else {
        body.classList.remove('cursor-is-hover', 'cursor-is-text');
      }

      if (!rafId) rafId = requestAnimationFrame(updateGlow);
    }, { passive: true });

    window.addEventListener('mousedown', function (e) {
      if (e.pointerType === 'touch') return;
      body.classList.add('cursor-is-down');
    }, { passive: true });

    window.addEventListener('mouseup', function () {
      body.classList.remove('cursor-is-down');
    }, { passive: true });

    document.addEventListener('pointerleave', function () {
      body.classList.remove('has-cursor', 'cursor-is-hover', 'cursor-is-text', 'cursor-is-down');
    });
  })();
})();
