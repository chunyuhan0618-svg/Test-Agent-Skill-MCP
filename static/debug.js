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
  const signature=JSON.stringify([data.status,data.events.map(e=>[e.seq,e.status]),Object.keys(data.results),data.errors,data.error]);
  if(signature===debugSignature)return;
  debugSignature=signature;
  debug$('#debug-next').disabled=data.status!=='paused';
  debug$('#debug-cancel').disabled=['completed','cancelled','error'].includes(data.status);
  const current=data.events.at(-1);
  debug$('#debug-state').textContent=data.error|| (data.status==='paused'?`第 ${current.seq} 步已暂停 · ${data.pair}。点击下一步执行：${current.title}`:data.status==='running'?'正在执行当前步骤，等待程序到达下一个断点…':data.status==='cancelled'?'调试已结束，尚未执行的步骤不会继续。':'本次调试执行结束。');
  const list=data.events.map(event=>{const li=document.createElement('li');li.dataset.status=event.status;const button=document.createElement('button');button.type='button';const title=document.createElement('span');title.className='flow-title';const kind=document.createElement('span');kind.className='flow-kind';kind.textContent=event.kind;title.append(kind,document.createTextNode(`${event.seq}. ${event.title}`));const meta=document.createElement('span');meta.className='flow-meta';meta.textContent=`${event.pair} · ${debugStates[event.status]||event.status} · ${event.file}:${event.line}`;button.append(title,meta);button.addEventListener('click',()=>showStep(event));li.append(button);return li;});
  debug$('#flow-list').replaceChildren(...list);
  if(current)showStep(current);
  const flow=debug$('#flow-list');flow.scrollTop=flow.scrollHeight;
  Object.values(data.results).forEach(result=>render(result));
  Object.entries(data.errors).forEach(([pair,error])=>message(pair,error,'失败',true));
}
async function cancelDebug(){
  if(!debugJob)return;
  debug$('#debug-next').disabled=true;debug$('#debug-cancel').disabled=true;
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
  finally{debugJob=null;debug$('#debug-next').disabled=true;debug$('#debug-cancel').disabled=true;}
}
debug$('#debug-next').addEventListener('click',async()=>{
  if(!debugJob||debugSnapshot?.status!=='paused')return;
  debug$('#debug-next').disabled=true;
  try{drawDebug(await debugRequest(`/api/debug/${debugJob}/next`,{seq:debugSnapshot.events.at(-1).seq}));}
  catch(error){debug$('#debug-state').textContent=error.message;debugSignature='';}
});
debug$('#debug-cancel').addEventListener('click',cancelDebug);
debug$('#debug-toggle').addEventListener('change',()=>{
  const enabled=debug$('#debug-toggle').checked;
  debug$('#debug-panel').hidden=!enabled;debug$('#workspace').classList.toggle('debug-enabled',enabled);
  if(!enabled&&debugJob)cancelDebug();
});
