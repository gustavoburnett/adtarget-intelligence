"""Marca original e recursos locais da apresentação do login."""

import ast
import base64
import re
from pathlib import Path

from src.components import login, shell
from src.components.design_tokens import COLOR

ROOT = Path(__file__).resolve().parents[1]


def _contrato_autenticacao(fonte):
    """Retira somente os elementos visuais autorizados da guarda congelada."""
    def chamada_st(no, nomes):
        return (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                and isinstance(no.func.value, ast.Name) and no.func.value.id == 'st'
                and no.func.attr in nomes)

    class SemApresentacao(ast.NodeTransformer):
        def visit_ImportFrom(self, no):
            if no.module == 'src.components' and {nome.name for nome in no.names} == {'login', 'shell'}:
                return None
            return no

        def visit_Expr(self, no):
            if chamada_st(no.value, {'html', 'markdown', 'title', 'caption'}):
                return None
            return self.generic_visit(no)

        def visit_With(self, no):
            container_visual = all(chamada_st(item.context_expr, {'container'}) for item in no.items)
            no = self.generic_visit(no)
            return no.body if container_visual else no

        def visit_Call(self, no):
            # Somente estilo: nenhuma opção de sessão, callbacks ou submit
            # é liberada por esta exceção.
            if chamada_st(no, {'form'}):
                no.keywords = [kw for kw in no.keywords
                               if not (kw.arg == 'border' and isinstance(kw.value, ast.Constant)
                                       and kw.value.value is False)]
            elif chamada_st(no, {'form_submit_button'}):
                no.keywords = [kw for kw in no.keywords
                               if not (isinstance(kw.value, ast.Constant)
                                       and (kw.arg, kw.value.value) in {('type', 'primary'), ('width', 'stretch')})]
            return self.generic_visit(no)

    return ast.dump(SemApresentacao().visit(ast.parse(fonte)))


def test_login_usa_bytes_da_logo_oficial_sem_transformacao():
    html = login.header()
    encoded = re.search(r'src="data:image/svg\+xml;base64,([^"]+)"', html).group(1)
    assert base64.b64decode(encoded) == (ROOT / "assets/AdTarget_Intelligence_logo.svg").read_bytes()
    assert 'alt="AdTarget Intelligence"' in html
    assert 'width="220" height="99"' in html


def test_login_reutiliza_fonte_local_sem_pedido_a_servidor_externo():
    style = shell.font_style()
    encoded = re.search(r'data:font/woff2;base64,([^\"]+)', style).group(1)
    assert base64.b64decode(encoded) == (ROOT / "static/fonts/InterVariable.woff2").read_bytes()
    assert "https://" not in style + login.header() + login.CSS_LOGIN


def test_regras_css_do_login_sao_limitadas_a_marcadores_da_tela():
    css = re.sub(r'/\*.*?\*/', '', login.CSS_LOGIN, flags=re.S).removeprefix('<style>').removesuffix('</style>\n')
    rules = re.findall(r'([^{}]+)\{[^{}]*\}', css)
    selectors = [selector.strip() for rule in rules for selector in rule.split(',')
                 if not rule.strip().startswith(':root')]
    assert selectors
    assert all('design_login_' in selector or 'atg-login-' in selector for selector in selectors)
    assert 'position:fixed' not in css and 'overflow:hidden' not in css


def test_tokens_de_contraste_do_login():
    def luminance(value):
        rgb = [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= .04045 else ((channel + .055) / 1.055) ** 2.4
                  for channel in rgb]
        return sum(channel * weight for channel, weight in zip(linear, (.2126, .7152, .0722)))

    for foreground, background in (
        ('ink', 'surface-card'), ('text-secondary', 'surface-card'),
        ('identity-white', 'brand'), ('side-text', 'side-bg'),
        ('negative-label', 'negative-surface'),
    ):
        values = sorted((luminance(COLOR[foreground]), luminance(COLOR[background])))
        assert (values[1] + .05) / (values[0] + .05) >= 4.5
