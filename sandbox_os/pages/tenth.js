/* SPDX-FileCopyrightText: 2026 Hameed, under the Winktank name */
/* SPDX-License-Identifier: LicenseRef-Winktank-Person-1.0 */
/* keys, cards and answers. keys are read by KeyboardEvent.code, so an arabic layout uses the same physical keys; its letters
   (غ ى ل) and the eastern digits are accepted too. an answer is the card's own form, posted to this page's own address; the
   page holds no words of its own: every word it shows was rendered from the strings table. */
(function () {
  var rows = [].slice.call(document.querySelectorAll('.row'));
  var cards = rows.filter(function (r) { return r.hasAttribute('data-card'); });
  var open = cards.length ? 0 : -1;
  function show(i) {
    open = i;
    cards.forEach(function (row, k) {
      var c = row.querySelector('.card'), b = row.querySelector('.open-card');
      if (c) c.hidden = k !== i && !!b;
      if (b) b.setAttribute('aria-expanded', k === i ? 'true' : 'false');
    });
  }
  function answer(a) {
    var row = cards[open], b = row && row.querySelector('.answers button[value="' + a + '"]');
    if (b && !b.disabled) b.click();
  }
  var CODES = {KeyY: 'yes', KeyN: 'no', KeyL: 'later'}, LETTERS = {'غ': 'yes', 'ى': 'no', 'ل': 'later'};
  var EASTERN = '١٢٣٤٥٦٧٨٩';
  document.addEventListener('keydown', function (e) {
    var t = e.target;
    if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) { if (e.key === 'Escape') t.blur(); return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var d = /^Digit([1-9])$/.exec(e.code), n = d ? +d[1] : EASTERN.indexOf(e.key) + 1;
    if (n > 0) { if (cards[n - 1]) { show(n - 1); cards[n - 1].focus(); } return; }
    if (e.key === 'Escape') { show(-1); return; }
    var a = CODES[e.code] || LETTERS[e.key];
    if (a && open >= 0) { e.preventDefault(); answer(a); return; }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      var k = rows.indexOf(document.activeElement) + (e.key === 'ArrowDown' ? 1 : -1);
      if (rows[k]) { e.preventDefault(); rows[k].focus(); }
    }
  });
  cards.forEach(function (row, k) {
    var b = row.querySelector('.open-card');
    if (b) b.addEventListener('click', function () { show(open === k ? -1 : k); });
  });
  [].forEach.call(document.querySelectorAll('form.answers'), function (f) {
    f.addEventListener('submit', function (e) {
      var words = f.querySelector('input[name=words]'), by = e.submitter;
      if ((!by || by.value === 'words') && !(words && words.value)) e.preventDefault();
    });
  });
  [].forEach.call(document.querySelectorAll('button.skip'), function (b) {
    b.addEventListener('click', function () {
      var f = document.getElementById(b.getAttribute('data-skip'));
      if (f) { f.value = f.tagName === 'SELECT' ? 'some' : ''; f.disabled = !f.disabled; }
    });
  });
  if (open >= 0) show(open);
})();
