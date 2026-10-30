const $ = (selector) => document.querySelector(selector);
const pairs = ["zh-ja", "zh-en", "en-ja"];
const names = {zh:"中文", ja:"日本語", en:"English"};
let busy = false;
const card = (pair) => document.querySelector(`[data-pair="${pair}"]`);
const selected = () => [...document.querySelectorAll('.choices input:checked')].map(x=>x.value);
function message(pair, text, badge, error=false) {
  const el=card(pair); el.querySelector('.badge').textContent=badge;
  const p=document.createElement('p');p.className=error?'error':'empty';p.textContent=text;
  el.querySelector('.result-body').replaceChildren(p);
}
function render(result) {
  const el=card(result.pair), body=el.querySelector('.result-body');body.replaceChildren();
  el.querySelector('.badge').textContent='已完成';
  for(const [language,text] of [[result.left_language,result.left],[result.right_language,result.right]]) {
    const h=document.createElement('h3');h.textContent=names[language];
    const p=document.createElement('p');p.className='translation';p.lang=language;p.textContent=text;body.append(h,p);
  }
  const explanation=document.createElement('div');explanation.className='explanation';
  for(const [title,text] of [['意思解释',result.explanation],['关键词与用法',result.keywords],['术语参考',result.references]]) {
    const h=document.createElement('h3');h.textContent=title;const p=document.createElement('p');p.textContent=text;explanation.append(h,p);
  }
  const note=document.createElement('div');note.className='skill-note';note.textContent=result.mode==='free'?`${result.engine} · 组合 ${result.skill} · MCP 本地术语`:`Skill / ${result.skill} · MCP 术语查询`;body.append(explanation,note);
}
function updateSelection() {
  const enabled=selected();
  for(const pair of pairs){card(pair).classList.toggle('disabled',!enabled.includes(pair));
    if(!enabled.includes(pair))message(pair,'本组已关闭，不进行对照翻译。','未启用');
    else if(card(pair).querySelector('.badge').textContent==='未启用')message(pair,'输入原文后，开始本组对照。','待翻译');
  }
  $('#submit').disabled=!enabled.length;
  $('#status').textContent=enabled.length?`已选择 ${enabled.length} 组对照，等待输入。`:'请至少选择一组对照。';
}
document.querySelectorAll('.choices input').forEach(x=>x.addEventListener('change',updateSelection));
function updateMode(){const ai=Boolean($('#model').value&&$('#api-key').value.trim());$('#mode-hint').textContent=ai?'大模型模式：使用所选模型与 API Key，原文发送至 OpenAI，可能产生 API 费用。取消勾选的组合不翻译。':'免费模式：无需模型和 Key，原文将发送至 MyMemory 翻译服务，需联网，有每日额度；每次最多 1000 字符。解释使用本地术语资料。取消勾选的组合不翻译。';}
$('#model').addEventListener('change',()=>{const custom=$('#model').value==='custom';$('#custom-wrap').hidden=!custom;updateMode();});
$('#api-key').addEventListener('input',updateMode);
$('#text').addEventListener('input',()=>{$('#count').textContent=`${$('#text').value.length.toLocaleString()} / 10,000`;});
$('#sample').addEventListener('click',()=>{$('#source').value='ja';$('#text').value='お疲れ様です。ご確認をお願いいたします。';$('#text').dispatchEvent(new Event('input'));});
$('#toggle-key').addEventListener('click',()=>{const show=$('#api-key').type==='password';$('#api-key').type=show?'text':'password';$('#toggle-key').textContent=show?'隐藏':'显示';$('#toggle-key').setAttribute('aria-label',show?'隐藏 API Key':'显示 API Key');$('#toggle-key').setAttribute('aria-pressed',String(show));});
$('#form').addEventListener('submit',async(event)=>{
  event.preventDefault();if(busy)return;
  const enabled=selected(),text=$('#text').value,api_key=$('#api-key').value.trim();
  const model=($('#model').value==='custom'?$('#custom-model').value:$('#model').value).trim();
  if(!enabled.length||!text.trim()){$('#status').textContent='请填写原文，并选择至少一组对照。';return;}
  if($('#model').value==='custom'&&!model&&api_key){$('#status').textContent='请填写自定义模型 ID，或选择“不指定模型”使用免费翻译。';return;}
  if((!model||!api_key)&&text.length>1000){$('#status').textContent='免费模式每次最多 1000 字符，请缩短原文。';return;}
  busy=true;const source=$('#source').value;
  // 固定本轮快照并锁定编辑，避免旧结果对应到新设置。
  document.querySelectorAll('form input,form textarea,form select,form button').forEach(x=>x.disabled=true);
  $('#submit').textContent='正在对照翻译…';$('#status').textContent=`正在翻译 ${enabled.length} 组，请稍候…`;
  enabled.forEach(pair=>message(pair,'正在理解原文、查询术语并生成对照…','翻译中'));
  let succeeded=0;
  let ending='';
  if($('#debug-toggle').checked){
    try{({succeeded,ending}=await runDebug({text,source,pairs:enabled,model,api_key}));}
    catch(error){ending=error.message;enabled.forEach(pair=>message(pair,error.message,'失败',true));}
  }else{
  await Promise.all(enabled.map(async(pair)=>{
    try{
      const response=await fetch('/api/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,source,pair,model,api_key})});
      const data=await response.json();if(!response.ok)throw new Error(data.error||'翻译失败，请稍后重试。');render(data);succeeded++;
    }catch(error){message(pair,error.message||'连接失败，请确认本地网页服务正在运行。','失败',true);}
  }));
  }
  document.querySelectorAll('form input,form textarea,form select,form button').forEach(x=>x.disabled=false);
  busy=false;$('#submit').textContent='开始对照翻译 →';$('#status').textContent=`已完成 ${succeeded} / ${enabled.length} 组对照。${ending||(succeeded<enabled.length?'请检查失败栏位的提示。':'')}`;
});
