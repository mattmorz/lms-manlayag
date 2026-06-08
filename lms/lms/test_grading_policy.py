# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import frappe
from frappe.utils import add_to_date, now_datetime, get_datetime, nowdate
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.api import get_student_grades


class TestGradingPolicy(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._setup_course_flow()

	def test_grading_policy_disabled(self):
		# By default, grading policy should be disabled.
		grades = get_student_grades(self.course.name, self.student1.email)
		self.assertFalse(grades.get("enable_grading_policy"))
		self.assertEqual(grades.get("final_percentage"), 0)
		self.assertEqual(grades.get("final_grade"), "N/A")

	def test_weighted_grade_calculation(self):
		# Create a course specific to this test
		course = self._create_course(title="Grading Course 1")
		course.enable_grading_policy = 1
		course.grading_grace_period = 0

		# Add categories: Homework (40%), Exam (60%)
		course.append("grading_categories", {
			"category_name": "Homework",
			"weight": 40,
			"drop_lowest": 0
		})
		course.append("grading_categories", {
			"category_name": "Exam",
			"weight": 60,
			"drop_lowest": 0
		})

		# Add grading scale: A >= 90, B >= 80, Pass >= 50, Fail >= 0
		course.append("grading_scale", {"grade": "A", "min_percentage": 90})
		course.append("grading_scale", {"grade": "B", "min_percentage": 80})
		course.append("grading_scale", {"grade": "Pass", "min_percentage": 50})
		course.append("grading_scale", {"grade": "Fail", "min_percentage": 0})
		course.save()

		# Create a quiz and an assignment assigned to these categories
		quiz = self._create_quiz(title="Course 1 Exam")
		quiz.course = course.name
		quiz.grading_category = "Exam"
		quiz.save()

		assignment = self._create_assignment(title="Course 1 Homework")
		assignment.course = course.name
		assignment.grading_category = "Homework"
		assignment.save()

		# Setup student submissions
		# Quiz submission: 90%
		q_sub = frappe.new_doc("LMS Quiz Submission")
		q_sub.update({
			"quiz": quiz.name,
			"member": self.student1.email,
			"score_out_of": 10,
			"passing_percentage": 70,
			"percentage": 90.0,
		})
		q_sub.insert()
		self.cleanup_items.append(("LMS Quiz Submission", q_sub.name))

		# Assignment submission: 80% (numeric score)
		a_sub = frappe.new_doc("LMS Assignment Submission")
		a_sub.update({
			"assignment": assignment.name,
			"member": self.student1.email,
			"answer": "Homework answer",
			"score": 80,
			"status": "Pass"
		})
		a_sub.insert()
		self.cleanup_items.append(("LMS Assignment Submission", a_sub.name))

		# Fetch student grades
		grades = get_student_grades(course.name, self.student1.email)
		self.assertTrue(grades.get("enable_grading_policy"))
		
		# Weighted score: 0.40 * 80 + 0.60 * 90 = 32 + 54 = 86
		self.assertEqual(grades.get("final_percentage"), 86.0)
		self.assertEqual(grades.get("final_grade"), "B")

	def test_drop_lowest_scores(self):
		# Create a course specific to this test
		course = self._create_course(title="Grading Course 2")
		course.enable_grading_policy = 1
		course.grading_grace_period = 0

		# Add category Homework (100%) with drop_lowest = 1
		course.append("grading_categories", {
			"category_name": "Homework",
			"weight": 100,
			"drop_lowest": 1
		})
		course.save()

		# Create two Homework assignments
		a1 = self._create_assignment(title="Course 2 Homework 1")
		a1.course = course.name
		a1.grading_category = "Homework"
		a1.save()

		a2 = self._create_assignment(title="Course 2 Homework 2")
		a2.course = course.name
		a2.grading_category = "Homework"
		a2.save()

		# Submissions
		# Homework 1: 50%
		sub1 = frappe.new_doc("LMS Assignment Submission")
		sub1.update({
			"assignment": a1.name,
			"member": self.student1.email,
			"answer": "Homework 1 answer",
			"score": 50,
			"status": "Pass"
		})
		sub1.insert()
		self.cleanup_items.append(("LMS Assignment Submission", sub1.name))

		# Homework 2: 95%
		sub2 = frappe.new_doc("LMS Assignment Submission")
		sub2.update({
			"assignment": a2.name,
			"member": self.student1.email,
			"answer": "Homework 2 answer",
			"score": 95,
			"status": "Pass"
		})
		sub2.insert()
		self.cleanup_items.append(("LMS Assignment Submission", sub2.name))

		# Fetch student grades
		grades = get_student_grades(course.name, self.student1.email)
		
		# The lowest (50%) should be dropped, leaving 95%
		self.assertEqual(grades.get("final_percentage"), 95.0)

		# Verify dropped flag is set in category results returned to UI
		cat_homework = next(c for c in grades.get("categories") if c["category_name"] == "Homework")
		dropped_items = [i for i in cat_homework["items"] if i.get("dropped")]
		self.assertEqual(len(dropped_items), 1)
		self.assertEqual(dropped_items[0]["name"], a1.name)

	def test_late_submission_penalty(self):
		course = self._create_course(title="Grading Course 3")
		course.enable_grading_policy = 1
		course.grading_grace_period = 2 # 2 hours grace period

		course.append("grading_categories", {
			"category_name": "Homework",
			"weight": 100,
			"drop_lowest": 0
		})
		course.save()

		# Assignment due date and time
		due_date = nowdate()
		due_time = "12:00:00"

		a1 = self._create_assignment(title="Course 3 Homework 1")
		a1.course = course.name
		a1.grading_category = "Homework"
		a1.due_date = due_date
		a1.due_time = due_time
		a1.save()

		# Student 1: Submit 1 hour after deadline (within grace period of 2 hours) -> No penalty
		sub1 = frappe.new_doc("LMS Assignment Submission")
		sub1.update({
			"assignment": a1.name,
			"member": self.student1.email,
			"answer": "On time within grace",
			"score": 90,
			"status": "Pass"
		})
		sub1.insert()
		self.cleanup_items.append(("LMS Assignment Submission", sub1.name))

		# Set creation time of sub1 to 1 hour after due time
		due_dt = get_datetime(f"{due_date} {due_time}")
		on_time_dt = add_to_date(due_dt, hours=1)
		frappe.db.set_value("LMS Assignment Submission", sub1.name, "creation", on_time_dt)

		# Fetch grades for student 1
		grades1 = get_student_grades(course.name, self.student1.email)
		self.assertEqual(grades1.get("final_percentage"), 90.0)

		# Student 2: Submit 3 hours after deadline (exceeds grace period of 2 hours) -> Penalty (evaluated as 0%)
		sub2 = frappe.new_doc("LMS Assignment Submission")
		sub2.update({
			"assignment": a1.name,
			"member": self.student2.email,
			"answer": "Late submission",
			"score": 90,
			"status": "Pass"
		})
		sub2.insert()
		self.cleanup_items.append(("LMS Assignment Submission", sub2.name))

		# Set creation time of sub2 to 3 hours after due time
		late_dt = add_to_date(due_dt, hours=3)
		frappe.db.set_value("LMS Assignment Submission", sub2.name, "creation", late_dt)

		# Fetch grades for student 2
		grades2 = get_student_grades(course.name, self.student2.email)
		self.assertEqual(grades2.get("final_percentage"), 0.0)

	def test_assignment_pass_fail_fallback(self):
		course = self._create_course(title="Grading Course 4")
		course.enable_grading_policy = 1
		course.grading_grace_period = 0

		course.append("grading_categories", {
			"category_name": "Homework",
			"weight": 100,
			"drop_lowest": 0
		})
		course.save()

		a1 = self._create_assignment(title="Course 4 Homework 1")
		a1.course = course.name
		a1.grading_category = "Homework"
		a1.save()

		# Submission with status "Pass" but no score
		sub = frappe.new_doc("LMS Assignment Submission")
		sub.update({
			"assignment": a1.name,
			"member": self.student1.email,
			"answer": "Pass fail answer",
			"status": "Pass"
		})
		# Clear score field explicitly to test fallback
		sub.score = None
		sub.insert()
		self.cleanup_items.append(("LMS Assignment Submission", sub.name))

		grades = get_student_grades(course.name, self.student1.email)
		# Should fallback Pass -> 100%
		self.assertEqual(grades.get("final_percentage"), 100.0)
