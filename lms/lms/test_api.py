import frappe

from lms.lms.api import get_certified_participants, get_course_assessment_progress
from lms.lms.test_helpers import BaseTestUtils


class TestLMSAPI(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._setup_course_flow()

	def test_certified_participants_with_category(self):
		filters = {"category": "Utility Course"}
		certified_participants = get_certified_participants(filters=filters)
		self.assertEqual(len(certified_participants), 1)
		self.assertEqual(certified_participants[0].member, self.student1.email)

		filters = {"category": "Nonexistent Category"}
		certified_participants_no_match = get_certified_participants(filters=filters)
		self.assertEqual(len(certified_participants_no_match), 0)

	def test_certified_participants_with_open_to_work(self):
		filters = {"open_to_work": 1}
		certified_participants_open_to_work = get_certified_participants(filters=filters)
		self.assertEqual(len(certified_participants_open_to_work), 0)

		frappe.db.set_value("User", self.student1.email, "open_to", "Work")
		certified_participants_open_to_work = get_certified_participants(filters=filters)
		self.assertEqual(len(certified_participants_open_to_work), 1)
		frappe.db.set_value("User", self.student1.email, "open_to", "")

	def test_certified_participants_with_open_to_hiring(self):
		filters = {"hiring": 1}
		certified_participants_hiring = get_certified_participants(filters=filters)
		self.assertEqual(len(certified_participants_hiring), 0)

		frappe.db.set_value("User", self.student1.email, "open_to", "Hiring")
		certified_participants_hiring = get_certified_participants(filters=filters)
		self.assertEqual(len(certified_participants_hiring), 1)
		frappe.db.set_value("User", self.student1.email, "open_to", "")

	def test_course_assessment_progress(self):
		progress = get_course_assessment_progress(self.course.name, self.student1.name)
		progress = frappe._dict(progress)

		self.assertEqual(len(progress.quizzes), 1)
		for quiz in progress.quizzes:
			self.assertEqual(quiz.quiz, self.quiz.name)
			self.assertEqual(quiz.quiz_title, self.quiz.title)
			self.assertEqual(quiz.score, 12)
			self.assertEqual(quiz.percentage, 80)

		self.assertEqual(len(progress.assignments), 1)
		for assignment in progress.assignments:
			self.assertEqual(assignment.assignment, self.assignment.name)
			self.assertEqual(assignment.assignment_title, self.assignment.title)
			self.assertEqual(assignment.status, "Pass")

		self.assertEqual(len(progress.exercises), 1)
		for exercise in progress.exercises:
			self.assertEqual(exercise.exercise, self.programming_exercise.name)
			self.assertEqual(exercise.exercise_title, self.programming_exercise.title)
			self.assertEqual(exercise.status, "Passed")

	def test_video_progress_90_percent(self):
		import json
		# Create a lesson with a video block
		lesson = frappe.new_doc("Course Lesson")
		lesson.title = "Test Video Lesson"
		lesson.course = self.course.name
		lesson.content = json.dumps({
			"blocks": [
				{
					"type": "video",
					"data": {
						"url": "https://www.youtube.com/watch?v=mock"
					}
				}
			]
		})
		lesson.insert()

		from lms.lms.doctype.course_lesson.course_lesson import get_video_progress
		from lms.lms.api import track_video_watch_duration

		# Login as student1
		frappe.session.user = self.student1.email

		# Initially, get_video_progress should return False because no watch duration exists
		self.assertFalse(get_video_progress(lesson.name))

		# Now track watch duration below 90% (e.g. 50s watch time, 100s duration)
		track_video_watch_duration(
			lesson.name,
			[{"source": "https://www.youtube.com/watch?v=mock", "watch_time": 50, "duration": 100}]
		)
		# get_video_progress should still be False
		self.assertFalse(get_video_progress(lesson.name))

		# Now track watch duration >= 90% (e.g. 95s watch time, 100s duration)
		track_video_watch_duration(
			lesson.name,
			[{"source": "https://www.youtube.com/watch?v=mock", "watch_time": 95, "duration": 100}]
		)
		# get_video_progress should now be True!
		self.assertTrue(get_video_progress(lesson.name))

		# Clean up
		lesson.delete()
		frappe.session.user = "Administrator"
