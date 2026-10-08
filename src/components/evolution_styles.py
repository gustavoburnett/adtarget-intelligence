"""Design 1D: apresentação isolada do módulo Evolução da Performance."""

CSS_EVOLUTION = """<style>
.st-key-design_performance_evolution {
  padding:var(--atg-space-28) var(--atg-space-32) var(--atg-space-24);
  border:1px solid var(--atg-line-card);border-radius:var(--atg-radius-card);
  background:var(--atg-surface-card);box-shadow:var(--atg-shadow-card);
  container-type:inline-size;container-name:atg-performance-evolution;}
.st-key-design_performance_evolution_header {gap:var(--atg-space-28);}
.st-key-design_performance_evolution_title {min-width:120px;}
.st-key-design_performance_evolution_title [data-testid="stMarkdownContainer"] {margin-bottom:0;}
.st-key-design_performance_evolution .atg-evolution-title {
  color:var(--atg-ink);font-size:var(--atg-type-section-size);font-weight:800;
  letter-spacing:-.02em;line-height:1.3;margin:0;}
.st-key-design_performance_evolution_header > [data-testid="stLayoutWrapper"] {
  max-width:100%;}
.st-key-design_performance_evolution_controls {max-width:100%;}
.st-key-design_performance_evolution_controls [data-testid="stHorizontalBlock"] {
  gap:var(--atg-space-28);}
.st-key-design_performance_evolution_controls .stButtonGroup {
  display:flex;align-items:center;flex-wrap:wrap;gap:var(--atg-space-12);}
.st-key-design_performance_evolution_controls [data-testid="stWidgetLabel"] {
  margin:0;min-height:0;}
.st-key-design_performance_evolution_controls [data-testid="stWidgetLabel"] p {
  color:var(--atg-text-meta);font-size:var(--atg-type-label-size);font-weight:600;
  line-height:1.4;letter-spacing:.04em;text-transform:uppercase;}
.st-key-design_performance_evolution_controls [role="radiogroup"] {
  padding:3px;gap:2px;border-radius:var(--atg-radius-control);
  background:var(--atg-surface-muted);}
.st-key-design_performance_evolution_controls [data-testid="stButtonGroup"] [role="radiogroup"] button {
  min-height:44px;padding:var(--atg-space-8) var(--atg-space-14);
  border:0;border-radius:var(--atg-radius-option);background:transparent;
  color:var(--atg-text-secondary);font-size:var(--atg-type-control-size);font-weight:600;}
.st-key-design_performance_evolution_controls [data-testid="stButtonGroup"] button p {
  font-size:var(--atg-type-control-size);font-weight:600;line-height:1.3;white-space:nowrap;}
.st-key-design_performance_evolution_controls [data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] {
  background:var(--atg-brand);color:var(--atg-side-text-strong);}
.st-key-design_performance_evolution_controls button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
.st-key-design_performance_evolution_controls button:disabled {cursor:not-allowed;}
.st-key-design_performance_evolution_controls button:disabled:not([aria-checked="true"]) {
  color:var(--atg-text-meta);opacity:.55;}
.st-key-design_performance_evolution [role="tablist"] {
  gap:var(--atg-space-24);margin-top:18px;border-bottom:1px solid var(--atg-line-card);}
.st-key-design_performance_evolution [role="tab"] {
  padding:var(--atg-space-12) 2px;min-height:44px;color:var(--atg-text-muted);}
.st-key-design_performance_evolution [role="tab"] p {
  font-size:14px;font-weight:600;line-height:1.4;}
.st-key-design_performance_evolution [role="tab"][aria-selected="true"] {color:var(--atg-brand);}
.st-key-design_performance_evolution [role="tab"]:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
.st-key-design_performance_evolution [data-baseweb="tab-highlight"] {height:2px;background:var(--atg-brand);}
.st-key-design_performance_evolution [data-baseweb="tab-border"] {height:0;}
.st-key-design_performance_evolution [data-testid="stCaptionContainer"] p {
  color:var(--atg-text-muted);font-size:var(--atg-type-metadata-size);}
@container atg-performance-evolution (width < 720px) {
  .st-key-design_performance_evolution_controls [data-testid="stHorizontalBlock"] {
    display:grid;grid-template-columns:minmax(0,1fr);gap:var(--atg-space-16);}
  .st-key-design_performance_evolution_controls [data-testid="stColumn"] {width:100%;min-width:0;}
}
@media(max-width:640px) {
  .st-key-design_performance_evolution {
    padding-left:var(--atg-space-16);padding-right:var(--atg-space-16);}
}
</style>"""
