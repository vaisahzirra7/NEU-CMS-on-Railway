"""
fix_mobile_responsive.py  (v2)
================================
Run from your project root:
    python fix_mobile_responsive.py

Handles ALL grid layouts found across templates:
- repeat(2-5, 1fr)  → single column on mobile
- 1fr Npx / Npx 1fr (sidebar+content layouts) → single column
- kpi-grid, mod-grid, bottom-grid, qa-grid → responsive
- dashboard-specific grids
- Topbar responsive
- Darker overlay
- Tables scroll horizontally
"""

import os
import re

SKIP_FILES = {
    'login.html', 'forgot_password.html', 'password_reset_confirm.html',
    'force_password_change.html', 'base.html', '_sidebar.html',
    'report.html', 'slip.html', 'print.html', 'verify.html',
    'form.html', 'success.html', 'status_check.html',
    'already_submitted.html', 'certificate.html', 'verify_internal.html',
}

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')

MOBILE_CSS = """
    /* ═══════════════════════════════════════════════════════════
       MOBILE RESPONSIVE v2 — fix_mobile_responsive.py
       ═══════════════════════════════════════════════════════════ */

    .sb-overlay {
      display:none; position:fixed; inset:0;
      background:rgba(0,0,0,.75);
      z-index:299; backdrop-filter:blur(3px);
      -webkit-backdrop-filter:blur(3px);
    }
    .sb-overlay.open { display:block; }

    .hamburger {
      display:none; align-items:center; justify-content:center;
      width:36px; height:36px; flex-shrink:0;
      background:rgba(255,255,255,.06);
      border:1px solid rgba(255,255,255,.1);
      border-radius:8px; cursor:pointer;
      transition:background .2s;
    }
    .hamburger:hover { background:rgba(255,255,255,.12); }
    .hamburger span,
    .hamburger span::before,
    .hamburger span::after {
      display:block; width:16px; height:2px;
      background:#6B84A3; border-radius:2px;
      position:relative; transition:all .25s;
    }
    .hamburger span::before,
    .hamburger span::after { content:''; position:absolute; left:0; }
    .hamburger span::before { top:-5px; }
    .hamburger span::after  { top:5px;  }
    .hamburger.open span             { background:transparent; }
    .hamburger.open span::before     { transform:rotate(45deg);  top:0; }
    .hamburger.open span::after      { transform:rotate(-45deg); top:0; }

    @media (max-width: 768px) {
      .hamburger { display:flex; }

      .sidebar {
        transform: translateX(-100%);
        transition: transform .28s cubic-bezier(.4,0,.2,1);
        z-index: 300;
      }
      .sidebar.open { transform: translateX(0); }

      .main { margin-left: 0 !important; }

      /* Topbar */
      .topbar {
        padding: 10px 14px !important;
        height: auto !important;
        min-height: 56px;
        flex-wrap: wrap;
        gap: 8px;
      }
      .topbar-left h1 { font-size: 16px !important; }
      .topbar-left p  { display: none !important; }
      .topbar-right   { flex-wrap: wrap; gap: 6px; }
      .topbar-right .btn-primary,
      .topbar-right .btn-sm {
        font-size: 12px !important;
        padding: 7px 11px !important;
      }

      /* Content padding */
      .content { padding: 14px !important; }

      /* ALL named grid layouts → single column */
      .grid-2, .grid-3, .grid-4,
      .bottom-grid, .qa-grid,
      .layout, .two-col, .split,
      [class*="col-grid"], [class*="two-col"] {
        grid-template-columns: 1fr !important;
        gap: 12px !important;
      }

      /* Stat/KPI grids → 2 columns */
      .kpi-grid,
      .stats-grid,
      .stats-row,
      [class*="stat-grid"] {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 10px !important;
      }

      /* Module grid → 2 columns */
      .mod-grid {
        grid-template-columns: repeat(2, 1fr) !important;
      }

      /* Cards */
      .card { border-radius: 10px; overflow-x: auto; }
      .card-body   { padding: 14px !important; }
      .card-header { padding: 12px 14px !important; }

      /* Tables scroll */
      .table-wrap { overflow-x: auto; }
      table { min-width: 480px; }

      /* Form rows */
      .field-row, .form-row {
        grid-template-columns: 1fr !important;
        flex-direction: column !important;
      }

      /* Welcome card */
      .welcome-card { padding: 20px !important; }
      .welcome-card h2 { font-size: 22px !important; }

      .btn-primary, .btn-sm { font-size: 12.5px; }
      .stat-card p { font-size: 11px; }
    }

    @media (max-width: 420px) {
      .topbar-right .btn-primary,
      .topbar-right .btn-sm {
        font-size: 11px !important;
        padding: 6px 9px !important;
      }
      .content { padding: 10px !important; }
    }
    /* ═══════════════════════════════════════════════════════════ */
"""

MOBILE_JS = """
<script>
/* Mobile sidebar */
function toggleSidebar() {
  var s = document.querySelector('.sidebar');
  var o = document.getElementById('sbOverlay');
  var h = document.getElementById('hamburgerBtn');
  if (!s) return;
  s.classList.toggle('open');
  if (o) o.classList.toggle('open');
  if (h) h.classList.toggle('open');
}
(function() {
  var o = document.getElementById('sbOverlay');
  if (o) o.addEventListener('click', function() {
    var s = document.querySelector('.sidebar');
    var h = document.getElementById('hamburgerBtn');
    if (s) s.classList.remove('open');
    o.classList.remove('open');
    if (h) h.classList.remove('open');
  });
  document.querySelectorAll('.sb-item').forEach(function(l) {
    l.addEventListener('click', function() {
      if (window.innerWidth <= 768) {
        var s = document.querySelector('.sidebar');
        var o = document.getElementById('sbOverlay');
        var h = document.getElementById('hamburgerBtn');
        if (s) s.classList.remove('open');
        if (o) o.classList.remove('open');
        if (h) h.classList.remove('open');
      }
    });
  });
})();
</script>
"""

OVERLAY_HTML = '\n<div class="sb-overlay" id="sbOverlay"></div>\n'
HAMBURGER_HTML = '<button class="hamburger" id="hamburgerBtn" onclick="toggleSidebar()" aria-label="Toggle menu"><span></span></button>'


def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Skip if no sidebar
    if 'class="sidebar"' not in content and "class='sidebar'" not in content:
        print(f'  SKIP (no sidebar): {os.path.basename(filepath)}')
        return False

    original = content

    # Strip ALL previous patches cleanly
    content = re.sub(
        r'/\* ═+\s*MOBILE RESPONSIVE.*?═+ \*/\s*',
        '',
        content,
        flags=re.DOTALL
    )
    content = re.sub(r'\n<div class="sb-overlay"[^>]*></div>\n', '', content)
    content = re.sub(
        r'\s*<button[^>]*id="hamburgerBtn"[^>]*>.*?</button>',
        '',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'\n<script>\n/\* Mobile sidebar \*/.*?</script>\n',
        '',
        content,
        flags=re.DOTALL
    )

    # 1. Inject CSS before </style>
    content = content.replace('</style>', MOBILE_CSS + '\n  </style>', 1)

    # 2. Inject overlay before sidebar div
    content = re.sub(
        r'(<div class=["\']sidebar["\'])',
        OVERLAY_HTML + r'\1',
        content,
        count=1
    )

    # 3. Inject hamburger into topbar
    injected = False
    for pattern in [
        r'(<div[^>]*class=["\'][^"\']*topbar[^"\']*["\'][^>]*>)',
        r'(<div[^>]*class=["\'][^"\']*top-bar[^"\']*["\'][^>]*>)',
        r'(<nav[^>]*class=["\'][^"\']*topbar[^"\']*["\'][^>]*>)',
    ]:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            pos = m.end()
            content = content[:pos] + '\n        ' + HAMBURGER_HTML + content[pos:]
            injected = True
            break
    if not injected:
        print(f'  WARN (no topbar found): {os.path.basename(filepath)}')

    # 4. Inject JS before </body>
    content = content.replace('</body>', MOBILE_JS + '\n</body>', 1)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  ✓  {filepath}')
        return True
    else:
        print(f'  -- no change: {os.path.basename(filepath)}')
        return False


def main():
    patched = skipped = 0
    for root, dirs, files in os.walk(TEMPLATES_DIR):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for filename in sorted(files):
            if not filename.endswith('.html'):
                continue
            if filename in SKIP_FILES:
                skipped += 1
                continue
            result = patch_file(os.path.join(root, filename))
            if result:
                patched += 1
            else:
                skipped += 1
    print(f'\nDone — {patched} patched, {skipped} skipped.')


if __name__ == '__main__':
    main()