"""Render pipeline stage: produce Markdown digest, summary page, and HTML dashboard."""

from __future__ import annotations

import html as html_mod
import json
from datetime import datetime

from models import RepoSummary


# ─────────── Markdown helpers ───────────

def _card_md(s: RepoSummary) -> str:
    lines = [
        f"### [{s.full_name}]({s.html_url})",
        f"> {s.one_liner}",
        "",
    ]
    if s.highlights:
        lines.append("**Why it matters**")
        for h in s.highlights:
            lines.append(f"- {h}")
        lines.append("")
    if s.risks:
        lines.append("**Risks / Notes**")
        for r in s.risks:
            lines.append(f"- {r}")
        lines.append("")
    qf = s.quick_facts
    lines.append(
        f"⭐ {qf.get('stars_total', '?')} "
        f"(+{qf.get('star_growth_7d', '?')} / 7d) · "
        f"📅 {qf.get('last_update', '?')} · "
        f"📄 {qf.get('license', '?')} · "
        f"🎯 {s.recommended_action}"
    )
    lines.append("")
    return "\n".join(lines)


# ─────────── Public API ───────────

def render_digest_md(summaries: list[RepoSummary], run_date: str, summary_page_link: str = "") -> str:
    """Generate the Teams/Email daily digest in Markdown."""
    lines = [f"# 🚀 Daily AI GitHub Radar – {run_date}", ""]

    lines.append("## 🔥 Top Trending Projects")
    lines.append("")
    for s in summaries[:5]:
        lines.append(f"- **[{s.full_name}]({s.html_url})** – {s.one_liner}")
    lines.append("")

    lines.append("## 🧠 By Category")
    lines.append("")
    cats: dict[str, list[RepoSummary]] = {}
    for s in summaries:
        cats.setdefault(s.category, []).append(s)
    for cat, items in sorted(cats.items()):
        lines.append(f"### {cat}")
        for s in items[:2]:
            lines.append(f"- **[{s.full_name}]({s.html_url})** – {s.one_liner}")
        lines.append("")

    if summary_page_link:
        lines.append(f"---\n👉 [Full summary page]({summary_page_link})")

    return "\n".join(lines)


def render_summary_page_md(summaries: list[RepoSummary], run_date: str) -> str:
    """Generate the full summary page in Markdown."""
    lines = [f"# AI GitHub Radar – {run_date}", ""]

    lines.append("## 🔥 Top Trending")
    lines.append("")
    for s in summaries[:10]:
        lines.append(_card_md(s))

    lines.append("## 🧠 By Category")
    lines.append("")
    cats: dict[str, list[RepoSummary]] = {}
    for s in summaries:
        cats.setdefault(s.category, []).append(s)
    for cat, items in sorted(cats.items()):
        lines.append(f"### {cat}")
        lines.append("")
        for s in items:
            lines.append(_card_md(s))

    return "\n".join(lines)


def _summaries_to_json(summaries: list[RepoSummary]) -> str:
    """Serialize summaries to JSON for embedding in HTML."""
    data = []
    for s in summaries:
        data.append({
            "full_name": s.full_name,
            "html_url": s.html_url,
            "category": s.category,
            "tags": s.tags,
            "one_liner": s.one_liner,
            "highlights": s.highlights,
            "risks": s.risks,
            "quick_facts": s.quick_facts,
            "recommended_action": s.recommended_action,
            "trend_score": round(s.trend_score, 4),
        })
    return json.dumps(data, ensure_ascii=False)


def render_summary_page_html(summaries: list[RepoSummary], run_date: str) -> str:
    """Generate an interactive dashboard HTML page for GitHub Pages."""

    def esc(text: str) -> str:
        return html_mod.escape(str(text))

    # Compute stats for the hero section
    total_stars = sum(s.quick_facts.get("stars_total", 0) for s in summaries)
    categories = sorted(set(s.category for s in summaries))
    cat_counts = {}
    for s in summaries:
        cat_counts[s.category] = cat_counts.get(s.category, 0) + 1

    cat_emoji = {
        "LLM / Agent": "🤖", "RAG & Retrieval": "🔍",
        "Inference & Deployment": "⚡", "Training & Fine-tuning": "🏋️",
        "Evaluation & Observability": "📊", "Multimodal": "🎨",
        "Data & Labeling": "📦", "Security & Compliance": "🔒",
        "AI Applications": "💡",
    }

    data_json = _summaries_to_json(summaries)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI GitHub Radar – {esc(run_date)}</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
<style>
/* ── Reset & Variables ── */
:root {{
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  --bg-tertiary: #1c2128;
  --border: #30363d;
  --border-hover: #484f58;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-muted: #656d76;
  --link: #58a6ff;
  --link-hover: #79c0ff;
  --green: #3fb950;
  --green-bg: rgba(63,185,80,.15);
  --blue: #58a6ff;
  --blue-bg: rgba(56,139,253,.15);
  --yellow: #d29922;
  --yellow-bg: rgba(210,153,34,.15);
  --red: #f85149;
  --red-bg: rgba(248,81,73,.15);
  --purple: #bc8cff;
  --purple-bg: rgba(188,140,255,.15);
  --orange: #f0883e;
  --radius: 12px;
  --radius-sm: 8px;
  --shadow: 0 1px 3px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.2);
  --transition: .2s cubic-bezier(.4,0,.2,1);
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Noto Sans, Helvetica, Arial, sans-serif;
  background: var(--bg-primary); color: var(--text-primary);
  line-height: 1.6; min-height: 100vh;
}}
a {{ color: var(--link); text-decoration: none; transition: color var(--transition); }}
a:hover {{ color: var(--link-hover); }}

/* ── Layout ── */
.container {{ max-width: 1200px; margin: 0 auto; padding: 0 24px; }}

/* ── Header ── */
.header {{
  background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a1e2e 100%);
  border-bottom: 1px solid var(--border);
  padding: 48px 0 40px;
  position: relative;
  overflow: hidden;
}}
.header::before {{
  content: ''; position: absolute; top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(circle at 30% 50%, rgba(56,139,253,.06) 0%, transparent 50%),
              radial-gradient(circle at 70% 50%, rgba(63,185,80,.04) 0%, transparent 50%);
  animation: headerGlow 20s ease-in-out infinite;
}}
@keyframes headerGlow {{
  0%,100% {{ transform: translate(0,0); }}
  50% {{ transform: translate(-2%,1%); }}
}}
.header-content {{ position: relative; z-index: 1; }}
.header h1 {{
  font-size: 2.2rem; font-weight: 800; letter-spacing: -.02em;
  background: linear-gradient(135deg, #e6edf3 0%, #58a6ff 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; margin-bottom: 8px;
}}
.header .subtitle {{
  color: var(--text-secondary); font-size: 1.05rem; margin-bottom: 28px;
}}
.header .run-date {{
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-tertiary); border: 1px solid var(--border);
  padding: 4px 14px; border-radius: 20px;
  font-size: .85rem; color: var(--text-secondary);
}}
.header .run-date .dot {{
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--green); box-shadow: 0 0 8px var(--green);
  animation: pulse 2s ease-in-out infinite;
}}
@keyframes pulse {{ 0%,100%{{ opacity:1; }} 50%{{ opacity:.5; }} }}

/* ── Stats Bar ── */
.stats-bar {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px; margin-top: 28px;
}}
.stat-card {{
  background: rgba(255,255,255,.03); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 16px 20px;
  text-align: center; transition: all var(--transition);
}}
.stat-card:hover {{ border-color: var(--border-hover); transform: translateY(-2px); }}
.stat-card .stat-value {{
  font-size: 1.8rem; font-weight: 700; color: var(--text-primary);
  line-height: 1.2;
}}
.stat-card .stat-label {{
  font-size: .8rem; color: var(--text-muted); text-transform: uppercase;
  letter-spacing: .05em; margin-top: 4px;
}}

/* ── Controls ── */
.controls {{
  padding: 24px 0;
  position: sticky; top: 0; z-index: 100;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border);
}}
.search-box {{
  position: relative; margin-bottom: 16px;
}}
.search-box input {{
  width: 100%; padding: 12px 16px 12px 44px;
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text-primary);
  font-size: .95rem; outline: none; transition: all var(--transition);
}}
.search-box input:focus {{ border-color: var(--blue); box-shadow: 0 0 0 3px rgba(56,139,253,.2); }}
.search-box input::placeholder {{ color: var(--text-muted); }}
.search-box .search-icon {{
  position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
  color: var(--text-muted); font-size: 1.1rem; pointer-events: none;
}}
.filter-row {{
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}}
.filter-btn {{
  padding: 6px 16px; border-radius: 20px; border: 1px solid var(--border);
  background: transparent; color: var(--text-secondary); cursor: pointer;
  font-size: .85rem; transition: all var(--transition);
  display: inline-flex; align-items: center; gap: 6px;
}}
.filter-btn:hover {{ border-color: var(--border-hover); color: var(--text-primary); background: var(--bg-tertiary); }}
.filter-btn.active {{ border-color: var(--blue); color: var(--blue); background: var(--blue-bg); }}
.filter-btn .count {{
  font-size: .75rem; background: var(--bg-tertiary); padding: 1px 7px;
  border-radius: 10px; min-width: 20px; text-align: center;
}}
.filter-btn.active .count {{ background: rgba(56,139,253,.2); }}
.sort-select {{
  margin-left: auto; padding: 6px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg-secondary);
  color: var(--text-secondary); font-size: .85rem; cursor: pointer;
  outline: none;
}}

/* ── Cards Grid ── */
.cards-grid {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px; padding: 24px 0 48px;
}}
.card {{
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 20px; position: relative;
  transition: all var(--transition); overflow: hidden;
}}
.card:hover {{
  border-color: var(--border-hover); transform: translateY(-3px);
  box-shadow: var(--shadow);
}}
.card-rank {{
  position: absolute; top: 14px; right: 16px;
  font-size: .75rem; font-weight: 700; color: var(--text-muted);
  background: var(--bg-tertiary); padding: 2px 10px; border-radius: 10px;
}}
.card-rank.top3 {{ color: var(--yellow); background: var(--yellow-bg); }}
.card-header {{ margin-bottom: 12px; padding-right: 50px; }}
.card-header h3 {{ font-size: 1.05rem; font-weight: 600; line-height: 1.4; }}
.card-header h3 a {{ color: var(--text-primary); }}
.card-header h3 a:hover {{ color: var(--link); }}
.card-oneliner {{
  color: var(--text-secondary); font-size: .9rem; margin-bottom: 14px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}}
.card-meta {{
  display: flex; flex-wrap: wrap; gap: 12px; font-size: .82rem;
  color: var(--text-muted); margin-bottom: 14px;
}}
.card-meta span {{ display: inline-flex; align-items: center; gap: 4px; }}
.card-highlights {{
  margin-bottom: 14px; padding: 10px 14px;
  background: var(--bg-tertiary); border-radius: var(--radius-sm);
}}
.card-highlights h4 {{
  font-size: .78rem; font-weight: 600; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: .04em; margin-bottom: 6px;
}}
.card-highlights li {{
  font-size: .85rem; color: var(--text-secondary); margin-left: 16px; margin-bottom: 2px;
}}
.card-risks {{
  font-size: .82rem; color: var(--red); margin-bottom: 12px;
  display: flex; flex-wrap: wrap; gap: 6px;
}}
.card-risks span {{
  background: var(--red-bg); padding: 2px 10px; border-radius: 10px;
}}
.card-footer {{
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding-top: 12px; border-top: 1px solid var(--border);
}}
.badge-category {{
  font-size: .75rem; font-weight: 500; padding: 3px 10px; border-radius: 12px;
  background: var(--blue-bg); color: var(--blue);
}}
.badge-action {{
  font-size: .72rem; font-weight: 600; padding: 3px 10px; border-radius: 12px;
  text-transform: uppercase; letter-spacing: .04em;
}}
.badge-action.poc {{ background: var(--green-bg); color: var(--green); }}
.badge-action.explore {{ background: var(--blue-bg); color: var(--blue); }}
.badge-action.track {{ background: var(--yellow-bg); color: var(--yellow); }}
.badge-action.ignore {{ background: rgba(110,118,129,.15); color: var(--text-muted); }}
.badge-tag {{
  font-size: .7rem; padding: 2px 8px; border-radius: 10px;
  background: var(--bg-tertiary); color: var(--text-muted);
  border: 1px solid var(--border);
}}
.trend-bar {{
  position: absolute; bottom: 0; left: 0; height: 3px;
  background: linear-gradient(90deg, var(--green), var(--blue));
  border-radius: 0 0 var(--radius) var(--radius);
  transition: width .6s ease;
}}

/* ── No Results ── */
.no-results {{
  text-align: center; padding: 60px 20px; color: var(--text-muted);
}}
.no-results .emoji {{ font-size: 3rem; margin-bottom: 12px; }}

/* ── Footer ── */
.footer {{
  text-align: center; padding: 32px 0; border-top: 1px solid var(--border);
  color: var(--text-muted); font-size: .85rem;
}}

/* ── Responsive ── */
@media (max-width: 640px) {{
  .header h1 {{ font-size: 1.6rem; }}
  .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
  .cards-grid {{ grid-template-columns: 1fr; }}
  .sort-select {{ margin-left: 0; margin-top: 8px; }}
}}
</style>
</head>
<body>

<!-- ══ Header ══ -->
<div class="header">
  <div class="container header-content">
    <h1>🚀 AI GitHub Radar</h1>
    <p class="subtitle">Daily discovery of high-potential AI projects on GitHub</p>
    <span class="run-date"><span class="dot"></span> Last updated: {esc(run_date)}</span>

    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-value">{len(summaries)}</div>
        <div class="stat-label">Projects Found</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{len(categories)}</div>
        <div class="stat-label">Categories</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{_format_stars(total_stars)}</div>
        <div class="stat-label">Total Stars</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{sum(1 for s in summaries if s.recommended_action == 'POC')}</div>
        <div class="stat-label">POC Ready</div>
      </div>
    </div>
  </div>
</div>

<!-- ══ Controls ══ -->
<div class="controls">
  <div class="container">
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" placeholder="Search projects by name, description, or tag…">
    </div>
    <div class="filter-row">
      <button class="filter-btn active" data-cat="all">All <span class="count">{len(summaries)}</span></button>
      {"".join(f'<button class="filter-btn" data-cat="{esc(c)}">{cat_emoji.get(c, "📁")} {esc(c)} <span class="count">{cat_counts[c]}</span></button>' for c in categories)}
      <select class="sort-select" id="sortSelect">
        <option value="trend">Sort: Trend Score</option>
        <option value="stars">Sort: Stars</option>
        <option value="name">Sort: Name</option>
      </select>
    </div>
  </div>
</div>

<!-- ══ Cards ══ -->
<div class="container">
  <div class="cards-grid" id="cardsGrid"></div>
  <div class="no-results" id="noResults" style="display:none">
    <div class="emoji">🔭</div>
    <p>No projects match your search.</p>
  </div>
</div>

<!-- ══ Footer ══ -->
<div class="footer">
  <div class="container">
    AI GitHub Radar · Powered by GitHub API · Auto-generated on {esc(run_date)}
  </div>
</div>

<script>
const DATA = {data_json};

const grid = document.getElementById('cardsGrid');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const noResults = document.getElementById('noResults');
const filterBtns = document.querySelectorAll('.filter-btn');

let activeCat = 'all';
const maxScore = Math.max(...DATA.map(d => d.trend_score), 1);

function formatStars(n) {{
  if (n >= 1000) return (n/1000).toFixed(n >= 10000 ? 0 : 1) + 'K';
  return String(n);
}}

function renderCards(data) {{
  if (!data.length) {{
    grid.innerHTML = '';
    noResults.style.display = 'block';
    return;
  }}
  noResults.style.display = 'none';
  grid.innerHTML = data.map((d, i) => {{
    const qf = d.quick_facts || {{}};
    const rank = i + 1;
    const pct = Math.max((d.trend_score / maxScore) * 100, 5);
    const highlights = (d.highlights || [])
      .filter(h => !h.startsWith('[') && h.length > 5)
      .slice(0, 3)
      .map(h => `<li>${{esc(h)}}</li>`).join('');
    const risks = (d.risks || []).map(r => `<span>${{esc(r)}}</span>`).join('');
    const tags = (d.tags || []).slice(0, 5).map(t => `<span class="badge-tag">${{esc(t)}}</span>`).join('');
    const actionCls = (d.recommended_action || '').toLowerCase();

    return `
    <div class="card" data-cat="${{esc(d.category)}}" data-name="${{esc(d.full_name.toLowerCase())}}" data-desc="${{esc((d.one_liner||'').toLowerCase())}}">
      <span class="card-rank ${{rank <= 3 ? 'top3' : ''}}">#${{rank}}</span>
      <div class="card-header">
        <h3><a href="${{d.html_url}}" target="_blank" rel="noopener">${{esc(d.full_name)}}</a></h3>
      </div>
      <p class="card-oneliner">${{esc(d.one_liner || '')}}</p>
      <div class="card-meta">
        <span>⭐ ${{formatStars(qf.stars_total || 0)}}</span>
        <span>📅 ${{qf.last_update || '?'}}</span>
        <span>📄 ${{qf.license || '?'}}</span>
        <span>📈 ${{d.trend_score}}</span>
      </div>
      ${{highlights ? `<div class="card-highlights"><h4>Why it matters</h4><ul>${{highlights}}</ul></div>` : ''}}
      ${{risks ? `<div class="card-risks">${{risks}}</div>` : ''}}
      <div class="card-footer">
        <span class="badge-category">${{esc(d.category)}}</span>
        <span class="badge-action ${{actionCls}}">${{esc(d.recommended_action || '')}}</span>
        ${{tags}}
      </div>
      <div class="trend-bar" style="width:${{pct}}%"></div>
    </div>`;
  }}).join('');
}}

function esc(s) {{ const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }}

function applyFilters() {{
  const q = searchInput.value.toLowerCase().trim();
  const sortBy = sortSelect.value;
  let filtered = DATA.filter(d => {{
    if (activeCat !== 'all' && d.category !== activeCat) return false;
    if (q) {{
      const hay = [d.full_name, d.one_liner, d.category, ...(d.tags||[])].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});
  filtered.sort((a, b) => {{
    if (sortBy === 'stars') return (b.quick_facts?.stars_total||0) - (a.quick_facts?.stars_total||0);
    if (sortBy === 'name') return a.full_name.localeCompare(b.full_name);
    return b.trend_score - a.trend_score;
  }});
  renderCards(filtered);
}}

filterBtns.forEach(btn => {{
  btn.addEventListener('click', () => {{
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeCat = btn.dataset.cat;
    applyFilters();
  }});
}});

searchInput.addEventListener('input', applyFilters);
sortSelect.addEventListener('change', applyFilters);

// Initial render
applyFilters();
</script>
</body>
</html>"""


def _format_stars(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)
