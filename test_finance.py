# test_finance.py
import unittest
from app import calculate_financials

class TestFinancialBusinessLogic(unittest.TestCase):

    def test_empty_projects(self):
        """Kullanıcının hiç projesi yoksa tüm finansal özetler 0 dönmeli."""
        projects = []
        gross, paid, pending = calculate_financials(projects)
        self.assertEqual(gross, 0)
        self.assertEqual(paid, 0)
        self.assertEqual(pending, 0)

    def test_mixed_project_statuses(self):
        """Paid ve Pending projeler olduğunda matematiksel toplamlar doğru hesaplanmalı."""
        projects = [
            {'budget': 1000.0, 'status': 'Paid'},
            {'budget': 500.0, 'status': 'Pending'},
            {'budget': 250.0, 'status': 'Paid'},
            {'budget': 300.0, 'status': 'Pending'}
        ]
        # Beklenen: Gross=2050, Paid=1250, Pending=800
        gross, paid, pending = calculate_financials(projects)
        self.assertEqual(gross, 2050.0)
        self.assertEqual(paid, 1250.0)
        self.assertEqual(pending, 800.0)

    def test_all_paid_projects(self):
        """Tüm projeler Paid ise Outstanding (Pending) 0 kalmalı, Gross ile Paid eşit olmalı."""
        projects = [
            {'budget': 1500.0, 'status': 'Paid'},
            {'budget': 700.0, 'status': 'Paid'}
        ]
        gross, paid, pending = calculate_financials(projects)
        self.assertEqual(gross, 2200.0)
        self.assertEqual(paid, 2200.0)
        self.assertEqual(pending, 0)

if __name__ == '__main__':
    unittest.main()