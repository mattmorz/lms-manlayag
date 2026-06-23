import frappe

from lms.lms.api import get_certified_participants, get_course_assessment_progress
from lms.lms.test_helpers import BaseTestUtils


class TestLMSAPI(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self._setup_course_flow()

	def switch_user(self, user):
		frappe.set_user(user)
		frappe.cache.hdel("roles", user)
		frappe.clear_cache(user=user)
		frappe.local.cache = {}
		if hasattr(frappe.local, "roles"):
			frappe.local.roles = None

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

		from lms.lms.doctype.course_lesson.course_lesson import get_video_progress
		from lms.lms.api import track_video_watch_duration

		# Login as student1
		self.switch_user(self.student1.email)

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
		self.switch_user("Administrator")
		frappe.delete_doc("Course Lesson", lesson.name, force=True)

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
		
		from lms.lms.doctype.course_lesson.course_lesson import get_quiz_progress
 
		# Login as student1
		self.switch_user(self.student1.email)
 
		# The student has already passed self.quiz in setup flow, so get_quiz_progress should be True
		self.assertTrue(get_quiz_progress(lesson.name))
 
		# Now create a quiz that the student has NOT passed
		self.switch_user("Administrator")
		unpassed_quiz = frappe.new_doc("LMS Quiz")
		unpassed_quiz.title = "Unpassed Quiz"
		unpassed_quiz.passing_percentage = 80
		unpassed_quiz.insert()
 
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
 
		self.switch_user(self.student1.email)
		# get_quiz_progress should now be False!
		self.assertFalse(get_quiz_progress(lesson.name))
 
		# Clean up
		self.switch_user("Administrator")
		frappe.delete_doc("Course Lesson", lesson.name, force=True)
		frappe.delete_doc("LMS Quiz", unpassed_quiz.name, force=True)

	def test_upload_video_transcript(self):
		import json
		# Create a mock lesson
		lesson = frappe.new_doc("Course Lesson")
		lesson.title = "Test Transcript Lesson"
		lesson.course = self.course.name
		lesson.chapter = self.course.chapters[0].chapter
		lesson.youtube = "https://www.youtube.com/watch?v=mockytid"
		lesson.insert()

		# Log in as moderator/instructor
		self.switch_user(self.admin.email)

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

		# Clean up
		self.switch_user("Administrator")
		frappe.delete_doc("Course Lesson", lesson.name, force=True)

	def test_get_all_students_across_batches(self):
		self.switch_user(self.admin.email)
		
		from lms.lms.api import get_all_students_across_batches
		res = get_all_students_across_batches()
		
		self.assertIn("data", res)
		self.assertIn("total_count", res)
		self.assertIn("batch_options", res)
		
		self.switch_user(self.student1.email)
		with self.assertRaises(frappe.PermissionError):
			get_all_students_across_batches()
			
		self.switch_user("Administrator")

	def test_import_students_csv(self):
		self.switch_user(self.admin.email)
		
		batch = self._create_batch(self.course.name, title="CSV Import Test Batch")
		
		from lms.lms.api import import_students_csv, assign_students_to_batch
		
		csv_content = "email,full_name\nimport1@example.com,Imported User One\nimport2@example.com,Imported User Two\ninvalid-email,Invalid"
		res = import_students_csv(csv_content)
		
		self.assertEqual(res["created"], 2)
		self.assertEqual(len(res["imported_users"]), 2)
		self.assertEqual(len(res["errors"]), 1)
		
		self.assertTrue(frappe.db.exists("User", "import1@example.com"))
		
		# Test bulk assignment to batch
		emails = [u["email"] for u in res["imported_users"]]
		assign_res = assign_students_to_batch(emails, batch=batch.name)
		self.assertEqual(assign_res["assigned_count"], 2)
		self.assertEqual(len(assign_res["errors"]), 0)
		self.assertTrue(frappe.db.exists("LMS Batch Enrollment", {"batch": batch.name, "member": "import1@example.com"}))
		
		frappe.db.delete("LMS Batch Enrollment", {"batch": batch.name})
		frappe.db.delete("User", {"email": ["in", ["import1@example.com", "import2@example.com"]]})
		frappe.delete_doc("LMS Batch", batch.name, force=True)
		
		self.switch_user("Administrator")

	def test_add_student_manually(self):
		self.switch_user(self.admin.email)
		
		batch = self._create_batch(self.course.name, title="Manual Add Test Batch")
		
		from lms.lms.api import add_student_manually
		
		res = add_student_manually("manual1@example.com", "Manual User One", batch=batch.name)
		self.assertEqual(res["status"], "success")
		self.assertTrue(res["is_new"])
		self.assertTrue(res["enrolled"])
		
		self.assertTrue(frappe.db.exists("User", "manual1@example.com"))
		self.assertTrue(frappe.db.exists("LMS Batch Enrollment", {"batch": batch.name, "member": "manual1@example.com"}))
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": "manual1@example.com"}))
		
		frappe.db.delete("Notification Log", {"for_user": "manual1@example.com"})
		frappe.db.delete("LMS Batch Enrollment", {"batch": batch.name})
		frappe.db.delete("User", {"email": "manual1@example.com"})
		frappe.delete_doc("LMS Batch", batch.name, force=True)
		
		self.switch_user("Administrator")

	def test_version_creation(self):
		self.switch_user("Administrator")
		# Create initial quiz version
		quiz = frappe.new_doc("LMS Quiz")
		quiz.title = "Test Version Quiz"
		quiz.passing_percentage = 80
		quiz.version_number = 1
		quiz.is_current_version = 1
		quiz.insert(ignore_permissions=True)
		
		# Create new version
		from lms.lms.api import create_new_content_version, list_versions
		res = create_new_content_version(
			content_doctype="LMS Quiz",
			content_name=quiz.name,
			change_log="Updated quiz settings",
			doc_data='{"passing_percentage": 90}'
		)
		
		new_quiz_name = res["new_name"]
		self.assertNotEqual(new_quiz_name, quiz.name)
		self.assertEqual(res["version_number"], 2)
		
		# Verify is_current_version states
		self.assertEqual(frappe.db.get_value("LMS Quiz", quiz.name, "is_current_version"), 0)
		self.assertEqual(frappe.db.get_value("LMS Quiz", new_quiz_name, "is_current_version"), 1)
		self.assertEqual(frappe.db.get_value("LMS Quiz", new_quiz_name, "passing_percentage"), 90)
		
		# Verify version listing
		versions = list_versions("LMS Quiz", quiz.name)
		self.assertEqual(len(versions), 2)
		
		# Clean up
		frappe.delete_doc("LMS Quiz", quiz.name, force=True)
		frappe.delete_doc("LMS Quiz", new_quiz_name, force=True)

	def test_content_save_check(self):
		self.switch_user("Administrator")
		quiz = frappe.new_doc("LMS Quiz")
		quiz.title = "Check attempts quiz"
		quiz.passing_percentage = 80
		quiz.insert(ignore_permissions=True)
		
		from lms.lms.api import check_content_before_save
		res = check_content_before_save("LMS Quiz", quiz.name)
		self.assertFalse(res["has_submissions"])
		
		# Insert mock attempt
		sub = frappe.new_doc("LMS Quiz Submission")
		sub.quiz = quiz.name
		sub.member = self.student1.email
		sub.score = 5
		sub.percentage = 50
		sub.passing_percentage = 80
		sub.score_out_of = 10
		sub.insert(ignore_permissions=True)
		
		res2 = check_content_before_save("LMS Quiz", quiz.name)
		self.assertTrue(res2["has_submissions"])
		
		# Clean up
		frappe.delete_doc("LMS Quiz Submission", sub.name, force=True)
		frappe.delete_doc("LMS Quiz", quiz.name, force=True)

	def test_course_upgrade(self):
		self.switch_user("Administrator")
		# Setup mock Course Content Link and Lesson Reference
		course = self.course.name
		chapter = self.course.chapters[0].chapter
		
		lesson = frappe.new_doc("Course Lesson")
		lesson.title = "Upgrade test lesson"
		lesson.course = course
		lesson.chapter = chapter
		lesson.version_number = 1
		lesson.is_current_version = 1
		lesson.insert(ignore_permissions=True)
		
		ref = frappe.new_doc("Lesson Reference")
		ref.parent = chapter
		ref.parenttype = "Course Chapter"
		ref.parentfield = "lessons"
		ref.lesson = lesson.name
		ref.idx = 10
		ref.insert(ignore_permissions=True)
		
		link = frappe.new_doc("Course Content Link")
		link.course = course
		link.chapter = chapter
		link.content_doctype = "Course Lesson"
		link.content_name = lesson.name
		link.library = "Test Library"
		link.mode = "Linked"
		link.source_version = 1
		link.insert(ignore_permissions=True)
		
		# Create new version
		from lms.lms.api import create_new_content_version, upgrade_course_content, get_upgrade_candidates
		res = create_new_content_version(
			content_doctype="Course Lesson",
			content_name=lesson.name,
			change_log="v2 upgrade",
			doc_data='{"title": "Upgrade test lesson v2"}'
		)
		
		new_lesson_name = res["new_name"]
		
		# Check upgrade candidates
		candidates = get_upgrade_candidates()
		c_links = [c["link_name"] for c in candidates]
		self.assertIn(link.name, c_links)
		
		# Upgrade course
		upgrade_course_content(course, chapter, "Course Lesson", lesson.name, new_lesson_name)
		
		# Verify updated references
		self.assertEqual(frappe.db.get_value("Lesson Reference", ref.name, "lesson"), new_lesson_name)
		self.assertEqual(frappe.db.get_value("Course Content Link", link.name, "content_name"), new_lesson_name)
		self.assertEqual(frappe.db.get_value("Course Content Link", link.name, "source_version"), 2)
		
		# Clean up
		frappe.delete_doc("Lesson Reference", ref.name, force=True)
		frappe.delete_doc("Course Content Link", link.name, force=True)
		frappe.delete_doc("Course Lesson", lesson.name, force=True)
		frappe.delete_doc("Course Lesson", new_lesson_name, force=True)

	def test_convert_course_to_library(self):
		self.switch_user("Administrator")
		course = self.course.name
		chapter = self.course.chapters[0].chapter
		
		# Create a normal lesson
		normal_lesson = frappe.new_doc("Course Lesson")
		normal_lesson.title = "Normal test lesson"
		normal_lesson.course = course
		normal_lesson.chapter = chapter
		normal_lesson.insert(ignore_permissions=True)
		
		# Create a quiz block lesson
		quiz_lesson = frappe.new_doc("Course Lesson")
		quiz_lesson.title = "Quiz test lesson"
		quiz_lesson.course = course
		quiz_lesson.chapter = chapter
		quiz_lesson.content = '{"blocks": [{"type": "quiz", "data": {"quiz": "Test Quiz Name"}}]}'
		quiz_lesson.insert(ignore_permissions=True)
		
		# Add references to chapter
		ref1 = frappe.new_doc("Lesson Reference")
		ref1.parent = chapter
		ref1.parenttype = "Course Chapter"
		ref1.parentfield = "lessons"
		ref1.lesson = normal_lesson.name
		ref1.idx = 11
		ref1.insert(ignore_permissions=True)
		
		ref2 = frappe.new_doc("Lesson Reference")
		ref2.parent = chapter
		ref2.parenttype = "Course Chapter"
		ref2.parentfield = "lessons"
		ref2.lesson = quiz_lesson.name
		ref2.idx = 12
		ref2.insert(ignore_permissions=True)
		
		# Convert course to library
		from lms.lms.api import convert_course_to_library
		lib_title = "Conversion Test Library"
		if frappe.db.exists("Content Library", lib_title):
			frappe.delete_doc("Content Library", lib_title, force=True)
			
		lib = convert_course_to_library(course, lib_title)
		
		# Verify library items types
		items = lib.get("items", [])
		normal_item = next((it for it in items if it.get("content_name") == normal_lesson.name), None)
		quiz_item = next((it for it in items if it.get("content_name") == "Test Quiz Name"), None)
		
		self.assertIsNotNone(normal_item)
		self.assertEqual(normal_item.get("content_doctype"), "Course Lesson")
		
		self.assertIsNotNone(quiz_item)
		self.assertEqual(quiz_item.get("content_doctype"), "LMS Quiz")
		
		# Clean up
		frappe.delete_doc("Lesson Reference", ref1.name, force=True)
		frappe.delete_doc("Lesson Reference", ref2.name, force=True)
		frappe.delete_doc("Course Lesson", normal_lesson.name, force=True)
		frappe.delete_doc("Course Lesson", quiz_lesson.name, force=True)
		frappe.delete_doc("Content Library", lib_title, force=True)



