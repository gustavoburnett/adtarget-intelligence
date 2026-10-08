"""Design 1D: apresentação isolada do Radar Executivo no DS v1.0.1."""

CSS_RADAR = """
<style>
.st-key-design_performance_radar {
  container-type:inline-size;container-name:atg-radar;
  padding:var(--atg-space-24) var(--atg-space-28);gap:var(--atg-space-16);
  margin-bottom:var(--atg-space-8);
  background:var(--atg-surface-card);border:1px solid var(--atg-line-card);
  border-radius:var(--atg-radius-card);box-shadow:var(--atg-shadow-card);}
.st-key-design_performance_radar [data-testid="stMarkdownContainer"],
.st-key-design_performance_radar [data-testid="stCaptionContainer"] {margin-bottom:0;}
.st-key-design_performance_radar .atg-radar-header {
  display:flex;align-items:baseline;flex-wrap:wrap;gap:var(--atg-space-12);
  margin:0;}
.st-key-design_performance_radar .atg-radar-header h3.atg-radar-title {
  font-size:var(--atg-type-section-size);font-weight:800;color:var(--atg-ink);
  line-height:1.3;letter-spacing:-.02em;margin:0;padding:0;}
.st-key-design_performance_radar .atg-radar-meta {
  font-size:var(--atg-type-context-size);color:var(--atg-text-muted);line-height:1.5;}
.st-key-design_performance_radar .atg-radar {
  display:grid;grid-template-columns:minmax(0,1fr);gap:var(--atg-space-16);margin:0;}
.st-key-design_performance_radar .atg-radar-two {
  grid-template-columns:repeat(2,minmax(0,1fr));}
.st-key-design_performance_radar .atg-radar-single {
  width:calc((100% - var(--atg-space-16))/2);max-width:none;}
.st-key-design_performance_radar .atg-radar-item {
  display:flex;align-items:flex-start;gap:var(--atg-space-16);min-width:0;
  padding:var(--atg-space-20) 22px;border:1px solid var(--atg-line-control);
  border-radius:var(--atg-radius-insight);background:var(--atg-surface-muted);
  line-height:1.5;overflow-wrap:anywhere;}
.st-key-design_performance_radar .atg-radar-item[data-radar-kind="queda"] {
  background:var(--atg-negative-surface);border-color:var(--atg-negative-border);}
.st-key-design_performance_radar .atg-radar-item[data-radar-kind="crescimento"] {
  background:var(--atg-positive-surface);border-color:var(--atg-positive-border);}
.st-key-design_performance_radar .atg-radar-icon {
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  width:44px;height:44px;border-radius:var(--atg-radius-pill);
  background:var(--atg-surface-card);color:var(--atg-neutral-tile-fg);}
.st-key-design_performance_radar [data-radar-kind="queda"] .atg-radar-icon {
  color:var(--atg-negative);}
.st-key-design_performance_radar [data-radar-kind="crescimento"] .atg-radar-icon {
  color:var(--atg-positive);}
.st-key-design_performance_radar .atg-radar-copy {min-width:0;flex:1;}
.st-key-design_performance_radar .atg-radar-category {
  font-size:var(--atg-type-label-size);font-weight:600;letter-spacing:.06em;
  line-height:1.4;color:var(--atg-text-secondary);margin:0 0 var(--atg-space-8);}
.st-key-design_performance_radar [data-radar-kind="queda"] .atg-radar-category {
  color:var(--atg-negative-label);}
.st-key-design_performance_radar [data-radar-kind="crescimento"] .atg-radar-category {
  color:var(--atg-positive-label);}
.st-key-design_performance_radar .atg-radar-headline {
  font-size:var(--atg-type-radar-size);font-weight:800;letter-spacing:-.03em;
  line-height:1.15;color:var(--atg-ink);margin:0 0 var(--atg-space-8);}
.st-key-design_performance_radar .atg-radar-context {
  font-size:var(--atg-type-support-size);font-weight:400;color:var(--atg-text-secondary);
  line-height:1.5;margin:0 0 var(--atg-space-4);}
.st-key-design_performance_radar .atg-radar-cta {
  font-size:var(--atg-type-control-size);font-weight:400;font-style:italic;
  color:var(--atg-text-muted);line-height:1.5;}
.st-key-design_performance_radar_sync {gap:0;}
.st-key-design_performance_radar_sync [data-testid="stCaptionContainer"] p {
  color:var(--atg-text-meta);font-size:11px;line-height:1.5;margin:0;}
/* Três cards pedem ao menos 320 px cada: 3 x 320 + 2 x 16 = 992 px úteis.
   A consulta mede o espaço disponível após sidebar e padding do módulo. */
@container atg-radar (min-width:992px) {
  .st-key-design_performance_radar .atg-radar-three {
    grid-template-columns:repeat(3,minmax(0,1fr));}
}
@media(max-width:1000px) {
  .st-key-design_performance_radar .atg-radar-two,
  .st-key-design_performance_radar .atg-radar-three {
    grid-template-columns:minmax(0,1fr);}
  .st-key-design_performance_radar .atg-radar-single {width:100%;}
}
@media(max-width:640px) {
  .st-key-design_performance_radar {
    padding:var(--atg-space-24) var(--atg-space-16);}
  .st-key-design_performance_radar .atg-radar-item {
    padding:var(--atg-space-20) var(--atg-space-16);}
}
</style>
"""
