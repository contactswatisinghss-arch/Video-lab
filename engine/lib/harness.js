/* Minimal HyperFrames-like runtime for quick LOCAL previews in Claude's sandbox (no npm there).
   It mounts <template> sub-compositions, shows clips over [start, start+duration), and seeks every
   registered timeline. The real HyperFrames check/render on GitHub stays the source of truth. */
(function () {
  window.__timelines = window.__timelines || {};
  window.__hfErrors = [];
  window.addEventListener("error", function (e) { window.__hfErrors.push(String(e.message || e)); });
  window.__hyperframes = window.__hyperframes || {
    getVariables: function () { return {}; },
    fitTextFontSize: function (text, o) {
      o = o || {};
      var c = document.createElement("canvas").getContext("2d");
      var size = o.baseFontSize || 78, min = o.minFontSize || 42, step = o.step || 2;
      var maxW = o.maxWidth || 900;
      while (size > min) {
        c.font = (o.fontWeight || 700) + " " + size + "px " + (o.fontFamily || "Inter");
        if (c.measureText(text).width <= maxW) break;
        size -= step;
      }
      return { fontSize: size };
    },
  };

  var comps = [];   // {id, el, absStart, dur, host}

  function num(v, d) { var n = parseFloat(v); return isNaN(n) ? d : n; }

  function startOf(el, scopeStart) {
    var v = (el.getAttribute("data-start") || "0").trim();
    var m = v.match(/^([A-Za-z_][\w-]*)\s*(?:([+-])\s*([\d.]+))?$/);
    if (m && isNaN(parseFloat(v))) {
      var ref = document.getElementById(m[1]);
      var base = ref ? startOf(ref, scopeStart) + num(ref.getAttribute("data-duration"), 0) : scopeStart;
      var off = m[3] ? (m[2] === "-" ? -1 : 1) * parseFloat(m[3]) : 0;
      return base + off;
    }
    return scopeStart + num(v, 0);
  }

  async function mountHosts(scope, scopeStart) {
    var hosts = Array.prototype.slice.call(scope.querySelectorAll("[data-composition-src]"));
    var scopeHost = scope === document ? null : scope;
    hosts = hosts.filter(function (h) {
      var up = h.parentElement ? h.parentElement.closest("[data-composition-src]") : null;
      return up === scopeHost;
    });
    for (var i = 0; i < hosts.length; i++) {
      var h = hosts[i];
      if (h.__hfMounted) continue;
      h.__hfMounted = true;
      var id = h.getAttribute("data-composition-id");
      var src = h.getAttribute("data-composition-src");
      var html = await (await fetch(src)).text();
      var doc = new DOMParser().parseFromString(html, "text/html");
      var tpl = doc.querySelector("template");
      var frag = tpl ? tpl.content.cloneNode(true) : doc.body.cloneNode(true);
      var rootId = id + "__root";
      var sroot = frag.querySelector("#root");
      if (sroot) sroot.id = rootId;
      Array.prototype.forEach.call(frag.querySelectorAll("style"), function (s) {
        s.textContent = s.textContent.split("#root").join("#" + rootId);
        document.head.appendChild(s.cloneNode(true)); s.remove();
      });
      var scripts = Array.prototype.slice.call(frag.querySelectorAll("script"));
      scripts.forEach(function (s) { s.remove(); });
      h.style.position = "absolute"; h.style.left = "0"; h.style.top = "0";
      h.style.width = "100%"; h.style.height = "100%";
      h.appendChild(frag);
      var abs = startOf(h, scopeStart);
      comps.push({ id: id, el: h, absStart: abs, dur: num(h.getAttribute("data-duration"), 1e9), host: true });
      for (var k = 0; k < scripts.length; k++) {
        var code = scripts[k].textContent.split('"#root"').join('"#' + rootId + '"').split("'#root'").join("'#" + rootId + "'");
        var n = document.createElement("script");
        n.textContent = "(function(){try{" + code + "\n}catch(e){window.__hfErrors.push('" + id + ": '+e.message)}})();";
        document.body.appendChild(n);
      }
      await mountHosts(h, abs);
    }
  }

  function clipsOf() {
    return Array.prototype.slice.call(document.querySelectorAll(".clip")).filter(function (el) { return !el.hasAttribute("data-composition-src"); });
  }

  function compStartFor(el) {
    var host = el.parentElement && el.parentElement.closest("[data-composition-src]");
    if (!host) return 0;
    var c = comps.find(function (x) { return x.el === host; });
    return c ? c.absStart : 0;
  }

  window.__hfSeek = function (t) {
    comps.forEach(function (c) {
      var local = t - c.absStart;
      if (c.host) c.el.style.visibility = (local >= 0 && local < c.dur) ? "" : "hidden";
      var tl = window.__timelines[c.id];
      if (tl && tl.seek) tl.seek(Math.max(0, Math.min(local, c.dur - 0.0001)), false);
    });
    clipsOf().forEach(function (el) {
      var s = startOf(el, compStartFor(el)), d = num(el.getAttribute("data-duration"), 1e9);
      el.style.visibility = (t >= s && t < s + d) ? "" : "hidden";
    });
    return true;
  };

  window.__hfInit = async function (standin) {
    var root = document.querySelector("[data-composition-id]");
    var W = num(root.getAttribute("data-width"), 1080), H = num(root.getAttribute("data-height"), 1920);
    root.style.position = "relative"; root.style.width = W + "px"; root.style.height = H + "px"; root.style.overflow = "hidden";
    comps.push({ id: root.getAttribute("data-composition-id"), el: root, absStart: 0, dur: num(root.getAttribute("data-duration"), 1e9), host: false });
    Array.prototype.forEach.call(document.querySelectorAll("video"), function (v) {
      if (standin) { v.removeAttribute("src"); v.setAttribute("poster", standin); v.style.objectFit = "cover"; v.style.background = "#444"; }
    });
    await mountHosts(document, 0);
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    return { comps: comps.map(function (c) { return [c.id, c.absStart, c.dur]; }), errors: window.__hfErrors };
  };
})();
