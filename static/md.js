/* Minimal safe markdown renderer (vendored, no CDN).
   Supports: headings (#/##/###), bold, italic, inline code,
   links [t](http...), unordered/ordered lists, paragraphs.
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
    s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    s = s.replace(/@@CODE(\d+)@@/g, function (_, i) {
      return "<code>" + codes[Number(i)] + "</code>";
    });
    return s;
  }

  function renderMarkdown(src) {
    var blocks = String(src || "").split(/\n{2,}/);
    var out = [];
    for (var b = 0; b < blocks.length; b++) {
      var block = blocks[b].replace(/^\n+|\n+$/g, "");
      if (!block) continue;
      var lines = block.split("\n");
      var m = block.match(/^(#{1,3})\s+(.*)$/);
      if (m) {
        var level = m[1].length;
        out.push("<h" + (level + 3) + ">" + renderInline(escapeHtml(m[2])) +
          "</h" + (level + 3) + ">");
      } else if (lines.every(function (l) { return /^[-*]\s+/.test(l); })) {
        out.push("<ul>" + lines.map(function (l) {
          return "<li>" + renderInline(escapeHtml(l.replace(/^[-*]\s+/, ""))) + "</li>";
        }).join("") + "</ul>");
      } else if (lines.every(function (l) { return /^\d+\.\s+/.test(l); })) {
        out.push("<ol>" + lines.map(function (l) {
          return "<li>" + renderInline(escapeHtml(l.replace(/^\d+\.\s+/, ""))) + "</li>";
        }).join("") + "</ol>");
      } else {
        out.push("<p>" + renderInline(escapeHtml(block)).replace(/\n/g, "<br>") + "</p>");
      }
    }
    return out.join("");
  }

  window.renderMarkdown = renderMarkdown;
})();
