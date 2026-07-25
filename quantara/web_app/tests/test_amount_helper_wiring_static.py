from pathlib import Path
import unittest


WEB_APP_ROOT = Path(__file__).resolve().parents[1]


class AmountHelperWiringStaticTests(unittest.TestCase):
    def test_distributed_raw_unit_conversions_use_amount_helper(self):
        source_roots = [
            WEB_APP_ROOT / "api" / "position.py",
            WEB_APP_ROOT / "contract_tools" / "mixins" / "deposit.py",
            WEB_APP_ROOT / "contract_tools" / "mixins" / "health_ratio.py",
        ]
        joined_source = "\n".join(path.read_text() for path in source_roots)

        self.assertIn("from_stellar_units(", joined_source)
        self.assertIn("to_stellar_units(", joined_source)
        self.assertNotIn("int(Decimal(amount) * 10 **", joined_source)
        self.assertNotIn("Decimal(10 ** int(TokenParams.get_token_decimals", joined_source)


if __name__ == "__main__":
    unittest.main()
