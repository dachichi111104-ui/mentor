from django.test import TestCase
from django.utils import timezone
from django.template import Template, Context

class StatCardsTestCase(TestCase):
    def test_stat_card_template_include_with_href(self):
        tmpl = Template('{% include "includes/_stat_card.html" with title="Test Card" value=10 href="/projects/" %}')
        rendered = tmpl.render(Context({}))
        self.assertIn('Test Card', rendered)
        self.assertIn('href="/projects/"', rendered)
        self.assertIn('aria-label=', rendered)

    def test_stat_card_template_include_without_href(self):
        tmpl = Template('{% include "includes/_stat_card.html" with title="No Href Card" value=5 %}')
        rendered = tmpl.render(Context({}))
        self.assertIn('No Href Card', rendered)
        self.assertIn('aria-label="No Href Card"', rendered)
