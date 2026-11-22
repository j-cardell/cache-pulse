import unittest

from cache_pulse.core import run


class SmokeTest(unittest.TestCase):
    def test_run(self) -> None:
        self.assertEqual(run(), "ok")


if __name__ == "__main__":
    unittest.main()
