import io
import unittest

import httpx
from docx import Document
from contract_guard.application.use_cases.clause_splitter import segment_clauses
from contract_guard.application.use_cases.extract_closing import extract_closing
from contract_guard.application.use_cases.search_context import search_context
from contract_guard.application.use_cases.taxonomy_rules import classify_rule
from contract_guard.domain.models.taxonomy import Category, ClauseInput
from contract_guard.infrastructure.web.app import app
from contract_guard.infrastructure.web.dependencies import current_session


class PolishTests(unittest.TestCase):
    def test_closing_and_signatures(self):
        text = 'ماده پانزدهم - حل اختلاف\n۳-۱۵ اختلاف به داوری ارجاع می‌شود.\nاین قرارداد در دو نسخه تنظیم و امضا گردید.\nامضای کارفرما: علی\nامضای پیمانکار: بهرام'
        body, closing = extract_closing(text)
        self.assertIn('داوری', body)
        self.assertNotIn('دو نسخه', body)
        self.assertIn('امضای پیمانکار', closing)
        self.assertNotIn('امضا', segment_clauses(body)[0]['text'])

    def test_signature_only_and_legal_mention(self):
        text = 'ماده اول - قرارداد\n۱-۱ هر تغییر با امضای کارفرما معتبر است.\nامضای کارفرما: علی'
        body, closing = extract_closing(text)
        self.assertIn('با امضای کارفرما معتبر', body)
        self.assertEqual(closing, 'امضای کارفرما: علی')

    def test_corroborated_number_correction_and_reference(self):
        text = 'ماده یک - موضوع\n0-0 طراحی سامانه\n2-0 تحویل سامانه\nماده پانزدهم - داوری\n0-05 شرط داوری طبق ماده 05\n2-05 دادگاه صالح'
        clauses = segment_clauses(text)
        self.assertEqual([c['text'].split()[0] for c in clauses], ['1-1', '2-1', '1-15', '2-15'])
        self.assertIn('ماده 15', clauses[2]['text'])
        self.assertIn('ماده 05', clauses[2]['original_text'])
        self.assertEqual(clauses[0]['original_text'], '0-0 طراحی سامانه')

    def test_ambiguous_and_real_zero_unchanged(self):
        text = 'ماده اول - مبلغ\n0-1 مبلغ 0 ریال در 1403/05/01\nماده پنجم - الف\n0-5 بند مستقل'
        clauses = segment_clauses(text)
        self.assertTrue(clauses[0]['text'].startswith('0-1'))
        self.assertIn('0 ریال', clauses[0]['text'])
        self.assertIn('1403/05/01', clauses[0]['text'])
        self.assertNotIn('original_text', clauses[0])

    def test_ambiguous_reference_is_not_changed(self):
        text = 'ماده پنجم - الف\n۵-۱ تعهد\nماده پانزدهم - داوری\n0-05 مطابق ماده 05\n2-05 داوری'
        clauses = segment_clauses(text)
        self.assertIn('ماده 05', next(c['text'] for c in clauses if c['text'].startswith('1-15')))

    def test_explicit_keywords(self):
        samples = {
            'عدم رقابت': Category.non_compete,
            'فعالیت مشابه': Category.non_compete,
            'وجه التزام': Category.penalty_compensation,
            'ضرر و زیان': Category.penalty_compensation,
            'افشای اطلاعات': Category.confidentiality,
            'رفع نقص': Category.sla_obligations,
            'پشتیبانی': Category.sla_obligations,
        }
        for text, category in samples.items():
            with self.subTest(text=text):
                result = classify_rule(ClauseInput(clause_id='x', index=1, text=text))
                self.assertEqual(result.primary_category, category)
                self.assertGreater(result.confidence, .85)
                self.assertEqual(result.source.value, 'rule_based')

    def test_mixed_topic_and_context(self):
        item = ClauseInput(clause_id='x', index=1, article_title='ماده هشتم - عدم رقابت', text='عدم رقابت و پرداخت جریمه')
        result = classify_rule(item)
        self.assertEqual(result.primary_category, Category.non_compete)
        self.assertIn(Category.penalty_compensation, result.secondary_categories)
        self.assertEqual(search_context(item.article_title, result.primary_category, item.text), '[ماده هشتم - عدم رقابت | دسته‌بندی: عدم رقابت] \n متن بند: عدم رقابت و پرداخت جریمه')


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_docx_json_output(self):
        doc = Document()
        for text in ('ماده هشتم - عدم رقابت', '0-8 پیمانکار از رقابت خودداری می‌کند.', '2-8 جریمه نقض تعهد.', 'این قرارداد در دو نسخه تنظیم و امضا گردید.', 'امضای کارفرما: علی'):
            doc.add_paragraph(text)
        file = io.BytesIO()
        doc.save(file)
        app.dependency_overrides[current_session] = lambda: {'id': 'test'}
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                response = await client.post('/api/v1/contracts/extract', files={'file': ('a.docx', file.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertIn('دو نسخه', payload['closing_metadata'])
                self.assertEqual(payload['total_clauses'], 2)
                self.assertTrue(payload['clauses'][0]['text'].startswith('1-8'))
                self.assertTrue(payload['clauses'][0]['original_text'].startswith('0-8'))
                self.assertEqual(payload['clauses'][0]['taxonomy']['primary_category'], 'non_compete')
                self.assertIn('دسته‌بندی: عدم رقابت', payload['clauses'][0]['search_context'])
                self.assertNotIn('دو نسخه', payload['clauses'][1]['text'])
        finally:
            app.dependency_overrides.clear()
