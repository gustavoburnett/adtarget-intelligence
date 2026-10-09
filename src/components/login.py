"""Apresentação do login; não consulta credenciais nem estado de autenticação."""

from base64 import b64encode
from functools import lru_cache
from pathlib import Path

from src.components.design_tokens import css_variables

_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def header() -> str:
    """Incorpora a marca oficial positiva, sem modificar o SVG."""
    logo = b64encode((_ROOT / "assets/AdTarget_Intelligence_logo.svg").read_bytes()).decode("ascii")
    return (
        '<div class="atg-login-heading">'
        f'<img src="data:image/svg+xml;base64,{logo}" '
        'alt="AdTarget Intelligence" width="220" height="99">'
        '<h1>Bem-vindo ao Intelligence</h1>'
        '<p>Informe sua senha para continuar.</p></div>'
    )


EDITORIAL = '<p class="atg-login-editorial">Dados que impulsionam grandes negócios.</p>'

# O marcador deixa de existir após a autenticação. Nenhum seletor visual do
# login atua nas páginas protegidas, inclusive durante a troca de sessão.
CSS_LOGIN = "<style>" + css_variables() + """
.stApp:has(.st-key-design_login_card),
.stApp:has(.st-key-design_login_card) [data-testid="stAppViewContainer"],
.stApp:has(.st-key-design_login_card) [data-testid="stMain"] {
  background:var(--atg-side-bg);}
.stApp:has(.st-key-design_login_card) header[data-testid="stHeader"] {display:none;}
.stApp:has(.st-key-design_login_card) [data-testid="stMainBlockContainer"] {
  max-width:none;padding:var(--atg-space-32) var(--atg-space-24);}
.stApp:has(.st-key-design_login_card) [data-testid="stMainBlockContainer"]
  > [data-testid="stVerticalBlock"] {
  min-height:calc(100vh - 64px);min-height:calc(100dvh - 64px);
  justify-content:center;gap:0;}
.st-key-design_login_stage {
  width:100%;max-width:440px;margin-inline:auto;gap:var(--atg-space-24);}
.st-key-design_login_card {
  background:var(--atg-surface-card);border:1px solid var(--atg-line-card);
  border-radius:var(--atg-radius-card);padding:var(--atg-space-40);
  box-shadow:var(--atg-shadow-card);gap:var(--atg-space-24);}
.st-key-design_login_stage, .st-key-design_login_stage input,
.st-key-design_login_stage button, .st-key-design_login_stage p,
.st-key-design_login_stage h1 {font-family:var(--atg-font);}
.atg-login-heading {text-align:center;}
.atg-login-heading img {
  display:block;width:220px;max-width:100%;height:auto;margin:0 auto var(--atg-space-28);}
.atg-login-heading h1 {
  font-size:22px;font-weight:600;letter-spacing:-.025em;line-height:1.3;
  color:var(--atg-ink);margin:0 0 var(--atg-space-10);padding:0;}
.atg-login-heading p {
  font-size:var(--atg-type-support-size);line-height:1.5;
  color:var(--atg-text-secondary);margin:0;}
.st-key-design_login_card [data-testid="stForm"] {
  border:0;padding:0;gap:var(--atg-space-20);}
.st-key-design_login_card [data-testid="stForm"] > [data-testid="stVerticalBlock"] {
  gap:var(--atg-space-20);}
.st-key-design_login_card [data-testid="stWidgetLabel"] p {
  color:var(--atg-text-secondary);font-size:var(--atg-type-support-size);font-weight:500;}
.st-key-design_login_card [data-testid="stTextInputRootElement"] {
  border:1px solid var(--atg-line-control);border-radius:var(--atg-radius-control);
  background:var(--atg-surface-card);min-height:52px;}
.st-key-design_login_card [data-testid="stTextInputRootElement"]:focus-within {
  border-color:var(--atg-focus-ring);box-shadow:0 0 0 1px var(--atg-focus-ring);}
.st-key-design_login_card [data-testid="stTextInputRootElement"] input {
  color:var(--atg-ink);font-size:16px;min-height:50px;}
.st-key-design_login_card [data-testid="stTextInputRootElement"] button {
  min-width:44px;min-height:50px;color:var(--atg-text-secondary);}
.st-key-design_login_card [data-testid="stTextInputRootElement"] button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:-4px;}
.st-key-design_login_card [data-testid="stFormSubmitButton"] button {
  width:100%;min-height:48px;border-radius:var(--atg-radius-control);
  background:var(--atg-brand);border:1px solid var(--atg-brand);
  color:var(--atg-identity-white);font-weight:600;font-size:var(--atg-type-support-size);}
.st-key-design_login_card [data-testid="stFormSubmitButton"] button:hover {
  background:var(--atg-side-bg);border-color:var(--atg-side-bg);}
.st-key-design_login_card [data-testid="stFormSubmitButton"] button:focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:3px;}
.st-key-design_login_card [data-testid="stAlert"] {
  background:var(--atg-negative-surface);color:var(--atg-negative-label);
  border:1px solid var(--atg-negative-border);border-radius:var(--atg-radius-control);}
.st-key-design_login_card [data-testid="stAlert"] p {
  color:var(--atg-negative-label);font-size:var(--atg-type-context-size);}
.st-key-design_login_stage .atg-login-editorial {
  color:var(--atg-side-text);font-size:var(--atg-type-context-size);
  text-align:center;line-height:1.5;margin:0;}
@media(max-width:640px) {
  .stApp:has(.st-key-design_login_card) [data-testid="stMainBlockContainer"] {
    padding:var(--atg-space-24) var(--atg-space-20);}
  .stApp:has(.st-key-design_login_card) [data-testid="stMainBlockContainer"]
    > [data-testid="stVerticalBlock"] {
    min-height:calc(100vh - 48px);min-height:calc(100dvh - 48px);}
  .st-key-design_login_card {padding:var(--atg-space-28) var(--atg-space-24);}
  .atg-login-heading img {width:200px;margin-bottom:var(--atg-space-24);}
  .atg-login-heading h1 {font-size:20px;}
}
</style>
"""
