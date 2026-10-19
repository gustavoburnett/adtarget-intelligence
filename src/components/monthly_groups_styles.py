"""Apresentação isolada do Checkpoint 2B, com tokens do Design System 1.0.1."""

CSS = """<style>
.st-key-design_group_monthly {
  container-type:inline-size;container-name:atg-group-monthly;
  min-width:0;padding:var(--atg-space-32);margin:var(--atg-space-8) 0 var(--atg-space-24);
  border:1px solid var(--atg-line-card);border-radius:var(--atg-radius-card);
  background:var(--atg-surface-card);box-shadow:var(--atg-shadow-card);}
.st-key-design_group_monthly,.st-key-design_group_monthly * {box-sizing:border-box;min-width:0;}
.st-key-design_group_monthly .atg-group-title {
  color:var(--atg-ink);font-size:var(--atg-type-section-size);font-weight:800;
  letter-spacing:-.02em;line-height:1.3;margin:0 0 var(--atg-space-6);}
.st-key-design_group_monthly .atg-group-copy {
  color:var(--atg-text-muted);font-size:var(--atg-type-context-size);line-height:1.5;
  margin:0;overflow-wrap:anywhere;}
.st-key-design_group_monthly .atg-group-label {
  color:var(--atg-text-muted);font-size:var(--atg-type-label-size);font-weight:600;
  letter-spacing:.05em;line-height:1.5;text-transform:uppercase;}
.st-key-group_monthly_header {align-items:center;gap:var(--atg-space-24);}
.st-key-group_monthly_heading {flex:0 1 auto;}
.st-key-group_monthly_header > div:has(> .st-key-group_monthly_heading) {flex:1 1 440px;}
.st-key-group_monthly_header > div:has(> .st-key-group_monthly_picker) {flex:0 1 216px;}
.st-key-group_monthly_picker {width:216px;max-width:100%;}
.st-key-group_monthly_picker [data-testid="stWidgetLabel"] p {
  font-size:var(--atg-type-label-size);font-weight:600;color:var(--atg-text-muted);
  text-transform:uppercase;letter-spacing:.05em;}
.st-key-design_group_monthly [data-baseweb="select"] > div {
  background:var(--atg-surface-card);border-color:var(--atg-line-control);
  border-radius:var(--atg-radius-control);min-height:44px;font-size:var(--atg-type-control-size);}
.st-key-design_group_monthly :is(button,[role="combobox"]):focus-visible {
  outline:2px solid var(--atg-focus-ring);outline-offset:2px;}
.atg-group-summary {display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.85fr);
  gap:var(--atg-space-32);padding:var(--atg-space-24) 0 var(--atg-space-28);
  border-bottom:1px solid var(--atg-line-card);color:var(--atg-ink);}
.atg-group-ytd {padding-right:var(--atg-space-32);border-right:1px solid var(--atg-line-card);}
.atg-group-identity {display:flex;align-items:center;flex-wrap:wrap;gap:var(--atg-space-12);
  margin-bottom:var(--atg-space-12);}
.atg-group-badge {display:inline-block;border-radius:var(--atg-radius-pill);padding:4px 10px;
  font-size:var(--atg-type-badge-size);font-weight:600;line-height:1.4;max-width:100%;overflow-wrap:anywhere;}
.atg-group-badge.positive {color:var(--atg-positive);background:var(--atg-positive-bg);}
.atg-group-badge.negative {color:var(--atg-negative);background:var(--atg-negative-bg);}
.atg-group-badge.neutral {color:var(--atg-text-muted);background:var(--atg-surface-muted);}
.atg-group-ytd-number {font-size:var(--atg-type-hero-size);font-weight:800;line-height:1.1;
  letter-spacing:-.04em;margin:var(--atg-space-8) 0 var(--atg-space-12);}
.atg-group-ytd-number.negative {color:var(--atg-negative);}
.atg-group-ytd-number.positive {color:var(--atg-positive);}
.atg-group-ytd-number.neutral {color:var(--atg-text-muted);font-size:28px;letter-spacing:-.02em;}
.atg-group-summary strong {color:var(--atg-ink);font-weight:700;}
.atg-group-ytd-track {height:8px;position:relative;border-radius:99px;background:var(--atg-surface-muted);
  margin:var(--atg-space-24) 0 var(--atg-space-12);}
.atg-group-ytd-track > span {display:block;height:100%;border-radius:99px;background:var(--atg-brand);}
.atg-group-ytd-track::after {content:"";position:absolute;left:80%;top:-4px;height:16px;
  border-left:2px solid var(--atg-text-muted);}
.atg-group-ruler {text-align:right;font-size:var(--atg-type-label-size);color:var(--atg-text-muted);}
.atg-group-annual-line {display:flex;align-items:baseline;flex-wrap:wrap;gap:var(--atg-space-12);
  justify-content:space-between;margin:var(--atg-space-8) 0 var(--atg-space-16);}
.atg-group-annual-number {font-size:36px;line-height:1.2;font-weight:800;letter-spacing:-.035em;}
.atg-group-annual-number .num {white-space:normal;}
.atg-group-annual-number small {font-size:var(--atg-type-support-size);font-weight:600;letter-spacing:0;}
.atg-group-annual-track {display:flex;height:26px;border-radius:99px;background:var(--atg-surface-muted);overflow:hidden;}
.atg-group-annual-track span {flex:none;height:100%;}
.atg-group-closed {background:var(--atg-brand);}
.atg-group-open {background:color-mix(in srgb,var(--atg-brand) 48%,white);}
.atg-group-gap {background:repeating-linear-gradient(135deg,transparent,transparent 3px,var(--atg-line-control-hover) 3px,var(--atg-line-control-hover) 4px);}
.atg-group-key {display:flex;align-items:center;flex-wrap:wrap;gap:var(--atg-space-8) var(--atg-space-16);
  margin:var(--atg-space-10) 0;color:var(--atg-text-muted);font-size:var(--atg-type-label-size);line-height:1.5;}
.atg-group-key-item {display:inline-flex;align-items:center;gap:var(--atg-space-6);}
.atg-group-swatch {display:inline-block;width:13px;height:13px;flex:none;border-radius:3px;}
.atg-group-gap-copy {font-size:var(--atg-type-support-size);margin:var(--atg-space-12) 0;color:var(--atg-ink);}
.atg-group-outside {margin-top:var(--atg-space-16);padding-top:var(--atg-space-12);
  border-top:1px solid var(--atg-line-card);font-size:var(--atg-type-context-size);line-height:1.5;color:var(--atg-text-secondary);}
.st-key-group_monthly_body {margin-top:var(--atg-space-16);}
.st-key-group_monthly_plot_title {flex:0 1 auto;}
.st-key-group_monthly_chart_controls > div:has(> .st-key-group_monthly_plot_title) {flex:1 1 180px;}
.st-key-group_monthly_chart_controls {align-items:center;gap:var(--atg-space-12);}
.st-key-design_group_monthly [role="radiogroup"] {
  padding:3px;gap:2px;border-radius:var(--atg-radius-control);background:var(--atg-surface-muted);}
.st-key-design_group_monthly [data-testid="stButtonGroup"] [role="radiogroup"] button {
  min-height:44px;border:0;background:transparent;border-radius:var(--atg-radius-option);
  padding:var(--atg-space-8) var(--atg-space-12);color:var(--atg-text-secondary);font-size:var(--atg-type-control-size);}
.st-key-design_group_monthly [data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] {
  color:var(--atg-side-text-strong);background:var(--atg-brand);}
.st-key-design_group_monthly [data-testid="stButtonGroup"] button p {font-size:var(--atg-type-control-size);font-weight:600;}
.st-key-group_monthly_chart_mobile {display:none;}
.st-key-group_monthly_vehicle {padding-left:var(--atg-space-24);border-left:1px solid var(--atg-line-card);}
.atg-group-vehicles {margin-top:var(--atg-space-16);color:var(--atg-ink);}
.atg-group-vehicle-stack {display:flex;height:14px;overflow:hidden;border-radius:99px;margin-bottom:var(--atg-space-16);}
.atg-group-vehicle-row {display:grid;grid-template-columns:minmax(72px,1fr) minmax(40px,.8fr) auto;
  align-items:center;gap:var(--atg-space-8);padding:var(--atg-space-8) 0;font-size:var(--atg-type-control-size);}
.atg-group-vehicle-name {font-weight:600;overflow-wrap:anywhere;}
.atg-group-vehicle-row strong {font-weight:700;white-space:nowrap;}
.atg-group-vehicle-value {text-align:right;}
.atg-group-vehicle-pct {font-weight:400;color:var(--atg-text-muted);font-size:var(--atg-type-label-size);}
.atg-group-vehicle-bar {height:7px;background:var(--atg-surface-muted);border-radius:99px;}
.atg-group-vehicle-bar span {display:block;height:100%;border-radius:99px;}
.atg-group-total {display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:var(--atg-space-8);
  border-top:1px solid var(--atg-line-card);padding-top:var(--atg-space-16);margin:var(--atg-space-16) 0;color:var(--atg-text-muted);
  font-size:var(--atg-type-control-size);}
.atg-group-total strong {color:var(--atg-ink);}
.atg-group-detail {background:var(--atg-surface-muted);border-radius:var(--atg-radius-control);
  padding:var(--atg-space-16);margin:var(--atg-space-12) 0;color:var(--atg-ink);}
.atg-group-detail-head {display:flex;justify-content:space-between;flex-wrap:wrap;gap:var(--atg-space-8);margin-bottom:var(--atg-space-10);}
.atg-group-detail dl {margin:0;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:var(--atg-space-8);font-size:var(--atg-type-control-size);}
.atg-group-detail dt {color:var(--atg-text-secondary);}
.atg-group-detail dd {margin:0;text-align:right;font-weight:700;}
.atg-group-detail dd .num {white-space:normal;}
.st-key-design_group_monthly p.atg-group-footnote {font-size:var(--atg-type-label-size);color:var(--atg-text-muted);line-height:1.5;margin:var(--atg-space-12) 0 0;}
@container atg-group-monthly (width < 900px) {
  .st-key-group_monthly_body > div > [data-testid="stHorizontalBlock"] {flex-direction:column;gap:var(--atg-space-24);}
  .st-key-group_monthly_body > div > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width:100%;flex:1 1 100%;}
  .st-key-group_monthly_vehicle {padding-left:0;padding-top:var(--atg-space-24);border-left:0;border-top:1px solid var(--atg-line-card);}
}
@container atg-group-monthly (width < 640px) {
  .atg-group-summary {grid-template-columns:minmax(0,1fr);gap:var(--atg-space-24);}
  .atg-group-ytd {padding:0 0 var(--atg-space-24);border-right:0;border-bottom:1px solid var(--atg-line-card);}
  .atg-group-ytd-number {font-size:48px;}
  .atg-group-annual-number {font-size:30px;}
  .st-key-group_monthly_chart_desktop {display:none;}
  .st-key-group_monthly_chart_mobile {display:block;}
}
@media(max-width:640px) {
  .st-key-design_group_monthly {padding:var(--atg-space-20);}
  .st-key-group_monthly_picker {width:100%;}
  .st-key-group_monthly_header > div:has(> .st-key-group_monthly_picker) {flex:1 1 100%;}
  .st-key-group_monthly_header {gap:var(--atg-space-16);}
}
</style>"""
