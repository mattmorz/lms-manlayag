# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import json
import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.doctype.course_lesson.course_lesson import save_progress, get_quiz_progress, get_assignment_progress, get_programming_exercise_progress
from lms.lms.api import create_programming_exercise_submission


class TestCourseLesson(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self.student = self._create_user("student_test@example.com", "Test", "Student", ["LMS Student"])
		self.course = self._create_course(title="Progress Course")
		self.chapter = self._create_chapter(title="Progress Chapter 1", course=self.course.name)
		self._create_enrollment(self.student.email, self.course.name)
		frappe.session.user = self.student.email

	def tearDown(self):
		frappe.session.user = "Administrator"
		super().tearDown()

	def test_lesson_with_programming_exercise(self):
		exercise = self._create_programming_exercise(title="Test Prog Exercise")
		
		# Create lesson containing this programming exercise
		lesson_content = json.dumps({
			"time": 1765194986690,
			"blocks": [
				{
					"id": "exercise_block",
					"type": "program",
					"data": { "exercise": exercise.name }
				}
			],
			"version": "2.29.0"
		})
		lesson = self._create_lesson(
			title="Programming Exercise Lesson",
			chapter=self.chapter.name,
			course=self.course.name,
			content=lesson_content
		)

		# At first, no submission exists, so progress should not be completed.
		save_progress(lesson.name, self.course.name)
		progress_exists = frappe.db.exists(
			"LMS Course Progress",
			{"lesson": lesson.name, "member": self.student.email, "status": "Complete"}
		)
		self.assertFalse(progress_exists)

		# Make submission via API
		create_programming_exercise_submission(
			exercise=exercise.name,
			submission="new",
			code="print('hello')",
			test_cases=[{"input": "1", "output": "1", "expected_output": "1", "status": "Passed"}]
		)

		# Progress should now be complete
		progress_exists = frappe.db.exists(
			"LMS Course Progress",
			{"lesson": lesson.name, "member": self.student.email, "status": "Complete"}
		)
		self.assertTrue(progress_exists)

	def test_lesson_with_graded_quiz(self):
		quiz = self._create_quiz(title="Graded Quiz")
		quiz.passing_percentage = 70
		quiz.save()
		
		# Create lesson containing this quiz (include_in_grading = 1)
		lesson_content = json.dumps({
			"time": 1765194986690,
			"blocks": [
				{
					"id": "quiz_block",
					"type": "quiz",
					"data": {
						"quiz": quiz.name,
						"include_in_grading": 1
					}
				}
			],
			"version": "2.29.0"
		})
		lesson = self._create_lesson(
			title="Graded Quiz Lesson",
			chapter=self.chapter.name,
			course=self.course.name,
			content=lesson_content
		)

		# Submission with 50% score (fails)
		sub = frappe.new_doc("LMS Quiz Submission")
		sub.update({
			"quiz": quiz.name,
			"member": self.student.email,
			"score_out_of": 10,
			"passing_percentage": 70,
			"percentage": 50.0,
		})
		sub.insert()
		self.cleanup_items.append(("LMS Quiz Submission", sub.name))

		save_progress(lesson.name, self.course.name)
		progress_exists = frappe.db.exists(
			"LMS Course Progress",
			{"lesson": lesson.name, "member": self.student.email, "status": "Complete"}
		)
		self.assertFalse(progress_exists)

		# Submission with 80% score (passes)
		sub2 = frappe.new_doc("LMS Quiz Submission")
		sub2.update({
			"quiz": quiz.name,
			"member": self.student.email,
			"score_out_of": 10,
			"passing_percentage": 70,
			"percentage": 80.0,
		})
		sub2.insert()
		self.cleanup_items.append(("LMS Quiz Submission", sub2.name))

		save_progress(lesson.name, self.course.name)
		progress_exists = frappe.db.exists(
			"LMS Course Progress",
			{"lesson": lesson.name, "member": self.student.email, "status": "Complete"}
		)
		self.assertTrue(progress_exists)

	def test_lesson_with_non_graded_quiz(self):
		quiz = self._create_quiz(title="Non-Graded Quiz")
		quiz.passing_percentage = 70
		quiz.save()
		
		# Create lesson containing this quiz (include_in_grading = 0)
		lesson_content = json.dumps({
			"time": 1765194986690,
			"blocks": [
				{
					"id": "quiz_block",
					"type": "quiz",
					"data": {
						"quiz": quiz.name,
						"include_in_grading": 0
					}
				}
			],
			"version": "2.29.0"
		})
		lesson = self._create_lesson(
			title="Non-Graded Quiz Lesson",
			chapter=self.chapter.name,
			course=self.course.name,
			content=lesson_content
		)

		# Submission with 50% score (fails passing threshold, but quiz is non-graded)
		sub = frappe.new_doc("LMS Quiz Submission")
		sub.update({
			"quiz": quiz.name,
			"member": self.student.email,
			"score_out_of": 10,
			"passing_percentage": 70,
			"percentage": 50.0,
		})
		sub.insert()
		self.cleanup_items.append(("LMS Quiz Submission", sub.name))

		save_progress(lesson.name, self.course.name)
		progress_exists = frappe.db.exists(
			"LMS Course Progress",
			{"lesson": lesson.name, "member": self.student.email, "status": "Complete"}
		)
		self.assertTrue(progress_exists)
