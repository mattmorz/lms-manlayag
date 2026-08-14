import frappe
from frappe.tests.utils import FrappeTestCase
from lms.lms.api import (
	get_web_playground_exercise,
	create_web_playground_submission,
	save_web_playground_exercise,
)

class TestLMSWebPlaygroundExercise(FrappeTestCase):
	def setUp(self):
		frappe.session.user = "Administrator"
		self.exercise_doc = save_web_playground_exercise({
			"title": "Test Web Playground - HTML & CSS",
			"instructions": "<p>Create a blue heading</p>",
			"starter_html": "<h1>Hello</h1>",
			"starter_css": "h1 { color: red; }",
			"starter_js": "console.log('test');",
			"solution_html": "<h1>Hello World</h1>",
			"solution_css": "h1 { color: blue; }",
			"solution_js": "console.log('solution');",
			"passing_score": 70,
			"max_attempts": 2,
			"allow_javascript": 1,
			"allow_console": 1,
			"test_cases": [
				{
					"title": "Heading Exists",
					"test_type": "Element Exists",
					"selector": "h1",
					"points": 50,
					"required": 1,
				},
				{
					"title": "Heading is Blue",
					"test_type": "CSS Property",
					"selector": "h1",
					"property": "color",
					"expected_value": "blue",
					"points": 50,
					"required": 0,
				},
			],
		})
		self.exercise_id = self.exercise_doc.get("name")

	def tearDown(self):
		frappe.session.user = "Administrator"
		if frappe.db.exists("LMS Web Playground Exercise", self.exercise_id):
			frappe.delete_doc("LMS Web Playground Exercise", self.exercise_id, force=True)
		subs = frappe.get_all("LMS Web Playground Submission", filters={"exercise": self.exercise_id}, pluck="name")
		for s in subs:
			frappe.delete_doc("LMS Web Playground Submission", s, force=True)

	def test_get_exercise_strips_solution_fields(self):
		ex = get_web_playground_exercise(self.exercise_id)
		self.assertEqual(ex.get("title"), "Test Web Playground - HTML & CSS")
		self.assertNotIn("solution_html", ex)
		self.assertNotIn("solution_css", ex)
		self.assertNotIn("solution_js", ex)
		self.assertEqual(len(ex.get("test_cases")), 2)

	def test_create_submission_and_attempt_limits(self):
		# Attempt 1
		sub1 = create_web_playground_submission(
			exercise=self.exercise_id,
			html_code="<h1>Hello</h1>",
			css_code="h1 { color: red; }",
			javascript_code="console.log('hi');",
			score=50.0,
			passed=0,
		)
		self.assertEqual(sub1.get("status"), "success")
		self.assertEqual(sub1.get("attempt_number"), 1)
		self.assertEqual(sub1.get("passed"), 0)

		# Attempt 2
		sub2 = create_web_playground_submission(
			exercise=self.exercise_id,
			html_code="<h1>Hello</h1>",
			css_code="h1 { color: blue; }",
			javascript_code="console.log('hi');",
			score=100.0,
			passed=1,
		)
		self.assertEqual(sub2.get("status"), "success")
		self.assertEqual(sub2.get("attempt_number"), 2)
		self.assertEqual(sub2.get("passed"), 1)

		# Attempt 3 (Should fail due to max_attempts = 2)
		self.assertRaises(
			frappe.ValidationError,
			create_web_playground_submission,
			exercise=self.exercise_id,
			html_code="<h1>Hello</h1>",
			score=100.0,
			passed=1,
		)
