/* HFCaps — caption mechanics for HyperFrames (grouping, timing, fit, clean exits).
   The LOOK and MOTION are designed per Reel: pass your own CSS classes and enter/word/exit functions.
   Inline it in a captions scene with the lib:captions token and feed it the words token (final-timeline word timings).

   HFCaps.build({
     tl,                      // the scene's paused GSAP timeline
     container: "#cap-stage", // element or selector the groups are added to
     words,                   // [{id,text,start,end}]  (the words token)
     maxWords: 3, maxChars: 22, pauseBreak: 0.3, hold: 0.45,
     upper: false,
     emphasis: { "em-red": ["seventy percent", "hackers"], "em-green": ["patched"] },  // phrase -> class
     font: { family: "Inter", weight: 900, size: 92, min: 54, maxWidth: 900 },
     enter(tl, g, spans, grp) {},   // group arrives (default: quick fade)
     word(tl, span, w, grp, i) {},  // each word as it is spoken (default: pop)
     exit(tl, g, grp) {},           // group leaves (default: fade); a hard kill is always added after it
   }) -> groups [{el, words, start, end}]
*/
(function () {
  function norm(s) { return String(s || "").toLowerCase().replace(/[^\w%]/g, ""); }

  function group(words, o) {
    var out = [], cur = [];
    var maxW = o.maxWords || 3, maxC = o.maxChars || 22, pause = o.pauseBreak == null ? 0.3 : o.pauseBreak;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (cur.length) {
        var prev = cur[cur.length - 1];
        var text = cur.map(function (x) { return x.text; }).join(" ") + " " + w.text;
        if (cur.length >= maxW || text.length > maxC || w.start - prev.end > pause || /[.?!:;]$/.test(prev.text)) {
          out.push(cur); cur = [];
        }
      }
      cur.push(w);
    }
    if (cur.length) out.push(cur);
    var hold = o.hold == null ? 0.45 : o.hold;
    return out.map(function (ws, gi) {
      var next = out[gi + 1];
      var start = Math.max(0.05, ws[0].start - 0.04);
      var end = ws[ws.length - 1].end + hold;
      // never overlap the next group (it appears 0.04 s before its first word): the next group always wins
      if (next) end = Math.min(end, Math.max(0.05, next[0].start - 0.04) - 0.02);
      end = Math.max(end, start + 0.12);
      return { words: ws, start: start, end: end };
    });
  }

  function marks(ws, emphasis) {
    var res = {};
    if (!emphasis) return res;
    var nw = ws.map(function (w) { return norm(w.text); });
    Object.keys(emphasis).forEach(function (cls) {
      (emphasis[cls] || []).slice().sort(function (a, b) { return b.length - a.length; }).forEach(function (phrase) {
        var p = String(phrase).split(/\s+/).map(norm).filter(Boolean);
        for (var i = 0; i + p.length <= nw.length; i++) {
          var ok = true;
          for (var k = 0; k < p.length; k++) if (nw[i + k] !== p[k]) { ok = false; break; }
          if (ok) for (var k2 = 0; k2 < p.length; k2++) if (!res[i + k2]) res[i + k2] = cls;
        }
      });
    });
    return res;
  }

  var _cv = null;
  function fit(text, f) {
    if (window.__hyperframes && window.__hyperframes.fitTextFontSize) {
      try {
        var r = window.__hyperframes.fitTextFontSize(text, { fontFamily: f.family, fontWeight: f.weight, maxWidth: f.maxWidth, baseFontSize: f.size, minFontSize: f.min });
        if (r && r.fontSize) return Math.min(r.fontSize, f.size);
      } catch (e) {}
    }
    _cv = _cv || document.createElement("canvas").getContext("2d");
    var size = f.size;
    while (size > f.min) {
      _cv.font = f.weight + " " + size + "px " + f.family;
      if (_cv.measureText(text).width <= f.maxWidth) break;
      size -= 2;
    }
    return size;
  }

  function build(o) {
    var root = typeof o.container === "string" ? document.querySelector(o.container) : o.container;
    if (!root) throw new Error("HFCaps: container not found");
    var tl = o.tl, f = Object.assign({ family: "Inter", weight: 900, size: 88, min: 52, maxWidth: 900 }, o.font || {});
    var groups = group(o.words || [], o);
    groups.forEach(function (grp, gi) {
      var g = document.createElement("div");
      g.className = "cap-group"; g.id = (o.idPrefix || "cap") + "-g" + gi;
      g.style.opacity = "0"; g.style.visibility = "hidden";
      var line = document.createElement("div"); line.className = "cap-line"; g.appendChild(line);
      var m = marks(grp.words, o.emphasis);
      var text = grp.words.map(function (w) { return o.upper ? w.text.toUpperCase() : w.text; }).join(" ");
      line.style.fontSize = fit(text, f) + "px";
      var spans = grp.words.map(function (w, i) {
        var s = document.createElement("span");
        s.className = "cap-word" + (m[i] ? " " + m[i] : "");
        s.id = (o.idPrefix || "cap") + "-" + w.id;
        var inner = document.createElement("span"); inner.className = "cap-txt";
        inner.textContent = o.upper ? w.text.toUpperCase() : w.text;
        s.appendChild(inner);
        line.appendChild(s);
        if (i < grp.words.length - 1) line.appendChild(document.createTextNode(" "));
        return s;
      });
      root.appendChild(g);
      grp.el = g; grp.spans = spans; grp.marks = m;
      tl.set(g, { visibility: "visible" }, grp.start);
      if (o.enter) o.enter(tl, g, spans, grp);
      else tl.fromTo(g, { opacity: 0 }, { opacity: 1, duration: 0.08, ease: "power1.out" }, grp.start);
      grp.words.forEach(function (w, i) {
        if (o.word) o.word(tl, spans[i], w, grp, i);
        else tl.fromTo(spans[i], { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1, duration: 0.16, ease: "back.out(2)" }, Math.max(grp.start, w.start - 0.03));
      });
      if (o.exit) o.exit(tl, g, grp);
      else tl.to(g, { opacity: 0, duration: 0.1, ease: "power2.in" }, grp.end - 0.1);
      tl.set(g, { opacity: 0, visibility: "hidden" }, grp.end);   // hard kill: never a stale group
    });
    return groups;
  }

  window.HFCaps = { build: build, group: group, marks: marks, fit: fit, norm: norm };
})();
