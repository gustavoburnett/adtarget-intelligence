// Actual template restoration and share-link roundtrips; no browser emulation.
import assert from 'node:assert/strict';
import {loadFrontend} from './carteira_frontend.mjs';
const name="Água & O'Neill + 日本 / %";
const slices={};
for(const grain of [1,3,6,12])for(let m=1;m<=12;m+=grain)for(const group of ['',name])slices[`2026|${group}|${m}|${grain}`]={total:0,inside:0,out:0,target:null,gap:null,coverage:null,old:0,hasOld:false,partial:false,missing:[],inactive:false};
const data={reference:'2026-04-15',years:[2026],groupsByYear:{2026:[name]},rows:[],slices};
let count=0;
for(const grain of [1,3,6,12]){
 const context=new URLSearchParams({grain,month:7,year:2026,partner:name,detail:name,client:'A&B + %',agency:'Água',vehicle:'日本',campaign:'a=b?c#d',scope:'out',status:'FATURADO'}).toString();
 // A fresh loader has no sessionStorage: separate profiles / reload.
 for(let profile=0;profile<3;profile++){
  const {api,elements}=await loadFrontend({...data,context});
  for(const [key,value] of new URLSearchParams(context))assert.equal(String(api.state[key]),value);
  const shared=new URL(elements.get('context-link').href);
  assert.equal(shared.origin,'https://example.test');
  assert.equal(new URLSearchParams(shared.searchParams.get('carteira')).get('partner'),name);
  count++;
 }
}
for(const context of ['grain=NaN&year=0&month=99&partner=unknown&detail=unknown&scope=bad&status=undefined','https://evil.invalid/','%','']){
 const {api,elements}=await loadFrontend({...data,context});
 assert.equal(api.state.grain,1);assert.equal(api.state.year,2026);
 assert.ok(api.state.month>=1&&api.state.month<=12);
 assert.equal(api.state.partner,'');assert.equal(api.state.detail,null);
 assert.equal(api.state.status,'');assert.equal(api.state.scope,'all');
 assert.equal(new URL(elements.get('context-link').href).origin,'https://example.test');count++;
}
export const result={cases:count};
