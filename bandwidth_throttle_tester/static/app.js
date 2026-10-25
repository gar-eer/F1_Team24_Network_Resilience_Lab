'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let meta, phases = [], mode = 'compare', useFile = false, fileReady = false, job = null, jobId = null, selected = null, polling = false, busy = false;
const fmt = (v, places=1) => v == null ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits:places,minimumFractionDigits:places});
const bytes = n => n == null ? '—' : n >= 1048576 ? `${fmt(n/1048576,2)} MiB` : `${fmt(n/1024,1)} KiB`;
function toast(message){ $('toast').textContent = message; $('toast').hidden = false; }
$('toast').onclick=()=>{$('toast').hidden=true;};
async function api(path, options){
 const response = await fetch(path, options);
 const data = await response.json();
 if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
 return data;
}
function editPhases(){
 $('phase-preview').innerHTML = phases.map((p,i)=>`${i?'<i>→</i>':''}<span class="${p.kbps===0?'outage-phase':''}">${p.kbps===0?'Offline':p.kbps>=1000?`${fmt(p.kbps/1000, p.kbps%1000?2:0)} Mbps`:`${p.kbps} kbps`}<small>t = ${p.at}s</small></span>`).join('');
 $('phase-editor').innerHTML = phases.map((p,i)=>`<div class="phase-row"><input type="number" min="0" max="3600" step="0.1" value="${p.at}" aria-label="Phase ${i+1} start seconds" data-index="${i}" data-field="at"><input type="number" min="0" max="100000" step="1" value="${p.kbps}" aria-label="Phase ${i+1} bandwidth kbps" data-index="${i}" data-field="kbps"><button type="button" data-remove="${i}" aria-label="Remove phase ${i+1}">×</button></div>`).join('');
 $('scenario-hint').textContent = $('scenario').value === 'demo' ? '2 Mbps → 256 kbps → 5s outage → restored. Use 2 MiB or larger to experience every phase.' : 'Each strategy starts at t=0 under the same schedule.';
}
$('phase-editor').addEventListener('change', e=>{
 if(!e.target.dataset.field)return;
 phases[Number(e.target.dataset.index)][e.target.dataset.field] = Number(e.target.value);
 $('scenario').value='custom'; editPhases();
});
$('phase-editor').addEventListener('click', e=>{
 if(e.target.dataset.remove===undefined)return;
 phases.splice(Number(e.target.dataset.remove),1); $('scenario').value='custom'; editPhases();
});
$('add-phase').onclick=()=>{if(phases.length>=20)return toast('At most 20 phases.'); phases.push({at:(phases.at(-1)?.at||0)+5,kbps:2048});$('scenario').value='custom';editPhases();};
$('scenario').onchange=()=>{if(meta.scenarios[$('scenario').value])phases=structuredClone(meta.scenarios[$('scenario').value]); editPhases();};
function setMode(next){
 mode=next;
 document.querySelectorAll('button.nav').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
 $('boundary-fields').hidden=mode!=='boundary';
 $('breadcrumb').textContent=mode==='boundary'?'Failure boundaries':'Experiments';
 $('page-title').innerHTML=mode==='boundary'?'Find the failure boundary<span class="beta">SWEEP</span>':'Network Resilience Lab<span class="beta">BETA</span>';
 $('scenario').closest('fieldset').hidden=mode==='boundary';
 $('start').textContent=mode==='boundary'?'▶  Start boundary sweep':'▶  Start experiment';
}
document.querySelectorAll('button.nav').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
function payloadTab(file){useFile=file;$('generated-input').hidden=file;$('file-input').hidden=!file;$('generated-tab').classList.toggle('selected',!file);$('file-tab').classList.toggle('selected',file);$('size').required=!file;}
$('generated-tab').onclick=()=>payloadTab(false);$('file-tab').onclick=()=>payloadTab(true);
$('file').onchange=async()=>{
 const file=$('file').files[0];fileReady=false;
 if(!file)return;
 if(file.size<1024||file.size>32*1048576){toast('Choose a file between 1 KiB and 32 MiB.');return;}
 $('start').disabled=true;
 try{const info=await api(`/api/payload?name=${encodeURIComponent(file.name)}`,{method:'POST',body:file});fileReady=true;$('file-name').textContent=`${info.name} · ${bytes(info.size_bytes)}`;}
 catch(e){toast(e.message);}finally{$('start').disabled=busy;}
};
function setBusy(value){
 busy=value;
 $('start').disabled=value;
 $('cancel').hidden=!value;
 $('experiment-form').querySelectorAll('input,select,button:not(#cancel):not(#start)').forEach(e=>e.disabled=value);
 document.querySelectorAll('button.nav').forEach(b=>b.disabled=value);
}
$('experiment-form').onsubmit=async e=>{
 e.preventDefault(); if(busy)return;
 $('toast').hidden=true;
 if(useFile&&!fileReady)return toast('Select a valid local file first.');
 const strategies=[...document.querySelectorAll('[name=strategy]:checked')].map(c=>c.value);
 if(!strategies.length)return toast('Select at least one upload strategy.');
 const config={mode,scenario:$('scenario').value,phases,strategies,use_file:useFile,size_bytes:Math.round(Number($('size').value)*1048576),trials:Number($('trials').value),deadline_s:Number($('deadline').value),delay_ms:Number($('delay').value),max_retries:Number($('retries').value),chunk_bytes:Number($('chunk').value)};
 if(mode==='boundary'){
  config.bandwidths=$('bands').value.split(',').map(v=>Number(v.trim()));config.outages=$('outages').value.split(',').map(v=>Number(v.trim()));
 }
 setBusy(true);
 try{const data=await api('/api/experiments',{method:'POST',body:JSON.stringify(config)});jobId=data.id;selected=null;localStorage.setItem('nrl-job',jobId);await poll();}
 catch(err){setBusy(false);toast(err.message);}
};
$('cancel').onclick=async()=>{ $('cancel').disabled=true;try{await api('/api/cancel',{method:'POST'});await poll();}catch(e){toast(e.message);}finally{$('cancel').disabled=false;} };
function chart(samples=[]){
 const w=700,h=220,left=45,right=10,top=12,bottom=25;
 const maxX=Math.max(1,...samples.map(s=>s.at));const maxY=Math.max(256,...samples.flatMap(s=>[s.kbps,s.limit_kbps]))*1.1;
 const x=t=>left+t/maxX*(w-left-right), y=v=>h-bottom-v/maxY*(h-top-bottom);
 let svg='<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#12a88d" stop-opacity=".16"/><stop offset="1" stop-color="#12a88d" stop-opacity="0"/></linearGradient></defs>';
 for(let i=0;i<5;i++){let v=maxY*i/4,yy=y(v);svg+=`<line x1="${left}" y1="${yy}" x2="${w-right}" y2="${yy}" stroke="var(--chart-grid, #eaf0f4)" stroke-dasharray="3 4"/><text x="${left-9}" y="${yy+3}" text-anchor="end" fill="var(--chart-label, #a1adbb)" font-size="9">${Math.round(v)}</text>`;}
 for(let i=0;i<6;i++)svg+=`<text x="${x(maxX*i/5)}" y="${h-6}" text-anchor="middle" fill="var(--chart-label, #a1adbb)" font-size="9">${fmt(maxX*i/5,1)}</text>`;
 if(samples.length){
  const points=samples.map(s=>`${x(s.at)},${y(s.kbps)}`).join(' ');
  svg+=`<polygon points="${x(samples[0].at)},${y(0)} ${points} ${x(samples.at(-1).at)},${y(0)}" fill="url(#area)"/><polyline points="${points}" fill="none" stroke="#10a68e" stroke-width="2" stroke-linejoin="round"/>`;
  let path=`M${x(samples[0].at)},${y(samples[0].limit_kbps)}`;
  samples.slice(1).forEach(s=>{path+=`H${x(s.at)}V${y(s.limit_kbps)}`;});
  svg+=`<path d="${path}" fill="none" stroke="var(--chart-limit, #9eafbd)" stroke-width="1.3" stroke-dasharray="5 4"/>`;
 }
 $('chart').innerHTML=svg; $('chart-empty').hidden=!!samples.length;
}
function render(){
 const running=job.status==='running';setBusy(running);
 const inspected=selected!=null?job.results[selected]:null;
 const r=inspected||job.active||job.results.at(-1);
 const state=inspected?r.status:job.status;
 $('status-badge').className=`status ${state}`;$('status-badge').textContent=`●  ${state==='completed'?'Finished':state[0].toUpperCase()+state.slice(1)}`;
 $('trial-counter').textContent=`${job.results.length} / ${job.total}`;
 $('trial-label').textContent=r?`${r.strategy[0].toUpperCase()+r.strategy.slice(1)} · Trial ${r.trial}${inspected?' · inspecting result':''}`:'Preparing experiment…';
 if(r){
  $('elapsed').innerHTML=`${fmt(r.elapsed_s)}<small>s</small>`;
  $('throughput').innerHTML=`${fmt(r.samples.at(-1)?.kbps??null,0)}<small>kbps</small>`;
  $('network').innerHTML=`${fmt(r.network_kbps??null,0)}<small>kbps</small>`;
  const progress=Math.min(100,r.confirmed_bytes/r.payload_bytes*100);
  $('progress-text').textContent=`${fmt(progress,0)}%`;$('progress-bar').style.width=`${progress}%`;
  $('bytes-label').textContent=`${bytes(r.confirmed_bytes)} / ${bytes(r.payload_bytes)} confirmed · ${bytes(r.forwarded_bytes)} forwarded`;
  $('retry-label').textContent=`${r.retry_count} retries`;
  chart(r.samples);
  $('events-count').textContent=`${r.events.length} EVENTS`;
  const list=$('event-list'), atBottom=list.scrollTop+list.clientHeight>=list.scrollHeight-30;
  list.innerHTML=r.events.map(e=>`<div class="event ${esc(e.kind)}"><time>${fmt(e.at,2)}s</time><span></span><p>${esc(e.message)}</p></div>`).join('');
  if(atBottom)list.scrollTop=list.scrollHeight;
 }
 $('result-summary').textContent=`${job.results.length} of ${job.total} trials finished · ${job.payload_name} · ${job.status}${job.error?' · '+job.error:''}`;
 $('result-rows').innerHTML=job.results.length?job.results.map((r,i)=>{
  const recovery=r.recoveries.map(x=>x.recovery_s).filter(x=>x!=null);
  return `<tr data-index="${i}" tabindex="0" aria-label="Inspect ${r.strategy} trial ${r.trial}" class="${selected===i?'selected':''}"><td class="result-strategy">${esc(r.strategy)}<small>#${r.trial}${r.config.bandwidth_kbps!=null?' · '+r.config.bandwidth_kbps+' kbps / '+r.config.outage_s+'s outage':''}</small></td><td><span class="status ${esc(r.status)}">${r.status==='completed'?'✓ Verified':esc(r.status)}</span></td><td>${fmt(r.elapsed_s,2)}s</td><td>${fmt(r.useful_kbps,0)}</td><td>${bytes(r.retransmission_bytes)}</td><td>${r.retry_count}</td><td>${recovery.length?recovery.map(v=>fmt(v,2)+'s').join(', '):'—'}</td><td>${r.integrity===true?'✓ SHA-256':r.integrity===false?'✕ Mismatch':'—'}</td></tr>`;
 }).join(''):'<tr><td colspan="8" class="table-empty">Experiment running. Results will appear after each trial.</td></tr>';
 $('success-summary').innerHTML=job.summaries.filter(g=>g.bandwidth_kbps==null).map(g=>`<span><strong>${esc(g.strategy)}</strong> ${g.successes}/${g.trials} verified · ${fmt(g.success_rate==null?null:g.success_rate*100,0)}% success</span>`).join('');
 for(const [id,path] of [['export-csv','/csv'],['export-json','?download']]){ $(id).href=`/api/experiments/${job.id}${path}`;$(id).classList.remove('disabled');$(id).setAttribute('aria-disabled','false');$(id).setAttribute('download',''); }
 $('boundary-results').hidden=job.mode!=='boundary';
 if(job.mode==='boundary'){
  $('heatmap').innerHTML=`<table><thead><tr><th>kbps</th><th>OUTAGE</th><th>STRATEGY</th><th>VERIFIED</th><th>SUCCESS RATE</th></tr></thead><tbody>${job.summaries.map(g=>`<tr><td>${g.bandwidth_kbps}</td><td>${g.outage_s}s</td><td>${esc(g.strategy)}</td><td>${g.successes}/${g.trials}</td><td class="${g.success_rate>=.5?'good':'bad'}">${fmt(g.success_rate==null?null:g.success_rate*100,0)}%</td></tr>`).join('')}</tbody></table>`;
 }
 $('hash-detail').hidden=!inspected;
 if(inspected)$('hash-detail').innerHTML=`Expected SHA-256: ${esc(inspected.expected_sha256)}<br>Origin SHA-256: ${esc(inspected.actual_sha256||'Unavailable (no complete file verified)')}<br>Proxy ingress: ${inspected.bytes_sent.toLocaleString()} bytes · Client submitted: ${inspected.client_submitted_bytes.toLocaleString()} bytes · Forwarded: ${inspected.forwarded_bytes.toLocaleString()} bytes<br>Retransmission overhead: ${fmt(inspected.overhead_percent,2)}% · ${esc(inspected.error||'No terminal error')}<br>Configuration: ${esc(JSON.stringify(inspected.config))}`;
}
function inspect(e){const row=e.target.closest('tr[data-index]');if(row){selected=Number(row.dataset.index);render();}}
$('result-rows').onclick=inspect;$('result-rows').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect(e);}};
async function poll(){
 if(!jobId||polling)return;
 polling=true;
 try{job=await api(`/api/experiments/${jobId}`);$('connection').textContent='Connected';if(job.active)selected=null;render();}
 catch(e){$('connection').textContent='Unavailable';toast(e.message);}
 finally{polling=false;}
}
async function init(){
 chart();
 try{meta=await api('/api/meta');$('connection').textContent='Connected';phases=structuredClone(meta.scenarios.demo);editPhases();
 $('metric-definitions').innerHTML=Object.entries(meta.metrics).map(([k,v])=>`<p><strong>${esc(k)}</strong><br>${esc(v)}</p>`).join('');
 const jobs=await api('/api/experiments');jobId=jobs.find(j=>j.status==='running')?.id||jobs.find(j=>j.id===localStorage.getItem('nrl-job'))?.id||jobs.at(-1)?.id;
 if(jobId)await poll();
 }catch(e){$('connection').textContent='Unavailable';toast(e.message);}
}
init();setInterval(()=>{if(jobId&&(!job||job.status==='running'))poll();},500);
