/* Minimal safe markdown renderer (vendored, no CDN).
   Supports: headings (#/##/###), bold, italic, inline code,
   links [t](http...), unordered/ordered lists, paragraphs.
   List items ("- ", "* ", "1. ") start a list even with no blank
   line before them; italics never span lines.
   Safety: all input is HTML-escaped first; only this file's own tags
   are emitted, and link URLs must start with http:// or https://. */
(function () {
  "use strict";

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderInline(escaped) {
    var codes = [];
    var s = escaped.replace(/`([^`]+)`/g, function (_, code) {
      codes.push(code);
      return "@@CODE" + (codes.length - 1) + "@@";
    });
    s = s.replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, function (_, t, u) {
      return '<a href="' + u + '" target="_blank" rel="noopener">' + t + "</a>";
    });
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
    s = s.replace(/@@CODE(\d+)@@/g, function (_, i) {
      return "<code>" + codes[Number(i)] + "</code>";
    });
    return s;
  }

  function listKind(line) {
    if (/^\d+\.\s+/.test(line)) return "ol";
    if (/^[-*]\s+/.test(line)) return "ul";
    return null;
  }

  function renderMarkdown(src) {
    var lines = String(src || "").split("\n");
    var out = [];
    var para = [];
    function flushPara() {
      if (para.length) {
        out.push("<p>" + para.map(function (l) {
          return renderInline(escapeHtml(l));
        }).join("<br>") + "</p>");
        para = [];
      }
    }
    var i = 0;
    while (i < lines.length) {
      var line = lines[i];
      if (/^\s*$/.test(line)) { flushPara(); i++; continue; }
      var mh = line.match(/^(#{1,3})\s+(.*)$/);
      if (mh) {
        flushPara();
        var level = mh[1].length;
        out.push("<h" + (level + 3) + ">" +
          renderInline(escapeHtml(mh[2])) + "</h" + (level + 3) + ">");
        i++;
        continue;
      }
      var kind = listKind(line);
      if (kind) {
        flushPara();
        var items = [];
        var cur = kind;
        var pushList = function () {
          out.push("<" + cur + ">" + items.map(function (t) {
            return "<li>" + renderInline(escapeHtml(t)) + "</li>";
          }).join("") + "</" + cur + ">");
          items = [];
        };
        while (i < lines.length && listKind(lines[i])) {
          if (listKind(lines[i]) !== cur && items.length) {
            pushList();
            cur = listKind(lines[i]);
          }
          items.push(lines[i].replace(/^([-*]|\d+\.)\s+/, ""));
          i++;
        }
        pushList();
        continue;
      }
      para.push(line);
      i++;
    }
    flushPara();
    return out.join("");
  }

  window.renderMarkdown = renderMarkdown;
})();
