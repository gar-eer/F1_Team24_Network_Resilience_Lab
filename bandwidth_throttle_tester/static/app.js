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
function chart(){ $('chart-empty').hidden=false; }
function render(){
 const running=job.status==='running'; setBusy(running);
 const r=job.active||job.results.at(-1);
 $('status-badge').className=`status ${job.status}`;
 $('status-badge').textContent=job.status;
 $('trial-counter').textContent=`${job.results.length} / ${job.total}`;
 $('result-summary').textContent=`${job.results.length} of ${job.total} trials finished · ${job.payload_name}`;
 if(r){
  $('trial-label').textContent=`${r.strategy} · Trial ${r.trial}`;
  $('elapsed').textContent=`${fmt(r.elapsed_s)} s`;
  $('throughput').textContent=`${fmt(r.samples.at(-1)?.kbps??null,0)} kbps`;
  $('network').textContent=`${fmt(r.network_kbps??null,0)} kbps`;
  const progress=Math.min(100,r.confirmed_bytes/r.payload_bytes*100);
  $('progress-text').textContent=`${fmt(progress,0)}%`;
  $('progress-bar').style.width=`${progress}%`;
  $('bytes-label').textContent=`${bytes(r.confirmed_bytes)} / ${bytes(r.payload_bytes)} confirmed`;
  $('retry-label').textContent=`${r.retry_count} retries`;
  $('events-count').textContent=`${r.events.length} EVENTS`;
  $('event-list').innerHTML=r.events.map(e=>`<div class="event ${esc(e.kind)}"><time>${fmt(e.at,2)}s</time><p>${esc(e.message)}</p></div>`).join('');
 }
 $('result-rows').innerHTML=job.results.map(r=>`<tr><td>${esc(r.strategy)}</td><td>${esc(r.status)}</td><td>${fmt(r.elapsed_s,2)}s</td><td>${fmt(r.useful_kbps,0)}</td><td>${bytes(r.retransmission_bytes)}</td><td>${r.retry_count}</td><td>—</td><td>${r.integrity===true?'✓ SHA-256':'—'}</td></tr>`).join('')||'<tr><td colspan="8" class="table-empty">Waiting for finished trials.</td></tr>';
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
