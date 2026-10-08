"""Design 1G: apresentação do Analítico Comercial, sem regras de negócio.

Os pontos de quebra medem o espaço útil dos containers, após a sidebar.
Todos os seletores pertencem à página comercial; tabelas continuam nativas.
"""

from urllib.parse import quote

_FUNIL = quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.9" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4 4h16l-6 7v7l-4 2v-9Z"/></svg>'
)

CSS_ANALITICO_COMERCIAL = "<style>" + """
/* Shell aprovado: largura, fonte e cores vêm dos tokens compartilhados. */
[data-testid="stMainBlockContainer"]:has(.st-key-design_comercial_header) {
  max-width:1336px;padding-left:var(--atg-space-48);padding-right:var(--atg-space-48);}
.st-key-design_comercial_header {gap:var(--atg-space-24);margin-bottom:var(--atg-space-8);}
.st-key-design_comercial_title {min-width:min(100%,360px);}
.st-key-design_comercial_header .atg-h1 {
  color:var(--atg-ink);font-size:var(--atg-type-page-size);font-weight:800;
  letter-spacing:-.03em;line-height:1.1;margin:0;}
.st-key-design_comercial_actions {gap:var(--atg-space-12);}
.st-key-design_comercial_header .atg-updated,
.st-key-design_comercial_filters .atg-updated {
  color:var(--atg-text-muted);font-size:var(--atg-type-metadata-size);
  line-height:1.5;white-space:nowrap;}
.st-key-design_comercial_header button,
.st-key-design_comercial_filters button,
.st-key-design_comercial_table_footer button {
  min-height:44px;border-radius:var(--atg-radius-control);box-shadow:none;
  border:1px solid var(--atg-line-control);background:var(--atg-surface-card);
  color:var(--atg-ink);font-size:var(--atg-type-control-size);font-weight:600;
  padding:0 var(--atg-space-16);}
.st-key-design_comercial_header button p,
.st-key-design_comercial_filters button p,
.st-key-design_comercial_table_footer button p {
  font-size:var(--atg-type-control-size);font-weight:600;line-height:1.3;}
.st-key-design_comercial_header button:not(:disabled):hover,
.st-key-design_comercial_filters button:not(:disabled):hover,
.st-key-design_comercial_table_footer button:not(:disabled):hover {
  border-color:var(--atg-line-control-hover);color:var(--atg-brand);}
.st-key-design_comercial_header button:focus-visible,
.st-key-design_comercial_filters button:focus-visible,
.st-key-design_comercial_table_footer button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
.st-key-design_comercial_refresh button {
  background:var(--atg-side-bg);border-color:var(--atg-side-bg);color:var(--atg-side-text-strong);}
.st-key-design_comercial_refresh button:not(:disabled):hover {
  background:var(--atg-side-bg);color:var(--atg-side-text-strong);}
.st-key-design_comercial_header [data-testid="stIconMaterial"] {font-size:16px;}
.st-key-design_comercial_theme button {width:44px;min-width:44px;padding:0;}
.st-key-design_comercial_theme button p {font-size:20px;font-weight:400;}

/* Os widgets nativos conservam estados, rótulos e atalhos de teclado. */
.st-key-design_comercial_filters {
  min-width:0;container-type:inline-size;container-name:atg-comercial-filters;}
.st-key-design_comercial_filters [data-testid="stExpander"],
.st-key-design_comercial_quality [data-testid="stExpander"] {
  border:1px solid var(--atg-line-card);border-radius:var(--atg-radius-card);
  background:var(--atg-surface-card);box-shadow:var(--atg-shadow-card);min-width:0;}
.st-key-design_comercial_filters [data-testid="stExpander"] > details > summary,
.st-key-design_comercial_quality [data-testid="stExpander"] > details > summary {
  min-height:54px;padding:var(--atg-space-12) var(--atg-space-20);
  border-radius:var(--atg-radius-card);color:var(--atg-ink);}
.st-key-design_comercial_filters [data-testid="stExpander"] summary p,
.st-key-design_comercial_quality [data-testid="stExpander"] summary p {
  font-size:var(--atg-type-support-size);font-weight:700;line-height:1.4;}
.st-key-design_comercial_filters [data-testid="stExpanderDetails"],
.st-key-design_comercial_quality [data-testid="stExpanderDetails"] {
  padding:var(--atg-space-20);border-top:1px solid var(--atg-line-card);}
.st-key-design_comercial_filter_top {gap:var(--atg-space-20);}
.st-key-design_comercial_filter_top [data-testid="stHorizontalBlock"]:not(.st-key-design_comercial_toggles [data-testid="stHorizontalBlock"]) {
  display:grid;grid-template-columns:minmax(190px,.9fr) minmax(0,2.5fr) max-content;
  gap:var(--atg-space-20);align-items:end;}
.st-key-design_comercial_filter_top [data-testid="stColumn"],
.st-key-design_comercial_filter_dimensions [data-testid="stColumn"] {min-width:0;width:100%;}
.st-key-design_comercial_filters [data-testid="stWidgetLabel"] {margin:0 0 var(--atg-space-6);min-height:0;}
.st-key-design_comercial_filters [data-testid="stWidgetLabel"] p {
  color:var(--atg-text-meta);font-size:var(--atg-type-label-size);
  font-weight:600;letter-spacing:.06em;line-height:1.4;text-transform:uppercase;}
.st-key-design_comercial_filters [role="radiogroup"] {
  display:flex;padding:3px;gap:2px;border-radius:var(--atg-radius-control);
  background:var(--atg-surface-muted);width:max-content;max-width:100%;}
.st-key-design_comercial_filters [data-testid="stButtonGroup"] [role="radiogroup"] button {
  border:0;border-radius:var(--atg-radius-option);background:transparent;
  min-width:0;min-height:44px;padding:var(--atg-space-8) var(--atg-space-14);
  color:var(--atg-text-secondary);white-space:nowrap;flex:1 1 auto;}
.st-key-design_comercial_filters [data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] {
  background:var(--atg-brand);color:var(--atg-side-text-strong);}
.st-key-design_comercial_year [data-testid="stButtonGroup"] [role="radiogroup"] button {min-width:58px;}
.st-key-design_comercial_toggles [data-testid="stHorizontalBlock"] {
  display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.18fr);gap:var(--atg-space-20);}
.st-key-design_comercial_clear button p {display:flex;align-items:center;gap:var(--atg-space-8);}
.st-key-design_comercial_clear button p::before {
  content:"";width:16px;height:16px;flex-shrink:0;background:currentColor;
  mask:center/contain no-repeat url("data:image/svg+xml,ICON_FUNIL");}
.st-key-design_comercial_filter_dimensions [data-testid="stHorizontalBlock"] {
  display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:var(--atg-space-12);}
.st-key-design_comercial_filter_dimensions [data-testid="stPopover"] {width:100%;min-width:0;}
.st-key-design_comercial_filter_dimensions [data-testid="stPopover"] button {
  width:100%;max-width:100%;min-height:54px;justify-content:space-between;
  padding:var(--atg-space-10) var(--atg-space-12);
  border:1px solid var(--atg-line-control);background:var(--atg-surface-card);}
.st-key-design_comercial_filter_dimensions [data-testid="stPopover"] button p {
  white-space:normal;text-align:left;overflow-wrap:anywhere;line-height:1.4;}

/* Quatro métricas nativas, com os mesmos valores e legendas da página. */
.st-key-design_comercial_kpis {
  min-width:0;container-type:inline-size;container-name:atg-comercial-kpis;}
.st-key-design_comercial_kpis [data-testid="stHorizontalBlock"] {
  display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:var(--atg-space-16);align-items:stretch;}
.st-key-design_comercial_kpis [data-testid="stColumn"] {min-width:0;width:100%;}
.st-key-design_comercial_kpis :is(.st-key-design_comercial_kpi_vendas,.st-key-design_comercial_kpi_em_aberto,
  .st-key-design_comercial_kpi_cancelado,.st-key-design_comercial_kpi_alertas) {
  position:relative;height:100%;min-height:180px;padding:var(--atg-space-24) var(--atg-space-20);
  gap:var(--atg-space-10);background:var(--atg-surface-card);border:1px solid var(--atg-line-card);
  border-radius:var(--atg-radius-card);box-shadow:var(--atg-shadow-card);min-width:0;}
.st-key-design_comercial_kpis .atg-analytic-kpi-icon {
  display:flex;align-items:center;justify-content:center;
  width:44px;height:44px;border-radius:var(--atg-radius-tile);
  background:var(--atg-neutral-tile-bg);color:var(--atg-neutral-tile-fg);}
.st-key-design_comercial_kpis .stElementContainer:has(.atg-analytic-kpi-icon) {
  position:absolute;top:24px;left:20px;width:44px;height:44px;}
.st-key-design_comercial_kpi_vendas .atg-analytic-kpi-icon {
  background:var(--atg-brand-tint);color:var(--atg-brand);}
.st-key-design_comercial_kpi_em_aberto .atg-analytic-kpi-icon {
  background:var(--atg-warning-bg);color:var(--atg-warning);}
.st-key-design_comercial_kpis [data-testid="stMetric"] {min-width:0;}
.st-key-design_comercial_kpis [data-testid="stMetricLabel"] {
  min-height:44px;margin-bottom:var(--atg-space-10);padding-left:56px;}
.st-key-design_comercial_kpis [data-testid="stMetricLabel"] p {
  color:var(--atg-text-meta);font-size:var(--atg-type-label-size);font-weight:600;
  letter-spacing:.04em;line-height:1.35;text-transform:uppercase;white-space:normal;}
.st-key-design_comercial_kpis [data-testid="stMetricValue"] {
  color:var(--atg-ink);font-size:var(--atg-type-kpi-size);font-weight:800;
  letter-spacing:-.03em;line-height:1.2;white-space:nowrap;overflow:visible;text-overflow:clip;}
.st-key-design_comercial_kpis [data-testid="stMetricValue"] div {overflow:visible;text-overflow:clip;}
.st-key-design_comercial_kpi_vendas [data-testid="stMetricValue"] {color:var(--atg-brand);}
.st-key-design_comercial_kpi_em_aberto [data-testid="stMetricValue"] {color:var(--atg-warning);}
.st-key-design_comercial_kpi_cancelado [data-testid="stMetricValue"] {font-size:22px;}
.st-key-design_comercial_kpis [data-testid="stCaptionContainer"] p {
  color:var(--atg-text-muted);font-size:var(--atg-type-context-size);line-height:1.5;
  white-space:normal;overflow-wrap:anywhere;margin:0;}

/* Os quatro verificadores conservam título e contagem próprios. */
.st-key-design_comercial_quality {min-width:0;}
.st-key-design_comercial_quality [data-testid="stCaptionContainer"] p {
  color:var(--atg-text-muted);font-size:var(--atg-type-context-size);line-height:1.5;}
.st-key-design_comercial_quality .atg-analytic-alert {
  display:flex;align-items:center;gap:var(--atg-space-10);min-height:44px;
  padding:var(--atg-space-8) 0;color:var(--atg-ink);font-size:var(--atg-type-control-size);}
.st-key-design_comercial_quality .atg-analytic-alert-icon {
  display:flex;align-items:center;justify-content:center;width:24px;height:24px;flex-shrink:0;
  color:var(--atg-negative);background:var(--atg-negative-bg);border-radius:var(--atg-radius-pill);}
.st-key-design_comercial_quality .atg-analytic-alert-icon svg {width:14px;height:14px;}
.st-key-design_comercial_quality .atg-analytic-alert-inactive .atg-analytic-alert-icon {
  color:var(--atg-positive);background:var(--atg-positive-bg);}
.st-key-design_comercial_quality .atg-analytic-alert-title {
  color:var(--atg-ink);font-weight:700;line-height:1.5;min-width:0;overflow-wrap:anywhere;}
.st-key-design_comercial_quality .atg-analytic-alert-count {
  color:var(--atg-negative);font-size:16px;font-weight:700;white-space:nowrap;margin-left:auto;}
.st-key-design_comercial_quality .atg-analytic-alert-inactive .atg-analytic-alert-count {color:var(--atg-positive);}
.st-key-design_comercial_quality [data-testid="stHorizontalBlock"],
.st-key-design_comercial_quality [data-testid="stDataFrame"] {min-width:0;max-width:100%;}

/* Tabela e gráfico ocupam superfícies próprias; rolagem da tabela é interna. */
.st-key-design_comercial_status,.st-key-design_comercial_table {
  min-width:0;max-width:100%;padding:var(--atg-space-24);gap:var(--atg-space-16);
  background:var(--atg-surface-card);border:1px solid var(--atg-line-card);
  border-radius:var(--atg-radius-card);box-shadow:var(--atg-shadow-card);}
.st-key-design_comercial_status h3,.st-key-design_comercial_table h3 {
  color:var(--atg-ink);font-size:var(--atg-type-section-size);font-weight:800;
  letter-spacing:-.02em;line-height:1.3;margin:0;padding:0;}
.st-key-design_comercial_status [data-testid="stPlotlyChart"],
.st-key-design_comercial_table [data-testid="stDataFrame"] {min-width:0;max-width:100%;}
.st-key-design_comercial_table [data-testid="stWidgetLabel"] p {
  color:var(--atg-text-secondary);font-size:var(--atg-type-control-size);font-weight:600;
  line-height:1.5;white-space:normal;}
.st-key-design_comercial_table [data-testid="stTextInputRootElement"],
.st-key-design_comercial_table [data-baseweb="input"] {
  min-height:44px;border-radius:var(--atg-radius-control);background:var(--atg-surface-card);
  border-color:var(--atg-line-control);}
.st-key-design_comercial_table [data-testid="stTextInputRootElement"]:focus-within {
  border-color:var(--atg-brand);outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
.st-key-design_comercial_table [data-testid="stTextInput"] input {font-size:var(--atg-type-control-size);}
.st-key-design_comercial_table_footer {gap:var(--atg-space-16);}
.st-key-design_comercial_table_footer [data-testid="stCaptionContainer"] p {
  color:var(--atg-text-muted);font-size:var(--atg-type-context-size);margin:0;line-height:1.5;}

/* A largura útil considera sidebar e margens, não apenas a janela. */
@container atg-comercial-filters (width < 1080px) {
  .st-key-design_comercial_filter_top [data-testid="stHorizontalBlock"]:not(.st-key-design_comercial_toggles [data-testid="stHorizontalBlock"]) {
    grid-template-columns:minmax(0,1fr) minmax(0,2.6fr);}
  .st-key-design_comercial_filter_top [data-testid="stHorizontalBlock"]:not(.st-key-design_comercial_toggles [data-testid="stHorizontalBlock"]) > [data-testid="stColumn"]:last-child {
    grid-column:1/-1;justify-self:end;}
}
@container atg-comercial-filters (width < 980px) {
  .st-key-design_comercial_filter_dimensions [data-testid="stHorizontalBlock"] {
    grid-template-columns:repeat(3,minmax(0,1fr));}
}
@container atg-comercial-filters (width < 720px) {
  .st-key-design_comercial_filter_top [data-testid="stHorizontalBlock"]:not(.st-key-design_comercial_toggles [data-testid="stHorizontalBlock"]) {grid-template-columns:minmax(0,1fr);}
  .st-key-design_comercial_toggles [data-testid="stHorizontalBlock"] {grid-template-columns:minmax(0,1fr);}
  .st-key-design_comercial_filter_top [data-testid="stHorizontalBlock"]:not(.st-key-design_comercial_toggles [data-testid="stHorizontalBlock"]) > [data-testid="stColumn"]:last-child {
    grid-column:auto;justify-self:stretch;}
  .st-key-design_comercial_filters [role="radiogroup"] {width:100%;}
  .st-key-design_comercial_clear button {width:100%;}
}
@container atg-comercial-filters (width < 580px) {
  .st-key-design_comercial_filter_dimensions [data-testid="stHorizontalBlock"] {
    grid-template-columns:repeat(2,minmax(0,1fr));}
}
@container atg-comercial-kpis (width < 1040px) {
  .st-key-design_comercial_kpis [data-testid="stHorizontalBlock"] {
    grid-template-columns:repeat(2,minmax(0,1fr));}
}
@container atg-comercial-kpis (width < 600px) {
  .st-key-design_comercial_kpis [data-testid="stHorizontalBlock"] {grid-template-columns:minmax(0,1fr);}
}
@media(max-width:640px) {
  [data-testid="stMainBlockContainer"]:has(.st-key-design_comercial_header) {
    padding-left:var(--atg-space-16);padding-right:var(--atg-space-16);}
  .st-key-design_comercial_header {align-items:flex-start;}
  .st-key-design_comercial_actions {max-width:100%;gap:var(--atg-space-8);}
  .st-key-design_comercial_filters [data-testid="stExpanderDetails"],
  .st-key-design_comercial_quality [data-testid="stExpanderDetails"] {padding:var(--atg-space-16);}
  .st-key-design_comercial_status,.st-key-design_comercial_table {padding:var(--atg-space-16);}
  .st-key-design_comercial_table_footer button {width:100%;}
}
</style>
""".replace("ICON_FUNIL", _FUNIL)
