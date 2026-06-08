# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import json
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
			"number_of_assessments": 5
		})
		course.append("grading_categories", {
			"category_name": "Exam",
			"weight": 60,
			"number_of_assessments": 1
		})

		# Add grading scale: A >= 90, B >= 80, Pass >= 50, Fail >= 0
		course.append("grading_scale", {"grade": "A", "min_percentage": 90})
		course.append("grading_scale", {"grade": "B", "min_percentage": 80})
		course.append("grading_scale", {"grade": "Pass", "min_percentage": 50})
		course.append("grading_scale", {"grade": "Fail", "min_percentage": 0})
		course.save()

		# Create a chapter
		chapter = self._create_chapter(title="Chapter 1", course=course.name)

		# Create a quiz and an assignment assigned to these categories
		quiz = self._create_quiz(title="Course 1 Exam")
		assignment = self._create_assignment(title="Course 1 Homework")

		# Create a lesson containing the quiz and assignment with their categories
		lesson = self._create_lesson(
			title="Lesson 1",
			chapter=chapter.name,
			course=course.name,
			content=json.dumps({
				"time": 1765194986690,
				"blocks": [
					{
						"id": "quiz1",
						"type": "quiz",
						"data": {
							"quiz": quiz.name,
							"grading_category": "Exam"
						}
					},
					{
						"id": "assignment1",
						"type": "assignment",
						"data": {
							"assignment": assignment.name,
							"grading_category": "Homework"
						}
					}
				],
				"version": "2.29.0"
			})
		)

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

	def test_category_assessment_limit(self):
		# Create a course specific to this test
		course = self._create_course(title="Grading Course 2")
		course.enable_grading_policy = 1
		course.grading_grace_period = 0

		# Add category Homework (100%) with number_of_assessments = 2
		course.append("grading_categories", {
			"category_name": "Homework",
			"weight": 100,
			"number_of_assessments": 2
		})
		course.save()

		# Create a chapter
		chapter = self._create_chapter(title="Chapter 1", course=course.name)

		# Create three Homework assignments
		a1 = self._create_assignment(title="Course 2 Homework 1")
		a2 = self._create_assignment(title="Course 2 Homework 2")
		a3 = self._create_assignment(title="Course 2 Homework 3")

		# Creating a lesson with 2 homeworks should succeed
		lesson1 = self._create_lesson(
			title="Lesson 1",
			chapter=chapter.name,
			course=course.name,
			content=json.dumps({
				"blocks": [
					{
						"id": "asg1",
						"type": "assignment",
						"data": {
							"assignment": a1.name,
							"grading_category": "Homework"
						}
					},
					{
						"id": "asg2",
						"type": "assignment",
						"data": {
							"assignment": a2.name,
							"grading_category": "Homework"
						}
					}
				]
			})
		)

		# Creating a second lesson that pushes the category count to 3 should raise ValidationError
		with self.assertRaises(frappe.ValidationError):
			lesson2 = frappe.new_doc("Course Lesson")
			lesson2.update({
				"title": "Lesson 2",
				"chapter": chapter.name,
				"course": course.name,
				"content": json.dumps({
					"blocks": [
						{
							"id": "asg3",
							"type": "assignment",
							"data": {
								"assignment": a3.name,
								"grading_category": "Homework"
							}
						}
					]
				})
			})
			lesson2.insert()

		# Creating a quiz in the same category should also throw ValidationError because count includes quizzes
		q = self._create_quiz(title="Course 2 Homework Quiz")
		with self.assertRaises(frappe.ValidationError):
			lesson2_quiz = frappe.new_doc("Course Lesson")
			lesson2_quiz.update({
				"title": "Lesson 2 Quiz",
				"chapter": chapter.name,
				"course": course.name,
				"content": json.dumps({
					"blocks": [
						{
							"id": "quiz1",
							"type": "quiz",
							"data": {
								"quiz": q.name,
								"grading_category": "Homework"
							}
						}
					]
				})
			})
			lesson2_quiz.insert()

		# Try to create a quiz without category when policy is enabled -> throws ValidationError
		with self.assertRaises(frappe.ValidationError):
			lesson_nocat = frappe.new_doc("Course Lesson")
			lesson_nocat.update({
				"title": "No Cat Quiz Lesson",
				"chapter": chapter.name,
				"course": course.name,
				"content": json.dumps({
					"blocks": [
						{
							"id": "quiz_nocat",
							"type": "quiz",
							"data": {
								"quiz": q.name
							}
						}
					]
				})
			})
			lesson_nocat.insert()

	def test_late_submission_penalty(self):
		course = self._create_course(title="Grading Course 3")
		course.enable_grading_policy = 1
		course.grading_grace_period = 2 # 2 hours grace period

		course.append("grading_categories", {
			"category_name": "Homework",
			"weight": 100,
			"number_of_assessments": 5
		})
		course.save()

		# Create a chapter
		chapter = self._create_chapter(title="Chapter 1", course=course.name)

		# Assignment due date and time
		due_date = nowdate()
		due_time = "12:00:00"

		a1 = self._create_assignment(title="Course 3 Homework 1")
		
		# Create lesson with due date/time on assignment block
		lesson = self._create_lesson(
			title="Lesson 1",
			chapter=chapter.name,
			course=course.name,
			content=json.dumps({
				"blocks": [
					{
						"id": "asg1",
						"type": "assignment",
						"data": {
							"assignment": a1.name,
							"grading_category": "Homework",
							"due_date": due_date,
							"due_time": due_time
						}
					}
				]
			})
		)

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
			"number_of_assessments": 5
		})
		course.save()

		chapter = self._create_chapter(title="Chapter 1", course=course.name)
		a1 = self._create_assignment(title="Course 4 Homework 1")
		lesson = self._create_lesson(
			title="Lesson 1",
			chapter=chapter.name,
			course=course.name,
			content=json.dumps({
				"blocks": [
					{
						"id": "asg1",
						"type": "assignment",
						"data": {
							"assignment": a1.name,
							"grading_category": "Homework"
						}
					}
				]
			})
		)

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

	def test_course_import_export_with_grading_policy(self):
		import json
		from lms.lms.api import export_course, import_course

		# 1. Setup course with grading policy
		course = self._create_course(title="IE Grading Course")
		course.enable_grading_policy = 1
		course.grading_grace_period = 3
		course.append("grading_categories", {
			"category_name": "Homework",
			"weight": 30,
			"number_of_assessments": 3
		})
		course.append("grading_categories", {
			"category_name": "Exam",
			"weight": 70,
			"number_of_assessments": 1
		})
		course.append("grading_scale", {"grade": "A", "min_percentage": 90})
		course.append("grading_scale", {"grade": "B", "min_percentage": 80})
		course.save()

		chapter = self._create_chapter(title="Chapter 1", course=course.name)
		course.reload()
		course.append("chapters", {"chapter": chapter.name})
		course.save()

		quiz = self._create_quiz(title="IE Quiz")
		assignment = self._create_assignment(title="IE Assignment")

		lesson = self._create_lesson(
			title="Lesson 1",
			chapter=chapter.name,
			course=course.name,
			content=json.dumps({
				"blocks": [
					{
						"id": "quiz1",
						"type": "quiz",
						"data": {
							"quiz": quiz.name,
							"grading_category": "Exam",
							"due_date": "2026-06-15",
							"due_time": "18:00:00"
						}
					},
					{
						"id": "assignment1",
						"type": "assignment",
						"data": {
							"assignment": assignment.name,
							"grading_category": "Homework",
							"due_date": "2026-06-20",
							"due_time": "23:59:59"
						}
					}
				]
			})
		)
		chapter.reload()
		chapter.append("lessons", {"lesson": lesson.name})
		chapter.save()

		# 2. Export course
		exported = export_course(course.name)
		
		# Verify export structure and values
		self.assertEqual(exported["course"]["enable_grading_policy"], 1)
		self.assertEqual(exported["course"]["grading_grace_period"], 3)
		self.assertEqual(len(exported["course"]["grading_categories"]), 2)
		self.assertEqual(len(exported["course"]["grading_scale"]), 2)
		
		# Verify child tables do not have internal fields like parent/name
		for cat in exported["course"]["grading_categories"]:
			self.assertNotIn("name", cat)
			self.assertNotIn("parent", cat)
		for scale in exported["course"]["grading_scale"]:
			self.assertNotIn("name", scale)
			self.assertNotIn("parent", scale)

		# 3. Import course
		imported_res = import_course(exported)
		# imported_res is either the name of the new course or response dict
		imported_course_name = imported_res if isinstance(imported_res, str) else imported_res.get("name")
		
		self.assertTrue(frappe.db.exists("LMS Course", imported_course_name))
		imported_course = frappe.get_doc("LMS Course", imported_course_name)
		self.cleanup_items.append(("LMS Course", imported_course.name))

		# Verify imported course details
		self.assertEqual(imported_course.enable_grading_policy, 1)
		self.assertEqual(imported_course.grading_grace_period, 3)
		self.assertEqual(len(imported_course.grading_categories), 2)
		self.assertEqual(len(imported_course.grading_scale), 2)

		# Verify imported lessons contain mapped quiz/assignment with correct categories/deadlines
		imported_lessons = frappe.get_all(
			"Course Lesson",
			filters={"course": imported_course.name},
			fields=["content", "name"]
		)
		self.assertEqual(len(imported_lessons), 1)
		imported_content = json.loads(imported_lessons[0].content)
		
		blocks = imported_content.get("blocks", [])
		self.assertEqual(len(blocks), 2)
		
		quiz_block = next(b for b in blocks if b["type"] == "quiz")
		self.assertNotEqual(quiz_block["data"]["quiz"], quiz.name) # Must be remapped
		self.assertEqual(quiz_block["data"]["grading_category"], "Exam")
		self.assertEqual(quiz_block["data"]["due_date"], "2026-06-15")
		self.assertEqual(quiz_block["data"]["due_time"], "18:00:00")

		assignment_block = next(b for b in blocks if b["type"] == "assignment")
		self.assertNotEqual(assignment_block["data"]["assignment"], assignment.name) # Must be remapped
		self.assertEqual(assignment_block["data"]["grading_category"], "Homework")
		self.assertEqual(assignment_block["data"]["due_date"], "2026-06-20")
		self.assertEqual(assignment_block["data"]["due_time"], "23:59:59")

	def test_unique_quiz_per_course(self):
		course = self._create_course(title="Unique Quiz Course")
		chapter = self._create_chapter(title="Chapter 1", course=course.name)
		quiz = self._create_quiz(title="Unique Quiz")

		# Create a lesson with this quiz
		lesson1 = self._create_lesson(
			title="Lesson 1",
			chapter=chapter.name,
			course=course.name,
			content=json.dumps({
				"blocks": [
					{
						"id": "quiz1",
						"type": "quiz",
						"data": {
							"quiz": quiz.name
						}
					}
				]
			})
		)

		# Attempting to create a second lesson in the same course with the same quiz should raise ValidationError
		with self.assertRaises(frappe.ValidationError):
			lesson2 = frappe.new_doc("Course Lesson")
			lesson2.update({
				"title": "Lesson 2",
				"chapter": chapter.name,
				"course": course.name,
				"content": json.dumps({
					"blocks": [
						{
							"id": "quiz_dup",
							"type": "quiz",
							"data": {
								"quiz": quiz.name
							}
						}
					]
				})
			})
			lesson2.insert()

		# Attempting to add the same quiz multiple times in the same lesson should also throw ValidationError
		with self.assertRaises(frappe.ValidationError):
			lesson3 = frappe.new_doc("Course Lesson")
			lesson3.update({
				"title": "Lesson 3",
				"chapter": chapter.name,
				"course": course.name,
				"content": json.dumps({
					"blocks": [
						{
							"id": "quiz_a",
							"type": "quiz",
							"data": {
								"quiz": quiz.name
							}
						},
						{
							"id": "quiz_b",
							"type": "quiz",
							"data": {
								"quiz": quiz.name
							}
						}
					]
				})
			})
			lesson3.insert()


