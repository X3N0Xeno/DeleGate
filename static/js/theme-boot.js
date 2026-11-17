/* Runs in <head>, before first paint, so the page never flashes the wrong theme.
   - Signed in: the server-rendered data-theme (from UserSettings) is the truth;
     we mirror it into localStorage so the sign-in page remembers it next time.
   - Signed out: use whatever theme this browser last used. */
(function () {
  var root = document.documentElement;
  var THEMES = ['kyoto', 'shiroi', 'hinoki'];
  var signedIn = !!document.querySelector('meta[name="dg-auth"]');
  root.classList.add('js');
  try {
    if (signedIn) {
      localStorage.setItem('dg-theme', root.getAttribute('data-theme') || 'kyoto');
    } else {
      var saved = localStorage.getItem('dg-theme');
      if (saved && THEMES.indexOf(saved) !== -1) root.setAttribute('data-theme', saved);
    }
  } catch (e) { /* storage blocked: the server default still applies */ }
})();
