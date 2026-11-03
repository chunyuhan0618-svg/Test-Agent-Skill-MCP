"""English: verify locale isolation, model explanation language and trilingual source coverage.
日本語：言語の分離、モデル説明の言語、全資料の3言語説明を検証します。
中文：验证语言隔离、模型解释语言和全部资料的三语说明覆盖。
"""
import ast
import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from starlette.testclient import TestClient
from web import app
from ui_locale import UI_LANGUAGE
from skill_router import ROOT


class InternationalizationTests(unittest.TestCase):
    def test_english_default_and_language_selector(self):
        with TestClient(app) as client:
            page = client.get('/').text
            self.assertIn('<html lang="en">', page)
            self.assertIn('value="en" selected', page)
            self.assertIn('id="ui-language"', page)
            self.assertIn('v3.5.0', page)
            catalog = client.get('/static/locales.json').json()
            for key, values in catalog.items():
                self.assertEqual(set(values), {'zh', 'en', 'ja'}, key)
                self.assertTrue(all(values.values()), key)

    def test_background_debug_keeps_start_language_after_poll_language_changes(self):
        import time
        observed = []
        async def fake_free(text, source, pair):
            observed.append(UI_LANGUAGE.get())
            return {'pair': pair, 'explanation': 'test'}
        with TestClient(app) as client, patch('web.compare_free', side_effect=fake_free):
            start = client.post('/api/debug/start', headers={'X-UI-Language': 'en'}, json={
                'text':'hello', 'source':'en', 'pairs':['en-ja']})
            self.assertEqual(start.status_code, 201)
            path = '/api/debug/' + start.json()['id']
            for _ in range(100):
                state = client.get(path, headers={'X-UI-Language':'ja'}).json()
                if state['status'] == 'paused':
                    break
                time.sleep(0.01)
            self.assertEqual(state['status'], 'paused')
            client.post(path + '/continue', headers={'X-UI-Language':'zh'}, json={})
            for _ in range(100):
                state = client.get(path, headers={'X-UI-Language':'ja'}).json()
                if state['status'] == 'completed':
                    break
                time.sleep(0.01)
            self.assertEqual(state['status'], 'completed')
            self.assertEqual(observed, ['en'])

    def test_every_markdown_and_python_has_specific_trilingual_guidance(self):
        paths = list(ROOT.glob('*.md')) + list((ROOT / 'docs').rglob('*.md')) + list((ROOT / 'skills').rglob('*.md'))
        for path in paths:
            text = path.read_text(encoding='utf-8')
            for marker in ('English', '日本語', '中文'):
                self.assertIn(marker, text, path.name)
        for path in list(ROOT.glob('*.py')) + list((ROOT / 'tests').glob('*.py')):
            doc = ast.get_docstring(ast.parse(path.read_text(encoding='utf-8')))
            for marker in ('English:', '日本語：', '中文：'):
                self.assertIn(marker, doc or '', path.name)


class LocaleIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_requests_keep_distinct_languages(self):
        observed = []
        async def fake_compare(text, source, pair, model, key):
            language = UI_LANGUAGE.get()
            await asyncio.sleep(0.01)
            observed.append((text, language, UI_LANGUAGE.get()))
            return {'pair': pair, 'explanation': language}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            with patch('web.compare', side_effect=fake_compare):
                responses = await asyncio.gather(*[
                    client.post('/api/compare', headers={'X-UI-Language': language}, json={
                        'text': language, 'source': 'en', 'pair': 'en-ja',
                        'model': 'example-model', 'api_key': 'fake-local-key'})
                    for language in ('en', 'ja', 'zh')])
        self.assertEqual([r.json()['explanation'] for r in responses], ['en', 'ja', 'zh'])
        self.assertTrue(all(text == before == after for text, before, after in observed))
        self.assertEqual(UI_LANGUAGE.get(), 'zh')

    async def test_model_prompt_uses_selected_explanation_language(self):
        from comparison import compare
        for language in ('en', 'ja', 'zh'):
            token = UI_LANGUAGE.set(language)
            try:
                with patch('comparison.run_model_loop', new_callable=AsyncMock, return_value=json.dumps({
                    'left':'source', 'right':'translated', 'explanation':'meaning',
                    'keywords':'usage', 'references':'none'})) as model_loop:
                    await compare('Please review', 'en', 'en-ja', 'example-model', 'fake-local-key')
                    request = model_loop.call_args.args[3]
                    instructions = model_loop.call_args.args[4]
                    self.assertEqual(request.explain, language)
                    self.assertIn(f'references 使用 {language} 对应的语言', instructions)
            finally:
                UI_LANGUAGE.reset(token)
