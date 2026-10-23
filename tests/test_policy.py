import unittest

from hearthline.aqi import band_for, parse_air, parse_geocode, pm25_to_us_aqi
from hearthline.policy import build_plan


class AirScaleTests(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(band_for(42), "Good")
        self.assertEqual(band_for(80), "Moderate")
        self.assertEqual(band_for(120), "Unhealthy for Sensitive Groups")
        self.assertEqual(band_for(164), "Unhealthy")
        self.assertEqual(band_for(240), "Very Unhealthy")
        self.assertEqual(band_for(320), "Hazardous")

    def test_pm25_breakpoints(self):
        self.assertEqual(pm25_to_us_aqi(0), 0)
        self.assertLessEqual(pm25_to_us_aqi(10), 50)
        self.assertGreaterEqual(pm25_to_us_aqi(40), 101)
        self.assertLessEqual(pm25_to_us_aqi(40), 150)
        self.assertGreaterEqual(pm25_to_us_aqi(80), 151)
        self.assertLessEqual(pm25_to_us_aqi(80), 200)

    def test_parsers(self):
        place = parse_geocode(
            {"results": [{"name": "Ajmer", "admin1": "Rajasthan", "country": "India", "latitude": 26.4, "longitude": 74.6}]},
            "ajmer",
        )
        self.assertEqual(place["label"], "Ajmer, Rajasthan, India")
        reading = parse_air(
            {"current": {"us_aqi": 164, "pm2_5": 80.2, "pm10": 120, "time": "2026-10-24T00:00"}},
            place,
        )
        self.assertEqual(reading["us_aqi"], 164)
        self.assertEqual(reading["band"], "Unhealthy")
        self.assertEqual(reading["aqi_basis"], "us_aqi")

        estimated = parse_air({"current": {"pm2_5": 10}}, place)
        self.assertEqual(estimated["aqi_basis"], "pm2_5_estimate")
        self.assertLessEqual(estimated["us_aqi"], 50)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.home = {
            "city": "Ajmer",
            "place_label": "Ajmer, Rajasthan, India",
            "members": [
                {"name": "Riya", "role": "child", "age": 8, "notes": ["asthma"]},
                {"name": "Aditya", "role": "adult", "age": None, "notes": []},
            ],
        }

    def test_school_plan_keeps_riya_inside_when_unhealthy(self):
        air = {"us_aqi": 164, "band": "Unhealthy", "pm2_5": 80.2, "place_label": "Ajmer, Rajasthan, India", "city": "Ajmer"}
        plan = build_plan(self.home, air, "school")
        self.assertIn("164", plan["speech"])
        self.assertIn("Riya", plan["speech"])
        self.assertIn("saved this as today's school plan", plan["speech"])
        labels = [item["label"] for item in plan["card"]["actions"]]
        self.assertIn("No outdoor PE", labels)
        self.assertEqual(plan["card"]["people"][0]["note"], "asthma")

    def test_good_air_opens_the_evening(self):
        air = {"us_aqi": 38, "band": "Good", "pm2_5": 8, "place_label": "Ajmer, Rajasthan, India", "city": "Ajmer"}
        plan = build_plan(self.home, air, "evening")
        self.assertIn("Open the windows", plan["speech"])
        self.assertIn("balcony", plan["speech"].lower())

    def test_moderate_school_and_evening_give_different_moves(self):
        air = {"us_aqi": 74, "band": "Moderate", "pm2_5": 20, "place_label": "Ajmer, Rajasthan, India", "city": "Ajmer"}
        school = build_plan(self.home, air, "school")
        evening = build_plan(self.home, air, "evening")
        self.assertIn("short for Riya", school["speech"])
        self.assertIn("balcony", evening["speech"].lower())
        self.assertNotEqual(school["card"]["headline"], evening["card"]["headline"])

    def test_unknown_household_asks_who_lives_there(self):
        air = {"us_aqi": 130, "band": "Unhealthy for Sensitive Groups", "pm2_5": 45, "place_label": "Delhi, India", "city": "Delhi"}
        plan = build_plan({"city": "Delhi", "members": []}, air, "now")
        self.assertIn("who lives here", plan["speech"])


if __name__ == "__main__":
    unittest.main()
