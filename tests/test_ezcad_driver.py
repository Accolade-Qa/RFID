"""Unit tests for Laser Driver (Simulation Mode & Error Handling)."""

import unittest
from laser.ezcad_driver import SimulationEzcadDriver, create_laser_driver
from laser.errors import EZCADError, EZCAD_ERROR_MESSAGES


class TestEzcadDriver(unittest.TestCase):
    def test_simulation_driver_lifecycle(self):
        driver = SimulationEzcadDriver("C:/Fake/Path")
        self.assertFalse(driver.is_initialized())

        driver.initialize("C:/Fake/Path")
        self.assertTrue(driver.is_initialized())

        driver.load_template("C:/Fake/Path/test.ezd")
        entities = driver.list_entities()
        self.assertIn("t1", entities)

        ok, msg = driver.change_text("t1", "TEST_TAG_VALUE_999")
        self.assertTrue(ok)
        self.assertIn("TEST_TAG_VALUE_999", msg)

        ok_mark, mark_msg = driver.mark(fly_mark=False)
        self.assertTrue(ok_mark)
        self.assertIn("completed", mark_msg)

        driver.close()
        self.assertFalse(driver.is_initialized())

    def test_factory_creates_simulation(self):
        driver = create_laser_driver("C:/Fake/Path", simulation_mode=True)
        self.assertTrue(driver.is_initialized())
        self.assertIsInstance(driver, SimulationEzcadDriver)

    def test_error_lookup(self):
        err = EZCADError(4, "Init")
        self.assertIn("No valid LMC1 device", str(err))


if __name__ == "__main__":
    unittest.main()
