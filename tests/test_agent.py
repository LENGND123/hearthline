import unittest

from hearthline.agent import parse, respond


class ParseTests(unittest.TestCase):
    def test_demo_remember_line(self):
        intent = parse("Remember our home in Ajmer. Riya is 8 and has asthma. I am Aditya.")
        self.assertEqual(intent.city_to_save, "Ajmer")
        names = {member["name"]: member for member in intent.members}
        self.assertEqual(names["Riya"]["age"], 8)
        self.assertEqual(names["Riya"]["role"], "child")
        self.assertEqual(names["Riya"]["note"], "asthma")
        self.assertEqual(names["Aditya"]["role"], "adult")
        self.assertFalse(intent.wants_plan)

    def test_school_brief(self):
        intent = parse("Give me the school morning brief.")
        self.assertTrue(intent.wants_plan)
        self.assertEqual(intent.focus, "school")

    def test_evening_windows(self):
        intent = parse("Should we open the windows tonight?")
        self.assertTrue(intent.wants_plan)
        self.assertEqual(intent.focus, "evening")

    def test_memory_question_is_not_a_save(self):
        intent = parse("What do you remember about our home?")
        self.assertTrue(intent.wants_memory)
        self.assertFalse(intent.members)

    def test_air_only_does_not_save_the_city(self):
        intent = parse("What's the air in Delhi?")
        self.assertTrue(intent.wants_air_only)
        self.assertEqual(intent.city_for_query, "Delhi")
        self.assertEqual(intent.city_to_save, "")

    def test_help(self):
        self.assertTrue(parse("what can you do").is_help)


class RespondTests(unittest.IsolatedAsyncioTestCase):
    async def test_remember_then_confirm_uses_only_mcp_calls(self):
        calls = []

        async def call(name, arguments):
            calls.append((name, arguments))
            if name == "remember_household":
                return {
                    "ok": True,
                    "household": {
                        "city": "Ajmer",
                        "place_label": "",
                        "members": [{"name": "Riya", "role": "child", "age": 8, "notes": ["asthma"]}],
                        "last_brief": None,
                    },
                }
            raise AssertionError(name)

        reply = await respond("Remember our home in Ajmer. Riya is 8 and has asthma.", call)
        self.assertIn("Ajmer", reply["speech"])
        self.assertIn("Riya", reply["speech"])
        self.assertEqual([name for name, _ in calls], ["remember_household", "remember_household"])
        self.assertEqual(calls[0][1]["city"], "Ajmer")
        self.assertEqual(calls[1][1]["member_name"], "Riya")

    async def test_brief_calls_plan_day(self):
        calls = []

        async def call(name, arguments):
            calls.append(name)
            if name == "plan_day":
                return {
                    "ok": True,
                    "speech": "Ajmer is at 164, unhealthy. I saved this as today's school plan.",
                    "card": {"title": "School morning", "headline": "No outdoor PE", "aqi": 164},
                }
            if name == "save_routine":
                return {"ok": True}
            raise AssertionError(name)

        reply = await respond("Give me the school morning brief.", call)
        self.assertEqual(calls, ["plan_day"])
        self.assertIn("164", reply["speech"])
        self.assertEqual(reply["card"]["headline"], "No outdoor PE")


if __name__ == "__main__":
    unittest.main()
