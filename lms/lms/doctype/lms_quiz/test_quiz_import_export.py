# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import unittest
import frappe
from lms.lms.api import import_quiz, export_quiz


class TestQuizImportExport(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		# Clean up any leftover test quizzes/questions from prior aborted runs
		for title in ["Import Export Test Quiz", "GIFT Test Quiz"]:
			quizzes = frappe.get_all("LMS Quiz", {"title": title}, pluck="name")
			for q_name in quizzes:
				frappe.delete_doc("LMS Quiz", q_name, force=True)
		
		# Also delete test questions
		for pattern in ["%Import Export Test Quiz%", "%is abbreviation%", "%Paris?%", "%Two plus two%", "%2 + 2%"]:
			questions = frappe.get_all("LMS Question", {"question": ["like", pattern]}, pluck="name")
			for qst_name in questions:
				frappe.delete_doc("LMS Question", qst_name, force=True)
		frappe.db.commit()

		# Create a test quiz
		cls.quiz = frappe.get_doc({
			"doctype": "LMS Quiz",
			"title": "Import Export Test Quiz",
			"passing_percentage": 50
		}).insert(ignore_permissions=True)

	def test_import_export_aiken(self):
		# Clean up any existing questions in self.quiz
		self.quiz.questions = []
		self.quiz.save(ignore_permissions=True)

		aiken_content = (
			"What is 2 + 2?\n"
			"A. 3\n"
			"B. 4\n"
			"C. 5\n"
			"ANSWER: B\n"
		)
		
		# Set mock instructor session
		frappe.session.user = "Administrator"

		# Import aiken content
		import_quiz(self.quiz.name, aiken_content, "AIKEN")

		# Reload quiz and assert questions added
		self.quiz.reload()
		self.assertEqual(len(self.quiz.questions), 1)

		q_doc = frappe.get_doc("LMS Question", self.quiz.questions[0].question)
		self.assertEqual(q_doc.type, "Choices")
		self.assertEqual(q_doc.question, "What is 2 + 2?")
		self.assertEqual(q_doc.option_1, "3")
		self.assertEqual(q_doc.option_2, "4")
		self.assertEqual(q_doc.option_3, "5")
		self.assertEqual(q_doc.is_correct_2, 1)
		self.assertEqual(q_doc.is_correct_1, 0)

		# Test export
		exported_content = export_quiz(self.quiz.name, "AIKEN")
		self.assertIn("What is 2 + 2?", exported_content)
		self.assertIn("B. 4", exported_content)
		self.assertIn("ANSWER: B", exported_content)

		# Clean questions for next test
		self.quiz.questions = []
		self.quiz.save(ignore_permissions=True)

		# Test lowercase prefixes and lowercase answer letter
		lowercase_aiken = (
			"What is c?\n"
			"a. programming language\n"
			"b. letter\n"
			"ANSWER: a\n"
		)
		import_quiz(self.quiz.name, lowercase_aiken, "AIKEN")
		self.quiz.reload()
		self.assertEqual(len(self.quiz.questions), 1)
		q_doc_lc = frappe.get_doc("LMS Question", self.quiz.questions[0].question)
		self.assertEqual(q_doc_lc.option_1, "programming language")
		self.assertEqual(q_doc_lc.option_2, "letter")
		self.assertEqual(q_doc_lc.is_correct_1, 1)
		self.assertEqual(q_doc_lc.is_correct_2, 0)

		# Test validation throws if fewer than 2 options
		invalid_aiken = (
			"What is d?\n"
			"a. single option\n"
			"ANSWER: a\n"
		)
		self.assertRaises(frappe.ValidationError, import_quiz, self.quiz.name, invalid_aiken, "AIKEN")

	def test_import_special_characters(self):
		self.quiz.questions = []
		self.quiz.save(ignore_permissions=True)

		special_aiken = (
			"Which header is used for stdio in C?\n"
			"A. <stdio.h>\n"
			"B. <iostream>\n"
			"C. Vector<int>\n"
			"D. 5 < 10 && 10 > 5\n"
			"ANSWER: A\n"
		)
		frappe.session.user = "Administrator"
		import_quiz(self.quiz.name, special_aiken, "AIKEN")

		self.quiz.reload()
		self.assertEqual(len(self.quiz.questions), 1)
		q_doc = frappe.get_doc("LMS Question", self.quiz.questions[0].question)
		self.assertEqual(q_doc.question, "Which header is used for stdio in C?")
		self.assertEqual(q_doc.option_1, "<stdio.h>")
		self.assertEqual(q_doc.option_2, "<iostream>")
		self.assertEqual(q_doc.option_3, "Vector<int>")
		self.assertEqual(q_doc.option_4, "5 < 10 && 10 > 5")

	def test_import_export_gift(self):
		# Create a clean quiz
		gift_quiz = frappe.get_doc({
			"doctype": "LMS Quiz",
			"title": "GIFT Test Quiz",
			"passing_percentage": 50
		}).insert(ignore_permissions=True)

		try:
			gift_content = (
				"::Q1:: Moodle is an abbreviation for? {\n"
				"    =Modular Object-Oriented Dynamic Learning Environment\n"
				"    ~Modular Object-Oriented Digital Learning Environment\n"
				"}\n\n"
				"::Q2:: Is capital of France Paris? {T}\n\n"
				"::Q3:: Two plus two is? {=4 =four}\n"
			)

			import_quiz(gift_quiz.name, gift_content, "GIFT")

			gift_quiz.reload()
			self.assertEqual(len(gift_quiz.questions), 3)

			# Q1
			q1 = frappe.get_doc("LMS Question", gift_quiz.questions[0].question)
			self.assertEqual(q1.type, "Choices")
			self.assertEqual(q1.option_1, "Modular Object-Oriented Dynamic Learning Environment")
			self.assertEqual(q1.is_correct_1, 1)

			# Q2
			q2 = frappe.get_doc("LMS Question", gift_quiz.questions[1].question)
			self.assertEqual(q2.type, "Choices")
			self.assertEqual(q2.option_1, "True")
			self.assertEqual(q2.is_correct_1, 1)

			# Q3
			q3 = frappe.get_doc("LMS Question", gift_quiz.questions[2].question)
			self.assertEqual(q3.type, "User Input")
			self.assertEqual(q3.possibility_1, "4")
			self.assertEqual(q3.possibility_2, "four")

			# Test partial export
			import json
			# Select only the first question
			selected_ref = [gift_quiz.questions[0].name]
			partial_gift = export_quiz(gift_quiz.name, "GIFT", questions=json.dumps(selected_ref))
			self.assertIn("Moodle is an abbreviation for?", partial_gift)
			self.assertNotIn("Is capital of France Paris?", partial_gift)
			self.assertNotIn("Two plus two is?", partial_gift)
		finally:
			# Clean up
			if frappe.db.exists("LMS Quiz", gift_quiz.name):
				frappe.delete_doc("LMS Quiz", gift_quiz.name, force=True)

	@classmethod
	def tearDownClass(cls) -> None:
		if frappe.db.exists("LMS Quiz", cls.quiz.name):
			frappe.delete_doc("LMS Quiz", cls.quiz.name, force=True)
		
		# Deletes questions matching our pattern
		for pattern in ["%Import Export Test Quiz%", "%is abbreviation%", "%Paris?%", "%Two plus two%", "%2 + 2%"]:
			questions = frappe.get_all("LMS Question", {"question": ["like", pattern]}, pluck="name")
			for qst_name in questions:
				frappe.delete_doc("LMS Question", qst_name, force=True)
		frappe.db.commit()
