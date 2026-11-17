/* DeleGate circadian theme engine.
   Loaded in <head>, before first paint, so the page opens already tinted for the
   current hour. It does three jobs:

   1. Holds the Solarpunk palettes: 3 themes x 4 phases x 9 colours.
   2. Turns the local time (decimal hours) into one continuous palette by
      interpolating between the phase anchors, then writes the result to the
      --bg-canvas ... --ambient-sky-glow custom properties on <html>.
   3. Re-runs every 60 seconds. solarpunk.css registers those properties with
      @property so the browser eases each change over 1.2s.

   Phases: Dawn 05:00-08:00, Solar Day 08:00-16:30, Golden Hour 16:30-19:30,
   Bioluminescent Night 19:30-05:00.

   Public API: window.Circadian.{ setTheme, setMode, getState, paletteAt }
   The theme lives in <html data-solarpunk-theme>, the phase in <html data-phase>.
*/
(function (global) {
  'use strict';

  var KEYS = [
    '--bg-canvas', '--bg-surface', '--bg-elevated', '--border-hairline',
    '--text-primary', '--text-secondary', '--accent-primary', '--accent-solar',
    '--ambient-sky-glow'
  ];

  // Order: canvas, surface, elevated, hairline, text, text-2, accent, solar, glow
  var PALETTES = {
    // Aether Atrium: sunlit ivory, lush emerald botanical, radiant brass, golden dawn
    aether: {
      dawn:   ['#F4F8F4', '#FFFFFF', '#EAF2EB', '#CFE2D4', '#132E22', '#3C614F', '#059669', '#D97706', '#FDE68A'],
      day:    ['#F8FAF8', '#FFFFFF', '#EDF4EF', '#D1E3D8', '#0D261C', '#355948', '#047857', '#D97706', '#FEF3C7'],
      golden: ['#FAF7EE', '#FFFDF7', '#F2ECD9', '#E3DAC1', '#262414', '#5A5237', '#047857', '#D97706', '#FCD34D'],
      night:  ['#06140D', '#0C2016', '#132E20', '#1E4532', '#ECFDF5', '#A7F3D0', '#10B981', '#FBBF24', '#064E3B']
    },
    // Terrace Canopy: warm baked sand, rich burnt terracotta, amber ochre, smoked espresso
    terrace: {
      dawn:   ['#FBF3E8', '#FFFBF6', '#F3E5D4', '#E2CEBA', '#2E1810', '#6B4739', '#C2410C', '#B45309', '#FED7AA'],
      day:    ['#FAF4ED', '#FFFDF9', '#F4E8DC', '#E3CFBE', '#26140B', '#614133', '#C2410C', '#B45309', '#FFEDD5'],
      golden: ['#F9EDE0', '#FFF9F2', '#F0DDCB', '#DEC2A8', '#2E1408', '#6E3E26', '#C2410C', '#EA580C', '#FDBA74'],
      night:  ['#160E0B', '#231712', '#33211B', '#4D3229', '#FFF7ED', '#FDBA74', '#FB923C', '#F59E0B', '#7C2D12']
    },
    // Mist Conservatory: crisp glacial mist, electric arctic cyan, titanium steel, abyssal navy
    mist: {
      dawn:   ['#EDF5FA', '#FAFCFE', '#E1EDF5', '#C8DDEB', '#0B202E', '#36566D', '#0284C7', '#6366F1', '#BAE6FD'],
      day:    ['#F0F6FA', '#FFFFFF', '#E2EEF5', '#CBE0EC', '#081E2B', '#315166', '#0284C7', '#4F46E5', '#CFEAFC'],
      golden: ['#EDF3F7', '#FAFCFE', '#DFE9F0', '#C5D7E3', '#101E29', '#3D5466', '#0284C7', '#8B5CF6', '#DDD6FE'],
      night:  ['#071018', '#0E1B26', '#152737', '#203A50', '#F0F9FF', '#BAE6FD', '#38BDF8', '#818CF8', '#0369A1']
    }
  };

  // Anchors on the 24h clock. Between two anchors the palette is a straight blend.
  // Night holds from 19:30 to 05:00, dawn peaks mid-window, day holds 08:30-16:00,
  // golden peaks at 18:00 and is gone by 19:30.
  var STOPS = [
    [0, 'night'], [5, 'night'], [6.5, 'dawn'], [8.5, 'day'],
    [16, 'day'], [18, 'golden'], [19.5, 'night'], [24, 'night']
  ];

  var PREVIEW_HOUR = { dawn: 6.5, day: 12, golden: 18, night: 23 };
  var PHASE_LABEL = { dawn: 'Dawn', day: 'Solar day', golden: 'Golden hour', night: 'Night' };
  var THEME_NAMES = Object.keys(PALETTES);
  var MODES = ['auto', 'dawn', 'day', 'golden', 'night'];
  var DARK_TEXT = '#0A1410';

  /* ------------------------------------------------------------- colour maths */
  function parse(hex) {
    var n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function toHex(rgb) {
    return '#' + rgb.map(function (v) {
      var s = Math.max(0, Math.min(255, Math.round(v))).toString(16);
      return s.length < 2 ? '0' + s : s;
    }).join('');
  }
  function mix(a, b, t) {
    var A = parse(a), B = parse(b);
    return toHex([A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t]);
  }
  function luminance(hex) {
    return parse(hex).map(function (v) {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    }).reduce(function (sum, v, i) { return sum + v * [0.2126, 0.7152, 0.0722][i]; }, 0);
  }
  function contrast(a, b) {
    var la = luminance(a), lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }
  // Two passes of smoothstep: slow at both ends, quick through the middle. The
  // middle of a night-to-day blend is mid-grey, where no text colour can reach
  // AA, so the palette should spend as little time there as it can.
  function smooth(t) { t = t * t * (3 - 2 * t); return t * t * (3 - 2 * t); }

  /* ---------------------------------------------------------------- the clock */
  function decimalHour(date) {
    date = date || new Date();
    return date.getHours() + date.getMinutes() / 60;
  }

  function phaseName(h) {
    if (h >= 5 && h < 8) return 'dawn';
    if (h >= 8 && h < 16.5) return 'day';
    if (h >= 16.5 && h < 19.5) return 'golden';
    return 'night';
  }

  function solarCoords(h) {
    var x, y, angle;
    if (h >= 5 && h < 8) {
      // Dawn (05:00 - 08:00): sunrise climbs from bottom-right (88%, 95%) to morning sky (72%, 25%)
      var t = (h - 5) / 3;
      x = 88 - t * 16;
      y = 95 - t * 70;
      angle = 115 + t * 45;
    } else if (h >= 8 && h < 16.5) {
      // Solar Day (08:00 - 16:30): high arch over workstation zenith
      var t = (h - 8) / 8.5;
      x = 72 - t * 44;
      y = -14 + Math.pow(t - 0.47, 2) * 160;
      angle = 160 + t * 60;
    } else if (h >= 16.5 && h < 19.5) {
      // Golden Hour (16:30 - 19:30): sunset descends to bottom-left (12%, 85%)
      var t = (h - 16.5) / 3;
      x = 28 - t * 16;
      y = 26 + t * 59;
      angle = 220 + t * 40;
    } else {
      // Night (19:30 - 05:00): lunar zenith at top center
      x = 50;
      y = -15;
      angle = 0;
    }
    return {
      x: Math.round(x * 10) / 10,
      y: Math.round(y * 10) / 10,
      angle: Math.round(angle)
    };
  }

  // Nudge fg toward black or white, whichever works, until it clears `min`
  // against every background in `bgs`. A straight blend between a dark night
  // palette and a light day palette passes through mid-grey where text and
  // background meet; this keeps every hour of the day readable.
  function ensure(fg, bgs, min) {
    function worst(c) {
      var w = 99;
      for (var i = 0; i < bgs.length; i++) w = Math.min(w, contrast(c, bgs[i]));
      return w;
    }
    if (worst(fg) >= min) return fg;
    var black = '#000000', white = '#FFFFFF';
    var target = worst(black) >= worst(white) ? black : white;
    for (var t = 0.04; t <= 1.0001; t += 0.04) {
      var c = mix(fg, target, t);
      if (worst(c) >= min) return c;
    }
    return target;
  }

  function paletteAt(theme, h) {
    var set = PALETTES[theme] || PALETTES.aether;
    var i = 0;
    while (i < STOPS.length - 2 && h >= STOPS[i + 1][0]) i++;
    var from = STOPS[i], to = STOPS[i + 1];
    var t = to[0] === from[0] ? 0 : smooth(Math.max(0, Math.min(1, (h - from[0]) / (to[0] - from[0]))));
    var a = set[from[1]], b = set[to[1]];
    var out = {};
    for (var k = 0; k < KEYS.length; k++) out[KEYS[k]] = mix(a[k], b[k], t);

    var canvas = out['--bg-canvas'], surface = out['--bg-surface'], elevated = out['--bg-elevated'];
    var solar = out['--accent-solar'];
    var base = [canvas, surface, elevated];
    var accentSoft = function (accent) { return mix(surface, accent, 0.11); };
    var dangerSoft = mix(surface, '#C0392B', 0.12);

    out['--text-primary'] = ensure(out['--text-primary'], base, 8);
    out['--text-secondary'] = ensure(out['--text-secondary'], base, 5.6);
    out['--accent-primary'] = ensure(out['--accent-primary'], base.concat(accentSoft(out['--accent-primary'])), 4.8);
    out['--accent-primary'] = ensure(out['--accent-primary'], base.concat(accentSoft(out['--accent-primary'])), 4.8);
    out['--accent-solar'] = solar = ensure(solar, base, 2.5);
    var text = out['--text-primary'];

    var solarSoft = mix(surface, solar, 0.15);
    // Derived text colours, solved here so they hold their contrast mid-blend
    out['--ink-3'] = ensure(mix(out['--text-secondary'], canvas, 0.1), base, 4.5);
    out['--signal-ink'] = ensure(mix(solar, text, 0.48), base.concat(solarSoft), 4.5);
    out['--danger'] = ensure(mix('#C0392B', text, 0.32), base.concat(dangerSoft), 4.5);

    var ac = out['--accent-primary'];
    out['--on-accent'] = contrast('#FFFFFF', ac) >= contrast(DARK_TEXT, ac) ? '#FFFFFF' : DARK_TEXT;
    return out;
  }

  /* -------------------------------------------------------------------- state */
  var root = global.document && global.document.documentElement;
  var state = { theme: 'aether', mode: 'auto', phase: 'day', hour: 12 };

  function read(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) { try { localStorage.setItem(key, value); } catch (e) {} }

  function currentHour() {
    return state.mode === 'auto' ? decimalHour() : PREVIEW_HOUR[state.mode];
  }

  function apply() {
    var h = currentHour();
    var palette = paletteAt(state.theme, h);
    for (var key in palette) root.style.setProperty(key, palette[key]);
    var coords = solarCoords(h);
    root.style.setProperty('--sun-x', coords.x + '%');
    root.style.setProperty('--sun-y', coords.y + '%');
    root.style.setProperty('--sun-angle', coords.angle + 'deg');
    state.hour = h;
    state.phase = state.mode === 'auto' ? phaseName(h) : state.mode;
    root.setAttribute('data-phase', state.phase);
    root.setAttribute('data-solarpunk-theme', state.theme);
    root.setAttribute('data-sun-mode', state.mode);
    if (global.CustomEvent) {
      global.dispatchEvent(new CustomEvent('circadian:change', {
        detail: { theme: state.theme, mode: state.mode, phase: state.phase, label: PHASE_LABEL[state.phase] }
      }));
    }
  }

  function setTheme(theme) {
    if (THEME_NAMES.indexOf(theme) === -1) return;
    state.theme = theme;
    write('dg-solarpunk-theme', theme);
    apply();
  }

  function setMode(mode) {
    if (MODES.indexOf(mode) === -1) return;
    state.mode = mode;
    write('dg-sun-mode', mode);
    apply();
  }

  function getState() {
    return { theme: state.theme, mode: state.mode, phase: state.phase, hour: state.hour, label: PHASE_LABEL[state.phase] };
  }

  /* ------------------------------------------------------------------- boot */
  if (root) {
    var signedIn = !!document.querySelector('meta[name="dg-auth"]');
    var served = root.getAttribute('data-solarpunk-theme');
    var saved = read('dg-solarpunk-theme');

    // Signed in: the account's saved theme (rendered by the server) wins.
    // Signed out: whatever this browser used last.
    if (signedIn && THEME_NAMES.indexOf(served) !== -1) state.theme = served;
    else if (THEME_NAMES.indexOf(saved) !== -1) state.theme = saved;
    else if (THEME_NAMES.indexOf(served) !== -1) state.theme = served;
    if (signedIn) write('dg-solarpunk-theme', state.theme);

    var mode = read('dg-sun-mode');
    if (MODES.indexOf(mode) !== -1) state.mode = mode;

    root.classList.add('js');
    apply(); // synchronous: the first paint already has the right colours

    // Switch the 1.2s easing on only after first paint, so nothing animates on load.
    var arm = function () { root.classList.add('sun-ready'); };
    if (global.requestAnimationFrame) global.requestAnimationFrame(function () { global.requestAnimationFrame(arm); });
    else arm();

    // Live sun: re-evaluate every minute, and when the tab wakes up again.
    setInterval(function () { if (state.mode === 'auto') apply(); }, 60000);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden && state.mode === 'auto') apply();
    });
  }

  var api = {
    setTheme: setTheme, setMode: setMode, getState: getState,
    paletteAt: paletteAt, phaseName: phaseName, solarCoords: solarCoords, contrast: contrast,
    PALETTES: PALETTES, KEYS: KEYS, THEMES: THEME_NAMES, MODES: MODES, PREVIEW_HOUR: PREVIEW_HOUR
  };
  global.Circadian = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
