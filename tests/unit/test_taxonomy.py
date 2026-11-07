import asyncio
import io
import time
import unittest
from unittest.mock import patch

import httpx
from docx import Document
from contract_guard.application.use_cases.classify_clauses import HybridClauseClassifier
from contract_guard.application.use_cases.clause_splitter import segment_clauses
from contract_guard.application.use_cases.taxonomy_rules import classify_rule
from contract_guard.domain.models.taxonomy import Category, ClauseInput, Classification, ClassificationSource
from contract_guard.infrastructure.llm.taxonomy_gateway import LLMTaxonomyGateway
from contract_guard.infrastructure.web.app import app
from contract_guard.infrastructure.web.dependencies import current_session


class FakeGateway:
    def __init__(self, error=False):
        self.calls = 0
        self.error = error

    async def classify(self, clause):
        self.calls += 1
        if self.error:
            raise TimeoutError()
        return Classification(clause_id=clause.clause_id, primary_category=Category.termination,
            secondary_categories=[Category.penalty_compensation], confidence=0.7,
            matched_keywords=['فسخ', 'خسارت'], source=ClassificationSource.llm)


class RuleTests(unittest.TestCase):
    def test_ten_subjects(self):
        examples = [
            ('پرداخت اقساط', Category.financial),
            ('جریمه و وجه التزام', Category.penalty_compensation),
            ('مالکیت فکری و حق نشر', Category.intellectual_property),
            ('اطلاعات محرمانه و عدم افشا', Category.confidentiality),
            ('فسخ و انفساخ', Category.termination),
            ('طراحی و تحویل', Category.scope_delivery),
            ('گارانتی و رفع باگ', Category.warranty_support),
            ('داوری و دادگاه', Category.dispute_resolution),
            ('قوه قاهره و بلایای طبیعی', Category.force_majeure),
            ('اقامتگاه قانونی و ابلاغ', Category.general_legal),
        ]
        for text, expected in examples:
            with self.subTest(category=expected):
                result = classify_rule(ClauseInput(clause_id='1', index=1, text=text))
                self.assertEqual(result.primary_category, expected)
    def test_one_indicator_or_ambiguous(self):
        self.assertIsNone(classify_rule(ClauseInput(clause_id='1', index=1, text='پرداخت در موعد')))
        self.assertEqual(classify_rule(ClauseInput(clause_id='1', index=1, text='جبران خسارت')).primary_category, Category.penalty_compensation)
        self.assertIsNone(classify_rule(ClauseInput(clause_id='1', index=1, text='پرداخت اقساط و داوری دادگاه')))
    def test_title_and_normalization(self):
        result = classify_rule(ClauseInput(clause_id='1', index=1, article_title='ماده دوم - محرمانگی', text='مفاد در پایان معتبر است'))
        self.assertEqual(result.primary_category, Category.confidentiality)
        result = classify_rule(ClauseInput(clause_id='1', index=1, text='ماليات و اقساط'))
        self.assertEqual(result.primary_category, Category.financial)
    def test_split_preserves_parent_and_non_numbered(self):
        clauses = segment_clauses('ماده چهارم – تعهدات پیمانکار\n۱-۴ تعهد اول\n۲-۴ تعهد دوم\nماده پنجم - محرمانگی\nاطلاعات محرمانه است')
        self.assertEqual(len(clauses), 3)
        self.assertEqual(clauses[0]['article_title'], 'ماده چهارم – تعهدات پیمانکار')
        self.assertEqual(clauses[1]['article_title'], clauses[0]['article_title'])
        self.assertEqual(clauses[2]['article_title'], 'ماده پنجم - محرمانگی')
    def test_rule_speed(self):
        clauses = [ClauseInput(clause_id=str(i), index=i+1, text='پرداخت اقساط در پایان ماه') for i in range(100)]
        start = time.perf_counter()
        for clause in clauses: classify_rule(clause)
        self.assertLess(time.perf_counter() - start, 0.05)


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_mixed_and_rule_no_call(self):
        gateway = FakeGateway()
        items = [ClauseInput(clause_id='1', index=1, text='پرداخت اقساط'),
                 ClauseInput(clause_id='2', index=2, text='پرداخت اقساط و داوری دادگاه')]
        results = await HybridClauseClassifier(gateway, 2).classify_batch(items)
        self.assertEqual(gateway.calls, 1)
        self.assertEqual(results[0].source, ClassificationSource.rule_based)
        self.assertEqual(results[1].secondary_categories, [Category.penalty_compensation])
    async def test_failure_degrades(self):
        item = ClauseInput(clause_id='3', index=1, text='نامشخص')
        result = (await HybridClauseClassifier(FakeGateway(error=True), 1).classify_batch([item]))[0]
        self.assertEqual((result.primary_category, result.confidence, result.degraded), (Category.general_legal, 0.0, True))
    async def test_model_response_format_failure_degrades(self):
        class Response:
            def raise_for_status(self): pass
            def json(self): return {'choices': [{'message': {'content': 'invalid json'}}]}
        class Client:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def post(self, *args, **kwargs): return Response()
        with patch('contract_guard.infrastructure.llm.taxonomy_gateway.Settings') as get_settings, patch('contract_guard.infrastructure.llm.taxonomy_gateway.httpx.AsyncClient', Client):
            get_settings.return_value.taxonomy_llm_url = 'https://example.invalid'
            get_settings.return_value.taxonomy_llm_model = 'test'
            get_settings.return_value.taxonomy_llm_api_key = ''
            get_settings.return_value.taxonomy_llm_max_chars = 1000
            get_settings.return_value.taxonomy_llm_timeout_seconds = 1
            item = ClauseInput(clause_id='4', index=1, text='نامشخص')
            result = (await HybridClauseClassifier(LLMTaxonomyGateway(), 1).classify_batch([item]))[0]
            self.assertTrue(result.degraded)
    async def test_model_json_response(self):
        class Response:
            def raise_for_status(self): pass
            def json(self):
                return {'choices': [{'message': {'content': '{"primary_category":"financial","secondary_categories":[],"confidence":0.8,"matched_keywords":["پرداخت"]}'}}]}
        class Client:
            def __init__(self, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def post(self, *args, **kwargs): return Response()
        with patch('contract_guard.infrastructure.llm.taxonomy_gateway.Settings') as get_settings, patch('contract_guard.infrastructure.llm.taxonomy_gateway.httpx.AsyncClient', Client):
            get_settings.return_value.taxonomy_llm_url = 'https://example.invalid'
            get_settings.return_value.taxonomy_llm_model = 'test'
            get_settings.return_value.taxonomy_llm_api_key = ''
            get_settings.return_value.taxonomy_llm_max_chars = 1000
            get_settings.return_value.taxonomy_llm_timeout_seconds = 1
            result = await LLMTaxonomyGateway().classify(ClauseInput(clause_id='4', index=1, text='پرداخت'))
            self.assertEqual((result.primary_category, result.confidence, result.degraded), (Category.financial, 0.8, False))
    async def test_api_validation_and_auth_override(self):
        app.dependency_overrides[current_session] = lambda: {'id': 'test'}
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                response = await client.post('/api/v1/contracts/classify', json={'clauses':[{'clause_id':'x','index':1,'text':'پرداخت اقساط'}]})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()[0]['primary_category'], 'financial')
                response = await client.post('/api/v1/contracts/classify', json={'clauses':[{'clause_id':'x','index':0,'text':'a'}]})
                self.assertEqual(response.status_code, 422)
        finally:
            app.dependency_overrides.clear()
    async def test_docx_pipeline_in_memory(self):
        document = Document()
        document.add_paragraph('ماده اول - پرداخت')
        document.add_paragraph('۱- پرداخت اقساط')
        stream = io.BytesIO()
        document.save(stream)
        app.dependency_overrides[current_session] = lambda: {'id': 'test'}
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                result = await client.post('/api/v1/contracts/extract', files={'file': ('a.docx', stream.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
                self.assertEqual(result.status_code, 200, result.text)
                clause = result.json()['clauses'][0]
                self.assertEqual(clause['article_title'], 'ماده اول - پرداخت')
                self.assertEqual(clause['taxonomy']['primary_category'], 'financial')
        finally:
            app.dependency_overrides.clear()


if __name__ == '__main__': unittest.main()
