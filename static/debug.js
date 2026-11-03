// 后端检查点驱动的真实单步执行，不在浏览器中伪造已执行步骤。
const debug$ = selector=>document.querySelector(selector);
let debugJob=null,debugSnapshot=null,debugSignature='';
const debugStates={paused:'待执行',running:'执行中',completed:'已完成',error:'失败',cancelled:'已结束'};
async function debugRequest(path,body){
  const options=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
  const response=await fetch(path,options),data=await response.json();
  if(!response.ok)throw new Error(data.error||'调试服务请求失败。');
  return data;
}
function showStep(event){
  debug$('#code-location').textContent=`${event.file}:${event.line} · ${event.kind}`;
  debug$('#code-detail').textContent=event.detail;
  const lines=event.code.map(row=>{const span=document.createElement('span');span.className='code-line'+(row.number===event.line?' current':'');const number=document.createElement('span');number.className='line-number';number.textContent=row.number;span.append(number,document.createTextNode(row.text));return span;});
  debug$('#debug-code').replaceChildren(...lines);
  debug$('#skill-resource').hidden=!event.resource;
  if(event.resource)debug$('#skill-source').textContent=`${event.resource.file}\n\n${event.resource.text}`;
}
function drawDebug(data){
  debugSnapshot=data;
  const signature=JSON.stringify([data.status,data.run_to_end,data.events.map(e=>[e.seq,e.status]),Object.keys(data.results),data.errors,data.error]);
  if(signature===debugSignature)return;
  debugSignature=signature;
  debug$('#debug-next').disabled=data.status!=='paused'||data.run_to_end;
  debug$('#debug-continue').disabled=!['paused','running'].includes(data.status)||data.run_to_end;
  debug$('#debug-cancel').disabled=['completed','cancelled','error'].includes(data.status);
  const current=data.events.at(-1);
  debug$('#debug-state').textContent=data.error|| (data.status==='paused'?`第 ${current.seq} 步已暂停 · ${data.pair}。点击下一步执行：${current.title}`:data.status==='running'?(data.run_to_end?'一步到底执行中：后续步骤不再暂停，仍可结束调试。':'正在执行当前步骤，等待程序到达下一个断点…'):data.status==='cancelled'?'调试已结束，尚未执行的步骤不会继续。':'本次调试执行结束。');
  const list=data.events.map(event=>{const li=document.createElement('li');li.dataset.status=event.status;const button=document.createElement('button');button.type='button';const title=document.createElement('span');title.className='flow-title';const kind=document.createElement('span');kind.className='flow-kind';kind.textContent=event.kind;title.append(kind,document.createTextNode(`${event.seq}. ${event.title}`));const meta=document.createElement('span');meta.className='flow-meta';meta.textContent=`${event.pair} · ${debugStates[event.status]||event.status} · ${event.file}:${event.line}`;button.append(title,meta);button.addEventListener('click',()=>showStep(event));li.append(button);return li;});
  debug$('#flow-list').replaceChildren(...list);
  if(current)showStep(current);
  const flow=debug$('#flow-list');flow.scrollTop=flow.scrollHeight;
  Object.values(data.results).forEach(result=>render(result));
  Object.entries(data.errors).forEach(([pair,error])=>message(pair,error,'失败',true));
}
async function cancelDebug(){
  if(!debugJob)return;
  debug$('#debug-next').disabled=true;debug$('#debug-continue').disabled=true;debug$('#debug-cancel').disabled=true;
  try{drawDebug(await debugRequest(`/api/debug/${debugJob}/cancel`,{}));}
  catch(error){debug$('#debug-state').textContent=error.message;debugSignature='';}
}
async function runDebug(payload){
  debugSignature='';debugSnapshot=null;
  debug$('#flow-list').replaceChildren();debug$('#debug-state').textContent='正在建立调试会话…';
  const start=await debugRequest('/api/debug/start',payload);debugJob=start.id;
  const delivered=new Set();
  try{
    while(true){
      const data=await debugRequest(`/api/debug/${debugJob}`);drawDebug(data);
      Object.keys(data.results).forEach(pair=>delivered.add(pair));
      if(['completed','cancelled','error'].includes(data.status)){
        for(const pair of payload.pairs)if(!data.results[pair]&&!data.errors[pair])message(pair,data.error||'调试已结束，本组尚未完成。',data.status==='error'?'失败':'已结束',data.status==='error');
        return {succeeded:delivered.size,ending:data.status==='cancelled'?'调试已结束。':data.error||''};
      }
      await new Promise(resolve=>setTimeout(resolve,400));
    }
  }catch(error){await cancelDebug();throw error;}
  finally{debugJob=null;debug$('#debug-next').disabled=true;debug$('#debug-continue').disabled=true;debug$('#debug-cancel').disabled=true;}
}
debug$('#debug-next').addEventListener('click',async()=>{
  if(!debugJob||debugSnapshot?.status!=='paused')return;
  debug$('#debug-next').disabled=true;
  try{drawDebug(await debugRequest(`/api/debug/${debugJob}/next`,{seq:debugSnapshot.events.at(-1).seq}));}
  catch(error){debug$('#debug-state').textContent=error.message;debugSignature='';}
});
debug$('#debug-cancel').addEventListener('click',cancelDebug);
debug$('#debug-continue').addEventListener('click',async()=>{
  if(!debugJob||!['paused','running'].includes(debugSnapshot?.status))return;
  debug$('#debug-continue').disabled=true;debug$('#debug-next').disabled=true;
  try{drawDebug(await debugRequest(`/api/debug/${debugJob}/continue`,{}));}
  catch(error){debug$('#debug-state').textContent=error.message;debugSignature='';}
});
function updateDebugVisibility(){
  const enabled=debug$('#debug-toggle').checked;
  debug$('#debug-panel').hidden=!enabled;debug$('#workspace').classList.toggle('debug-enabled',enabled);
  debug$('#debug-resizer').hidden=!enabled;
  if(enabled)requestAnimationFrame(sizeDebugPanel);
  if(!enabled&&debugJob)cancelDebug();
}
debug$('#debug-toggle').addEventListener('change',updateDebugVisibility);

// 分隔条只调整布局，不改变调试任务。比例存在当前页面内存中。
const resizer=debug$('#debug-resizer'),workspace=debug$('#workspace');
let debugRatio=50,resizeFrame=0;
function applyDebugRatio(ratio){
  const width=workspace.getBoundingClientRect().width;
  const minimum=width?Math.max(30,Math.min(50,320/width*100)):30;
  const maximum=width?Math.min(70,Math.max(50,100-334/width*100)):70;
  debugRatio=Math.min(maximum,Math.max(minimum,ratio));
  workspace.style.setProperty('--debug-width',`${debugRatio}%`);
  resizer.setAttribute('aria-valuemin',String(Math.ceil(minimum)));
  resizer.setAttribute('aria-valuemax',String(Math.floor(maximum)));
  resizer.setAttribute('aria-valuenow',String(Math.round(debugRatio)));
}
function sizeDebugPanel(){
  resizeFrame=0;
  const panel=debug$('#debug-panel');if(panel.hidden)return;
  const top=Math.max(16,panel.getBoundingClientRect().top);
  panel.style.height=`${Math.max(240,window.innerHeight-top-16)}px`;
}
function queuePanelSize(){if(!resizeFrame)resizeFrame=requestAnimationFrame(sizeDebugPanel);}
resizer.addEventListener('pointerdown',event=>{
  if(event.button!==0)return;
  event.preventDefault();resizer.setPointerCapture(event.pointerId);
  resizer.classList.add('dragging');document.body.classList.add('resizing-debug');
});
resizer.addEventListener('pointermove',event=>{
  if(!resizer.hasPointerCapture(event.pointerId))return;
  const bounds=workspace.getBoundingClientRect();
  applyDebugRatio((bounds.right-event.clientX)/bounds.width*100);
});
function finishResize(){resizer.classList.remove('dragging');document.body.classList.remove('resizing-debug');queuePanelSize();}
resizer.addEventListener('pointerup',event=>{if(resizer.hasPointerCapture(event.pointerId))resizer.releasePointerCapture(event.pointerId);finishResize();});
resizer.addEventListener('lostpointercapture',finishResize);
resizer.addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  applyDebugRatio(event.key==='Home'?30:event.key==='End'?70:debugRatio+(event.key==='ArrowLeft'?2:-2));
});
window.addEventListener('scroll',queuePanelSize,{passive:true});
window.addEventListener('resize',()=>{if(window.innerWidth>900)applyDebugRatio(debugRatio);queuePanelSize();},{passive:true});

// 页面首次加载时同步默认勾选状态，面板、分隔条及高度无需等待 change 事件。
updateDebugVisibility();
