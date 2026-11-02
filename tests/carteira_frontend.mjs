// Run with Node: node tests/carteira_frontend.mjs
// Exercises the actual inline script, using a minimal DOM for its output strings.
// It does not replace browser, keyboard, or screen-reader acceptance tests.
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';

export async function loadFrontend(data, {referrer='https://example.test/',frameUrl='https://example.test/',blockedParent=false,templateURL=new URL('../src/components/carteira_b.html',import.meta.url)}={}) {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      innerHTML:'', textContent:'', value:'', open:false, hidden:false,
      querySelector:selector=>element(id+selector), querySelectorAll:()=>[],
      addEventListener(){}, setAttribute(){}, removeAttribute(){},
      showModal(){this.open=true;}, close(){this.open=false;},
      after(){}, remove(){}, focus(){}, scrollIntoView(){},
    });
    return elements.get(id);
  }
  const root=element('root');
  root.querySelector=selector=>element(selector.replace('#atg-',''));
  const storage=new Map();
  globalThis.document={getElementById:()=>root,createElement:()=>element('new'),referrer};
  globalThis.location={href:frameUrl,hash:''};
  globalThis.window={location:globalThis.location,history:{replaceState(){}},addEventListener(){}};
  window.parent=blockedParent?{get location(){throw new Error('Cross-origin frame')}}:window;
  globalThis.matchMedia=()=>({matches:false});
  globalThis.sessionStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};
  data.appUrl ??= 'https://example.test/';
  globalThis.__carteiraData=data;
  let source=await readFile(templateURL,'utf8');
  source=source.slice(source.lastIndexOf('<script>')+8,source.lastIndexOf('</script>'));
  source=source.replace('const DATA=__CARTEIRA_DATA__;','const DATA=globalThis.__carteiraData;');
  const end=source.lastIndexOf('})();');
  source=source.slice(0,end)+'globalThis.__carteiraAudit={state,calc,selected,render,renderDetail,restore,remember,esc};\n'+source.slice(end);
  const dir=await mkdtemp(join(tmpdir(),'carteira-frontend-'));
  try {
    const file=join(dir,'script.mjs');
    await writeFile(file,source);
    await import(pathToFileURL(file).href);
    return {api:globalThis.__carteiraAudit,elements,storage};
  } finally { await rm(dir,{recursive:true,force:true}); }
}

export async function verifyPayload(data, options) {
  const {api,elements}=await loadFrontend(data, options);
  let slices=0,renderedPartners=0;
  const close=(a,b)=>assert.ok(Math.abs(a-b)<0.00001,`${a} != ${b}`);
  for (const [key,expected] of Object.entries(data.slices)) {
    const parts=key.split('|');
    const year=Number(parts.shift()), grain=Number(parts.pop()), month=Number(parts.pop()), partner=parts.join('|');
    Object.assign(api.state,{year,month,grain,partner,detail:null});
    const ms=Array.from({length:grain},(_,i)=>month+i);
    const got=api.calc(ms,partner);
    assert.deepEqual(got,expected,`slice lookup ${key}`);
    const rows=data.rows.filter(r=>r.year===year&&ms.includes(r.month)&&(!partner||r.group===partner));
    close(got.total,rows.reduce((s,r)=>s+r.value,0));
    close(got.inside,rows.filter(r=>r.inside).reduce((s,r)=>s+r.value,0));
    close(got.out,rows.filter(r=>!r.inside).reduce((s,r)=>s+r.value,0));
    assert.equal(api.selected(ms,year,partner).length,rows.length);
    if (!partner) {
      api.render();
      for (const g of data.groupsByYear[String(year)]) {
        assert.ok(elements.get('partners').innerHTML.includes('class="atg-name">'+api.esc(g)),`missing/unsafe partner ${g}`);
        renderedPartners++;
      }
    }
    slices++;
  }
  for (const row of data.rows) assert.ok(data.groupsByYear[String(row.year)].includes(row.group),'sale partner absent from selector');
  return {slices,renderedPartners};
}

export async function verifySpecialNames() {
  let cases=0;
  for (const name of ['A&B',"O'NEILL",'A"B','<b>PARCEIRO</b>','CARREGA+ (DF/RJ)','ÁGUA — 日本','A|B']) {
    const c={total:5000,inside:5000,out:0,target:10000,gap:5000,coverage:50,old:0,hasOld:false,partial:false,missing:[],inactive:false};
    const slices={};
    for(const grain of [1,3,6,12])for(let m=1;m<=12;m+=grain)for(const g of ['',name]) slices[`2026|${g}|${m}|${grain}`]={...c,total:m===1?5000:0,inside:m===1?5000:0};
    const data={reference:'2026-01-15',years:[2026],groupsByYear:{2026:[name]},rows:[{year:2026,month:1,group:name,vehicle:name,client:name,agency:name,campaign:name,status:'FATURADO',value:5000,inside:true,pi:'1'}],slices};
    const {api,elements,storage}=await loadFrontend(data);
    assert.equal(api.calc([1],name).total,5000,'special name must retain financial values');
    assert.ok(elements.get('partners').innerHTML.includes('class="atg-name">'+api.esc(name)),'partner table must escape source names');
    assert.ok(!elements.get('partners').innerHTML.includes('<b>PARCEIRO</b>'),'source markup must remain text');
    assert.ok(!new URL(elements.get('context-link').href).searchParams.get('carteira').includes('undefined'),'initial context must not invent a status');
    Object.assign(api.state,{detail:name,vehicle:name,client:name,agency:name,campaign:name,status:'FATURADO'});
    api.renderDetail();
    assert.ok(elements.get('pis').innerHTML.includes('1 PI · subtotal filtrado'),'combined filters must keep the matching PI');
    assert.ok(elements.get('vehicle').innerHTML.includes(api.esc(name)),'vehicle option must preserve escaped text');
    api.remember();
    const context=new URL(elements.get('context-link').href).searchParams.get('carteira');
    storage.clear(); data.context=context;
    Object.assign(api.state,{detail:null,partner:'',vehicle:'',client:'',agency:'',campaign:'',status:''});
    api.restore();
    assert.equal(api.state.vehicle,name); assert.equal(api.state.status,'FATURADO');
    api.renderDetail();
    assert.ok(elements.get('pis').innerHTML.includes('1 PI · subtotal filtrado'));
    storage.clear(); data.context='status=undefined'; api.restore();
    assert.equal(api.state.status,'','legacy undefined status must not hide PIs');
    cases++;
  }
  return {cases};
}

export const specialNamesResult=await verifySpecialNames();
