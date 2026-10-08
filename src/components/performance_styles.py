"""Design 1C: cabeçalho, filtros e indicadores; sem estilos de Radar/gráficos."""

from urllib.parse import quote

_FUNIL = quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.9" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 4h16l-6 7v7l-4 2v-9Z"/></svg>'
)

CSS_PERFORMANCE = "<style>" + """
/* Somente a página que contém o cabeçalho de Performance. */
[data-testid="stMainBlockContainer"]:has(.st-key-design_performance_header) {
  max-width:1336px;padding-left:var(--atg-space-48);padding-right:var(--atg-space-48);}
.st-key-design_performance_header {gap:var(--atg-space-24);margin-bottom:var(--atg-space-8);}
.st-key-design_performance_title {min-width:min(100%,360px);}
.st-key-design_performance_header .atg-h1 {
  color:var(--atg-ink);font-size:var(--atg-type-page-size);font-weight:800;
  letter-spacing:-.03em;line-height:1.1;margin:0;}
.st-key-design_performance_actions {gap:var(--atg-space-12);}
.st-key-design_performance_header .atg-updated {
  color:var(--atg-text-meta);font-size:var(--atg-type-metadata-size);
  line-height:1.5;white-space:nowrap;}
.st-key-design_performance_header button,
.st-key-design_performance_filters button {
  min-height:44px;border-radius:var(--atg-radius-control);box-shadow:none;
  border:1px solid var(--atg-line-control);background:var(--atg-surface-card);
  color:var(--atg-ink);font-size:var(--atg-type-control-size);font-weight:600;
  padding:0 var(--atg-space-16);}
.st-key-design_performance_header button p,
.st-key-design_performance_filters button p {
  font-size:var(--atg-type-control-size);font-weight:600;line-height:1.3;}
.st-key-design_performance_header button:not(:disabled):hover,
.st-key-design_performance_filters button:not(:disabled):hover {
  border-color:var(--atg-line-control-hover);color:var(--atg-brand);}
.st-key-design_performance_header button:focus-visible,
.st-key-design_performance_filters button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
.st-key-design_performance_refresh button {
  background:var(--atg-side-bg);border-color:var(--atg-side-bg);
  color:var(--atg-side-text-strong);}
.st-key-design_performance_refresh button:not(:disabled):hover {
  background:var(--atg-side-bg);color:var(--atg-side-text-strong);}
.st-key-design_performance_header [data-testid="stIconMaterial"] {font-size:16px;}
.st-key-design_performance_theme button {width:44px;min-width:44px;padding:0;}
.st-key-design_performance_theme button p {font-size:20px;font-weight:400;}
/* Controle de ano e seletor reais, sem mudanças de estado ou callbacks. */
.st-key-design_performance_filters {
  padding:var(--atg-space-16) var(--atg-space-20);gap:var(--atg-space-24);
  border:1px solid var(--atg-line-card);border-radius:var(--atg-radius-card);
  background:var(--atg-surface-card);box-shadow:var(--atg-shadow-card);}
.st-key-design_performance_year .stButtonGroup {
  display:flex;align-items:center;gap:var(--atg-space-12);}
.st-key-design_performance_year [data-testid="stWidgetLabel"] {margin:0;min-height:0;}
.st-key-design_performance_year [data-testid="stWidgetLabel"] p {
  color:var(--atg-text-meta);font-size:var(--atg-type-label-size);
  font-weight:600;letter-spacing:.06em;text-transform:uppercase;}
.st-key-design_performance_year [role="radiogroup"] {
  padding:3px;gap:2px;border-radius:var(--atg-radius-control);
  background:var(--atg-surface-muted);}
.st-key-design_performance_year [data-testid="stButtonGroup"] [role="radiogroup"] button {
  border:0;border-radius:var(--atg-radius-option);background:transparent;
  min-width:60px;min-height:44px;padding:var(--atg-space-8) var(--atg-space-14);
  color:var(--atg-text-secondary);}
.st-key-design_performance_year [data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] {
  background:var(--atg-brand);color:var(--atg-side-text-strong);}
.st-key-design_performance_group {max-width:100%;}
.st-key-design_performance_group [data-testid="stPopover"] button {
  justify-content:space-between;min-height:44px;padding:0 var(--atg-space-16);
  background:var(--atg-surface-card);border:1px solid var(--atg-line-control);}
.st-key-design_performance_group button:disabled {
  background:var(--atg-surface-muted);color:var(--atg-text-meta);}
.st-key-design_performance_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-design_performance_clear) {
  margin-left:auto;}
.st-key-design_performance_clear button p {display:flex;align-items:center;gap:var(--atg-space-8);}
.st-key-design_performance_clear button p::before {
  content:"";width:16px;height:16px;flex-shrink:0;background:currentColor;
  mask:center/contain no-repeat url("data:image/svg+xml,ICON_FUNIL");}
/* Cinco indicadores com conteúdo integral, sem ellipsis ou strip compartilhado. */
.atg-performance-indicators {container-type:inline-size;}
.atg-performance-indicators .atg-kpi-row {
  display:grid;grid-template-columns:minmax(0,1fr);gap:var(--atg-space-16);
  margin:var(--atg-space-8) 0 var(--atg-space-24);}
.atg-performance-indicators .atg-card {
  background:var(--atg-surface-card);border:1px solid var(--atg-line-card);
  border-radius:var(--atg-radius-card);box-shadow:var(--atg-shadow-card);min-width:0;}
.atg-performance-indicators .atg-card:hover {box-shadow:var(--atg-shadow-card);}
.atg-performance-indicators .atg-kpi-hero {
  padding:var(--atg-space-24);gap:var(--atg-space-12);justify-content:center;}
.atg-performance-indicators .atg-eyebrow {
  color:var(--atg-brand);font-size:var(--atg-type-label-size);font-weight:600;
  letter-spacing:.06em;line-height:1.4;margin:0;}
.atg-performance-indicators .atg-hero-value {align-items:center;gap:var(--atg-space-8);}
.atg-performance-indicators .atg-hero-arrow {display:flex;flex-shrink:0;}
.atg-performance-indicators .atg-hero-number {
  font-size:var(--atg-type-hero-size);font-weight:800;letter-spacing:-.04em;
  line-height:1;min-width:0;}
.atg-performance-indicators .atg-hero-alta .atg-hero-value {color:var(--atg-positive);}
.atg-performance-indicators .atg-hero-queda .atg-hero-value {color:var(--atg-negative);}
.atg-performance-indicators .atg-hero-neutro .atg-hero-value {color:var(--atg-text-muted);}
.atg-performance-indicators .atg-hero-caption {
  color:var(--atg-text-secondary);font-size:var(--atg-type-context-size);
  font-weight:400;line-height:1.5;margin:0;}
.atg-performance-indicators .atg-kpi-grid {
  display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--atg-space-16);
  border:0;background:transparent;border-radius:0;}
.atg-performance-indicators .atg-kpi-card {
  padding:var(--atg-space-24) var(--atg-space-20);
  display:flex;flex-direction:column;gap:var(--atg-space-14);}
.atg-performance-indicators .atg-stat+.atg-stat {border-left:1px solid var(--atg-line-card);}
.atg-performance-indicators .atg-kpi-heading {display:flex;align-items:center;gap:var(--atg-space-12);}
.atg-performance-indicators .atg-kpi-icon {
  display:flex;align-items:center;justify-content:center;flex-shrink:0;
  width:44px;height:44px;border-radius:var(--atg-radius-tile);
  background:var(--atg-neutral-tile-bg);color:var(--atg-neutral-tile-fg);}
.atg-performance-indicators .atg-kpi-vendas .atg-kpi-icon {
  background:var(--atg-brand-tint);color:var(--atg-brand);}
.atg-performance-indicators .atg-kpi-em-aberto .atg-kpi-icon {
  background:var(--atg-warning-bg);color:var(--atg-warning);}
.atg-performance-indicators .atg-kpi-label {
  color:var(--atg-text-meta);font-size:var(--atg-type-label-size);font-weight:600;
  letter-spacing:.06em;line-height:1.4;text-transform:uppercase;}
.atg-performance-indicators .atg-kpi-value {
  color:var(--atg-ink);font-size:var(--atg-type-kpi-size);font-weight:800;
  letter-spacing:-.03em;line-height:1.1;margin:0;white-space:nowrap;}
.atg-performance-indicators .atg-kpi-vendas .atg-kpi-value {color:var(--atg-brand);}
.atg-performance-indicators .atg-kpi-em-aberto .atg-kpi-value {color:var(--atg-warning);}
.atg-performance-indicators .atg-kpi-value.atg-kpi-empty {
  font-size:var(--atg-type-support-size);font-weight:400;line-height:1.5;
  white-space:normal;}
.atg-performance-indicators .atg-kpi-caption {
  color:var(--atg-text-muted);font-size:var(--atg-type-context-size);
  line-height:1.5;margin:0;white-space:normal;overflow:visible;text-overflow:clip;}
.atg-performance-indicators .atg-sr-only {position:absolute;width:1px;height:1px;padding:0;margin:-1px;
  overflow:hidden;clip-path:inset(50%);white-space:nowrap;border:0;}
@media(min-width:1440px) {
  /* 5 colunas apenas quando cabe na largura efetiva (incluindo a sidebar). */
  @container(min-width:1224px) {
    .atg-performance-indicators .atg-kpi-row {
      grid-template-columns:minmax(0,1.5fr) repeat(4,minmax(0,1fr));}
    .atg-performance-indicators .atg-kpi-grid {display:contents;}
  }
}
@media(min-width:1001px) and (max-width:1199px) {
  .atg-performance-indicators .atg-kpi-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media(max-width:1000px) {
  .atg-performance-indicators .atg-kpi-grid {grid-template-columns:minmax(0,1fr);}
}
/* Três rankings exigem ~1183 px úteis; 1200 px mantém um pequeno respiro.
   O container mede o espaço após sidebar e margens, sem alterar os cards. */
.st-key-design_performance_rankings {
  container-type:inline-size;container-name:atg-performance-rankings;}
@container atg-performance-rankings (width < 1200px) {
  .st-key-design_performance_rankings [data-testid="stHorizontalBlock"] {
    display:grid;grid-template-columns:minmax(0,1fr);}
  .st-key-design_performance_rankings [data-testid="stColumn"] {width:100%;min-width:0;}
}
@media(max-width:640px) {
  [data-testid="stMainBlockContainer"]:has(.st-key-design_performance_header) {
    padding-left:var(--atg-space-16);padding-right:var(--atg-space-16);}
  .st-key-design_performance_header {align-items:flex-start;}
  .st-key-design_performance_actions {max-width:100%;gap:var(--atg-space-8);}
  .st-key-design_performance_filters > [data-testid="stLayoutWrapper"]:has(> .st-key-design_performance_clear) {
    margin-left:0;}
}
</style>
""".replace("ICON_FUNIL", _FUNIL)
