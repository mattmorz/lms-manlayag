# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.realtime import get_website_room
from frappe.utils.telemetry import capture

from lms.lms.utils import get_course_progress

from ...md import find_macros


class CourseLesson(Document):
	def validate(self):
		self.validate_grading_policy()
		self.validate_unique_assessments()

	def validate_grading_policy(self):
		course = self.course
		if not course and self.chapter:
			course = frappe.db.get_value("Course Chapter", self.chapter, "course")
		if not course:
			return
		course_doc = frappe.get_doc("LMS Course", course)
		if not getattr(course_doc, "enable_grading_policy", False):
			return

		# Parse self.content
		if not self.content:
			return
		try:
			content = json.loads(self.content)
		except Exception:
			return

		# Extract quizzes/assignments in this lesson
		lesson_assessments = []
		for block in content.get("blocks", []):
			if block.get("type") in ["quiz", "assignment"]:
				data = block.get("data", {})
				item_id = data.get("quiz") or data.get("assignment")
				item_type = "Quiz" if block.get("type") == "quiz" else "Assignment"
				cat = data.get("grading_category")
				due_date = data.get("due_date")
				due_time = data.get("due_time")
				include_in_grading = data.get("include_in_grading", 1)
				lesson_assessments.append({
					"id": item_id,
					"type": item_type,
					"category": cat,
					"due_date": due_date,
					"due_time": due_time,
					"include_in_grading": include_in_grading,
				})

		# 1. Check if all graded quizzes/assignments have a category selected
		for item in lesson_assessments:
			if not item.get("include_in_grading"):
				continue

			if not item["category"]:
				frappe.throw(
					_("{0} '{1}' is missing a Grading Category, which is required by the course grading policy.").format(
						item["type"], item["id"]
					)
				)

			# 2. Check if the category exists in the course
			cat_exists = False
			for course_cat in getattr(course_doc, "grading_categories", []):
				if course_cat.category_name == item["category"]:
					cat_exists = True
					break
			if not cat_exists:
				frappe.throw(
					_("Grading category '{0}' selected for {1} '{2}' is not defined in Course '{3}'.").format(
						item["category"], item["type"], item["id"], course_doc.title
					)
				)

		# 3. Check limit for each category
		# For this, we count assessments in all OTHER lessons in the course, plus the new ones in this lesson.
		other_lessons = frappe.get_all(
			"Course Lesson",
			filters={"course": course, "name": ["!=", self.name]},
			fields=["content", "exclude_from_course"]
		)

		# Aggregate counts from other lessons
		cat_counts = {}
		for other in other_lessons:
			if getattr(other, "exclude_from_course", 0):
				continue
			if not other.content:
				continue
			try:
				other_content = json.loads(other.content)
			except Exception:
				continue
			for block in other_content.get("blocks", []):
				if block.get("type") in ["quiz", "assignment"]:
					data = block.get("data", {})
					cat = data.get("grading_category")
					if cat:
						cat_counts[cat] = cat_counts.get(cat, 0) + 1

		# Add counts from current lesson
		for item in lesson_assessments:
			if not item.get("include_in_grading"):
				continue
			cat = item["category"]
			cat_counts[cat] = cat_counts.get(cat, 0) + 1

		# Validate limits
		for course_cat in getattr(course_doc, "grading_categories", []):
			cat_name = course_cat.category_name
			limit = getattr(course_cat, "number_of_assessments", 0) or 0
			if limit > 0 and cat_counts.get(cat_name, 0) > limit:
				frappe.throw(
					_("The category '{0}' has reached its limit of {1} assessment(s) in Course {2}.").format(
						cat_name, limit, course_doc.title
					)
				)

	def validate_unique_assessments(self):
		course = self.course
		if not course and self.chapter:
			course = frappe.db.get_value("Course Chapter", self.chapter, "course")
		if not course:
			return

		# Parse self.content
		if not self.content:
			return
		try:
			content = json.loads(self.content)
		except Exception:
			return

		current_quizzes = set()
		for block in content.get("blocks", []):
			if block.get("type") == "quiz":
				q_id = block.get("data", {}).get("quiz")
				if q_id:
					if q_id in current_quizzes:
						frappe.throw(
							_("Quiz '{0}' is added multiple times in this lesson.").format(q_id)
						)
					current_quizzes.add(q_id)

		if not current_quizzes:
			return

		# Find all other lessons in the same course
		other_lessons = frappe.get_all(
			"Course Lesson",
			filters={"course": course, "name": ["!=", self.name]},
			fields=["name", "content"]
		)

		for other in other_lessons:
			if not other.content:
				continue
			try:
				other_content = json.loads(other.content)
			except Exception:
				continue
			for block in other_content.get("blocks", []):
				if block.get("type") == "quiz":
					q_id = block.get("data", {}).get("quiz")
					if q_id in current_quizzes:
						frappe.throw(
							_("Quiz '{0}' is already used in another lesson ('{1}') of this course.").format(
								q_id, other.name
							)
						)

	def on_update(self):
		self.validate_quiz_id()

	def validate_quiz_id(self):
		for quiz in get_quiz_ids(self.quiz_id):
			if not frappe.db.exists("LMS Quiz", quiz):
				frappe.throw(_("Invalid Quiz ID"))

		if self.content:
			self.save_lesson_details_in_quiz(self.content)

		if self.instructor_content:
			self.save_lesson_details_in_quiz(self.instructor_content)

	def save_lesson_details_in_quiz(self, content):
		content = json.loads(content)
		for block in content.get("blocks", []):
			if block.get("type") == "quiz":
				quiz = block.get("data", {}).get("quiz")
				self.validate_and_set_quiz(quiz)
			elif block.get("type") in ["upload", "embed"]:
				quizzes = block.get("data", {}).get("quizzes", [])
				for q in quizzes:
					if q.get("quiz"):
						self.validate_and_set_quiz(q.get("quiz"))

	def validate_and_set_quiz(self, quiz):
		if not frappe.db.exists("LMS Quiz", quiz):
			frappe.throw(_("Invalid Quiz ID: {0}").format(quiz))
		frappe.db.set_value(
			"LMS Quiz",
			quiz,
			{
				"course": self.course,
				"lesson": self.name,
			},
		)


def get_quiz_ids(quiz_id):
	if not quiz_id:
		return []
	return [quiz.strip() for quiz in quiz_id.split(",") if quiz.strip()]


@frappe.whitelist()
def save_progress(lesson: str, course: str, scorm_details: dict = None):
	"""
	Note: Pass the argument scorm_details as a dict if it is SCORM related save_progress
	"""
	membership = frappe.db.exists("LMS Enrollment", {"course": course, "member": frappe.session.user})
	if not membership:
		return 0

	frappe.db.set_value("LMS Enrollment", membership, "current_lesson", lesson)
	progress_already_exists = frappe.db.exists(
		"LMS Course Progress", {"lesson": lesson, "member": frappe.session.user}
	)
	lesson_already_completed = frappe.db.exists(
		"LMS Course Progress",
		{"lesson": lesson, "member": frappe.session.user, "status": "Complete"},
	)

	quiz_completed = get_quiz_progress(lesson)
	assignment_completed = get_assignment_progress(lesson)
	video_completed = get_video_progress(lesson)

	if scorm_details:
		scorm_details = frappe._dict(**scorm_details)

	if not progress_already_exists and quiz_completed and assignment_completed and video_completed and not scorm_details:
		frappe.get_doc(
			{
				"doctype": "LMS Course Progress",
				"lesson": lesson,
				"status": "Complete",
				"member": frappe.session.user,
			}
		).save(ignore_permissions=True)
	elif scorm_details and not lesson_already_completed and not progress_already_exists:
		# Create new SCORM progress
		frappe.get_doc(
			{
				"doctype": "LMS Course Progress",
				"lesson": lesson,
				"status": "Complete" if scorm_details.is_complete else "Partially Complete",
				"member": frappe.session.user,
				"scorm_content": "" if scorm_details.is_complete else scorm_details.scorm_content,
			}
		).save(ignore_permissions=True)
	elif scorm_details and not lesson_already_completed and progress_already_exists:
		# Update Existing SCORM Progress
		frappe.db.set_value(
			"LMS Course Progress",
			progress_already_exists,
			{
				"lesson": lesson,
				"status": "Complete" if scorm_details.is_complete else "Partially Complete",
				"member": frappe.session.user,
				"scorm_content": "" if scorm_details.is_complete else scorm_details.scorm_content,
			},
		)

	progress = get_course_progress(course)
	capture_progress_for_analytics()

	# Had to get doc, as on_change doesn't trigger when you use set_value. The trigger is necessary for badge to get assigned.
	enrollment = frappe.get_doc("LMS Enrollment", membership)
	enrollment.progress = progress
	enrollment.save()
	enrollment.run_method("on_change")

	frappe.publish_realtime(
		event="update_lesson_progress",
		room=get_website_room(),
		message={"course": course, "lesson": lesson, "progress": progress},
		after_commit=True,
	)

	return progress


def capture_progress_for_analytics():
	capture("course_progress", "lms")


def get_quiz_progress(lesson):
	lesson_details = frappe.db.get_value("Course Lesson", lesson, ["body", "content"], as_dict=1)
	quizzes = []

	if lesson_details.content:
		content = json.loads(lesson_details.content)

		for block in content.get("blocks", []):
			if block.get("type") == "quiz":
				quizzes.append(block.get("data").get("quiz"))
			elif block.get("type") in ["upload", "embed"]:
				quizzes_in_video = block.get("data", {}).get("quizzes")
				if quizzes_in_video and len(quizzes_in_video) > 0:
					for row in quizzes_in_video:
						quizzes.append(row.get("quiz"))

	elif lesson_details.body:
		macros = find_macros(lesson_details.body)
		quizzes = [value for name, value in macros if name == "Quiz"]

	for quiz in quizzes:
		passing_percentage = frappe.db.get_value("LMS Quiz", quiz, "passing_percentage")
		if not frappe.db.exists(
			"LMS Quiz Submission",
			{
				"quiz": quiz,
				"member": frappe.session.user,
				"percentage": [">=", passing_percentage],
			},
		):
			return False
	return True


def get_assignment_progress(lesson):
	lesson_details = frappe.db.get_value("Course Lesson", lesson, ["body", "content"], as_dict=1)
	assignments = []

	if lesson_details.content:
		content = json.loads(lesson_details.content)

		for block in content.get("blocks"):
			if block.get("type") == "assignment":
				assignments.append(block.get("data").get("assignment"))

	elif lesson_details.body:
		macros = find_macros(lesson_details.body)
		assignments = [value for name, value in macros if name == "Assignment"]

	for assignment in assignments:
		if not frappe.db.exists(
			"LMS Assignment Submission",
			{"assignment": assignment, "member": frappe.session.user},
		):
			return False
	return True


def get_video_progress(lesson):
	"""Check if all videos in the lesson have been watched to at least 90% of their duration"""
	lesson_details = frappe.db.get_value("Course Lesson", lesson, ["body", "content"], as_dict=1)
	videos = []

	# Extract videos from content
	if lesson_details.content:
		content = json.loads(lesson_details.content)
		for block in content.get("blocks", []):
			if block.get("type") == "video":
				videos.append(block.get("data", {}).get("url"))
			elif block.get("type") == "upload":
				# Videos uploaded in blocks
				video_url = block.get("data", {}).get("url")
				if video_url:
					videos.append(video_url)

	# If no videos found, return True (no video requirement)
	if not videos:
		return True

	has_duration_field = frappe.get_meta("LMS Video Watch Duration").has_field("duration")
	fields_to_fetch = ["source", "watch_time"]
	if has_duration_field:
		fields_to_fetch.append("duration")

	# Check watch durations
	watched_records = frappe.db.get_all(
		"LMS Video Watch Duration",
		filters={"lesson": lesson, "member": frappe.session.user},
		fields=fields_to_fetch,
	)

	if len(watched_records) < len(videos):
		return False

	for video_url in videos:
		record = next((r for r in watched_records if r.source == video_url), None)
		if not record:
			return False

		# Enforce that watch_time is at least 90% of duration
		if has_duration_field and record.get("duration"):
			try:
				watch_time = float(record.get("watch_time") or 0)
				duration = float(record.get("duration") or 0)
				if duration > 0 and watch_time < 0.9 * duration:
					return False
			except (ValueError, TypeError):
				return False

	return True
