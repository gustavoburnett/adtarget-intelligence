"""Fundação do shell Design 1B; não estiliza KPIs, Radar, gráficos ou filtros."""

from src.components.design_tokens import css_variables

CSS_SHELL = "<style>" + css_variables() + """
/* Fundação tipográfica: tamanhos e cores do conteúdo legado preservados. */
.stApp, .stApp input, .stApp textarea, .stApp select, .stApp button,
.stApp [data-testid="stMarkdownContainer"],
[class^="atg-"], [class^="atg-"] * {font-family:var(--atg-font);}
.stApp, .num {font-variant-numeric:tabular-nums;}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background:var(--atg-surface-page);}
[data-testid="stMainBlockContainer"] {
  padding-top:var(--atg-space-40);padding-bottom:var(--atg-space-56);}
/* A largura e o recolhimento continuam sob controle nativo do Streamlit. */
section[data-testid="stSidebar"] {background:var(--atg-side-bg);}
[data-testid="stSidebarContent"] {padding-left:0;padding-right:0;}
[data-testid="stSidebarHeader"] {
  position:absolute;top:var(--atg-space-8);right:var(--atg-space-8);
  width:44px;height:44px;margin:0;z-index:1;}
[data-testid="stSidebarHeader"] [data-testid="stLogoSpacer"] {display:none;}
[data-testid="stSidebarCollapseButton"] {visibility:visible;margin-left:0;}
[data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {
  color:var(--atg-side-text);}
[data-testid="stSidebarUserContent"] {padding:var(--atg-space-32) var(--atg-space-20);}
.st-key-design_sidebar_shell {min-height:calc(100dvh - 64px);gap:0;}
.st-key-design_sidebar_brand {margin-bottom:var(--atg-space-32);}
.atg-sidebar-brand {padding:var(--atg-space-8);}
.atg-sidebar-brand img {display:block;width:160px;min-width:120px;max-width:100%;height:auto;}
.st-key-design_sidebar_nav [role="radiogroup"] {gap:var(--atg-space-4);}
.st-key-design_sidebar_nav [role="radiogroup"] label {
  display:flex;align-items:center;min-height:44px;width:100%;margin:0;
  padding:var(--atg-space-12) var(--atg-space-14);
  border-left:3px solid transparent;border-radius:var(--atg-radius-control);
  cursor:pointer;color:var(--atg-side-text);}
/* Somente o indicador desenhado; o input nativo continua focável e selecionável. */
.st-key-design_sidebar_nav label div:has(> [data-testid="stMarkdownContainer"])
  > div:not([data-testid="stMarkdownContainer"]) {display:none;}
.st-key-design_sidebar_nav [role="radiogroup"] label p {
  display:flex;align-items:center;gap:var(--atg-space-12);
  margin:0;font-size:var(--atg-type-navigation-size);
  font-weight:var(--atg-type-navigation-weight);line-height:1.3;
  color:var(--atg-side-text);white-space:normal;overflow-wrap:normal;}
.st-key-design_sidebar_nav [role="radiogroup"] label p img {
  width:18px;height:18px;max-height:none;vertical-align:middle;
  flex-shrink:0;}
.st-key-design_sidebar_nav [role="radiogroup"] label:hover {
  background:var(--atg-side-hover);}
.st-key-design_sidebar_nav [role="radiogroup"] label:hover p {
  color:var(--atg-side-text-strong);}
.st-key-design_sidebar_nav [role="radiogroup"] label:has(input:checked) {
  background:var(--atg-side-active);border-left-color:var(--atg-brand-accent);}
.st-key-design_sidebar_nav [role="radiogroup"] label:has(input:checked) p {
  color:var(--atg-side-text-strong);}
/* Somente ícones decorativos da navegação; a marca nunca recebe filtros. */
.st-key-design_sidebar_nav label:hover p img,
.st-key-design_sidebar_nav label:has(input:checked) p img {filter:brightness(0) invert(1);}
.st-key-design_sidebar_nav [role="radiogroup"] label:has(input:checked):not(:has(input:focus-visible)) {
  outline:none;box-shadow:none;}
.st-key-design_sidebar_nav [role="radiogroup"] label:has(input:focus-visible) {
  outline:2px solid var(--atg-focus-ring-dark);outline-offset:2px;}
[data-testid="stSidebar"] button {
  color:var(--atg-side-text);min-width:44px;min-height:44px;}
[data-testid="stSidebar"] button:hover {color:var(--atg-side-text-strong);}
[data-testid="stSidebar"] button:focus-visible {
  outline:2px solid var(--atg-focus-ring-dark);outline-offset:2px;}
header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] button {
  min-width:44px;min-height:44px;}
.st-key-design_sidebar_shell > [data-testid="stLayoutWrapper"]:has(> .st-key-design_sidebar_footer) {
  margin-top:auto;}
.st-key-design_sidebar_footer {padding-top:var(--atg-space-40);}
.atg-sidebar-footer .atg-status-line {
  color:var(--atg-side-text-muted);font-size:var(--atg-type-metadata-size);line-height:1.5;
  white-space:normal;align-items:flex-start;}
.atg-sidebar-footer .atg-status-dot {
  width:7px;height:7px;background:var(--atg-brand-accent);box-shadow:none;margin-top:5px;}
.atg-sidebar-editorial {border-top:1px solid var(--atg-side-divider);
  margin-top:var(--atg-space-20);padding-top:var(--atg-space-24);}
.atg-sidebar-editorial p.atg-sidebar-quote {
  color:var(--atg-side-text-strong);font-size:var(--atg-type-sidebar-quote-size);
  font-weight:var(--atg-type-sidebar-quote-weight);
  line-height:1.25;letter-spacing:-.01em;margin:0 0 var(--atg-space-20);}
.atg-sidebar-editorial p.atg-sidebar-identification {
  color:var(--atg-side-text-muted);font-size:var(--atg-type-sidebar-identification-size);font-weight:400;
  line-height:1.5;margin:0;}
@media(max-width:640px) {
  [data-testid="stSidebarUserContent"] {padding-top:var(--atg-space-20);}
  [data-testid="stMainBlockContainer"] {padding-top:var(--atg-space-32);}
  .st-key-design_sidebar_shell {min-height:calc(100dvh - 52px);}
}
</style>
"""
