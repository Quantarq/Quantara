from decimal import Decimal
import unittest

from web_app.contract_tools.amounts import from_stellar_units, to_stellar_units


class AmountHelperTests(unittest.TestCase):
    def test_from_stellar_units_scales_decimal_amounts_to_raw_units(self):
        self.assertEqual(from_stellar_units(Decimal("1.5"), 7), 15_000_000)
        self.assertEqual(from_stellar_units("0.01", 2), 1)

    def test_from_stellar_units_uses_round_half_up_boundary_policy(self):
        self.assertEqual(from_stellar_units("1.23456784", 7), 12_345_678)
        self.assertEqual(from_stellar_units("1.23456785", 7), 12_345_679)

    def test_to_stellar_units_restores_raw_amounts(self):
        self.assertEqual(to_stellar_units(15_000_000, 7), Decimal("1.5000000"))
        self.assertEqual(to_stellar_units(1, 2), Decimal("0.01"))


if __name__ == "__main__":
    unittest.main()
