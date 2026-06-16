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
		lesson.chapter = self.course.chapters[0].chapter
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
		self.cleanup_items.append(("Course Lesson", lesson.name))

		from lms.lms.doctype.course_lesson.course_lesson import get_video_progress
		from lms.lms.api import track_video_watch_duration

		try:
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
		finally:
			frappe.session.user = "Administrator"

	def test_in_video_quiz_verification(self):
		import json
		# Create a lesson with an embed block containing a quiz
		lesson = frappe.new_doc("Course Lesson")
		lesson.title = "Test Embed Video Quiz Lesson"
		lesson.course = self.course.name
		lesson.chapter = self.course.chapters[0].chapter
		lesson.content = json.dumps({
			"blocks": [
				{
					"type": "embed",
					"data": {
						"service": "youtube",
						"source": "https://www.youtube.com/watch?v=mock",
						"embed": "https://www.youtube.com/embed/mock",
						"quizzes": [
							{"quiz": self.quiz.name, "time": 10}
						]
					}
				}
			]
		})
		
		lesson.insert()
		self.cleanup_items.append(("Course Lesson", lesson.name))

		# Create a quiz that the student has NOT passed (do this as Administrator)
		unpassed_quiz = frappe.new_doc("LMS Quiz")
		unpassed_quiz.title = "Unpassed Quiz"
		unpassed_quiz.passing_percentage = 80
		unpassed_quiz.insert()
		self.cleanup_items.append(("LMS Quiz", unpassed_quiz.name))

		from lms.lms.doctype.course_lesson.course_lesson import get_quiz_progress

		try:
			# Login as student1
			frappe.session.user = self.student1.email

			# The student has already passed self.quiz in setup flow, so get_quiz_progress should be True
			self.assertTrue(get_quiz_progress(lesson.name))

			# Update the lesson to contain this unpassed quiz
			lesson.content = json.dumps({
				"blocks": [
					{
						"type": "embed",
						"data": {
							"service": "youtube",
							"source": "https://www.youtube.com/watch?v=mock",
							"embed": "https://www.youtube.com/embed/mock",
							"quizzes": [
								{"quiz": unpassed_quiz.name, "time": 10}
							]
						}
					}
				]
			})
			lesson.save()

			# get_quiz_progress should now be False!
			self.assertFalse(get_quiz_progress(lesson.name))
		finally:
			frappe.session.user = "Administrator"

	def test_upload_video_transcript(self):
		import json
		# Create a mock lesson
		lesson = frappe.new_doc("Course Lesson")
		lesson.title = "Test Transcript Lesson"
		lesson.course = self.course.name
		lesson.chapter = self.course.chapters[0].chapter
		lesson.youtube = "https://www.youtube.com/watch?v=mockytid"
		lesson.insert()
		self.cleanup_items.append(("Course Lesson", lesson.name))

		try:
			# Log in as moderator/instructor
			frappe.session.user = self.admin.email

			# 1. Test SRT parsing
			srt_content = """1
00:00:01,000 --> 00:00:04,500
Hello World!

2
00:00:05,100 --> 00:00:08,200
This is a test.
"""
			from lms.lms.api import upload_video_transcript
			res = upload_video_transcript(lesson.name, "mockytid", srt_content, "subtitles.srt")
			
			# Verify parsed result
			self.assertEqual(len(res), 2)
			self.assertEqual(res[0]["text"], "Hello World!")
			self.assertEqual(res[0]["start"], 1.0)
			self.assertEqual(res[0]["duration"], 3.5)
			self.assertEqual(res[1]["text"], "This is a test.")
			self.assertEqual(res[1]["start"], 5.1)
			self.assertEqual(res[1]["duration"], 3.1)

			# Verify it is saved in DB correctly
			stored_transcript_str = frappe.db.get_value("Course Lesson", lesson.name, "video_transcript")
			stored_transcript = json.loads(stored_transcript_str)
			self.assertIn("mockytid", stored_transcript)
			self.assertEqual(len(stored_transcript["mockytid"]), 2)

			# 2. Test VTT parsing
			vtt_content = """WEBVTT

00:00:01.000 --> 00:00:04.500
Hello VTT!

00:00:05.100 --> 00:00:08.200
This is vtt test.
"""
			res2 = upload_video_transcript(lesson.name, "mockytid", vtt_content, "subtitles.vtt")
			self.assertEqual(len(res2), 2)
			self.assertEqual(res2[0]["text"], "Hello VTT!")

			# 3. Test JSON parsing
			json_content = json.dumps([
				{"text": "Hello JSON!", "start": 1.0, "duration": 3.5}
			])
			res3 = upload_video_transcript(lesson.name, "mockytid", json_content, "subtitles.json")
			self.assertEqual(len(res3), 1)
			self.assertEqual(res3[0]["text"], "Hello JSON!")
		finally:
			frappe.session.user = "Administrator"
