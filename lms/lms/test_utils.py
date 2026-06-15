# Copyright (c) 2021, FOSS United and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, nowdate, to_timedelta

from lms.lms.doctype.lms_certificate.lms_certificate import is_certified
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import (
	get_average_rating,
	get_batches,
	get_batch_details,
	get_chapters,
	get_course_details,
	get_course_outline,
	get_evaluator,
	get_instructors,
	get_lesson_index,
	get_lesson_url,
	get_lessons,
	get_lms_route,
	get_membership,
	get_reviews,
	has_course_instructor_role,
	has_evaluator_role,
	has_moderator_role,
	has_student_role,
	is_instructor,
	slugify,
)


class TestLMSUtils(BaseTestUtils):
	def setUp(self):
		super().setUp()

		self._setup_course_flow()
		self._setup_batch_flow()

	def test_simple_slugs(self):
		self.assertEqual(slugify("hello-world"), "hello-world")
		self.assertEqual(slugify("Hello World"), "hello-world")
		self.assertEqual(slugify("Hello, World!"), "hello-world")

	def test_duplicates_slugs(self):
		self.assertEqual(slugify("Hello World", ["hello-world"]), "hello-world-2")
		self.assertEqual(slugify("Hello World", ["hello-world", "hello-world-2"]), "hello-world-3")

	def test_get_membership(self):
		membership = get_membership(self.course.name, self.student1.email)
		self.assertIsNotNone(membership)
		self.assertEqual(membership.course, self.course.name)
		self.assertEqual(membership.member, self.student1.email)

	def test_get_chapters(self):
		chapters = get_chapters(self.course.name)
		self.assertEqual(len(chapters), len(self.course.chapters))

		for i, chapter in enumerate(chapters, start=1):
			self.assertEqual(chapter.title, f"Chapter {i}")

	def test_get_lessons(self):
		lessons = get_lessons(self.course.name)
		all_lessons = frappe.db.count("Course Lesson", {"course": self.course.name})
		self.assertEqual(len(lessons), all_lessons)

	def test_get_course_outline_locking(self):
		# Set sequential lessons enabled
		frappe.db.set_value("LMS Course", self.course.name, "enable_sequential_lessons", 1)

		# Login as student1
		frappe.session.user = self.student1.email

		# Get course outline with progress=True
		outline = get_course_outline(self.course.name, progress=True)
		self.assertTrue(len(outline) > 0)

		# The first lesson of the first chapter should be unlocked
		first_chapter = outline[0]
		self.assertTrue(len(first_chapter.lessons) > 0)
		self.assertFalse(first_chapter.lessons[0].locked)

		# Subsequent lessons should be locked
		if len(first_chapter.lessons) > 1:
			self.assertTrue(first_chapter.lessons[1].locked)

		# Now mark the first lesson as complete
		progress_doc = frappe.get_doc({
			"doctype": "LMS Course Progress",
			"course": self.course.name,
			"member": self.student1.email,
			"lesson": first_chapter.lessons[0].name,
			"status": "Complete"
		})
		progress_doc.insert()

		# Get course outline again
		outline = get_course_outline(self.course.name, progress=True)
		first_chapter = outline[0]
		self.assertFalse(first_chapter.lessons[0].locked)
		if len(first_chapter.lessons) > 1:
			# The second lesson should now be unlocked!
			self.assertFalse(first_chapter.lessons[1].locked)
			if len(first_chapter.lessons) > 2:
				# The third lesson should still be locked
				self.assertTrue(first_chapter.lessons[2].locked)

		# Clean up progress doc
		frappe.set_user("Administrator")
		progress_doc.delete()

	def test_chapter_and_lesson_exclusion(self):
		# Login as student1
		frappe.session.user = self.student1.email

		# Get active chapter and lesson reference names to edit
		chapter_ref = self.course.chapters[0].chapter
		lessons = frappe.get_all("Lesson Reference", {"parent": chapter_ref}, ["lesson", "idx"], order_by="idx")
		self.assertTrue(len(lessons) > 0)
		lesson_name = lessons[0].lesson

		# 1. Test chapter exclusion
		frappe.db.set_value("Course Chapter", chapter_ref, "exclude_from_course", 1)

		# For students, outline shouldn't contain the excluded chapter
		outline = get_course_outline(self.course.name)
		chapter_names = [ch.name for ch in outline]
		self.assertNotIn(chapter_ref, chapter_names)

		# But for instructor, it should still be visible
		frappe.session.user = "frappe@example.com" # instructor
		outline = get_course_outline(self.course.name)
		chapter_names = [ch.name for ch in outline]
		self.assertIn(chapter_ref, chapter_names)

		# Reset chapter exclusion
		frappe.db.set_value("Course Chapter", chapter_ref, "exclude_from_course", 0)

		# 2. Test lesson exclusion
		frappe.session.user = self.student1.email
		frappe.db.set_value("Course Lesson", lesson_name, "exclude_from_course", 1)

		# For students, the excluded lesson should not be in the chapter lessons details
		outline = get_course_outline(self.course.name)
		lessons_in_chapter = outline[0].lessons
		lesson_names = [l.name for l in lessons_in_chapter]
		self.assertNotIn(lesson_name, lesson_names)

		# For instructors, it should be visible
		frappe.session.user = "frappe@example.com"
		outline = get_course_outline(self.course.name)
		lessons_in_chapter = outline[0].lessons
		lesson_names = [l.name for l in lessons_in_chapter]
		self.assertIn(lesson_name, lesson_names)

		# Clean up
		frappe.db.set_value("Course Lesson", lesson_name, "exclude_from_course", 0)
		frappe.session.user = "Administrator"

	def test_chapter_and_lesson_rolling_release(self):
		# Get active chapter and lesson reference names
		chapter_ref = self.course.chapters[0].chapter
		lessons = frappe.get_all("Lesson Reference", {"parent": chapter_ref}, ["lesson", "idx"], order_by="idx")
		self.assertTrue(len(lessons) > 0)
		lesson_name = lessons[0].lesson

		# Login as student1
		frappe.session.user = self.student1.email

		# 1. Test future release date locks chapter
		from frappe.utils import add_days, now_datetime
		future_date = add_days(now_datetime(), 2)
		frappe.db.set_value("Course Chapter", chapter_ref, "release_date", future_date)
		frappe.db.set_value("Course Chapter", chapter_ref, "release_time", "12:00:00")

		outline = get_course_outline(self.course.name)
		first_chapter = outline[0]
		self.assertTrue(first_chapter.lessons[0].locked)

		# 2. Test past release date unlocks chapter
		past_date = add_days(now_datetime(), -2)
		frappe.db.set_value("Course Chapter", chapter_ref, "release_date", past_date)
		frappe.db.set_value("Course Chapter", chapter_ref, "release_time", "00:00:00")

		# Reset lesson dates to be sure
		frappe.db.set_value("Course Lesson", lesson_name, "release_date", None)
		frappe.db.set_value("Course Lesson", lesson_name, "release_time", None)

		outline = get_course_outline(self.course.name)
		first_chapter = outline[0]
		# The first lesson of the first chapter should be unlocked (assuming no other lock reasons)
		self.assertFalse(first_chapter.lessons[0].locked)

		# 3. Test future release date locks lesson
		frappe.db.set_value("Course Lesson", lesson_name, "release_date", future_date)
		frappe.db.set_value("Course Lesson", lesson_name, "release_time", "12:00:00")

		outline = get_course_outline(self.course.name)
		first_chapter = outline[0]
		self.assertTrue(first_chapter.lessons[0].locked)

		# Clean up
		frappe.db.set_value("Course Chapter", chapter_ref, "release_date", None)
		frappe.db.set_value("Course Chapter", chapter_ref, "release_time", None)
		frappe.db.set_value("Course Lesson", lesson_name, "release_date", None)
		frappe.db.set_value("Course Lesson", lesson_name, "release_time", None)
		frappe.session.user = "Administrator"

	def test_get_instructors(self):
		instructors = get_instructors("LMS Course", self.course.name)
		self.assertEqual(len(instructors), len(self.course.instructors))
		self.assertEqual(instructors[0].name, "frappe@example.com")

	def test_get_average_rating(self):
		average_rating = get_average_rating(self.course.name)
		self.assertEqual(average_rating, 4.5)

	def test_get_reviews(self):
		reviews = get_reviews(self.course.name)
		self.assertEqual(len(reviews), 2)

	def test_get_lesson_index(self):
		lessons = get_lessons(self.course.name)
		for lesson in lessons:
			self.assertEqual(get_lesson_index(lesson.name), lesson.number)

	def test_get_lesson_url(self):
		lessons = get_lessons(self.course.name)
		for lesson in lessons:
			expected_url = get_lms_route(f"courses/{self.course.name}/learn/{lesson.number}")
			self.assertEqual(get_lesson_url(self.course.name, lesson.number), expected_url)

	def test_is_instructor(self):
		frappe.session.user = "frappe@example.com"
		self.assertTrue(is_instructor(self.course.name))
		frappe.session.user = "Administrator"
		self.assertFalse(is_instructor(self.course.name))

	def test_has_course_instructor_role(self):
		self.assertIsNotNone(has_course_instructor_role("frappe@example.com"))
		self.assertIsNone(has_course_instructor_role("student1@example.com"))

	def test_has_moderator_role(self):
		self.assertIsNotNone(has_moderator_role("frappe@example.com"))
		self.assertIsNone(has_moderator_role("student2@example.com"))

	def test_has_evaluator_role(self):
		self.assertIsNotNone(has_evaluator_role("frappe@example.com"))
		self.assertIsNone(has_evaluator_role("student2@example.com"))

	def test_has_student_role(self):
		self.assertIsNotNone(has_student_role("student1@example.com"))
		self.assertIsNotNone(has_student_role("student2@example.com"))

	def test_is_certified(self):
		frappe.session.user = self.student1.email
		self.assertIsNotNone(is_certified(self.course.name))
		frappe.session.user = self.student2.email
		self.assertIsNone(is_certified(self.course.name))
		frappe.session.user = "Administrator"

	def test_rating_validation(self):
		student3 = self._create_user("student3@example.com", "Emily", "Cooper", ["LMS Student"])
		with self.assertRaises(frappe.exceptions.ValidationError):
			frappe.session.user = student3.email
			review = frappe.new_doc("LMS Course Review")
			review.course = self.course.name
			review.rating = -0.5
			review.review = "Bad course"
			review.save()
		frappe.session.user = "Administrator"

	def test_get_evaluator(self):
		evaluator_email = get_evaluator(self.course.name, self.batch.name)
		self.assertEqual(evaluator_email, self.evaluator.evaluator)

	def test_get_course_details(self):
		course_details = get_course_details(self.course.name)
		self.assertEqual(course_details.name, self.course.name)
		self.assertEqual(course_details.title, self.course.title)
		self.assertEqual(course_details.category, self.course.category)
		self.assertEqual(course_details.description, self.course.description)
		self.assertEqual(course_details.short_introduction, self.course.short_introduction)
		self.assertEqual(course_details.tags, self.course.tags)
		self.assertEqual(course_details.published, 1)
		self.assertEqual(len(course_details.instructors), len(self.course.instructors))

	def test_get_batch_details(self):
		batch_details = get_batch_details(self.batch.name)
		self.assertEqual(batch_details.name, self.batch.name)
		self.assertEqual(batch_details.title, self.batch.title)
		self.assertEqual(batch_details.start_date, getdate(self.batch.start_date))
		self.assertEqual(batch_details.end_date, getdate(self.batch.end_date))
		self.assertEqual(batch_details.start_time, to_timedelta(self.batch.start_time))
		self.assertEqual(batch_details.end_time, to_timedelta(self.batch.end_time))
		self.assertEqual(batch_details.timezone, self.batch.timezone)
		self.assertEqual(batch_details.published, 1)
		self.assertEqual(batch_details.description, self.batch.description)
		self.assertEqual(batch_details.batch_details, self.batch.batch_details)
		self.assertEqual(len(batch_details.courses), len(self.batch.courses))
		self.assertEqual(batch_details.evaluation_end_date, getdate(self.batch.evaluation_end_date))
		self.assertEqual(len(batch_details.instructors), len(self.batch.instructors))
		self.assertEqual(len(batch_details.students), 2)

	def test_get_batch_details_accept_enrollments_for_ongoing_batch_with_delayed_enrollment(self):
		frappe.db.set_value(
			"LMS Batch",
			self.batch.name,
			{
				"allow_delayed_enrollment": 1,
				"start_date": add_days(nowdate(), -2),
				"end_date": add_days(nowdate(), 2),
			},
		)
		batch_details = get_batch_details(self.batch.name)
		self.assertTrue(batch_details.accept_enrollments)

	def test_get_batch_details_accept_enrollments_false_for_ongoing_batch_without_delayed_enrollment(self):
		frappe.db.set_value(
			"LMS Batch",
			self.batch.name,
			{
				"allow_delayed_enrollment": 0,
				"start_date": add_days(nowdate(), -2),
				"end_date": add_days(nowdate(), 2),
			},
		)
		batch_details = get_batch_details(self.batch.name)
		self.assertFalse(batch_details.accept_enrollments)

	def test_get_batch_details_accept_enrollments_false_for_ended_batch(self):
		frappe.db.set_value(
			"LMS Batch",
			self.batch.name,
			{
				"start_date": add_days(nowdate(), -5),
				"end_date": add_days(nowdate(), -1),
			},
		)
		batch_details = get_batch_details(self.batch.name)
		self.assertFalse(batch_details.accept_enrollments)

	def test_self_enrollment_not_allowed_after_batch_end_date(self):
		student3 = self._create_user("student3@example.com", "Emily", "Cooper", ["LMS Student"])
		frappe.db.set_value(
			"LMS Batch",
			self.batch.name,
			{
				"allow_self_enrollment": 1,
				"allow_delayed_enrollment": 1,
				"end_date": add_days(nowdate(), -1),
			},
		)

		frappe.session.user = student3.email
		try:
			with self.assertRaises(frappe.exceptions.ValidationError):
				enrollment = frappe.new_doc("LMS Batch Enrollment")
				enrollment.update({"member": student3.email, "batch": self.batch.name})
				enrollment.insert()
		finally:
			frappe.session.user = "Administrator"

	def test_get_batches_shows_delayed_enrollment_batches_for_learners(self):
		frappe.db.set_value(
			"LMS Batch",
			self.batch.name,
			{
				"allow_self_enrollment": 1,
				"allow_delayed_enrollment": 1,
				"start_date": add_days(nowdate(), -2),
				"end_date": add_days(nowdate(), 2),
				"published": 1,
			},
		)

		frappe.session.user = self.student1.email
		try:
			batches = get_batches(filters={"published": 1, "start_date": [">=", nowdate()]})
			self.assertIn(self.batch.name, [batch.name for batch in batches])
		finally:
			frappe.session.user = "Administrator"

	def test_get_batches_hides_started_batches_without_delayed_enrollment_for_learners(self):
		frappe.db.set_value(
			"LMS Batch",
			self.batch.name,
			{
				"allow_self_enrollment": 1,
				"allow_delayed_enrollment": 0,
				"start_date": add_days(nowdate(), -2),
				"end_date": add_days(nowdate(), 2),
				"published": 1,
			},
		)

		frappe.session.user = self.student1.email
		try:
			batches = get_batches(filters={"published": 1, "start_date": [">=", nowdate()]})
			self.assertNotIn(self.batch.name, [batch.name for batch in batches])
		finally:
			frappe.session.user = "Administrator"
