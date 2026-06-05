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
		content = json.loads(self.content)
		for block in content.get("blocks"):
			if block.get("type") == "quiz":
				quiz = block.get("data").get("quiz")
				if not frappe.db.exists("LMS Quiz", quiz):
					frappe.throw(_("Invalid Quiz ID in content"))
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

		for block in content.get("blocks"):
			if block.get("type") == "quiz":
				quizzes.append(block.get("data").get("quiz"))
			if block.get("type") == "upload":
				quizzes_in_video = block.get("data").get("quizzes")
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
