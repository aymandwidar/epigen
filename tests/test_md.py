"""Tests for the vendored markdown renderer (run under node)."""

import shutil
from pathlib import Path

import pytest

NODE = shutil.which("node")
MD_JS = Path(__file__).parent.parent / "static" / "md.js"

NODE_SCRIPT = """
const fs = require("FSJS");
global.window = {};
eval(fs.readFileSync("MDJS", "utf8"));
const R = window.renderMarkdown;
function eq(got, want, name) {
  if (got !== want) {
    console.error("MISMATCH " + name + "\\n got:  " + got + "\\n want: " + want);
    process.exit(1);
  }
}
eq(R("- a\\n- b"), "<ul><li>a</li><li>b</li></ul>", "dash-list");
eq(R("* a\\n* b"), "<ul><li>a</li><li>b</li></ul>", "star-list");
eq(R("text\\n* star\\n* items"), "<p>text</p><ul><li>star</li><li>items</li></ul>", "list-no-blank");
eq(R("1. one\\n2. two"), "<ol><li>one</li><li>two</li></ol>", "ordered");
eq(R("*em* and *e2*"), "<p><em>em</em> and <em>e2</em></p>", "italics");
eq(R("<b>x</b>"), "<p>&lt;b&gt;x&lt;/b&gt;</p>", "escape");
const noem = R("a *b\\nc* d");
if (noem.includes("<em>")) { console.error("em spanned lines: " + noem); process.exit(1); }
console.log("md ok");
"""


@pytest.mark.skipif(NODE is None, reason="node not available")
def test_md_lists_and_emphasis(tmp_path):
    import subprocess

    script = NODE_SCRIPT.replace("FSJS", "fs").replace("MDJS", str(MD_JS))
    proc = subprocess.run(
        [NODE, "-e", script], capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0, proc.stderr
    assert "md ok" in proc.stdout
