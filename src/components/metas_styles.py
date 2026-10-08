"""Design 1F: apresentação de Metas; seletores isolados da página.

A régua de parceiros e os pontos de quebra são somente apresentação.
Os gráficos mantêm suas figuras, séries e configurações funcionais.
"""

CSS_METAS = """<style>
/* Mesmo shell e cabeçalho nativo da Performance, restritos à página Metas. */
[data-testid="stMainBlockContainer"]:has(.st-key-design_metas_header) {
  max-width:1336px;padding-left:var(--atg-space-48);padding-right:var(--atg-space-48);}
.st-key-design_metas_header {gap:var(--atg-space-24);margin-bottom:var(--atg-space-8);}
.st-key-design_metas_title {min-width:min(100%,360px);}
.st-key-design_metas_header .atg-h1 {
  color:var(--atg-ink);font-size:var(--atg-type-page-size);font-weight:800;
  letter-spacing:-.03em;line-height:1.1;margin:0;}
.st-key-design_metas_actions {gap:var(--atg-space-12);}
.st-key-design_metas_header .atg-updated {
  color:var(--atg-text-muted);font-size:var(--atg-type-metadata-size);
  line-height:1.5;white-space:nowrap;}
.st-key-design_metas_header button,.st-key-design_metas_filters button {
  min-height:44px;border-radius:var(--atg-radius-control);box-shadow:none;
  border:1px solid var(--atg-line-control);background:var(--atg-surface-card);
  color:var(--atg-ink);font-size:var(--atg-type-control-size);font-weight:600;
  padding:0 var(--atg-space-16);}
.st-key-design_metas_header button p,.st-key-design_metas_filters button p {
  font-size:var(--atg-type-control-size);font-weight:600;line-height:1.3;}
.st-key-design_metas_header button:not(:disabled):hover,
.st-key-design_metas_filters button:not(:disabled):hover {
  border-color:var(--atg-line-control-hover);color:var(--atg-brand);}
.st-key-design_metas_header button:focus-visible,
.st-key-design_metas_filters button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
.st-key-design_metas_refresh button {
  background:var(--atg-side-bg);border-color:var(--atg-side-bg);color:var(--atg-side-text-strong);}
.st-key-design_metas_refresh button:not(:disabled):hover {
  background:var(--atg-side-bg);color:var(--atg-side-text-strong);}
.st-key-design_metas_header [data-testid="stIconMaterial"] {font-size:16px;}
.st-key-design_metas_theme button {width:44px;min-width:44px;padding:0;}
.st-key-design_metas_theme button p {font-size:20px;font-weight:400;}
.st-key-design_metas_filters {
  padding:var(--atg-space-16) var(--atg-space-20);gap:var(--atg-space-24);
  border:1px solid var(--atg-line-card);border-radius:var(--atg-radius-card);
  background:var(--atg-surface-card);box-shadow:var(--atg-shadow-card);}
.st-key-design_metas_year .stButtonGroup {
  display:flex;align-items:center;flex-wrap:wrap;gap:var(--atg-space-12);}
.st-key-design_metas_year [data-testid="stWidgetLabel"] {margin:0;min-height:0;}
.st-key-design_metas_year [data-testid="stWidgetLabel"] p {
  color:var(--atg-text-meta);font-size:var(--atg-type-label-size);
  font-weight:600;letter-spacing:.06em;text-transform:uppercase;}
.st-key-design_metas_year [role="radiogroup"] {
  padding:3px;gap:2px;border-radius:var(--atg-radius-control);background:var(--atg-surface-muted);}
.st-key-design_metas_year [data-testid="stButtonGroup"] [role="radiogroup"] button {
  border:0;border-radius:var(--atg-radius-option);background:transparent;
  min-width:60px;min-height:44px;padding:var(--atg-space-8) var(--atg-space-14);
  color:var(--atg-text-secondary);}
.st-key-design_metas_year [data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] {
  background:var(--atg-brand);color:var(--atg-side-text-strong);}

/* Indicadores existentes: tipografia e superfícies do Design System. */
.st-key-design_metas_content {min-width:0;container-type:inline-size;container-name:atg-metas-content;}
.st-key-design_metas_content .atg-metas {
  color:var(--atg-ink);font-family:var(--atg-font);margin:var(--atg-space-8) 0 var(--atg-space-24);}
.st-key-design_metas_content .atg-metas,.st-key-design_metas_content .atg-metas * {
  box-sizing:border-box;min-width:0;overflow-wrap:anywhere;font-variant-numeric:tabular-nums;}
.st-key-design_metas_content .atg-card {
  background:var(--atg-surface-card);border:1px solid var(--atg-line-card);
  border-radius:var(--atg-radius-card);box-shadow:var(--atg-shadow-card);}
.st-key-design_metas_content .atg-card:hover {box-shadow:var(--atg-shadow-card);}
.st-key-design_metas_content .atg-metas-hero {padding:var(--atg-space-24);margin-bottom:var(--atg-space-16);}
.st-key-design_metas_content .atg-metas-hero-grid {
  display:grid;grid-template-columns:minmax(220px,.8fr) minmax(0,1.8fr);
  gap:var(--atg-space-24);align-items:center;}
.st-key-design_metas_content .atg-metas-label {
  font-size:var(--atg-type-label-size);font-weight:600;color:var(--atg-text-meta);
  letter-spacing:.04em;line-height:1.5;}
.st-key-design_metas_content .atg-metas-eyebrow {color:var(--atg-brand);font-weight:600;letter-spacing:.06em;}
.st-key-design_metas_content .atg-metas-number {
  font-size:var(--atg-type-hero-size);font-weight:800;letter-spacing:-.04em;
  line-height:1.1;margin-top:var(--atg-space-8);}
.st-key-design_metas_content .atg-metas-context {
  font-size:var(--atg-type-context-size);color:var(--atg-text-muted);line-height:1.5;
  margin-top:var(--atg-space-8);}
.st-key-design_metas_content .atg-metas-support {
  display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--atg-space-16) var(--atg-space-24);}
.st-key-design_metas_content .atg-metas-support-value {
  font-size:var(--atg-type-radar-size);font-weight:800;line-height:1.3;margin-top:var(--atg-space-4);}
.st-key-design_metas_content .atg-metas-annual {padding:var(--atg-space-24);margin-bottom:var(--atg-space-24);}
.st-key-design_metas_content .atg-metas-annual-grid {
  display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);
  gap:var(--atg-space-32);align-items:center;}
.st-key-design_metas_content .atg-metas-annual-sold {font-size:var(--atg-type-radar-size);font-weight:800;line-height:1.3;}
.st-key-design_metas_content .atg-metas-annual-pct {
  display:flex;justify-content:space-between;gap:var(--atg-space-12);align-items:center;
  font-size:var(--atg-type-context-size);color:var(--atg-text-secondary);margin-top:var(--atg-space-14);}
.st-key-design_metas_content .atg-metas-annual-pct strong {font-size:16px;color:var(--atg-ink);}
.st-key-design_metas_content .atg-metas-annual-progress {
  height:8px;border-radius:var(--atg-radius-pill);background:var(--atg-surface-muted);
  margin:var(--atg-space-8) 0 var(--atg-space-12);overflow:hidden;}
.st-key-design_metas_content .atg-metas-annual-fill {height:100%;background:var(--atg-brand);}
.st-key-design_metas_content .atg-metas-annual-gap {
  font-size:var(--atg-type-kpi-size);font-weight:800;letter-spacing:-.03em;line-height:1.3;}
.st-key-design_metas_content .atg-metas-annual-gap-copy {font-size:16px;font-weight:500;margin-top:var(--atg-space-4);}
.st-key-design_metas_content .atg-metas-projection {container-type:inline-size;}
.st-key-design_metas_content .atg-metas-band {
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));padding:var(--atg-space-20) 0;
  margin-bottom:var(--atg-space-16);}
.st-key-design_metas_content .atg-metas-band-cell {padding:0 var(--atg-space-24);min-width:0;}
.st-key-design_metas_content .atg-metas-band-cell+.atg-metas-band-cell {border-left:1px solid var(--atg-line-card);}
.st-key-design_metas_content .atg-metas-value {
  font-size:var(--atg-type-radar-size);font-weight:800;letter-spacing:-.03em;
  line-height:1.35;margin-top:var(--atg-space-8);}
.st-key-design_metas_content .atg-metas-state {font-size:16px;font-weight:600;line-height:1.4;}
.st-key-design_metas_content .atg-metas-positive {color:var(--atg-positive);}
.st-key-design_metas_content .atg-metas-negative {color:var(--atg-negative);}
.st-key-design_metas_content .atg-metas-neutral {color:var(--atg-ink);}
.st-key-design_metas_content .atg-metas h2.atg-metas-title {
  color:var(--atg-ink);font-size:var(--atg-type-section-size);font-weight:800;
  letter-spacing:-.02em;line-height:1.3;margin:0 0 var(--atg-space-12);padding:0;}
.st-key-design_metas_content .atg-metas-annual h2.atg-metas-title {
  color:var(--atg-text-meta);font-size:var(--atg-type-label-size);font-weight:600;letter-spacing:.06em;}
.st-key-design_metas_content .atg-metas-insight {
  font-size:var(--atg-type-context-size);color:var(--atg-text-muted);line-height:1.5;
  margin:0 0 var(--atg-space-24);padding:0 var(--atg-space-4);}
.st-key-design_metas_content .atg-metas-empty {padding:var(--atg-space-24);margin:var(--atg-space-8) 0 var(--atg-space-24);}
.st-key-design_metas_content .atg-metas-footer {
  font-size:var(--atg-type-label-size);color:var(--atg-text-muted);line-height:1.6;margin-top:var(--atg-space-24);}
.st-key-design_metas_content :is(.st-key-design_metas_chart_metas_mensal,.st-key-design_metas_chart_metas_acumulada) {
  padding:var(--atg-space-24);gap:var(--atg-space-12);min-width:0;
  background:var(--atg-surface-card);border:1px solid var(--atg-line-card);
  border-radius:var(--atg-radius-card);box-shadow:var(--atg-shadow-card);}

/* Parceiros: uma superfície compartilhada, colunas comparáveis e dados integrais. */
.st-key-design_metas_content .atg-metas.atg-metas-partner-section {
  container-type:inline-size;container-name:atg-metas-partners;}
.st-key-design_metas_content .atg-metas h3.atg-metas-partner-group {
  font-size:var(--atg-type-ranking-size);font-weight:800;letter-spacing:-.02em;
  line-height:1.3;margin:var(--atg-space-24) 0 var(--atg-space-12);padding:0;}
.st-key-design_metas_content .atg-metas-partners {
  --atg-metas-columns:116px 92px 128px minmax(236px,1.2fr) minmax(100px,1fr) 196px;
  padding:0;overflow:visible;}
.st-key-design_metas_content .atg-metas-partner {
  position:relative;display:grid;grid-template-columns:var(--atg-metas-columns);column-gap:var(--atg-space-14);
  align-items:center;min-height:64px;padding:var(--atg-space-10) var(--atg-space-24);
  border-bottom:1px solid #ECEFEB;}
.st-key-design_metas_content .atg-metas-partner:last-child {border-bottom:0;}
.st-key-design_metas_content :is(.atg-metas-partner-head,.atg-metas-partner-heading) {display:contents;}
.st-key-design_metas_content .atg-metas-partner-logo {
  grid-column:1;grid-row:1;display:flex;align-items:center;justify-content:flex-start;min-height:44px;}
.st-key-design_metas_content .atg-metas-partner-logo .atg-partner-logo {
  width:116px;max-width:100%;height:44px;}
.st-key-design_metas_content .atg-metas-partner-name {
  font-size:var(--atg-type-support-size);font-weight:700;line-height:1.4;overflow-wrap:anywhere;}
.st-key-design_metas_content .atg-metas-partner-pct {
  grid-column:2;grid-row:1;font-size:var(--atg-type-radar-size);font-weight:800;
  letter-spacing:-.03em;line-height:1.2;text-align:right;white-space:nowrap;color:var(--atg-ink);}
.st-key-design_metas_content .atg-metas-partner-status {
  grid-column:3;grid-row:1;justify-self:start;font-size:var(--atg-type-label-size);font-weight:700;
  line-height:1.35;border-radius:var(--atg-radius-pill);padding:var(--atg-space-4) var(--atg-space-8);
  white-space:normal;overflow-wrap:normal;max-width:100%;}
.st-key-design_metas_content .atg-metas-partner-status.atg-metas-positive {
  color:var(--atg-positive);background:var(--atg-positive-bg);}
.st-key-design_metas_content .atg-metas-partner-status.atg-metas-negative {
  color:var(--atg-negative);background:var(--atg-negative-bg);}
.st-key-design_metas_content .atg-metas-partner-status.atg-metas-neutral {
  color:var(--atg-text-muted);background:var(--atg-surface-muted);}
.st-key-design_metas_content .atg-metas-partner-comparison {
  grid-column:4;grid-row:1;font-size:var(--atg-type-badge-size);color:var(--atg-text-muted);
  font-weight:400;line-height:1.5;margin:0;overflow-wrap:normal;}
.st-key-design_metas_content .atg-metas-partner-comparison strong {
  color:var(--atg-ink);font-weight:700;}
.st-key-design_metas_content .atg-metas-partner-comparison .num {white-space:nowrap;}
.st-key-design_metas_content .atg-metas-partner-context {
  display:block;font-size:var(--atg-type-label-size);line-height:1.4;margin-top:var(--atg-space-4);}
.st-key-design_metas_content .atg-metas-progress-block {grid-column:5;grid-row:1;min-width:0;}
.st-key-design_metas_content .atg-metas-progress {
  position:relative;height:8px;background:var(--atg-surface-muted);border-radius:var(--atg-radius-pill);
  margin:0;overflow:visible;}
.st-key-design_metas_content .atg-metas-progress::before {
  content:"";position:absolute;left:80%;top:0;right:0;bottom:0;
  background:var(--atg-line-control);border-radius:0 var(--atg-radius-pill) var(--atg-radius-pill) 0;}
.st-key-design_metas_content .atg-metas-progress-fill {
  position:absolute;left:0;top:0;height:8px;max-width:80%;border-radius:var(--atg-radius-pill);
  background:var(--atg-brand);}
.st-key-design_metas_content .atg-metas-progress-over {
  position:absolute;left:80%;top:0;height:8px;max-width:20%;background:var(--atg-positive);
  border-radius:0 var(--atg-radius-pill) var(--atg-radius-pill) 0;}
.st-key-design_metas_content .atg-metas-progress-reference {
  position:absolute;left:80%;width:2px;height:16px;top:-4px;background:var(--atg-text-muted);z-index:1;}
.st-key-design_metas_content .atg-metas-progress-overflow {
  display:block;font-size:var(--atg-type-label-size);font-weight:600;color:var(--atg-positive);
  line-height:1.4;margin-top:var(--atg-space-6);}
.st-key-design_metas_content .atg-metas-scale {
  display:grid;grid-template-columns:var(--atg-metas-columns);column-gap:var(--atg-space-14);
  height:28px;font-size:10px;color:var(--atg-text-meta);margin:0;
  padding:var(--atg-space-10) var(--atg-space-24) 0;}
.st-key-design_metas_content .atg-metas-scale span {
  position:relative;grid-column:5;left:80%;transform:translateX(-50%);
  width:max-content;white-space:nowrap;text-align:center;}
.st-key-design_metas_content .atg-metas-partner-inactive .atg-metas-progress-fill {background:var(--atg-chart-previous);}
.st-key-design_metas_content .atg-metas-partner-inactive .atg-metas-progress-over {background:var(--atg-text-muted);}
.st-key-design_metas_content .atg-metas-partner details.atg-metas-partner-detail-shell {
  display:block;grid-column:1/-1;grid-row:2;width:100%;
  color:var(--atg-text-muted);font-size:var(--atg-type-control-size);margin:0;}
.st-key-design_metas_content .atg-metas-partner summary {
  position:absolute;top:10px;right:24px;display:flex;align-items:center;justify-content:space-between;
  gap:var(--atg-space-8);min-height:44px;width:196px;padding:0;
  cursor:pointer;list-style:none;color:var(--atg-text-muted);font-size:var(--atg-type-control-size);
  font-weight:500;line-height:1.4;white-space:nowrap;border-radius:var(--atg-radius-option);}
.st-key-design_metas_content .atg-metas-partner summary::-webkit-details-marker {display:none;}
.st-key-design_metas_content .atg-metas-partner summary::marker {content:"";}
.st-key-design_metas_content .atg-metas-partner summary::after {
  content:"";flex:0 0 6px;width:6px;height:6px;border-right:1.5px solid currentColor;
  border-bottom:1.5px solid currentColor;transform:rotate(45deg);margin-right:var(--atg-space-4);}
.st-key-design_metas_content .atg-metas-partner details[open] summary::after {transform:rotate(225deg);}
.st-key-design_metas_content .atg-metas-partner summary:hover {color:var(--atg-brand);}
.st-key-design_metas_content .atg-metas-partner summary:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:3px;}
.st-key-design_metas_content .atg-metas-partner-details {
  width:100%;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
  gap:var(--atg-space-14) var(--atg-space-20);padding:var(--atg-space-20) 0 var(--atg-space-8);
  margin-top:var(--atg-space-10);border-top:1px solid #ECEFEB;}
.st-key-design_metas_content .atg-metas-partner details:not([open]) > .atg-metas-partner-details {display:none;}
.st-key-design_metas_content .atg-metas-detail-value {
  font-size:var(--atg-type-support-size);font-weight:700;color:var(--atg-ink);
  line-height:1.4;margin-top:var(--atg-space-4);}

/* Mede o conteúdo útil após sidebar e margens: as seis colunas pedem 986 px.
   1040 px reserva espaço para Inter real e nomes/estados de tamanho variável. */
@container atg-metas-partners (width < 1040px) {
  .st-key-design_metas_content .atg-metas-partner {
    grid-template-columns:minmax(0,1fr) auto;column-gap:var(--atg-space-14);
    row-gap:0;padding:var(--atg-space-20) var(--atg-space-24);}
  .st-key-design_metas_content .atg-metas-partner-logo {grid-column:1;grid-row:1;}
  .st-key-design_metas_content .atg-metas-partner-pct {grid-column:2;grid-row:1;}
  .st-key-design_metas_content .atg-metas-partner-status {
    grid-column:1/-1;grid-row:2;margin-top:var(--atg-space-8);}
  .st-key-design_metas_content .atg-metas-partner-comparison {
    grid-column:1/-1;grid-row:3;font-size:var(--atg-type-support-size);margin-top:var(--atg-space-8);}
  .st-key-design_metas_content .atg-metas-progress-block {
    grid-column:1/-1;grid-row:4;margin:var(--atg-space-12) 0 var(--atg-space-4);}
  .st-key-design_metas_content .atg-metas-partner details.atg-metas-partner-detail-shell {grid-row:5;}
  .st-key-design_metas_content .atg-metas-partner summary {
    position:static;top:auto;right:auto;width:100%;margin-top:var(--atg-space-8);}
  .st-key-design_metas_content .atg-metas-scale {
    display:block;height:auto;padding:var(--atg-space-10) var(--atg-space-24) 0;text-align:right;}
  .st-key-design_metas_content .atg-metas-scale span {
    display:block;position:static;left:auto;transform:none;width:auto;text-align:right;}
}
@container atg-metas-content (width < 700px) {
  .st-key-design_metas_content .atg-metas-hero-grid,
  .st-key-design_metas_content .atg-metas-annual-grid {grid-template-columns:minmax(0,1fr);gap:var(--atg-space-20);}
  .st-key-design_metas_content .atg-metas-band {grid-template-columns:minmax(0,1fr);padding:0 var(--atg-space-24);}
  .st-key-design_metas_content .atg-metas-band-cell {padding:var(--atg-space-20) 0;}
  .st-key-design_metas_content .atg-metas-band-cell+.atg-metas-band-cell {border-left:0;border-top:1px solid var(--atg-line-card);}
}
@container atg-metas-partners (width < 480px) {
  .st-key-design_metas_content .atg-metas-partner {padding:var(--atg-space-20);}
  .st-key-design_metas_content .atg-metas-partner-details {grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media(max-width:640px) {
  [data-testid="stMainBlockContainer"]:has(.st-key-design_metas_header) {
    padding-left:var(--atg-space-16);padding-right:var(--atg-space-16);}
  .st-key-design_metas_header {align-items:flex-start;}
  .st-key-design_metas_actions {max-width:100%;gap:var(--atg-space-8);}
  .st-key-design_metas_content .atg-metas-support {grid-template-columns:minmax(0,1fr);}
  .st-key-design_metas_content :is(.atg-metas-hero,.atg-metas-annual,.atg-metas-empty) {padding:var(--atg-space-20);}
  .st-key-design_metas_content .atg-metas-number {font-size:40px;}
  .st-key-design_metas_content :is(.st-key-design_metas_chart_metas_mensal,.st-key-design_metas_chart_metas_acumulada) {
    padding:var(--atg-space-16);}
}
</style>"""
