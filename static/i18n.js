// English: presentation-only localization. Never change source text, translations or code.
// 日本語：表示専用の翻訳。原文・訳文・コードは変更しません。
// 中文：仅翻译界面，不改变原文、译文或真实代码。
(() => {
  let language = 'en', messages = {}, patterns = [];
  const original = new WeakMap(), attributes = new WeakMap();
  const selector = document.querySelector('#ui-language');
  function canonical(text) {
    for (const [key, values] of Object.entries(messages)) {
      if (key === text || Object.values(values).includes(text)) return key;
    }
    return text;
  }
  function translate(text, depth = 0) {
    if (typeof text !== 'string' || depth > 6) return text;
    const key = canonical(text);
    if (messages[key]) return messages[key][language];
    for (const {expression, key, slots} of patterns) {
      const found = text.match(expression);
      if (found) return messages[key][language].replace(/\{(\d+)\}/g,
        (_, index) => translate(found[slots.indexOf(Number(index)) + 1], depth + 1));
    }
    const numbered = text.match(/^(\d+\. )(.*)$/s);
    if (numbered) return numbered[1] + translate(numbered[2], depth + 1);
    if (text.includes(' · ')) return text.split(' · ').map(part => translate(part, depth + 1)).join(' · ');
    if (text.includes('\n')) return text.split('\n').map(line => translate(line, depth + 1)).join('\n');
    // Leading/trailing spaces are significant for inline labels.
    const trimmed = text.trim();
    if (trimmed !== text && trimmed) return text.slice(0, text.indexOf(trimmed)) + translate(trimmed, depth + 1) + text.slice(text.indexOf(trimmed) + trimmed.length);
    return text;
  }
  function protectedNode(element) {
    return element.closest('script,style,textarea,#skill-source,.translation,.line-number,.code-line');
  }
  function update() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (!node.parentElement || protectedNode(node.parentElement)) continue;
      const prior = original.get(node);
      const source = prior && node.nodeValue === prior.output ? prior.source : canonical(node.nodeValue);
      const output = translate(source);
      original.set(node, {source, output});
      if (node.nodeValue !== output) node.nodeValue = output;
    }
    for (const element of document.querySelectorAll('[placeholder],[aria-label]')) {
      let saved = attributes.get(element);
      if (!saved) { saved = {}; attributes.set(element, saved); }
      for (const attribute of ['placeholder','aria-label']) {
        const value = element.getAttribute(attribute);
        if (value === null) continue;
        const prior = saved[attribute];
        const source = prior && value === prior.output ? prior.source : canonical(value);
        const output = translate(source); saved[attribute] = {source, output};
        if (value !== output) element.setAttribute(attribute, output);
      }
    }
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : language;
    document.title = translate('通过翻译产品理解 Agent、Skill、MCP 的流程');
  }
  // Every API request carries display language. Existing API clients keep their previous default.
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, options = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    if (url.origin === location.origin && url.pathname.startsWith('/api/')) {
      const headers = new Headers(options.headers || (input instanceof Request ? input.headers : undefined));
      headers.set('X-UI-Language', language); options = {...options, headers};
    }
    return nativeFetch(input, options);
  };
  window.uiI18n = {translate, get language() { return language; }, ready: null};
  window.uiI18n.ready = nativeFetch('/static/locales.json').then(response => {
    if (!response.ok) throw new Error('Cannot load interface translations. Reload the page.');
    return response.json();
  }).then(data => {
    messages = data;
    for (const key of Object.keys(messages)) {
      if (!key.includes('{0}')) continue;
      const slots = [];
      const escaped = key.split(/(\{\d+\})/).map(part => {
        if (/^\{\d+\}$/.test(part)) { slots.push(Number(part.slice(1,-1))); return '([\\s\\S]*?)'; }
        return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      }).join('');
      patterns.push({key, slots, expression: new RegExp('^' + escaped + '$')});
    }
    update();
    new MutationObserver(update).observe(document.body, {subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','aria-label']});
    selector.addEventListener('change', () => { language = selector.value; update(); window.dispatchEvent(new Event('ui-language-change')); });
  }).catch(error => { document.querySelector('#status').textContent = error.message; });
})();
