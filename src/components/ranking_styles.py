"""Design 1E: apresentação isolada dos rankings comerciais da Performance.

A consulta responsiva de largura útil permanece em performance_styles.py.
Os três containers nativos incluem lista e CTA na mesma superfície.
"""

CSS_RANKING = """<style>
.st-key-design_performance_rankings [data-testid="stHorizontalBlock"] {
  gap:var(--atg-space-20);align-items:stretch;}
.st-key-design_performance_rankings [data-testid="stColumn"] {min-width:0;}
.st-key-design_performance_rankings :is(
  .st-key-design_performance_ranking_groups,
  .st-key-design_performance_ranking_agencies,
  .st-key-design_performance_ranking_clients) {
  box-sizing:border-box;min-width:0;height:100%;
  padding:26px var(--atg-space-24) var(--atg-space-20);
  gap:var(--atg-space-14);background:var(--atg-surface-card);
  border:1px solid var(--atg-line-card);border-radius:var(--atg-radius-card);
  box-shadow:var(--atg-shadow-card);}
.st-key-design_performance_rankings [data-testid="stMarkdownContainer"] {margin-bottom:0;}
.st-key-design_performance_rankings .atg-card.atg-rank {
  padding:0;min-width:0;background:transparent;border:0;border-radius:0;
  box-shadow:none;transition:none;font-family:var(--atg-font);}
.st-key-design_performance_rankings .atg-card.atg-rank:hover {box-shadow:none;}
.st-key-design_performance_rankings .atg-rank-title {
  color:var(--atg-ink);font-size:var(--atg-type-ranking-size);font-weight:800;
  letter-spacing:-.02em;line-height:1.3;margin:0;}
.st-key-design_performance_rankings .atg-rank-list {
  display:flex;flex-direction:column;gap:18px;margin-top:var(--atg-space-20);}
.st-key-design_performance_rankings .atg-rank-row {
  display:flex;align-items:center;gap:var(--atg-space-12);min-width:0;margin:0;}
.st-key-design_performance_rankings .atg-rank-position {
  display:flex;align-items:center;justify-content:center;flex:0 0 24px;
  width:24px;height:24px;border-radius:var(--atg-radius-pill);
  background:var(--atg-surface-muted);color:var(--atg-text-secondary);
  font-size:var(--atg-type-badge-size);font-weight:700;line-height:1;}
.st-key-design_performance_rankings .atg-rank-content {flex:1;min-width:0;}
.st-key-design_performance_rankings .atg-rank-top {
  display:flex;align-items:baseline;gap:var(--atg-space-12);min-width:0;}
.st-key-design_performance_rankings .atg-rank-name {
  flex:1;min-width:0;width:auto;font-size:var(--atg-type-control-size);
  font-weight:700;letter-spacing:.02em;line-height:1.5;color:var(--atg-ink);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.st-key-design_performance_rankings .atg-rank-value {
  flex:none;min-width:0;font-size:15px;font-weight:700;line-height:1.5;
  color:var(--atg-ink);white-space:nowrap;text-align:right;}
.st-key-design_performance_rankings .atg-rank-bottom {
  display:flex;align-items:center;gap:var(--atg-space-12);min-width:0;
  margin-top:var(--atg-space-8);}
.st-key-design_performance_rankings .atg-rank-barwrap {
  flex:1;min-width:0;height:6px;border-radius:var(--atg-radius-pill);
  background:var(--atg-surface-muted);}
.st-key-design_performance_rankings .atg-rank-bar {
  height:6px;border-radius:var(--atg-radius-pill);background:var(--atg-brand);}
.st-key-design_performance_rankings .atg-rank-pct {
  width:30px;flex:0 0 30px;text-align:right;font-size:var(--atg-type-badge-size);
  font-weight:600;line-height:1.3;color:var(--atg-text-muted);white-space:nowrap;}
.st-key-design_performance_rankings .atg-trend {
  box-sizing:border-box;
  display:inline-flex;align-items:center;justify-content:center;
  gap:var(--atg-space-4);width:auto;min-width:68px;flex:none;
  padding:3px var(--atg-space-8);border-radius:var(--atg-radius-pill);
  font-size:var(--atg-type-badge-size);font-weight:700;line-height:1.3;
  text-align:center;white-space:nowrap;}
.st-key-design_performance_rankings .atg-trend.alta {
  color:var(--atg-positive);background:var(--atg-positive-bg);}
.st-key-design_performance_rankings .atg-trend.queda {
  color:var(--atg-negative);background:var(--atg-negative-bg);}
.st-key-design_performance_rankings .atg-trend.neutro {
  color:var(--atg-text-muted);background:var(--atg-surface-muted);font-weight:700;}
.st-key-design_performance_rankings .atg-rank-trend-arrow {font-size:8px;line-height:1;}
.st-key-design_performance_rankings .atg-rank-empty {
  margin-top:var(--atg-space-20);font-size:var(--atg-type-context-size);
  color:var(--atg-text-muted);line-height:1.5;white-space:normal;}
.st-key-design_performance_rankings [data-testid="stButton"] {min-width:0;}
.st-key-design_performance_rankings [data-testid="stButton"] button {
  padding:0;min-height:44px;border:0;border-radius:0;background:transparent;
  color:var(--atg-brand);box-shadow:none;justify-content:flex-start;}
.st-key-design_performance_rankings [data-testid="stButton"] button p {
  font-family:var(--atg-font);font-size:var(--atg-type-control-size);
  font-weight:700;line-height:1.4;}
.st-key-design_performance_rankings [data-testid="stButton"] button:hover {
  background:transparent;color:var(--atg-brand);text-decoration:underline;}
.st-key-design_performance_rankings [data-testid="stButton"] button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
@media(max-width:640px) {
  .st-key-design_performance_rankings :is(
    .st-key-design_performance_ranking_groups,
    .st-key-design_performance_ranking_agencies,
    .st-key-design_performance_ranking_clients) {
    padding-left:var(--atg-space-16);padding-right:var(--atg-space-16);}
}
</style>"""
