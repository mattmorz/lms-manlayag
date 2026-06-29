"""API methods for the LMS."""

import json
import os
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from datetime import timedelta
from xml.dom.minidom import parseString

import frappe
from frappe import _
from frappe.integrations.frappe_providers.frappecloud_billing import (
	current_site_info,
	is_fc_site,
)
from frappe.translate import get_all_translations
from frappe.utils import (
	add_days,
	cint,
	date_diff,
	flt,
	format_date,
	get_datetime,
	getdate,
	now,
)
from frappe.utils.response import Response
from pypika import functions as fn

from lms.lms.doctype.course_lesson.course_lesson import save_progress
from lms.lms.utils import (
	can_modify_batch,
	can_modify_course,
	get_average_rating,
	get_batch_details,
	get_course_details,
	get_instructors,
	get_lesson_count,
	get_lms_route,
	has_course_instructor_role,
	has_evaluator_role,
	has_moderator_role,
)


@frappe.whitelist()
def get_user_info():
	if frappe.session.user == "Guest":
		return None

	user = frappe.db.get_value(
		"User",
		frappe.session.user,
		["name", "email", "enabled", "user_image", "full_name", "user_type", "username"],
		as_dict=1,
	)
	user["roles"] = frappe.get_roles(user.name)
	user.is_instructor = "Course Creator" in user.roles
	user.is_moderator = "Moderator" in user.roles
	user.is_evaluator = "Batch Evaluator" in user.roles
	user.is_student = not user.is_instructor and not user.is_moderator and not user.is_evaluator
	user.is_fc_site = is_fc_site()
	user.is_system_manager = "System Manager" in user.roles
	user.sitename = frappe.local.site
	user.developer_mode = frappe.conf.developer_mode
	if user.is_fc_site and user.is_system_manager:
		user.site_info = current_site_info()
	return user


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")
	return get_all_translations(language)


@frappe.whitelist()
def validate_billing_access(billing_type: str, name: str):
	doctype = "LMS Batch" if billing_type == "batch" else "LMS Course"
	access, message = verify_billing_access(doctype, name, billing_type)

	address = frappe.db.get_value(
		"Address",
		{"email_id": frappe.session.user},
		[
			"name",
			"address_title as billing_name",
			"address_line1",
			"address_line2",
			"city",
			"state",
			"country",
			"pincode",
			"phone",
		],
		as_dict=1,
	)

	return {"access": access, "message": message, "address": address}


def verify_billing_access(doctype, name, billing_type):
	access = True
	message = ""

	if frappe.session.user == "Guest":
		access = False
		message = _("Please login to continue with payment.")

	if access and billing_type not in ["course", "batch", "certificate"]:
		access = False
		message = _("Module is incorrect.")

	if access and not frappe.db.exists(doctype, name):
		access = False
		message = _("Module Name is incorrect or does not exist.")

	if access and billing_type == "course":
		membership = frappe.db.exists("LMS Enrollment", {"member": frappe.session.user, "course": name})
		if membership:
			access = False
			message = _("You are already enrolled for this course.")

	elif access and billing_type == "batch":
		membership = frappe.db.exists("LMS Batch Enrollment", {"member": frappe.session.user, "batch": name})
		if membership:
			access = False
			message = _("You are already enrolled for this batch.")

		seat_count = frappe.get_cached_value("LMS Batch", name, "seat_count")
		number_of_students = frappe.db.count("LMS Batch Enrollment", {"batch": name})
		if seat_count <= number_of_students:
			access = False
			message = _("Batch is sold out.")

		start_date = frappe.get_cached_value("LMS Batch", name, "start_date")
		if start_date and date_diff(start_date, now()) < 0:
			access = False
			message = _("Batch has already started.")

	elif access and billing_type == "certificate":
		purchased_certificate = frappe.db.exists(
			"LMS Enrollment",
			{
				"course": name,
				"member": frappe.session.user,
				"purchased_certificate": 1,
			},
		)
		if purchased_certificate:
			access = False
			message = _("You have already purchased the certificate for this course.")

	return access, message


@frappe.whitelist(allow_guest=True)
def get_job_details(job: str):
	return frappe.db.get_value(
		"Job Opportunity",
		job,
		[
			"job_title",
			"location",
			"country",
			"type",
			"work_mode",
			"company_name",
			"company_logo",
			"company_website",
			"name",
			"creation",
			"description",
			"owner",
		],
		as_dict=1,
	)


@frappe.whitelist(allow_guest=True)
def get_job_opportunities(filters: dict = None, orFilters: dict = None):
	if not filters:
		filters = {}

	jobs = frappe.get_all(
		"Job Opportunity",
		filters=filters,
		or_filters=orFilters,
		fields=[
			"job_title",
			"location",
			"country",
			"type",
			"work_mode",
			"company_name",
			"company_logo",
			"name",
			"creation",
			"description",
		],
		order_by="creation desc",
	)

	for job in jobs:
		job.description = frappe.utils.strip_html_tags(job.description)
		job.applicants = frappe.db.count("LMS Job Application", {"job": job.name})
	return jobs


@frappe.whitelist(allow_guest=True)
def get_chart_details():
	details = frappe._dict()
	details.enrollments = frappe.db.count("LMS Enrollment")
	details.courses = frappe.db.count(
		"LMS Course",
		{
			"published": 1,
			"upcoming": 0,
		},
	)
	details.users = frappe.db.count("User", {"enabled": 1, "name": ["not in", ("Administrator", "Guest")]})
	details.completions = frappe.db.count("LMS Enrollment", {"progress": ["like", "%100%"]})
	details.certifications = frappe.db.count("LMS Certificate", {"published": 1})
	return details


def get_file_info(file_url):
	"""Get file info for the given file URL."""
	file_info = frappe.db.get_value(
		"File", {"file_url": file_url}, ["file_name", "file_size", "file_url"], as_dict=1
	)
	return file_info


@frappe.whitelist(allow_guest=True)
def get_branding():
	"""Get branding details."""
	fields = ["app_name"]
	image_fields = ["banner_image", "footer_logo", "favicon", "app_logo"]
	fields = fields + image_fields
	settings = frappe._dict()

	for field in fields:
		value = frappe.get_cached_value("Website Settings", None, field)
		if field in image_fields and value:
			file_info = get_file_info(value)
			settings.update({field: json.loads(json.dumps(file_info))})
		else:
			settings.update({field: value})

	return settings


@frappe.whitelist()
def get_unsplash_photos(keyword: str = None):
	from lms.unsplash import get_by_keyword, get_list

	if keyword:
		return get_by_keyword(keyword)

	return frappe.cache().get_value("unsplash_photos", generator=get_list)


@frappe.whitelist()
def get_evaluator_details(evaluator: str):
	frappe.only_for("Batch Evaluator")

	if not frappe.db.exists("Google Calendar", {"user": evaluator}):
		calendar = frappe.new_doc("Google Calendar")
		calendar.update({"user": evaluator, "calendar_name": evaluator})
		calendar.insert()
	else:
		calendar = frappe.db.get_value(
			"Google Calendar", {"user": evaluator}, ["name", "authorization_code"], as_dict=1
		)

	if frappe.db.exists("Course Evaluator", {"evaluator": evaluator}):
		doc = frappe.get_doc("Course Evaluator", evaluator)
	else:
		doc = frappe.new_doc("Course Evaluator")
		doc.evaluator = evaluator
		doc.insert()

	return {
		"slots": doc.as_dict(),
		"calendar": calendar.name,
		"is_authorised": calendar.authorization_code,
	}


@frappe.whitelist()
def get_certified_participants(filters: dict = None, start: int = 0, page_length: int = 100):
	query = get_certification_query(filters)
	query = query.orderby("issue_date", order=frappe.qb.desc).offset(start).limit(page_length)
	participants = query.run(as_dict=True)

	for participant in participants:
		details = get_certified_participant_details(participant.member)
		participant.update(details)

	return participants


def get_certified_participant_details(member: str):
	count = frappe.db.count("LMS Certificate", {"member": member})
	details = frappe.db.get_value(
		"User",
		member,
		["full_name", "user_image", "username", "country", "headline", "open_to"],
		as_dict=1,
	)
	details["certificate_count"] = count
	return details


def get_certification_query(filters: dict = None):
	Certificate = frappe.qb.DocType("LMS Certificate")
	User = frappe.qb.DocType("User")

	query = (
		frappe.qb.from_(Certificate)
		.select(Certificate.member, Certificate.issue_date)
		.distinct()
		.join(User)
		.on(Certificate.member == User.name)
		.where(Certificate.published == 1)
		.where(User.enabled == 1)
	)

	if filters:
		for field, value in filters.items():
			if field == "category":
				query = query.where(
					Certificate.course_title.like(f"%{value}%") | Certificate.batch_title.like(f"%{value}%")
				)
			if field == "member_name":
				query = query.where(Certificate.member_name.like(value[1]))
			if field == "open_to_work":
				query = query.where(User.open_to == "Work")
			if field == "hiring":
				query = query.where(User.open_to == "Hiring")
	return query


@frappe.whitelist()
def get_count_of_certified_members(filters: dict = None):
	query = get_certification_query(filters)
	result = query.run(as_dict=True)
	return len(result) or 0


@frappe.whitelist()
def get_certification_categories():
	categories = []
	seen = set()
	docs = frappe.get_all(
		"LMS Certificate",
		filters={
			"published": 1,
		},
		fields=["course_title", "batch_title"],
	)

	for doc in docs:
		category = doc.course_title if doc.course_title else doc.batch_title
		if not category or category in seen:
			continue

		seen.add(category)
		categories.append({"label": category, "value": category})
	return categories


@frappe.whitelist()
def get_all_users():
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	users = frappe.get_all(
		"User",
		{
			"enabled": 1,
		},
		["name", "full_name", "user_image"],
	)

	return {user.name: user for user in users}


@frappe.whitelist(allow_guest=True)
def get_sidebar_settings():
	lms_settings = frappe.get_single("LMS Settings")
	if not lms_settings.allow_guest_access:
		return []

	sidebar_items = frappe._dict()
	items = [
		"courses",
		"batches",
		"certifications",
		"jobs",
		"statistics",
		"notifications",
		"programming_exercises",
	]
	for item in items:
		sidebar_items[item] = lms_settings.get(item)

	if len(lms_settings.sidebar_items):
		web_pages = frappe.get_all(
			"LMS Sidebar Item",
			{"parenttype": "LMS Settings", "parentfield": "sidebar_items"},
			["web_page", "route", "title as label", "icon", "name"],
		)
		for page in web_pages:
			page.to = page.route

		sidebar_items.web_pages = web_pages

	return sidebar_items


@frappe.whitelist()
def update_sidebar_item(webpage: str, icon: str):
	frappe.only_for("Moderator")
	filters = {
		"web_page": webpage,
		"parenttype": "LMS Settings",
		"parentfield": "sidebar_items",
		"parent": "LMS Settings",
	}

	if frappe.db.exists("LMS Sidebar Item", filters):
		frappe.db.set_value("LMS Sidebar Item", filters, "icon", icon)
	else:
		doc = frappe.new_doc("LMS Sidebar Item")
		doc.update(filters)
		doc.icon = icon
		doc.insert()


@frappe.whitelist()
def delete_sidebar_item(webpage: str):
	frappe.only_for("Moderator")
	return frappe.db.delete(
		"LMS Sidebar Item",
		{
			"web_page": webpage,
			"parenttype": "LMS Settings",
			"parentfield": "sidebar_items",
			"parent": "LMS Settings",
		},
	)


@frappe.whitelist()
def delete_lesson(lesson: str, chapter: str):
	course = frappe.db.get_value("Course Chapter", chapter, "course")
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to delete this lesson."), frappe.PermissionError)

	lessons = frappe.get_all(
		"Lesson Reference",
		{"parent": chapter},
		pluck="lesson",
		order_by="idx",
	)
	lessons.remove(lesson)
	frappe.db.delete("Lesson Reference", {"parent": chapter, "lesson": lesson})
	update_index(lessons, chapter)

	frappe.db.delete("LMS Course Progress", {"lesson": lesson})
	frappe.db.delete("Course Lesson", lesson)


@frappe.whitelist()
def update_lesson_index(lesson: str, sourceChapter: str, targetChapter: str, idx: int):
	course = frappe.db.get_value("Course Chapter", sourceChapter, "course")
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this lesson."), frappe.PermissionError)

	hasMoved = sourceChapter == targetChapter
	update_source_chapter(lesson, sourceChapter, idx, hasMoved)
	if not hasMoved:
		frappe.db.set_value("Course Lesson", lesson, "chapter", targetChapter)
		update_target_chapter(lesson, targetChapter, idx)


def update_source_chapter(lesson: str, chapter: str, idx: int, hasMoved: bool = False):
	lessons = frappe.get_all(
		"Lesson Reference",
		{
			"parent": chapter,
		},
		pluck="lesson",
		order_by="idx",
	)

	lessons.remove(lesson)
	if not hasMoved:
		frappe.db.delete("Lesson Reference", {"parent": chapter, "lesson": lesson})
	else:
		lessons.insert(idx, lesson)

	update_index(lessons, chapter)


def update_target_chapter(lesson: str, chapter: str, idx: int):
	lessons = frappe.get_all(
		"Lesson Reference",
		{
			"parent": chapter,
		},
		pluck="lesson",
		order_by="idx",
	)

	lessons.insert(idx, lesson)
	new_lesson_reference = frappe.new_doc("Lesson Reference")
	new_lesson_reference.update(
		{
			"lesson": lesson,
			"parent": chapter,
			"parenttype": "Course Chapter",
			"parentfield": "lessons",
		}
	)
	new_lesson_reference.insert()
	update_index(lessons, chapter)


def update_index(lessons: list, chapter: str):
	for row in lessons:
		frappe.db.set_value(
			"Lesson Reference", {"lesson": row, "parent": chapter}, "idx", lessons.index(row) + 1
		)


@frappe.whitelist()
def update_chapter_index(chapter: str, course: str, idx: int):
	"""Update the index of a chapter within a course"""

	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this chapter."), frappe.PermissionError)

	chapters = frappe.get_all(
		"Chapter Reference",
		{"parent": course},
		pluck="chapter",
		order_by="idx",
	)

	if chapter in chapters:
		chapters.remove(chapter)

	chapters.insert(idx, chapter)

	for i, chapter_name in enumerate(chapters):
		frappe.db.set_value("Chapter Reference", {"chapter": chapter_name, "parent": course}, "idx", i + 1)


@frappe.whitelist()
def get_members(start: int = 0, search: str = None):
	frappe.only_for(["Moderator"])
	filters = {"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]}
	or_filters = {}

	if search:
		or_filters["full_name"] = ["like", f"%{search}%"]
		or_filters["email"] = ["like", f"%{search}%"]

	members = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "user_image", "username", "last_active"],
		or_filters=or_filters,
		page_length=20,
		start=start,
	)

	for member in members:
		roles = frappe.get_all(
			"Has Role",
			{
				"parent": member.name,
				"parenttype": "User",
			},
			pluck="role",
		)
		if "Moderator" in roles:
			member.role = "Moderator"
		elif "Course Creator" in roles:
			member.role = "Course Creator"
		elif "Batch Evaluator" in roles:
			member.role = "Batch Evaluator"
		elif "LMS Student" in roles:
			member.role = "LMS Student"

	return members


def check_app_permission():
	"""Check if the user has permission to access the app."""
	if frappe.session.user == "Administrator":
		return True

	roles = frappe.get_roles()
	lms_roles = ["Moderator", "Course Creator", "Batch Evaluator", "LMS Student"]
	if any(role in roles for role in lms_roles):
		return True

	return False


@frappe.whitelist()
def save_evaluation_details(
	member: str,
	course: str,
	date: str,
	start_time: str,
	end_time: str,
	status: str,
	batch_name: str = None,
	evaluator: str = None,
	rating: float = 0,
	summary: str = None,
):
	"""
	Save evaluation details for a member against a course.
	"""
	frappe.only_for(["Batch Evaluator", "Moderator"])
	evaluation = frappe.db.exists("LMS Certificate Evaluation", {"member": member, "course": course})

	details = {
		"date": date,
		"start_time": start_time,
		"end_time": end_time,
		"status": status,
		"rating": rating / 5,
		"summary": summary,
		"batch_name": batch_name,
	}

	if evaluation:
		frappe.db.set_value("LMS Certificate Evaluation", evaluation, details)
		return evaluation
	else:
		doc = frappe.new_doc("LMS Certificate Evaluation")
		details.update(
			{
				"member": member,
				"course": course,
				"evaluator": evaluator,
			}
		)
		doc.update(details)
		doc.insert()
		return doc.name


@frappe.whitelist()
def save_certificate_details(
	member: str,
	issue_date: str,
	template: str,
	course: str = None,
	batch_name: str = None,
	evaluator: str = None,
	expiry_date: str = None,
	published: bool = True,
):
	"""
	Save certificate details for a member against a course.
	"""
	frappe.only_for(["Batch Evaluator", "Moderator"])
	certificate = frappe.db.exists("LMS Certificate", {"member": member, "course": course})

	details = {
		"published": published,
		"issue_date": issue_date,
		"expiry_date": expiry_date,
		"template": template,
		"batch_name": batch_name,
	}

	if certificate:
		frappe.db.set_value("LMS Certificate", certificate, details)
		return certificate
	else:
		doc = frappe.new_doc("LMS Certificate")
		details.update(
			{
				"member": member,
				"course": course,
				"evaluator": evaluator,
			}
		)
		doc.update(details)
		doc.insert()
		return doc.name


@frappe.whitelist()
def delete_documents(doctype: str, documents: list):
	frappe.only_for("Moderator")
	for doc in documents:
		frappe.delete_doc(doctype, doc)


@frappe.whitelist()
def get_payment_gateway_details(payment_gateway: str):
	frappe.only_for("Moderator")
	gateway = frappe.get_doc("Payment Gateway", payment_gateway)

	if gateway.gateway_controller is None:
		try:
			data = frappe.get_doc(f"{payment_gateway} Settings").as_dict()
			meta = frappe.get_meta(f"{payment_gateway} Settings").fields
			doctype = f"{payment_gateway} Settings"
			docname = f"{payment_gateway} Settings"
		except Exception:
			frappe.throw(_("{0} Settings not found").format(payment_gateway))
	else:
		try:
			data = frappe.get_doc(gateway.gateway_settings, gateway.gateway_controller).as_dict()
			meta = frappe.get_meta(gateway.gateway_settings).fields
			doctype = gateway.gateway_settings
			docname = gateway.gateway_controller
		except Exception:
			frappe.throw(_("{0} Settings not found").format(payment_gateway))

	gateway_fields = get_transformed_fields(meta, data)

	return {
		"fields": gateway_fields,
		"data": data,
		"doctype": doctype,
		"docname": docname,
	}


def get_transformed_fields(meta: list, data: dict = None):
	transformed_fields = []
	for row in meta:
		if row.fieldtype not in ["Column Break", "Section Break"]:
			if row.fieldtype in ["Attach", "Attach Image"]:
				fieldtype = "Upload"
				if data and data.get(row.fieldname):
					data[row.fieldname] = get_file_info(data.get(row.fieldname))
			elif row.fieldtype == "Check":
				fieldtype = "checkbox"
			else:
				fieldtype = row.fieldtype

			transformed_fields.append(
				{
					"label": row.label,
					"name": row.fieldname,
					"type": fieldtype,
				}
			)

	return transformed_fields


@frappe.whitelist()
def get_new_gateway_fields(doctype: str):
	frappe.only_for("Moderator")
	try:
		meta = frappe.get_meta(doctype).fields
	except Exception:
		frappe.throw(_("{0} not found").format(doctype))

	transformed_fields = get_transformed_fields(meta)

	return transformed_fields


def update_course_statistics():
	courses = frappe.get_all("LMS Course", fields=["name"])

	for course in courses:
		lessons = get_lesson_count(course.name)

		enrollments = frappe.db.count("LMS Enrollment", {"course": course.name, "member_type": "Student"})

		avg_rating = get_average_rating(course.name) or 0
		avg_rating = flt(avg_rating, frappe.get_system_settings("float_precision") or 3)

		from lms.lms.utils import calculate_course_completion_time
		est_time = calculate_course_completion_time(course.name)

		frappe.db.set_value(
			"LMS Course",
			course.name,
			{
				"lessons": lessons,
				"enrollments": enrollments,
				"rating": avg_rating,
				"estimated_completion_time": est_time
			},
		)


@frappe.whitelist()
def get_announcements(batch: str):
	roles = frappe.get_roles()
	is_batch_student = frappe.db.exists(
		"LMS Batch Enrollment", {"batch": batch, "member": frappe.session.user}
	)
	is_moderator = "Moderator" in roles
	is_evaluator = "Batch Evaluator" in roles

	if not (is_batch_student or is_moderator or is_evaluator):
		frappe.throw(
			_("You do not have permission to access announcements for this batch."), frappe.PermissionError
		)

	communications = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": "LMS Batch",
			"reference_name": batch,
		},
		fields=[
			"subject",
			"content",
			"recipients",
			"cc",
			"communication_date",
			"sender",
			"sender_full_name",
		],
		order_by="communication_date desc",
	)

	for communication in communications:
		communication.image = frappe.get_cached_value("User", communication.sender, "user_image")

	return communications


@frappe.whitelist()
def delete_course(course: str):
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to delete this course."), frappe.PermissionError)

	frappe.db.delete("LMS Enrollment", {"course": course})
	frappe.db.delete("LMS Course Progress", {"course": course})
	frappe.db.set_value("LMS Quiz", {"course": course}, {"course": None, "lesson": None})
	frappe.db.set_value("LMS Quiz Submission", {"course": course}, "course", None)
	frappe.db.set_value("LMS Assignment", {"course": course}, "course", None)

	chapters = frappe.get_all("Course Chapter", {"course": course}, pluck="name")
	frappe.db.delete("Chapter Reference", {"parent": course})

	for chapter in chapters:
		lessons = frappe.get_all("Course Lesson", {"chapter": chapter}, pluck="name")

		frappe.db.delete("Lesson Reference", {"parent": chapter})

		for lesson in lessons:
			topics = frappe.get_all(
				"Discussion Topic",
				{"reference_doctype": "Course Lesson", "reference_docname": lesson},
				pluck="name",
			)

			for topic in topics:
				frappe.db.delete("Discussion Reply", {"topic": topic})
				frappe.db.delete("Discussion Topic", topic)

			frappe.db.set_value("LMS Quiz", {"lesson": lesson}, {"course": None, "lesson": None})
			frappe.delete_doc("Course Lesson", lesson)

	for chapter in chapters:
		frappe.delete_doc("Course Chapter", chapter)

	frappe.delete_doc("LMS Course", course)


@frappe.whitelist()
def delete_batch(batch: str):
	if not can_modify_batch(batch):
		frappe.throw(_("You do not have permission to delete this batch."), frappe.PermissionError)

	frappe.db.delete("LMS Batch Enrollment", {"batch": batch})
	frappe.db.delete("Batch Course", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Assessment", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Batch Timetable", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Batch Feedback", {"batch": batch})
	delete_batch_discussions(batch)
	frappe.db.delete("LMS Batch", batch)


def delete_batch_discussions(batch: str):
	topics = frappe.get_all(
		"Discussion Topic",
		{"reference_doctype": "LMS Batch", "reference_docname": batch},
		pluck="name",
	)

	for topic in topics:
		frappe.db.delete("Discussion Reply", {"topic": topic})
		frappe.db.delete("Discussion Topic", topic)


def give_discussions_permission():
	doctypes = ["Discussion Topic", "Discussion Reply"]
	roles = ["LMS Student", "Course Creator", "Moderator", "Batch Evaluator"]
	for doctype in doctypes:
		for role in roles:
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
				frappe.get_doc(
					{
						"doctype": "Custom DocPerm",
						"parent": doctype,
						"role": role,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
						"if_owner": 0 if role == "Moderator" else 1,
					}
				).save()





@frappe.whitelist()
def upsert_chapter(
	title: str, course: str, is_scorm_package: bool = False, scorm_package: dict = None, name: str = None,
	exclude_from_course: bool = False, release_date: str = None, release_time: str = None
):
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this chapter."), frappe.PermissionError)

	values = frappe._dict({
		"title": title,
		"course": course,
		"is_scorm_package": is_scorm_package,
		"exclude_from_course": exclude_from_course,
		"release_date": release_date,
		"release_time": release_time
	})

	if is_scorm_package:
		scorm_package = frappe._dict(scorm_package)
		extract_path = extract_package(course, title, scorm_package)

		values.update(
			{
				"scorm_package": scorm_package.name,
				"scorm_package_path": extract_path.split("public")[1],
				"manifest_file": get_manifest_file(extract_path).split("public")[1],
				"launch_file": get_launch_file(extract_path).split("public")[1],
			}
		)

	if name:
		chapter = frappe.get_doc("Course Chapter", name)
	else:
		chapter = frappe.new_doc("Course Chapter")

	chapter.update(values)
	chapter.save()

	if is_scorm_package and not len(chapter.lessons):
		add_lesson(title, chapter.name, course, 1)

	return chapter


def extract_package(course: str, title: str, scorm_package: dict):
	package = frappe.get_doc("File", scorm_package.name)
	zip_path = package.get_full_path()
	# check_for_malicious_code(zip_path)
	extract_path = frappe.get_site_path("public", "scorm", course, title)
	zipfile.ZipFile(zip_path).extractall(extract_path)
	return extract_path


def check_for_malicious_code(zip_path):
	suspicious_patterns = [
		# Unsafe inline JavaScript
		r'on(click|load|mouseover|error|submit|focus|blur|change|keyup|keydown|keypress|resize)=".*?"',  # Inline event handlers (e.g., onerror, onclick)
		r'<script.*?src=["\']http',  # External script tags
		r"eval\(",  # Usage of eval()
		r"Function\(",  # Usage of Function constructor
		r"(btoa|atob)\(",  # Base64 encoding/decoding
		# Dangerous XML patterns
		r"<!ENTITY",  # XXE-related
		r"<\?xml-stylesheet .*?>",  # External stylesheets in XML
	]

	with zipfile.ZipFile(zip_path, "r") as zf:
		for file_name in zf.namelist():
			if file_name.endswith((".html", ".js", ".xml")):
				with zf.open(file_name) as file:
					content = file.read().decode("utf-8", errors="ignore")
					for pattern in suspicious_patterns:
						if re.search(pattern, content):
							frappe.throw(_("Suspicious pattern found in {0}: {1}").format(file_name, pattern))


def get_manifest_file(extract_path: str):
	manifest_file = None
	for root, _dirs, files in os.walk(extract_path):
		for file in files:
			if file == "imsmanifest.xml":
				manifest_file = os.path.join(root, file)
				break
		if manifest_file:
			break
	return manifest_file


def get_launch_file(extract_path: str):
	launch_file = None
	manifest_file = get_manifest_file(extract_path)

	if manifest_file:
		with open(manifest_file) as file:
			data = file.read()
			dom = parseString(data)
			resource = dom.getElementsByTagName("resource")
			for res in resource:
				if (
					res.getAttribute("adlcp:scormtype") == "sco"
					or res.getAttribute("adlcp:scormType") == "sco"
				):
					launch_file = res.getAttribute("href")
					break

		if launch_file:
			launch_file = os.path.join(os.path.dirname(manifest_file), launch_file)

	return launch_file


def add_lesson(title: str, chapter: str, course: str, idx: int):
	lesson = frappe.new_doc("Course Lesson")
	lesson.update(
		{
			"title": title,
			"chapter": chapter,
			"course": course,
		}
	)
	lesson.insert()

	lesson_reference = frappe.new_doc("Lesson Reference")
	lesson_reference.update(
		{
			"lesson": lesson.name,
			"idx": idx,
			"parent": chapter,
			"parenttype": "Course Chapter",
			"parentfield": "lessons",
		}
	)
	lesson_reference.insert()


@frappe.whitelist()
def delete_chapter(chapter: str):
	course = frappe.db.get_value("Course Chapter", chapter, "course")
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to delete this chapter."), frappe.PermissionError)

	chapterInfo = frappe.db.get_value(
		"Course Chapter", chapter, ["is_scorm_package", "scorm_package_path"], as_dict=True
	)

	if chapterInfo.is_scorm_package:
		delete_scorm_package(chapterInfo.scorm_package_path)

	course = frappe.db.get_value("Chapter Reference", {"chapter": chapter}, "parent")

	frappe.db.delete("Chapter Reference", {"chapter": chapter})
	frappe.db.delete("Lesson Reference", {"parent": chapter})
	frappe.db.delete("Course Lesson", {"chapter": chapter})
	frappe.db.delete("Course Chapter", chapter)

	# reset chapter reference index after deletion
	if course:
		chapters = frappe.get_all(
			"Chapter Reference", filters={"parent": course}, fields=["name"], order_by="idx asc"
		)

		i = 1
		for chapter in chapters:
			frappe.db.set_value("Chapter Reference", chapter.name, "idx", i)
			i += 1


def delete_scorm_package(scorm_package_path: str):
	scorm_package_path = frappe.get_site_path("public", scorm_package_path[1:])
	if os.path.exists(scorm_package_path):
		shutil.rmtree(scorm_package_path)


@frappe.whitelist()
def mark_lesson_progress(course: str, chapter_number: int, lesson_number: int):
	chapter_name = frappe.get_value("Chapter Reference", {"parent": course, "idx": chapter_number}, "chapter")
	lesson_name = frappe.get_value(
		"Lesson Reference", {"parent": chapter_name, "idx": lesson_number}, "lesson"
	)
	save_progress(lesson_name, course)


@frappe.whitelist()
def get_heatmap_data(member: str, base_days: int = 200):
	if not (has_course_instructor_role() or has_moderator_role() or has_evaluator_role()):
		frappe.throw(_("You do not have permission to access heatmap data."), frappe.PermissionError)

	base_date, start_date, number_of_days, days = calculate_date_ranges(base_days)
	date_count = initialize_date_count(days)

	lesson_completions, quiz_submissions, assignment_submissions = fetch_activity_data(member, start_date)
	count_dates(lesson_completions, date_count)
	count_dates(quiz_submissions, date_count)
	count_dates(assignment_submissions, date_count)

	heatmap_data, labels, total_activities, weeks = prepare_heatmap_data(
		start_date, number_of_days, date_count
	)

	return {
		"heatmap_data": heatmap_data,
		"labels": labels,
		"total_activities": total_activities,
		"weeks": weeks,
	}


def calculate_date_ranges(base_days: int):
	today = format_date(now(), "YYYY-MM-dd")
	day_today = get_datetime(today).strftime("%w")
	padding_end = 6 - cint(day_today)

	base_date = add_days(today, -base_days)
	day_of_base_date = cint(get_datetime(base_date).strftime("%w"))
	start_date = add_days(base_date, -day_of_base_date)
	number_of_days = base_days + day_of_base_date + padding_end
	days = [add_days(start_date, i) for i in range(number_of_days + 1)]

	return base_date, start_date, number_of_days, days


def initialize_date_count(days: list):
	return {format_date(day, "YYYY-MM-dd"): 0 for day in days}


def fetch_activity_data(member: str, start_date: str):
	lesson_completions = frappe.get_all(
		"LMS Course Progress",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date], "status": "Complete"},
	)

	quiz_submissions = frappe.get_all(
		"LMS Quiz Submission",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date]},
	)

	assignment_submissions = frappe.get_all(
		"LMS Assignment Submission",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date]},
	)

	return lesson_completions, quiz_submissions, assignment_submissions


def count_dates(data: list, date_count: dict):
	for entry in data:
		date = format_date(entry.creation, "YYYY-MM-dd")
		if date in date_count:
			date_count[date] += 1


def prepare_heatmap_data(start_date: str, number_of_days: int, date_count: dict):
	days_of_week = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
	heatmap_data = {day: [] for day in days_of_week}
	week_count = -(number_of_days // -7)
	labels = [None] * week_count
	last_seen_month = None
	sorted_dates = sorted(date_count.keys())

	for date in sorted_dates:
		activity_count = date_count[date]
		day_of_week = get_datetime(date).strftime("%a")
		current_month = get_datetime(date).strftime("%b")
		column_index = get_week_difference(start_date, date)

		if 0 <= column_index < week_count:
			heatmap_data[day_of_week].append(
				{
					"date": date,
					"count": activity_count,
					"label": f"{activity_count} activities on {format_date(date, 'dd MMM')}",
				}
			)

			if last_seen_month != current_month:
				labels[column_index] = current_month
				last_seen_month = current_month

	for index, label in enumerate(labels):
		if not label:
			labels[index] = ""

	formatted_heatmap_data = [{"name": day, "data": heatmap_data[day]} for day in days_of_week]

	total_activities = sum(date_count.values())
	return formatted_heatmap_data, labels, total_activities, week_count


def get_week_difference(start_date: str, current_date: str) -> int:
	diff_in_days = date_diff(current_date, start_date)
	return diff_in_days // 7


@frappe.whitelist()
def get_notifications(filters: dict = None):
	filters = frappe._dict(filters or {})
	filters.for_user = frappe.session.user
	notifications = frappe.get_all(
		"Notification Log",
		filters,
		[
			"subject",
			"from_user",
			"link",
			"read",
			"name",
			"creation",
			"document_type",
			"document_name",
			"type",
			"email_content",
		],
		order_by="creation desc",
	)

	for notification in notifications:
		notification = update_document_details(notification)
		notification = update_user_details(notification)

	return notifications


def update_user_details(notification: dict) -> dict:
	if (
		notification.document_details
		and len(notification.document_details.get("instructors", []))
		and not is_mention(notification)
	):
		from_user_details = notification.document_details["instructors"][0]
	else:
		from_user_details = frappe.db.get_value(
			"User", notification.from_user, ["full_name", "user_image"], as_dict=1
		)
	notification["from_user_details"] = from_user_details
	return notification


def is_mention(notification: dict) -> bool:
	if notification.type == "Mention":
		return True
	if "mentioned you" in notification.subject.lower():
		return True
	return False


def update_document_details(notification: dict) -> dict:
	if notification.document_type == "LMS Course":
		details = frappe.db.get_value(
			"LMS Course", notification.document_name, ["title", "video_link", "short_introduction"], as_dict=1
		)
		instructors = get_instructors("LMS Course", notification.document_name)
		details["instructors"] = instructors
		notification["document_details"] = details

	elif notification.document_type == "LMS Batch":
		details = frappe.db.get_value(
			"LMS Batch",
			notification.document_name,
			[
				"title",
				"description as short_introduction",
				"video_link",
				"start_date",
				"end_date",
				"start_time",
				"timezone",
			],
			as_dict=1,
		)
		instructors = get_instructors("LMS Batch", notification.document_name)
		details["instructors"] = instructors
		notification["document_details"] = details
	return notification


@frappe.whitelist(allow_guest=True)
def get_lms_settings():
	allowed_fields = [
		"allow_guest_access",
		"prevent_skipping_videos",
		"contact_us_email",
		"contact_us_url",
		"livecode_url",
		"disable_pwa",
		"statistics",
	]

	settings = frappe._dict()
	for field in allowed_fields:
		settings[field] = frappe.get_cached_value("LMS Settings", None, field)

	return settings


@frappe.whitelist()
def cancel_evaluation(evaluation: dict):
	evaluation = frappe._dict(evaluation)
	print(evaluation.member, frappe.session.user)
	if evaluation.member != frappe.session.user:
		frappe.throw(_("You do not have permission to cancel this evaluation."), frappe.PermissionError)

	frappe.db.set_value("LMS Certificate Request", evaluation.name, "status", "Cancelled")
	events = frappe.get_all(
		"Event Participants",
		{
			"email": evaluation.member,
		},
		["parent", "name"],
	)

	for event in events:
		info = frappe.db.get_value("Event", event.parent, ["starts_on", "subject"], as_dict=1)
		date = str(info.starts_on).split(" ")[0]

		if date == str(evaluation.date.format("YYYY-MM-DD")) and evaluation.member_name in info.subject:
			communication = frappe.db.get_value(
				"Communication",
				{"reference_doctype": "Event", "reference_name": event.parent},
				"name",
			)
			if communication:
				frappe.delete_doc("Communication", communication, ignore_permissions=True)

			frappe.delete_doc("Event Participants", event.name, ignore_permissions=True)
			frappe.delete_doc("Event", event.parent, ignore_permissions=True)


@frappe.whitelist()
def get_certification_details(course: str):
	membership = None
	filters = {"course": course, "member": frappe.session.user}

	if frappe.db.exists("LMS Enrollment", filters):
		membership = frappe.db.get_value(
			"LMS Enrollment",
			filters,
			["name", "purchased_certificate"],
			as_dict=1,
		)

	paid_certificate = frappe.db.get_value("LMS Course", course, "paid_certificate")
	certificate = frappe.db.get_value(
		"LMS Certificate",
		{"member": frappe.session.user, "course": course},
		["name", "template"],
		as_dict=1,
	)

	return {
		"membership": membership,
		"paid_certificate": paid_certificate,
		"certificate": certificate,
	}


@frappe.whitelist()
def save_role(user: str, role: str, value: int):
	frappe.only_for("Moderator")
	if cint(value):
		doc = frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": user,
				"role": role,
				"parenttype": "User",
				"parentfield": "roles",
			}
		)
		doc.save(ignore_permissions=True)
	else:
		frappe.db.delete("Has Role", {"parent": user, "role": role})
	frappe.clear_cache(user=user)
	return True


@frappe.whitelist()
def add_an_evaluator(email: str):
	frappe.only_for("Moderator")
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update(
			{
				"email": email,
				"first_name": email.split("@")[0].capitalize(),
				"enabled": 1,
			}
		)
		user.insert()
		user.add_roles("Batch Evaluator")

	evaluator = frappe.new_doc("Course Evaluator")
	evaluator.evaluator = email
	evaluator.insert()

	return evaluator




@frappe.whitelist()
def get_meta_info(type: str, route: str):
	if frappe.db.exists("Website Meta Tag", {"parent": f"{type}/{route}"}):
		meta_tags = frappe.get_all(
			"Website Meta Tag",
			{
				"parent": f"{type}/{route}",
			},
			["name", "key", "value"],
		)

		return meta_tags

	return []


@frappe.whitelist()
def update_meta_info(meta_type: str, route: str, meta_tags: list):
	frappe.only_for(["Course Creator", "Batch Evaluator", "Moderator"])
	validate_meta_data_permissions(meta_type)
	validate_meta_tags(meta_tags)

	parent_name = f"{meta_type}/{route}"
	for tag in meta_tags:
		existing_tag = frappe.db.exists(
			"Website Meta Tag",
			{
				"parent": parent_name,
				"parenttype": "Website Route Meta",
				"parentfield": "meta_tags",
				"key": tag["key"],
			},
		)
		if existing_tag:
			if not tag.get("value"):
				frappe.db.delete("Website Meta Tag", existing_tag)
				continue
			frappe.db.set_value("Website Meta Tag", existing_tag, "value", tag["value"])
		elif tag.get("value"):
			tag_properties = {
				"parent": parent_name,
				"parenttype": "Website Route Meta",
				"parentfield": "meta_tags",
				"key": tag["key"],
				"value": tag["value"],
			}

			parent_exists = frappe.db.exists("Website Route Meta", parent_name)
			if not parent_exists:
				create_meta(parent_name, tag_properties)
			else:
				create_meta_tag(tag_properties)


def validate_meta_tags(meta_tags: list):
	if not isinstance(meta_tags, list):
		frappe.throw(_("Meta tags should be a list."))


def create_meta(parent_name: str, tag_properties: dict):
	route_meta = frappe.new_doc("Website Route Meta")
	route_meta.update(
		{
			"__newname": parent_name,
		}
	)
	route_meta.append("meta_tags", tag_properties)
	route_meta.insert()


def create_meta_tag(tag_properties: dict):
	new_tag = frappe.new_doc("Website Meta Tag")
	new_tag.update(tag_properties)
	new_tag.insert()


def validate_meta_data_permissions(meta_type: str):
	roles = frappe.get_roles()

	if meta_type == "courses":
		if not ("Course Creator" in roles or "Moderator" in roles):
			frappe.throw(_("You do not have permission to update meta tags."))

	elif meta_type == "batches":
		if not ("Batch Evaluator" in roles or "Moderator" in roles):
			frappe.throw(_("You do not have permission to update meta tags."))


@frappe.whitelist()
def create_programming_exercise_submission(exercise: str, submission: str, code: str, test_cases: list):
	if submission == "new":
		sub_name = make_new_exercise_submission(exercise, code, test_cases)
	else:
		sub_name = submission
		update_exercise_submission(submission, code, test_cases)

	from lms.lms.doctype.course_lesson.course_lesson import save_progress_for_programming_exercise
	save_progress_for_programming_exercise(exercise)

	return sub_name


def make_new_exercise_submission(exercise: str, code: str, test_cases: list):
	submission = frappe.new_doc("LMS Programming Exercise Submission")
	submission.exercise = exercise
	submission.member = frappe.session.user
	submission.code = code

	for test_case in test_cases:
		submission.append(
			"test_cases",
			{
				"input": test_case.get("input"),
				"output": test_case.get("output"),
				"expected_output": test_case.get("expected_output"),
				"status": test_case.get("status", test_case.get("status", "Failed")),
			},
		)

	submission.status = get_exercise_status(test_cases)
	submission.insert()
	return submission.name


def update_exercise_submission(submission: str, code: str, test_cases: list):
	member = frappe.db.get_value("LMS Programming Exercise Submission", submission, "member")
	if member != frappe.session.user:
		frappe.throw(_("You do not have permission to update this submission."), frappe.PermissionError)

	update_test_cases(test_cases, submission)
	status = get_exercise_status(test_cases)
	frappe.db.set_value("LMS Programming Exercise Submission", submission, {"status": status, "code": code})


def get_exercise_status(test_cases: list):
	if not test_cases:
		return "Failed"

	if all(row.get("status", "Failed") == "Passed" for row in test_cases):
		return "Passed"
	else:
		return "Failed"


def update_test_cases(test_cases: list, submission: str):
	frappe.db.delete("LMS Test Case Submission", {"parent": submission})
	for row in test_cases:
		test_case = frappe.new_doc("LMS Test Case Submission")
		test_case.update(
			{
				"parent": submission,
				"parenttype": "LMS Programming Exercise Submission",
				"parentfield": "test_cases",
				"input": row.get("input"),
				"output": row.get("output"),
				"expected_output": row.get("expected_output"),
				"status": row.get("status", "Failed"),
			}
		)
		test_case.insert()


@frappe.whitelist()
def track_video_watch_duration(lesson: str, videos: list):
	"""
	Track the watch duration of videos in a lesson.
	"""
	if not isinstance(videos, list):
		videos = json.loads(videos)

	has_duration_field = frappe.get_meta("LMS Video Watch Duration").has_field("duration")

	for video in videos:
		# Skip entries with no source or no watch_time — these come from uninitialized
		# Plyr players (e.g., during the ready→seek→pause sequence) and would fail the
		# mandatory field check on insert.
		if not video.get("source") or video.get("watch_time") is None:
			continue

		filters = {
			"lesson": lesson,
			"source": video.get("source"),
			"member": frappe.session.user,
		}
		existing_record = frappe.db.get_value(
			"LMS Video Watch Duration", filters, ["name", "watch_time"], as_dict=True
		)

		update_values = {
			"watch_time": video.get("watch_time")
		}
		if video.get("duration") and has_duration_field:
			update_values["duration"] = video.get("duration")

		if existing_record:
			if flt(existing_record.watch_time) < flt(video.get("watch_time")):
				frappe.db.set_value(
					"LMS Video Watch Duration",
					filters,
					update_values
				)
		else:
			track_new_watch_time(lesson, video, has_duration_field)


def track_new_watch_time(lesson: str, video: dict, has_duration_field: bool = False):
	doc = frappe.new_doc("LMS Video Watch Duration")
	doc.lesson = lesson
	doc.source = video.get("source")
	doc.watch_time = video.get("watch_time")
	doc.member = frappe.session.user
	if video.get("duration") and has_duration_field:
		doc.duration = video.get("duration")
	doc.save()


@frappe.whitelist()
def get_course_progress_distribution(course: str, batch: str = None):
	if not can_modify_course(course):
		frappe.throw(
			_("You do not have permission to access this course's progress data."), frappe.PermissionError
		)

	filters = {"course": course}
	if batch:
		if batch == "unbatched":
			batch_courses = frappe.get_all(
				"Batch Course",
				filters={"course": course},
				pluck="parent",
			)
			if batch_courses:
				batch_members = frappe.get_all(
					"LMS Batch Enrollment",
					filters={"batch": ["in", batch_courses]},
					pluck="member",
				)
				if batch_members:
					filters["member"] = ["not in", batch_members]
		else:
			enrolled_students = frappe.get_all(
				"LMS Batch Enrollment",
				filters={"batch": batch},
				pluck="member",
			)
			if not enrolled_students:
				return {
					"average_progress": 0,
					"progress_distribution": [],
					"enrolled_count": 0,
					"average_rating": 0,
				}
			filters["member"] = ["in", enrolled_students]

	all_progress = frappe.get_all(
		"LMS Enrollment",
		filters=filters,
		pluck="progress",
	)

	average_progress = get_average_course_progress(all_progress)
	progress_distribution = get_progress_distribution(all_progress)
	enrolled_count = len(all_progress)
	average_rating = get_batch_average_rating(course, batch)

	return {
		"average_progress": average_progress,
		"progress_distribution": progress_distribution,
		"enrolled_count": enrolled_count,
		"average_rating": average_rating,
	}


def get_batch_average_rating(course: str, batch: str = None) -> float:
	if not batch:
		val = frappe.db.get_value("LMS Course", course, "rating")
		return flt(val) if val is not None else 0.0

	if batch == "unbatched":
		batch_courses = frappe.get_all(
			"Batch Course",
			filters={"course": course},
			pluck="parent",
		)
		if batch_courses:
			batch_members = frappe.get_all(
				"LMS Batch Enrollment",
				filters={"batch": ["in", batch_courses]},
				pluck="member",
			)
			if batch_members:
				reviews = frappe.get_all(
					"LMS Course Review",
					filters={"course": course, "owner": ["not in", batch_members]},
					fields=["rating"],
				)
			else:
				reviews = frappe.get_all(
					"LMS Course Review",
					filters={"course": course},
					fields=["rating"],
				)
		else:
			reviews = frappe.get_all(
				"LMS Course Review",
				filters={"course": course},
				fields=["rating"],
			)
	else:
		enrolled_students = frappe.get_all(
			"LMS Batch Enrollment",
			filters={"batch": batch},
			pluck="member",
		)
		if not enrolled_students:
			return 0.0

		reviews = frappe.get_all(
			"LMS Course Review",
			filters={"course": course, "owner": ["in", enrolled_students]},
			fields=["rating"],
		)
	if not reviews:
		return 0.0

	out_of_ratings = frappe.db.get_all(
		"DocField", {"parent": "LMS Course Review", "fieldtype": "Rating"}, ["options"]
	)
	out_of_ratings = (len(out_of_ratings) and out_of_ratings[0].options) or 5

	ratings = [r.rating * out_of_ratings for r in reviews]
	avg_rating = sum(ratings) / len(ratings)
	return flt(avg_rating, frappe.get_system_settings("float_precision") or 3)


def get_average_course_progress(progress_list: list):
	if not progress_list:
		return 0
	average_progress = sum(progress_list) / len(progress_list)
	return flt(average_progress, frappe.get_system_settings("float_precision") or 3)


def get_progress_distribution(progressList: list):
	distribution = [
		{
			"name": "Just Started (0-30%)",
			"value": len([p for p in progressList if 0 <= p < 30]),
		},
		{
			"name": "In Progress (30-60%)",
			"value": len([p for p in progressList if 30 <= p < 60]),
		},
		{
			"name": "Advanced (60-99%)",
			"value": len([p for p in progressList if 60 <= p < 100]),
		},
		{
			"name": "Completed (100%)",
			"value": len([p for p in progressList if p == 100]),
		},
	]

	return distribution


@frappe.whitelist(allow_guest=True)
def get_pwa_manifest():
	title = frappe.db.get_single_value("Website Settings", "app_name") or "Manlayag"
	banner_image = frappe.db.get_single_value("Website Settings", "banner_image")

	manifest = {
		"name": title,
		"short_name": title,
		"description": "Easy to use, 100% open source Learning Management System",
		"start_url": get_lms_route(),
		"icons": [
			{
				"src": banner_image or "/assets/lms/frontend/manifest/manifest-icon-192.maskable.png",
				"sizes": "192x192",
				"type": "image/png",
				"purpose": "maskable any",
			}
		],
	}

	return Response(json.dumps(manifest), status=200, content_type="application/manifest+json")


@frappe.whitelist()
def get_profile_details(username: str):
	details = frappe.db.get_value(
		"User",
		{"username": username},
		[
			"first_name",
			"last_name",
			"full_name",
			"name",
			"username",
			"user_image",
			"bio",
			"headline",
			"language",
			"cover_image",
			"open_to",
			"linkedin",
			"github",
			"twitter",
		],
		as_dict=True,
	)

	details.roles = frappe.get_roles(details.name)
	return details


@frappe.whitelist()
def get_streak_info():
	all_dates = fetch_activity_dates(frappe.session.user)
	streak, longest_streak = calculate_streaks(all_dates)
	current_streak = calculate_current_streak(all_dates, streak)

	return {
		"current_streak": current_streak,
		"longest_streak": longest_streak,
	}


def fetch_activity_dates(user: str):
	doctypes = [
		"LMS Course Progress",
		"LMS Quiz Submission",
		"LMS Assignment Submission",
		"LMS Programming Exercise Submission",
	]

	all_dates = []
	for dt in doctypes:
		all_dates.extend(frappe.get_all(dt, {"member": user}, pluck="creation"))

	return sorted({d.date() if hasattr(d, "date") else d for d in all_dates})


def calculate_streaks(all_dates: list):
	streak = 0
	longest_streak = 0
	prev_day = None

	for d in all_dates:
		if d.weekday() in (5, 6):
			continue

		if prev_day:
			expected = prev_day + timedelta(days=1)
			while expected.weekday() in (5, 6):
				expected += timedelta(days=1)

			streak = streak + 1 if d == expected else 1
		else:
			streak = 1

		longest_streak = max(longest_streak, streak)
		prev_day = d

	return streak, longest_streak


def calculate_current_streak(all_dates: list, streak: int):
	if not all_dates:
		return 0

	last_date = all_dates[-1]
	today = getdate()

	ref_day = today
	while ref_day.weekday() in (5, 6):
		ref_day -= timedelta(days=1)

	if last_date == ref_day or last_date == ref_day - timedelta(days=1):
		return streak
	return 0


@frappe.whitelist()
def get_my_live_classes():
	my_live_classes = []

	batches = frappe.get_all(
		"LMS Batch Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="creation desc",
		pluck="batch",
	)

	live_class_details = frappe.get_all(
		"LMS Live Class",
		filters={
			"date": [">=", getdate()],
			"batch_name": ["in", batches],
		},
		fields=[
			"name",
			"title",
			"description",
			"time",
			"date",
			"duration",
			"attendees",
			"start_url",
			"join_url",
			"owner",
		],
		limit=2,
		order_by="date",
	)

	if len(live_class_details):
		for live_class in live_class_details:
			live_class.course_title = frappe.db.get_value("LMS Course", live_class.course, "title")

			my_live_classes.append(live_class)

	return my_live_classes


@frappe.whitelist()
def get_created_courses():
	created_courses = []

	CourseInstructor = frappe.qb.DocType("Course Instructor")
	Course = frappe.qb.DocType("LMS Course")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(Course)
		.on(CourseInstructor.parent == Course.name)
		.select(Course.name)
		.where(CourseInstructor.instructor == frappe.session.user)
		.orderby(Course.published_on, order=frappe.qb.desc)
		.limit(3)
	)

	results = query.run(as_dict=True)
	courses = [row["name"] for row in results]

	for course in courses:
		course_details = get_course_details(course)
		created_courses.append(course_details)

	return created_courses


@frappe.whitelist()
def get_created_batches():
	created_batches = []

	CourseInstructor = frappe.qb.DocType("Course Instructor")
	Batch = frappe.qb.DocType("LMS Batch")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(Batch)
		.on(CourseInstructor.parent == Batch.name)
		.select(Batch.name)
		.where(CourseInstructor.instructor == frappe.session.user)
		.where(Batch.start_date >= getdate())
		.orderby(Batch.start_date, order=frappe.qb.asc)
		.limit(4)
	)

	results = query.run(as_dict=True)
	batches = [row["name"] for row in results]

	for batch in batches:
		batch_details = get_batch_details(batch)
		created_batches.append(batch_details)

	return created_batches


@frappe.whitelist()
def get_admin_live_classes():
	CourseInstructor = frappe.qb.DocType("Course Instructor")
	LMSLiveClass = frappe.qb.DocType("LMS Live Class")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(LMSLiveClass)
		.on(CourseInstructor.parent == LMSLiveClass.batch_name)
		.select(
			LMSLiveClass.name,
			LMSLiveClass.title,
			LMSLiveClass.description,
			LMSLiveClass.time,
			LMSLiveClass.date,
			LMSLiveClass.duration,
			LMSLiveClass.attendees,
			LMSLiveClass.start_url,
			LMSLiveClass.join_url,
			LMSLiveClass.owner,
		)
		.where(CourseInstructor.instructor == frappe.session.user)
		.where(LMSLiveClass.date >= getdate())
		.orderby(LMSLiveClass.date, order=frappe.qb.asc)
		.limit(4)
	)
	results = query.run(as_dict=True)
	return results


@frappe.whitelist()
def get_admin_evals():
	evals = frappe.get_all(
		"LMS Certificate Request",
		{
			"evaluator": frappe.session.user,
			"date": [">=", getdate()],
		},
		[
			"name",
			"date",
			"start_time",
			"course",
			"evaluator",
			"google_meet_link",
			"member",
			"member_name",
		],
		limit=4,
		order_by="date asc",
	)

	for evaluation in evals:
		evaluation.course_title = frappe.db.get_value("LMS Course", evaluation.course, "title")

	return evals


@frappe.whitelist()
def get_my_courses():
	my_courses = []
	courses = get_my_latest_courses()

	if not len(courses):
		courses = get_featured_home_courses()

	if not len(courses):
		courses = get_popular_courses()

	for course in courses:
		my_courses.append(get_course_details(course))

	return my_courses


def get_my_latest_courses():
	return frappe.get_all(
		"LMS Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="modified desc",
		limit=3,
		pluck="course",
	)


def get_featured_home_courses():
	return frappe.get_all(
		"LMS Course",
		{"published": 1, "featured": 1},
		order_by="published_on desc",
		limit=3,
		pluck="name",
	)


def get_popular_courses():
	return frappe.get_all(
		"LMS Course",
		{
			"published": 1,
		},
		order_by="enrollments desc",
		limit=3,
		pluck="name",
	)


@frappe.whitelist()
def get_my_batches():
	my_batches = []
	batches = get_my_latest_batches()

	if not len(batches):
		batches = get_upcoming_batches()

	for batch in batches:
		batch_details = get_batch_details(batch)
		if batch_details:
			my_batches.append(batch_details)

	return my_batches


def get_my_latest_batches():
	return frappe.get_all(
		"LMS Batch Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="creation desc",
		limit=4,
		pluck="batch",
	)


def get_upcoming_batches():
	return frappe.get_all(
		"LMS Batch",
		{
			"published": 1,
			"start_date": [">=", getdate()],
		},
		order_by="start_date asc",
		limit=4,
		pluck="name",
	)


@frappe.whitelist()
def delete_programming_exercise(exercise: str):
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	frappe.db.delete("LMS Programming Exercise Submission", {"exercise": exercise})
	frappe.db.delete("LMS Programming Exercise", exercise)


@frappe.whitelist()
def get_lesson_completion_stats(course: str, batch: str = None):
	roles = frappe.get_roles()
	if "Course Creator" not in roles and "Moderator" not in roles:
		frappe.throw(_("You do not have permission to access lesson completion stats."))

	CourseProgress = frappe.qb.DocType("LMS Course Progress")
	LessonReference = frappe.qb.DocType("Lesson Reference")
	ChapterReference = frappe.qb.DocType("Chapter Reference")
	Lesson = frappe.qb.DocType("Course Lesson")

	join_cond = (
		(CourseProgress.lesson == LessonReference.lesson)
		& (CourseProgress.course == course)
		& (CourseProgress.status == "Complete")
	)

	if batch:
		if batch == "unbatched":
			batch_courses = frappe.get_all(
				"Batch Course",
				filters={"course": course},
				pluck="parent",
			)
			if batch_courses:
				batch_members = frappe.get_all(
					"LMS Batch Enrollment",
					filters={"batch": ["in", batch_courses]},
					pluck="member",
				)
				if batch_members:
					course_students = frappe.get_all(
						"LMS Enrollment",
						filters={"course": course, "member": ["not in", batch_members]},
						pluck="member",
					)
				else:
					course_students = frappe.get_all(
						"LMS Enrollment",
						filters={"course": course},
						pluck="member",
					)
			else:
				course_students = frappe.get_all(
					"LMS Enrollment",
					filters={"course": course},
					pluck="member",
				)
			
			if course_students:
				join_cond &= (CourseProgress.member.isin(course_students))
			else:
				join_cond &= (CourseProgress.member == "")
		else:
			enrolled_students = frappe.get_all(
				"LMS Batch Enrollment",
				filters={"batch": batch},
				pluck="member",
			)
			if enrolled_students:
				course_enrolled_batch_students = frappe.get_all(
					"LMS Enrollment",
					filters={"course": course, "member": ["in", enrolled_students]},
					pluck="member",
				)
				if course_enrolled_batch_students:
					join_cond &= (CourseProgress.member.isin(course_enrolled_batch_students))
				else:
					join_cond &= (CourseProgress.member == "")
			else:
				join_cond &= (CourseProgress.member == "")
	else:
		course_students = frappe.get_all(
			"LMS Enrollment",
			filters={"course": course},
			pluck="member",
		)
		if course_students:
			join_cond &= (CourseProgress.member.isin(course_students))
		else:
			join_cond &= (CourseProgress.member == "")

	rows = (
		frappe.qb.from_(LessonReference)
		.join(ChapterReference)
		.on(LessonReference.parent == ChapterReference.chapter)
		.join(Lesson)
		.on(LessonReference.lesson == Lesson.name)
		.left_join(CourseProgress)
		.on(join_cond)
		.select(
			LessonReference.idx,
			ChapterReference.idx.as_("chapter_idx"),
			CourseProgress.lesson,
			Lesson.title,
			Lesson.name.as_("lesson_name"),
			fn.Count(CourseProgress.name).as_("completion_count"),
		)
		.where(ChapterReference.parent == course)
		.groupby(LessonReference.lesson)
		.orderby(ChapterReference.idx, LessonReference.idx)
		.run(as_dict=True)
	)

	return rows


@frappe.whitelist()
def get_course_assessment_progress(course: str, member: str):
	if not can_modify_course(course):
		frappe.throw(
			_("You do not have permission to access this course's assessment data."), frappe.PermissionError
		)

	quizzes = get_course_quiz_progress(course, member)
	assignments = get_course_assignment_progress(course, member)
	programming_exercises = get_course_programming_exercise_progress(course, member)

	return {
		"quizzes": quizzes,
		"assignments": assignments,
		"exercises": programming_exercises,
	}


def get_course_quiz_progress(course: str, member: str):
	quizzes = get_assessment_from_lesson(course, "quiz")
	attempts = []

	for quiz in quizzes:
		submissions = frappe.get_all(
			"LMS Quiz Submission",
			{
				"quiz": quiz,
				"member": member,
			},
			["name", "score", "percentage", "quiz", "quiz_title"],
			order_by="creation desc",
			limit=1,
		)
		if len(submissions):
			attempts.append(submissions[0])
		else:
			attempts.append(
				{
					"quiz": quiz,
					"quiz_title": frappe.db.get_value("LMS Quiz", quiz, "title"),
					"score": 0,
					"percentage": 0,
				}
			)

	return attempts


def get_course_assignment_progress(course: str, member: str):
	assignments = get_assessment_from_lesson(course, "assignment")
	submissions = []

	for assignment in assignments:
		assignment_subs = frappe.get_all(
			"LMS Assignment Submission",
			{
				"assignment": assignment,
				"member": member,
			},
			["name", "status", "assignment", "assignment_title"],
			order_by="creation desc",
			limit=1,
		)
		if len(assignment_subs):
			submissions.append(assignment_subs[0])
		else:
			submissions.append(
				{
					"assignment": assignment,
					"assignment_title": frappe.db.get_value("LMS Assignment", assignment, "title"),
					"status": "Not Submitted",
				}
			)

	return submissions


def get_course_programming_exercise_progress(course: str, member: str):
	exercises = get_assessment_from_lesson(course, "program")
	submissions = []

	for exercise in exercises:
		exercise_subs = frappe.get_all(
			"LMS Programming Exercise Submission",
			{
				"exercise": exercise,
				"member": member,
			},
			["name", "status", "exercise", "exercise_title"],
			order_by="creation desc",
			limit=1,
		)
		if len(exercise_subs):
			submissions.append(exercise_subs[0])
		else:
			submissions.append(
				{
					"exercise": exercise,
					"exercise_title": frappe.db.get_value("LMS Programming Exercise", exercise, "title"),
					"status": "Not Attempted",
				}
			)

	return submissions


def get_assessment_from_lesson(course: str, assessmentType: str):
	assessments = []
	lessons = frappe.get_all("Course Lesson", {"course": course}, ["name", "title", "content"])

	for lesson in lessons:
		if lesson.content:
			content = json.loads(lesson.content)
			for block in content.get("blocks", []):
				if block.get("type") == assessmentType:
					data_field = "exercise" if assessmentType == "program" else assessmentType
					quiz_name = block.get("data", {}).get(data_field)
					assessments.append(quiz_name)

	return assessments


def ensure_video_transcript_field():
	if not frappe.db.exists("Custom Field", {"dt": "Course Lesson", "fieldname": "video_transcript"}):
		try:
			from frappe.custom.doctype.custom_field.custom_field import create_custom_field
			create_custom_field("Course Lesson", {
				"fieldname": "video_transcript",
				"label": "Video Transcript",
				"fieldtype": "Long Text",
				"read_only": 1
			})
			frappe.db.commit()
		except Exception:
			try:
				doc = frappe.new_doc("Custom Field")
				doc.dt = "Course Lesson"
				doc.fieldname = "video_transcript"
				doc.label = "Video Transcript"
				doc.fieldtype = "Long Text"
				doc.read_only = 1
				doc.insert(ignore_permissions=True)
				frappe.db.commit()
			except Exception as e:
				frappe.log_error(f"Error creating custom field video_transcript: {str(e)}")


@frappe.whitelist(allow_guest=True)
def get_video_transcript(video_id: str, service: str):
	"""Get transcript for a YouTube or Vimeo video, auto-generating/scraping it and caching/persisting the result."""
	import json
	import re
	if not video_id:
		return []

	# Ensure DB column exists dynamically
	ensure_video_transcript_field()

	# Check Redis cache first (high performance)
	cache_key = f"video_transcript_v4_{service}_{video_id}"
	cached_val = frappe.cache().get_value(cache_key)
	if cached_val:
		try:
			return json.loads(cached_val)
		except Exception:
			pass

	# Find the Course Lesson name by matching the video_id in youtube, body, content, or instructor_notes fields
	lesson_name = None
	if video_id:
		like_str = f"%{video_id}%"
		results = frappe.db.sql(
			"""
			select name from `tabCourse Lesson`
			where youtube like %s or body like %s or content like %s or instructor_notes like %s
			limit 1
			""",
			(like_str, like_str, like_str, like_str),
			as_dict=True
		)
		if results:
			lesson_name = results[0].name

	# Check Database persistent storage
	transcripts_dict = {}
	if lesson_name:
		try:
			stored_val = frappe.db.get_value("Course Lesson", lesson_name, "video_transcript")
			if stored_val:
				data = json.loads(stored_val)
				if isinstance(data, dict):
					transcripts_dict = data
				elif isinstance(data, list):
					# Convert old list format to new dictionary format
					youtube_url = frappe.db.get_value("Course Lesson", lesson_name, "youtube")
					# Extract primary video id to use as key
					primary_video_id = video_id
					if youtube_url:
						if "vimeo" in youtube_url:
							vm_match = re.search(r'(?:vimeo\.com\/|player\.vimeo\.com\/video\/)(\d+)', youtube_url)
							if vm_match:
								primary_video_id = vm_match.group(1)
						else:
							yt_match = re.search(r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=))([\w-]{11})', youtube_url)
							if yt_match:
								primary_video_id = yt_match.group(1)
					transcripts_dict = {primary_video_id: data}

				# If our specific video ID is in the dictionary, cache and return it
				if video_id in transcripts_dict:
					frappe.cache().set_value(cache_key, json.dumps(transcripts_dict[video_id]), expires_in_sec=86400 * 7)
					return transcripts_dict[video_id]
		except Exception as db_err:
			frappe.log_error(f"Error reading video_transcript from DB: {str(db_err)}")

	# Fetch from External API / scraping
	transcript = None
	if service == "youtube":
		transcript = fetch_youtube_transcript(video_id)
	elif service == "vimeo":
		transcript = fetch_vimeo_transcript(video_id)

	# Save to Database and Cache if successful
	if transcript:
		# Cache in Redis
		frappe.cache().set_value(cache_key, json.dumps(transcript), expires_in_sec=86400 * 7)
		# Persist in Database
		if lesson_name:
			try:
				transcripts_dict[video_id] = transcript
				frappe.db.set_value("Course Lesson", lesson_name, "video_transcript", json.dumps(transcripts_dict))
				frappe.db.commit()
			except Exception as save_err:
				frappe.log_error(f"Failed to persist transcript to DB: {str(save_err)}")
		return transcript

	return []


def fetch_youtube_transcript(video_id):
	import requests
	import re
	import json
	import xml.etree.ElementTree as ET
	from html import unescape

	try:
		# First attempt: check if youtube_transcript_api is installed and use it
		try:
			try:
				from youtube_transcript_api import YouTubeTranscriptApi
			except ImportError:
				import subprocess
				import sys
				# Try installing it on the fly
				subprocess.check_call([sys.executable, "-m", "pip", "install", "youtube-transcript-api"])
				from youtube_transcript_api import YouTubeTranscriptApi

			transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
			return [{
				"text": unescape(t["text"]),
				"start": t["start"],
				"duration": t["duration"]
			} for t in transcript_list]
		except Exception as e:
			frappe.log_error(f"YouTubeTranscriptApi attempt failed for {video_id}: {str(e)}")

		# Second attempt: scrape YouTube initial player response
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
		}
		r = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=headers, timeout=10)
		match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', r.text)
		if not match:
			match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*</script>', r.text)
		
		if match:
			player_response = json.loads(match.group(1))
			captions = player_response.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
			if captions:
				# Find English track if possible, otherwise use the first available
				track_url = None
				for track in captions:
					if 'en' in track.get('languageCode', ''):
						track_url = track.get('baseUrl')
						break
				if not track_url:
					track_url = captions[0].get('baseUrl')

				if track_url:
					xml_r = requests.get(track_url, headers=headers, timeout=10)
					root = ET.fromstring(xml_r.text)
					transcript = []
					for text_el in root.findall('text'):
						start = float(text_el.attrib.get('start', 0))
						duration = float(text_el.attrib.get('dur', 0))
						text = unescape("".join(text_el.itertext()))
						text = " ".join(text.split())
						transcript.append({
							'text': text,
							'start': start,
							'duration': duration
						})
					return transcript
	except Exception as e:
		frappe.log_error(f"Error fetching YouTube transcript: {str(e)}")
	return None


def fetch_vimeo_transcript(video_id):
	import requests
	import re
	import json

	try:
		headers = {
			"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
		}
		r = requests.get(f"https://player.vimeo.com/video/{video_id}/config", headers=headers, timeout=10)
		if r.status_code == 200:
			config = r.json()
			text_tracks = config.get("request", {}).get("text_tracks", [])
			if text_tracks:
				track_url = None
				for track in text_tracks:
					if track.get("lang") == "en" or "en" in track.get("lang", ""):
						track_url = track.get("url")
						break
				if not track_url:
					track_url = text_tracks[0].get("url")

				if track_url:
					vtt_r = requests.get(f"https://player.vimeo.com{track_url}" if track_url.startswith("/") else track_url, headers=headers, timeout=10)
					if vtt_r.status_code == 200:
						return parse_vtt(vtt_r.text)
	except Exception as e:
		frappe.log_error(f"Error fetching Vimeo transcript: {str(e)}")
	return None


def parse_vtt(vtt_text):
	import re
	lines = vtt_text.split('\n')
	transcript = []
	current_time = None
	current_text = []

	def parse_time(time_str):
		parts = time_str.split(':')
		seconds_parts = parts[-1].split('.')
		seconds = float(seconds_parts[0])
		milliseconds = float('0.' + seconds_parts[1]) if len(seconds_parts) > 1 else 0
		minutes = float(parts[-2]) if len(parts) > 1 else 0
		hours = float(parts[-3]) if len(parts) > 2 else 0
		return hours * 3600 + minutes * 60 + seconds + milliseconds

	for line in lines:
		line = line.strip()
		if not line:
			if current_time and current_text:
				transcript.append({
					'text': " ".join(current_text),
					'start': current_time[0],
					'duration': current_time[1]
				})
				current_time = None
				current_text = []
			continue
		
		if line.startswith("WEBVTT") or line.startswith("STYLE") or line.startswith("NOTE"):
			continue

		if '-->' in line:
			match = re.search(r'(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)\s*-->\s*(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)', line)
			if match:
				start = parse_time(match.group(1))
				end = parse_time(match.group(2))
				current_time = (start, end - start)
		elif not line.isdigit() and current_time:
			line_cleaned = re.sub(r'<[^>]*>', '', line)
			if line_cleaned:
				current_text.append(line_cleaned)

	if current_time and current_text:
		transcript.append({
			'text': " ".join(current_text),
			'start': current_time[0],
			'duration': current_time[1]
		})

	return transcript


def parse_srt(srt_text):
	import re
	blocks = srt_text.replace('\r\n', '\n').split('\n\n')
	transcript = []
	
	def parse_time(time_str):
		time_str = time_str.replace(',', '.')
		parts = time_str.split(':')
		seconds_parts = parts[-1].split('.')
		seconds = float(seconds_parts[0])
		milliseconds = float('0.' + seconds_parts[1]) if len(seconds_parts) > 1 else 0
		minutes = float(parts[-2]) if len(parts) > 1 else 0
		hours = float(parts[-3]) if len(parts) > 2 else 0
		return hours * 3600 + minutes * 60 + seconds + milliseconds

	for block in blocks:
		block = block.strip()
		if not block:
			continue
		lines = block.split('\n')
		if len(lines) < 2:
			continue
		
		time_line_idx = -1
		for i, line in enumerate(lines):
			if '-->' in line:
				time_line_idx = i
				break
		
		if time_line_idx == -1:
			continue
			
		time_line = lines[time_line_idx]
		text_lines = lines[time_line_idx + 1:]
		
		match = re.search(r'(\d+:\d+:\d+[\.,]\d+|\d+:\d+[\.,]\d+)\s*-->\s*(\d+:\d+:\d+[\.,]\d+|\d+:\d+[\.,]\d+)', time_line)
		if match:
			try:
				start = parse_time(match.group(1))
				end = parse_time(match.group(2))
				text = " ".join([re.sub(r'<[^>]*>', '', l.strip()) for l in text_lines if l.strip()])
				if text:
					transcript.append({
						'text': text,
						'start': start,
						'duration': max(0.0, end - start)
					})
			except Exception:
				pass
	return transcript


@frappe.whitelist()
def upload_video_transcript(video_id: str, file_content: str, file_name: str, lesson_name: str = None, course_name: str = None, chapter_number: str = None, lesson_number: str = None):
	from lms.lms.utils import can_modify_course
	import json

	if not lesson_name and course_name and chapter_number and lesson_number:
		try:
			ch_idx = int(chapter_number)
			ls_idx = int(lesson_number)
			chapter_name = frappe.db.get_value("Chapter Reference", {"parent": course_name, "idx": ch_idx}, "chapter")
			if chapter_name:
				lesson_name = frappe.db.get_value("Lesson Reference", {"parent": chapter_name, "idx": ls_idx}, "lesson")
		except (ValueError, TypeError):
			pass

	if not lesson_name and video_id:
		like_str = f"%{video_id}%"
		results = frappe.db.sql(
			"""
			select name from `tabCourse Lesson`
			where youtube like %s or body like %s or content like %s or instructor_notes like %s
			limit 1
			""",
			(like_str, like_str, like_str, like_str),
			as_dict=True
		)
		if results:
			lesson_name = results[0].name

	if not lesson_name:
		frappe.throw(_("Could not resolve lesson from request parameters."))

	course = frappe.db.get_value("Course Lesson", lesson_name, "course")
	if not course or not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this course."))

	if not video_id:
		frappe.throw(_("Video ID is required to upload a transcript."))

	file_name_lower = file_name.lower()
	if file_name_lower.endswith('.json'):
		try:
			transcript = json.loads(file_content)
			if not isinstance(transcript, list):
				frappe.throw(_("JSON transcript must be a list of segment objects."))
			for idx, item in enumerate(transcript):
				if not isinstance(item, dict) or "text" not in item or "start" not in item:
					frappe.throw(_("Segment at index {0} is missing 'text' or 'start'.").format(idx))
				if "duration" not in item:
					item["duration"] = 0
		except Exception as e:
			frappe.throw(_("Failed to parse JSON file: {0}").format(str(e)))
	elif file_name_lower.endswith('.srt'):
		transcript = parse_srt(file_content)
	elif file_name_lower.endswith('.vtt'):
		transcript = parse_vtt(file_content)
	else:
		frappe.throw(_("Unsupported file format. Please upload a .vtt, .srt, or .json file."))

	if not transcript:
		frappe.throw(_("No transcript segments found or failed to parse the file."))

	ensure_video_transcript_field()
	stored_val = frappe.db.get_value("Course Lesson", lesson_name, "video_transcript")
	transcripts_dict = {}
	if stored_val:
		try:
			data = json.loads(stored_val)
			if isinstance(data, dict):
				transcripts_dict = data
			elif isinstance(data, list):
				youtube_url = frappe.db.get_value("Course Lesson", lesson_name, "youtube")
				primary_video_id = video_id
				if youtube_url:
					import re
					if "vimeo" in youtube_url:
						vm_match = re.search(r'(?:vimeo\.com\/|player\.vimeo\.com\/video\/)(\d+)', youtube_url)
						if vm_match:
							primary_video_id = vm_match.group(1)
					else:
						yt_match = re.search(r'(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=))([\w-]{11})', youtube_url)
						if yt_match:
							primary_video_id = yt_match.group(1)
				transcripts_dict = {primary_video_id: data}
		except Exception:
			pass

	transcripts_dict[video_id] = transcript

	frappe.db.set_value("Course Lesson", lesson_name, "video_transcript", json.dumps(transcripts_dict))
	frappe.db.commit()

	cache_key = f"video_transcript_v4_youtube_{video_id}"
	frappe.cache().delete_value(cache_key)
	cache_key_vimeo = f"video_transcript_v4_vimeo_{video_id}"
	frappe.cache().delete_value(cache_key_vimeo)

	return transcript


@frappe.whitelist()
def export_course(course_name: str):
	if not can_modify_course(course_name):
		frappe.throw(_("You do not have permission to export this course."), frappe.PermissionError)

	course_doc = frappe.get_doc("LMS Course", course_name)
	course_dict = course_doc.as_dict()

	exclude_fields = [
		"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", 
		"status", "rating", "enrollments", "lessons", "notification_sent",
		"instructors", "chapters", "related_courses"
	]
	cleaned_course = {k: v for k, v in course_dict.items() if k not in exclude_fields}

	if "grading_categories" in cleaned_course:
		cleaned_cats = []
		for cat in cleaned_course["grading_categories"]:
			cleaned_cat = {k: v for k, v in cat.items() if k not in ["name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield"]}
			cleaned_cats.append(cleaned_cat)
		cleaned_course["grading_categories"] = cleaned_cats

	if "grading_scale" in cleaned_course:
		cleaned_scales = []
		for scale in cleaned_course["grading_scale"]:
			cleaned_scale = {k: v for k, v in scale.items() if k not in ["name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield"]}
			cleaned_scales.append(cleaned_scale)
		cleaned_course["grading_scale"] = cleaned_scales

	chapters = []
	chapter_refs = frappe.get_all(
		"Chapter Reference", 
		filters={"parent": course_name, "parenttype": "LMS Course"}, 
		fields=["chapter", "idx"],
		order_by="idx"
	)
	
	quiz_names = set()
	assignment_names = set()

	for ref in chapter_refs:
		if not frappe.db.exists("Course Chapter", ref.chapter):
			continue
		chapter_doc = frappe.get_doc("Course Chapter", ref.chapter)
		chapter_dict = chapter_doc.as_dict()
		cleaned_chapter = {
			"title": chapter_dict.get("title"),
			"idx": ref.get("idx"),
			"is_scorm_package": chapter_dict.get("is_scorm_package"),
			"scorm_package": chapter_dict.get("scorm_package"),
			"scorm_package_path": chapter_dict.get("scorm_package_path"),
			"manifest_file": chapter_dict.get("manifest_file"),
			"launch_file": chapter_dict.get("launch_file"),
			"lessons": []
		}
		
		lesson_refs = frappe.get_all(
			"Lesson Reference",
			filters={"parent": ref.chapter, "parenttype": "Course Chapter"},
			fields=["lesson", "idx"],
			order_by="idx"
		)
		
		for l_ref in lesson_refs:
			if not frappe.db.exists("Course Lesson", l_ref.lesson):
				continue
			lesson_doc = frappe.get_doc("Course Lesson", l_ref.lesson)
			lesson_dict = lesson_doc.as_dict()
			cleaned_lesson = {
				"title": lesson_dict.get("title"),
				"idx": l_ref.get("idx"),
				"include_in_preview": lesson_dict.get("include_in_preview"),
				"body": lesson_dict.get("body"),
				"content": lesson_dict.get("content"),
				"instructor_notes": lesson_dict.get("instructor_notes"),
				"instructor_content": lesson_dict.get("instructor_content"),
				"youtube": lesson_dict.get("youtube"),
				"quiz_id": lesson_dict.get("quiz_id"),
				"require_quiz_pass": lesson_dict.get("require_quiz_pass"),
				"question": lesson_dict.get("question"),
				"file_type": lesson_dict.get("file_type")
			}
			
			if lesson_dict.get("quiz_id"):
				for q_id in [q.strip() for q in lesson_dict.get("quiz_id").split(",") if q.strip()]:
					quiz_names.add(q_id)
					
			for content_field in ["content", "instructor_content"]:
				if lesson_dict.get(content_field):
					try:
						content = json.loads(lesson_dict.get(content_field))
						for block in content.get("blocks", []):
							if block.get("type") == "quiz":
								q_id = block.get("data", {}).get("quiz")
								if q_id:
									quiz_names.add(q_id)
							elif block.get("type") == "assignment":
								a_id = block.get("data", {}).get("assignment")
								if a_id:
									assignment_names.add(a_id)
					except Exception:
						pass
					
			cleaned_chapter["lessons"].append(cleaned_lesson)
			
		chapters.append(cleaned_chapter)

	course_assignments = frappe.get_all(
		"LMS Assignment",
		filters={"course": course_name},
		fields=["name"]
	)
	for ass in course_assignments:
		assignment_names.add(ass.name)

	quizzes = []
	questions_to_export = set()
	for q_name in quiz_names:
		if frappe.db.exists("LMS Quiz", q_name):
			q_doc = frappe.get_doc("LMS Quiz", q_name)
			q_dict = q_doc.as_dict()
			
			cleaned_q_questions = []
			for qq in q_doc.questions:
				cleaned_q_questions.append({
					"question": qq.question,
					"marks": qq.marks
				})
				questions_to_export.add(qq.question)
				
			quizzes.append({
				"name": q_doc.name,
				"title": q_dict.get("title"),
				"max_attempts": q_dict.get("max_attempts"),
				"show_answers": q_dict.get("show_answers"),
				"show_submission_history": q_dict.get("show_submission_history"),
				"passing_percentage": q_dict.get("passing_percentage"),
				"shuffle_questions": q_dict.get("shuffle_questions"),
				"limit_questions_to": q_dict.get("limit_questions_to"),
				"enable_negative_marking": q_dict.get("enable_negative_marking"),
				"marks_to_cut": q_dict.get("marks_to_cut"),
				"duration": q_dict.get("duration"),
				"questions": cleaned_q_questions
			})

	questions = []
	for qst_name in questions_to_export:
		if frappe.db.exists("LMS Question", qst_name):
			qst_doc = frappe.get_doc("LMS Question", qst_name)
			qst_dict = qst_doc.as_dict()
			exclude_q_fields = ["name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"]
			cleaned_qst = {k: v for k, v in qst_dict.items() if k not in exclude_q_fields}
			cleaned_qst["name"] = qst_doc.name
			questions.append(cleaned_qst)

	assignments = []
	for ass_name in assignment_names:
		if frappe.db.exists("LMS Assignment", ass_name):
			ass_doc = frappe.get_doc("LMS Assignment", ass_name)
			ass_dict = ass_doc.as_dict()
			exclude_ass_fields = ["name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "course"]
			cleaned_ass = {k: v for k, v in ass_dict.items() if k not in exclude_ass_fields}
			cleaned_ass["name"] = ass_doc.name
			assignments.append(cleaned_ass)

	return {
		"course": cleaned_course,
		"chapters": chapters,
		"quizzes": quizzes,
		"questions": questions,
		"assignments": assignments
	}


@frappe.whitelist()
def import_course(course_data):
	if isinstance(course_data, str):
		data = json.loads(course_data)
	else:
		data = course_data

	question_name_map = {}
	for qst in data.get("questions", []):
		old_name = qst.get("name")
		cleaned_qst = qst.copy()
		cleaned_qst.pop("name", None)
		
		new_qst_doc = frappe.get_doc({
			"doctype": "LMS Question",
			**cleaned_qst
		})
		new_qst_doc.insert(ignore_permissions=True)
		question_name_map[old_name] = new_qst_doc.name
		
	quiz_name_map = {}
	for quiz in data.get("quizzes", []):
		old_name = quiz.get("name")
		cleaned_quiz = quiz.copy()
		cleaned_quiz.pop("name", None)
		
		original_title = cleaned_quiz.get("title")
		title = original_title
		suffix = 1
		while frappe.db.exists("LMS Quiz", {"title": title}):
			suffix += 1
			title = f"{original_title} ({suffix})"
		cleaned_quiz["title"] = title
		
		new_questions = []
		for qq in cleaned_quiz.get("questions", []):
			old_q_ref = qq.get("question")
			new_q_ref = question_name_map.get(old_q_ref, old_q_ref)
			new_questions.append({
				"question": new_q_ref,
				"marks": qq.get("marks", 1)
			})
		cleaned_quiz["questions"] = new_questions
		
		new_quiz_doc = frappe.get_doc({
			"doctype": "LMS Quiz",
			**cleaned_quiz
		})
		new_quiz_doc.insert(ignore_permissions=True)
		quiz_name_map[old_name] = new_quiz_doc.name

	assignment_name_map = {}
	for ass in data.get("assignments", []):
		old_name = ass.get("name")
		cleaned_ass = ass.copy()
		cleaned_ass.pop("name", None)
		
		new_ass_doc = frappe.get_doc({
			"doctype": "LMS Assignment",
			**cleaned_ass
		})
		new_ass_doc.insert(ignore_permissions=True)
		assignment_name_map[old_name] = new_ass_doc.name

	course_info = data.get("course")
	cleaned_course = course_info.copy()

	if "grading_categories" in cleaned_course:
		cleaned_cats = []
		for cat in cleaned_course["grading_categories"]:
			cleaned_cat = {k: v for k, v in cat.items() if k not in ["name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield"]}
			cleaned_cats.append(cleaned_cat)
		cleaned_course["grading_categories"] = cleaned_cats

	if "grading_scale" in cleaned_course:
		cleaned_scales = []
		for scale in cleaned_course["grading_scale"]:
			cleaned_scale = {k: v for k, v in scale.items() if k not in ["name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield"]}
			cleaned_scales.append(cleaned_scale)
		cleaned_course["grading_scale"] = cleaned_scales
	
	original_course_title = cleaned_course.get("title")
	course_title = original_course_title
	suffix = 1
	while frappe.db.exists("LMS Course", {"title": course_title}):
		suffix += 1
		course_title = f"{original_course_title} ({suffix})"
	cleaned_course["title"] = course_title
	
	current_user = frappe.session.user
	cleaned_course["instructors"] = [{"instructor": current_user}]
	cleaned_course["owner"] = current_user
	
	course_doc = frappe.get_doc({
		"doctype": "LMS Course",
		**cleaned_course
	})
	course_doc.insert(ignore_permissions=True)
	new_course_name = course_doc.name

	for old_ass_name, new_ass_name in assignment_name_map.items():
		frappe.db.set_value("LMS Assignment", new_ass_name, "course", new_course_name)

	for ch in data.get("chapters", []):
		chapter_doc = frappe.get_doc({
			"doctype": "Course Chapter",
			"course": new_course_name,
			"title": ch.get("title"),
			"idx": ch.get("idx"),
			"is_scorm_package": ch.get("is_scorm_package"),
			"scorm_package": ch.get("scorm_package"),
			"scorm_package_path": ch.get("scorm_package_path"),
			"manifest_file": ch.get("manifest_file"),
			"launch_file": ch.get("launch_file")
		})
		chapter_doc.insert(ignore_permissions=True)
		new_chapter_name = chapter_doc.name

		# Create Chapter Reference child row in the course
		chapter_ref_doc = frappe.get_doc({
			"doctype": "Chapter Reference",
			"parent": new_course_name,
			"parenttype": "LMS Course",
			"parentfield": "chapters",
			"chapter": new_chapter_name,
			"idx": ch.get("idx")
		})
		chapter_ref_doc.insert(ignore_permissions=True)
		
		for les in ch.get("lessons", []):
			cleaned_lesson = les.copy()
			
			old_quiz_ids = [q.strip() for q in (cleaned_lesson.get("quiz_id") or "").split(",") if q.strip()]
			new_quiz_ids = [quiz_name_map.get(q, q) for q in old_quiz_ids]
			cleaned_lesson["quiz_id"] = ", ".join(new_quiz_ids)
			
			for content_field in ["content", "instructor_content"]:
				if cleaned_lesson.get(content_field):
					try:
						content = json.loads(cleaned_lesson[content_field])
						for block in content.get("blocks", []):
							if block.get("type") == "quiz":
								q_ref = block.get("data", {}).get("quiz")
								if q_ref in quiz_name_map:
									block["data"]["quiz"] = quiz_name_map[q_ref]
							elif block.get("type") == "assignment":
								a_ref = block.get("data", {}).get("assignment")
								if a_ref in assignment_name_map:
									block["data"]["assignment"] = assignment_name_map[a_ref]
						cleaned_lesson[content_field] = json.dumps(content)
					except Exception:
						pass
			
			lesson_doc = frappe.get_doc({
				"doctype": "Course Lesson",
				"chapter": new_chapter_name,
				"course": new_course_name,
				"title": cleaned_lesson.get("title"),
				"include_in_preview": cleaned_lesson.get("include_in_preview"),
				"body": cleaned_lesson.get("body"),
				"content": cleaned_lesson.get("content"),
				"instructor_notes": cleaned_lesson.get("instructor_notes"),
				"instructor_content": cleaned_lesson.get("instructor_content"),
				"youtube": cleaned_lesson.get("youtube"),
				"require_quiz_pass": cleaned_lesson.get("require_quiz_pass"),
				"quiz_id": cleaned_lesson.get("quiz_id"),
				"question": cleaned_lesson.get("question"),
				"file_type": cleaned_lesson.get("file_type")
			})
			lesson_doc.insert(ignore_permissions=True)
			new_lesson_name = lesson_doc.name
			
			chapter_doc.append("lessons", {
				"lesson": new_lesson_name,
				"idx": les.get("idx")
			})

			for new_q_ref in new_quiz_ids:
				if frappe.db.exists("LMS Quiz", new_q_ref):
					frappe.db.set_value(
						"LMS Quiz",
						new_q_ref,
						{
							"course": new_course_name,
							"lesson": new_lesson_name
						}
					)

		# Save Chapter Document to persist lessons child table and trigger index/counts
		chapter_doc.save(ignore_permissions=True)

	return new_course_name


def export_aiken(quiz_name, selected_questions=None):
	quiz = frappe.get_doc("LMS Quiz", quiz_name)
	if not quiz.questions:
		frappe.throw(_("This quiz has no questions to export."))

	lines = []
	for q_ref in quiz.questions:
		if selected_questions and (q_ref.name not in selected_questions and q_ref.question not in selected_questions):
			continue
		if not frappe.db.exists("LMS Question", q_ref.question):
			frappe.throw(_("Question {0} ({1}) was not found in the database. The quiz cannot be exported.").format(
				q_ref.question, q_ref.question_detail or _("Untitled")
			))
		q = frappe.get_doc("LMS Question", q_ref.question)
		if q.type != "Choices":
			continue

		from frappe.utils.html_utils import clean_html
		import html
		q_text = html.unescape(clean_html(q.question)).strip()
		lines.append(q_text)

		options = []
		correct_option_letter = None
		letters = ['A', 'B', 'C', 'D']
		for idx, letter in enumerate(letters):
			option_text = q.get(f"option_{idx+1}")
			is_correct = q.get(f"is_correct_{idx+1}")
			if option_text:
				lines.append(f"{letter}. {option_text.strip()}")
				if is_correct:
					correct_option_letter = letter

		if correct_option_letter:
			lines.append(f"ANSWER: {correct_option_letter}")
		lines.append("")

	content = "\n".join(lines).strip()
	if not content:
		frappe.throw(_("No compatible questions found for AIKEN export. AIKEN format only supports multiple choice (Choices) questions."))
	return content + "\n"


def import_aiken(quiz_name, file_content):
	lines = [line.strip() for line in file_content.split("\n") if line.strip()]
	questions = []
	current_question = None
	current_options = []

	for line in lines:
		if line.startswith("ANSWER:") or line.startswith("ANSWER :"):
			correct_ans = line.split(":", 1)[1].strip()
			if current_question and correct_ans:
				if len(current_options) < 2:
					frappe.throw(_("Question '{0}' must have at least two options.").format(current_question))
				questions.append({
					"question": current_question,
					"options": current_options,
					"correct": correct_ans
				})
			current_question = None
			current_options = []
		elif any(line.startswith(prefix) for prefix in [f"{c}." for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"] + [f"{c})" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"]):
			letter = line[0]
			opt_text = line[2:].strip()
			current_options.append((letter, opt_text))
		else:
			current_question = line
			current_options = []

	quiz = frappe.get_doc("LMS Quiz", quiz_name)
	for q_data in questions:
		lms_q = frappe.new_doc("LMS Question")
		lms_q.type = "Choices"
		lms_q.question = q_data["question"]

		for idx, (letter, text) in enumerate(q_data["options"][:4]):
			lms_q.set(f"option_{idx+1}", text)
			if letter.upper() == q_data["correct"].upper():
				lms_q.set(f"is_correct_{idx+1}", 1)

		lms_q.insert(ignore_permissions=True)

		quiz.append("questions", {
			"question": lms_q.name,
			"marks": 1
		})
	quiz.save(ignore_permissions=True)


def export_gift(quiz_name, selected_questions=None):
	quiz = frappe.get_doc("LMS Quiz", quiz_name)
	if not quiz.questions:
		frappe.throw(_("This quiz has no questions to export."))

	lines = []
	for q_ref in quiz.questions:
		if selected_questions and (q_ref.name not in selected_questions and q_ref.question not in selected_questions):
			continue
		if not frappe.db.exists("LMS Question", q_ref.question):
			frappe.throw(_("Question {0} ({1}) was not found in the database. The quiz cannot be exported.").format(
				q_ref.question, q_ref.question_detail or _("Untitled")
			))
		q = frappe.get_doc("LMS Question", q_ref.question)
		from frappe.utils.html_utils import clean_html
		import html
		q_text = html.unescape(clean_html(q.question)).strip()

		if q.type == "Choices":
			options_str = []
			for i in range(1, 5):
				opt_text = q.get(f"option_{i}")
				is_correct = q.get(f"is_correct_{i}")
				explanation = q.get(f"explanation_{i}")
				if opt_text:
					prefix = "=" if is_correct else "~"
					exp_str = f" #{explanation.strip()}" if explanation else ""
					options_str.append(f"    {prefix}{opt_text.strip()}{exp_str}")

			options_block = "\n".join(options_str)
			lines.append(f"::Question::{q_text} {{\n{options_block}\n}}")

		elif q.type == "User Input":
			possibilities = []
			for i in range(1, 5):
				poss = q.get(f"possibility_{i}")
				if poss:
					possibilities.append(f"={poss.strip()}")
			if possibilities:
				poss_block = " ".join(possibilities)
				lines.append(f"::Question::{q_text} {{{poss_block}}}")
			else:
				lines.append(f"::Question::{q_text} {{}}")

		elif q.type == "Open Ended":
			lines.append(f"::Question::{q_text} {{}}")

		lines.append("")

	content = "\n".join(lines).strip()
	if not content:
		frappe.throw(_("No compatible questions found for GIFT export."))
	return content + "\n"


def import_gift(quiz_name, file_content):
	content_normalized = file_content.replace("\r\n", "\n")
	blocks = [b.strip() for b in content_normalized.split("\n\n") if b.strip()]


	quiz = frappe.get_doc("LMS Quiz", quiz_name)

	for block in blocks:
		lines = [line.strip() for line in block.split("\n") if line.strip() and not line.strip().startswith("//")]
		if not lines:
			continue

		block_text = "\n".join(lines)

		question_title = None
		if block_text.startswith("::"):
			parts = block_text.split("::", 2)
			if len(parts) >= 3:
				question_title = parts[1].strip()
				block_text = parts[2].strip()

		import re
		match = re.search(r'\{(.*?)\}', block_text, re.DOTALL)
		if not match:
			q_text = block_text.strip()
			q_type = "Open Ended"
			answers = []
		else:
			q_text = block_text[:match.start()].strip() + block_text[match.end():].strip()
			q_text = q_text.strip()
			answer_content = match.group(1).strip()

			if not answer_content:
				q_type = "Open Ended"
				answers = []
			elif answer_content in ["T", "F", "TRUE", "FALSE"]:
				q_type = "Choices"
				is_true = answer_content in ["T", "TRUE"]
				answers = [
					{"text": "True", "is_correct": 1 if is_true else 0},
					{"text": "False", "is_correct": 0 if is_true else 1}
				]
			else:
				options = []
				idx = 0
				while idx < len(answer_content):
					char = answer_content[idx]
					if char in ["~", "="]:
						is_correct = 1 if char == "=" else 0
						next_idx = len(answer_content)
						for next_prefix in ["~", "="]:
							p_idx = answer_content.find(next_prefix, idx + 1)
							if p_idx != -1 and p_idx < next_idx:
								next_idx = p_idx
						opt_content = answer_content[idx+1:next_idx].strip()
						opt_text = opt_content
						explanation = ""
						if "#" in opt_content:
							opt_parts = opt_content.split("#", 1)
							opt_text = opt_parts[0].strip()
							explanation = opt_parts[1].strip()

						options.append({
							"text": opt_text,
							"is_correct": is_correct,
							"explanation": explanation
						})
						idx = next_idx
					else:
						idx += 1

				has_choice_prefix = "~" in answer_content
				if has_choice_prefix:
					q_type = "Choices"
					answers = options
				else:
					q_type = "User Input"
					answers = options

		lms_q = frappe.new_doc("LMS Question")
		lms_q.type = q_type
		lms_q.question = q_text

		if q_type == "Choices":
			for idx, ans in enumerate(answers[:4]):
				lms_q.set(f"option_{idx+1}", ans["text"])
				lms_q.set(f"is_correct_{idx+1}", ans["is_correct"])
				if ans.get("explanation"):
					lms_q.set(f"explanation_{idx+1}", ans["explanation"])
		elif q_type == "User Input":
			for idx, ans in enumerate(answers[:4]):
				lms_q.set(f"possibility_{idx+1}", ans["text"])

		lms_q.insert(ignore_permissions=True)

		quiz.append("questions", {
			"question": lms_q.name,
			"marks": 1
		})

	quiz.save(ignore_permissions=True)


@frappe.whitelist()
def export_quiz(quiz: str, format_type: str, questions: str = None) -> str:
	quiz_doc = frappe.get_doc("LMS Quiz", quiz)
	if not can_modify_course(quiz_doc.course):
		frappe.throw(_("You do not have permission to export this quiz."), frappe.PermissionError)

	selected_questions = None
	if questions:
		selected_questions = json.loads(questions)

	if format_type.upper() == "AIKEN":
		return export_aiken(quiz, selected_questions)
	elif format_type.upper() == "GIFT":
		return export_gift(quiz, selected_questions)
	else:
		frappe.throw(_("Unsupported format type. Use GIFT or AIKEN."))


@frappe.whitelist()
def import_quiz(quiz: str, file_content: str, format_type: str):
	quiz_doc = frappe.get_doc("LMS Quiz", quiz)
	if not can_modify_course(quiz_doc.course):
		frappe.throw(_("You do not have permission to import to this quiz."), frappe.PermissionError)

	if format_type.upper() == "AIKEN":
		import_aiken(quiz, file_content)
	elif format_type.upper() == "GIFT":
		import_gift(quiz, file_content)
	else:
		frappe.throw(_("Unsupported format type. Use GIFT or AIKEN."))


@frappe.whitelist()
def get_student_grades(course: str, student: str = None) -> dict:
	from datetime import timedelta
	from frappe.utils import flt

	if not student:
		student = frappe.session.user

	course_doc = frappe.get_doc("LMS Course", course)

	if not getattr(course_doc, "enable_grading_policy", False):
		return {
			"enable_grading_policy": False,
			"categories": [],
			"grading_scale": [],
			"final_percentage": 0,
			"final_grade": "N/A"
		}

	grace_period_hours = getattr(course_doc, "grading_grace_period", 0) or 0
	categories = course_doc.get("grading_categories") or []
	grading_scale = course_doc.get("grading_scale") or []

	lessons = frappe.get_all(
		"Course Lesson",
		filters={"course": course, "exclude_from_course": 0},
		fields=["content"]
	)

	quizzes_dict = {}
	assignments_dict = {}

	for lesson in lessons:
		if not lesson.content:
			continue
		try:
			content = json.loads(lesson.content)
		except Exception:
			continue
		for block in content.get("blocks", []):
			if block.get("type") == "quiz":
				data = block.get("data", {})
				quiz_name = data.get("quiz")
				if quiz_name:
					quizzes_dict[quiz_name] = {
						"name": quiz_name,
						"grading_category": data.get("grading_category"),
						"due_date": data.get("due_date"),
						"due_time": data.get("due_time")
					}
			elif block.get("type") == "assignment":
				data = block.get("data", {})
				asg_name = data.get("assignment")
				if asg_name:
					assignments_dict[asg_name] = {
						"name": asg_name,
						"grading_category": data.get("grading_category"),
						"due_date": data.get("due_date"),
						"due_time": data.get("due_time")
					}

	quizzes = []
	if quizzes_dict:
		quiz_names = list(quizzes_dict.keys())
		quiz_docs = frappe.get_all(
			"LMS Quiz",
			filters={"name": ["in", quiz_names]},
			fields=["name", "title", "passing_percentage"]
		)
		for q in quiz_docs:
			scanned = quizzes_dict[q.name]
			quizzes.append(frappe._dict({
				"name": q.name,
				"title": q.title,
				"passing_percentage": q.passing_percentage,
				"grading_category": scanned["grading_category"],
				"due_date": scanned["due_date"],
				"due_time": scanned["due_time"]
			}))

	assignments = []
	if assignments_dict:
		asg_names = list(assignments_dict.keys())
		asg_docs = frappe.get_all(
			"LMS Assignment",
			filters={"name": ["in", asg_names]},
			fields=["name", "title"]
		)
		for a in asg_docs:
			scanned = assignments_dict[a.name]
			assignments.append(frappe._dict({
				"name": a.name,
				"title": a.title,
				"grading_category": scanned["grading_category"],
				"due_date": scanned["due_date"],
				"due_time": scanned["due_time"]
			}))

	quiz_submissions = {}
	for q in quizzes:
		subs = frappe.get_all(
			"LMS Quiz Submission",
			filters={"quiz": q.name, "member": student},
			fields=["name", "percentage", "creation"]
		)
		if not subs:
			quiz_submissions[q.name] = None
			continue

		valid_subs = []
		for sub in subs:
			score = sub.percentage
			is_late = False
			if q.due_date:
				due_time_str = q.due_time or "23:59:59"
				due_datetime = frappe.utils.get_datetime(f"{q.due_date} {due_time_str}")
				deadline_with_grace = due_datetime + timedelta(hours=grace_period_hours)
				if sub.creation > deadline_with_grace:
					is_late = True
					score = 0
			valid_subs.append({"percentage": score, "creation": sub.creation, "is_late": is_late})

		best_sub = max(valid_subs, key=lambda x: x["percentage"])
		quiz_submissions[q.name] = best_sub

	assignment_submissions = {}
	for a in assignments:
		subs = frappe.get_all(
			"LMS Assignment Submission",
			filters={"assignment": a.name, "member": student},
			fields=["name", "status", "creation", "score"]
		)
		if not subs:
			assignment_submissions[a.name] = None
			continue

		valid_subs = []
		for sub in subs:
			base_score = 0
			if getattr(sub, "score", 0) > 0:
				base_score = sub.score
			elif sub.status == "Pass":
				base_score = 100

			score = base_score
			is_late = False
			if a.due_date:
				due_time_str = a.due_time or "23:59:59"
				due_datetime = frappe.utils.get_datetime(f"{a.due_date} {due_time_str}")
				deadline_with_grace = due_datetime + timedelta(hours=grace_period_hours)
				if sub.creation > deadline_with_grace:
					is_late = True
					score = 0
			valid_subs.append({"percentage": score, "creation": sub.creation, "is_late": is_late})

		best_sub = max(valid_subs, key=lambda x: x["percentage"])
		assignment_submissions[a.name] = best_sub

	items_by_cat = {}
	for cat in categories:
		items_by_cat[cat.category_name] = []

	for q in quizzes:
		cat = q.grading_category or "Uncategorized"
		if cat not in items_by_cat:
			items_by_cat[cat] = []
		sub = quiz_submissions[q.name]
		score = sub["percentage"] if sub else 0
		is_submitted = sub is not None
		is_late = sub["is_late"] if sub else False
		items_by_cat[cat].append({
			"name": q.name,
			"title": q.title,
			"type": "Quiz",
			"score": score,
			"is_submitted": is_submitted,
			"is_late": is_late,
			"due_date": q.due_date,
			"due_time": q.due_time
		})

	for a in assignments:
		cat = a.grading_category or "Uncategorized"
		if cat not in items_by_cat:
			items_by_cat[cat] = []
		sub = assignment_submissions[a.name]
		score = sub["percentage"] if sub else 0
		is_submitted = sub is not None
		is_late = sub["is_late"] if sub else False
		items_by_cat[cat].append({
			"name": a.name,
			"title": a.title,
			"type": "Assignment",
			"score": score,
			"is_submitted": is_submitted,
			"is_late": is_late,
			"due_date": a.due_date,
			"due_time": a.due_time
		})

	category_results = []
	total_weight = 0
	weighted_score_sum = 0

	for cat in categories:
		cat_name = cat.category_name
		items = items_by_cat.get(cat_name, [])
		weight = cat.weight or 0
		number_of_assessments = cat.number_of_assessments or 0

		if items:
			cat_average = sum(x["score"] for x in items) / len(items)

			category_results.append({
				"category_name": cat_name,
				"weight": weight,
				"number_of_assessments": number_of_assessments,
				"average": round(cat_average, 2),
				"items": items
			})

			total_weight += weight
			weighted_score_sum += cat_average * weight
		else:
			category_results.append({
				"category_name": cat_name,
				"weight": weight,
				"number_of_assessments": number_of_assessments,
				"average": 0,
				"items": []
			})

	uncat_items = items_by_cat.get("Uncategorized", [])
	if uncat_items:
		uncat_average = sum(x["score"] for x in uncat_items) / len(uncat_items)
		category_results.append({
			"category_name": "Uncategorized",
			"weight": 0,
			"number_of_assessments": 0,
			"average": round(uncat_average, 2),
			"items": uncat_items
		})

	final_percentage = 0
	if total_weight > 0:
		final_percentage = round(weighted_score_sum / total_weight, 2)
	elif uncat_items:
		final_percentage = round(uncat_average, 2)

	final_grade = "N/A"
	sorted_scale = sorted(grading_scale, key=lambda x: x.min_percentage, reverse=True)
	for scale in sorted_scale:
		if final_percentage >= scale.min_percentage:
			final_grade = scale.grade
			break
	if final_grade == "N/A" and sorted_scale:
		final_grade = sorted_scale[-1].grade

	return {
		"enable_grading_policy": True,
		"categories": category_results,
		"grading_scale": [
			{"grade": s.grade, "min_percentage": s.min_percentage} for s in sorted_scale
		],
		"final_percentage": final_percentage,
		"final_grade": final_grade
	}


@frappe.whitelist()
def get_category_counts(course: str, current_lesson: str = None) -> dict:
	filters = {"course": course}
	if current_lesson:
		filters["name"] = ["!=", current_lesson]
	lessons = frappe.get_all(
		"Course Lesson",
		filters=filters,
		fields=["content", "exclude_from_course"]
	)

	counts = {}
	for lesson in lessons:
		if getattr(lesson, "exclude_from_course", 0):
			continue
		if not lesson.content:
			continue
		try:
			content = json.loads(lesson.content)
		except Exception:
			continue
		for block in content.get("blocks", []):
			if block.get("type") in ["quiz", "assignment"]:
				data = block.get("data", {})
				cat = data.get("grading_category")
				if cat:
					counts[cat] = counts.get(cat, 0) + 1
	return counts

@frappe.whitelist()
def get_used_quizzes(course: str) -> list:
	lessons = frappe.get_all(
		"Course Lesson",
		filters={"course": course},
		fields=["content"]
	)
	used_quizzes = set()
	for lesson in lessons:
		if not lesson.content:
			continue
		try:
			content = json.loads(lesson.content)
		except Exception:
			continue
		for block in content.get("blocks", []):
			if block.get("type") == "quiz":
				quiz = block.get("data", {}).get("quiz")
				if quiz:
					used_quizzes.add(quiz)
	return list(used_quizzes)

@frappe.whitelist()
def get_course_batches(course: str) -> list:
	batch_courses = frappe.get_all(
		"Batch Course",
		filters={"course": course},
		fields=["parent"],
	)
	batch_names = [bc.parent for bc in batch_courses]
	if not batch_names:
		return []

	batches = frappe.get_all(
		"LMS Batch",
		filters={"name": ["in", batch_names]},
		fields=["name", "title"],
	)
	return batches

@frappe.whitelist()
def get_batch_members(batch: str, course: str = None) -> list:
	if batch == "unbatched" and course:
		batch_courses = frappe.get_all(
			"Batch Course",
			filters={"course": course},
			pluck="parent",
		)
		if not batch_courses:
			return []
		return frappe.get_all(
			"LMS Batch Enrollment",
			filters={"batch": ["in", batch_courses]},
			pluck="member",
		)

	return frappe.get_all(
		"LMS Batch Enrollment",
		filters={"batch": batch},
		pluck="member",
	)


@frappe.whitelist()
def import_question_bank(file_content: str, format_type: str, bank_label: str, is_shared: int = 0, shared_with: str = None):
	roles = frappe.get_roles(frappe.session.user)
	if not any(r in roles for r in ["System Manager", "Moderator", "Course Creator"]):
		frappe.throw(_("You do not have permission to import to the Question Bank."), frappe.PermissionError)

	try:
		frappe.reload_doc("lms", "doctype", "lms_question_bank")
	except Exception:
		pass

	user = frappe.session.user
	if not frappe.db.exists("LMS Question Bank", bank_label):
		doc = frappe.get_doc({
			"doctype": "LMS Question Bank",
			"bank_name": bank_label,
			"is_shared": is_shared,
			"shared_with": shared_with if is_shared else ""
		})
		doc.insert(ignore_permissions=True)
	else:
		doc = frappe.get_doc("LMS Question Bank", bank_label)
		if doc.owner != user and user != "Administrator":
			frappe.throw(_("Only the owner of the question bank can modify it."), frappe.PermissionError)
		doc.is_shared = is_shared
		if is_shared:
			if shared_with is not None:
				doc.shared_with = shared_with
		else:
			doc.shared_with = ""
		doc.save(ignore_permissions=True)

	if "question_bank" not in frappe.db.get_table_columns("LMS Question"):
		frappe.db.add_column("LMS Question", "question_bank", "Data")

	questions = []
	if format_type.upper() == "AIKEN":
		questions = parse_aiken_questions(file_content)
	elif format_type.upper() == "GIFT":
		questions = parse_gift_questions(file_content)
	else:
		frappe.throw(_("Unsupported format type. Use GIFT or AIKEN."))

	for q_data in questions:
		lms_q = frappe.new_doc("LMS Question")
		lms_q.type = q_data["type"]
		lms_q.question = q_data["question"]
		lms_q.question_bank = bank_label

		if q_data["type"] == "Choices":
			for idx, ans in enumerate(q_data["answers"][:4]):
				lms_q.set(f"option_{idx+1}", ans["text"])
				lms_q.set(f"is_correct_{idx+1}", ans["is_correct"])
				if ans.get("explanation"):
					lms_q.set(f"explanation_{idx+1}", ans["explanation"])
		elif q_data["type"] == "User Input":
			for idx, ans in enumerate(q_data["answers"][:4]):
				lms_q.set(f"possibility_{idx+1}", ans["text"])

		lms_q.insert(ignore_permissions=True)

	return {"status": "success", "count": len(questions)}


def parse_aiken_questions(file_content):
	lines = [line.strip() for line in file_content.split("\n") if line.strip()]
	questions = []
	current_question = None
	current_options = []

	for line in lines:
		if line.startswith("ANSWER:") or line.startswith("ANSWER :"):
			correct_ans = line.split(":", 1)[1].strip()
			if current_question and correct_ans:
				if len(current_options) < 2:
					frappe.throw(_("Question '{0}' must have at least two options.").format(current_question))
				
				answers = []
				for idx, (letter, text) in enumerate(current_options[:4]):
					is_correct = 1 if letter.upper() == correct_ans.upper() else 0
					answers.append({
						"text": text,
						"is_correct": is_correct
					})
				
				questions.append({
					"question": current_question,
					"type": "Choices",
					"answers": answers
				})
			current_question = None
			current_options = []
		elif any(line.startswith(prefix) for prefix in [f"{c}." for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"] + [f"{c})" for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"]):
			letter = line[0]
			opt_text = line[2:].strip()
			current_options.append((letter, opt_text))
		else:
			current_question = line
			current_options = []
	return questions


def parse_gift_questions(file_content):
	content_normalized = file_content.replace("\r\n", "\n")
	blocks = [b.strip() for b in content_normalized.split("\n\n") if b.strip()]
	questions = []

	for block in blocks:
		lines = [line.strip() for line in block.split("\n") if line.strip() and not line.strip().startswith("//")]
		if not lines:
			continue

		block_text = "\n".join(lines)
		if block_text.startswith("::"):
			parts = block_text.split("::", 2)
			if len(parts) >= 3:
				block_text = parts[2].strip()

		import re
		match = re.search(r'\{(.*?)\}', block_text, re.DOTALL)
		if not match:
			q_text = block_text.strip()
			q_type = "Open Ended"
			answers = []
		else:
			q_text = block_text[:match.start()].strip() + block_text[match.end():].strip()
			q_text = q_text.strip()
			answer_content = match.group(1).strip()

			if not answer_content:
				q_type = "Open Ended"
				answers = []
			elif answer_content in ["T", "F", "TRUE", "FALSE"]:
				q_type = "Choices"
				is_true = answer_content in ["T", "TRUE"]
				answers = [
					{"text": "True", "is_correct": 1 if is_true else 0},
					{"text": "False", "is_correct": 0 if is_true else 1}
				]
			else:
				options = []
				idx = 0
				while idx < len(answer_content):
					char = answer_content[idx]
					if char in ["~", "="]:
						is_correct = 1 if char == "=" else 0
						next_idx = len(answer_content)
						for next_prefix in ["~", "="]:
							p_idx = answer_content.find(next_prefix, idx + 1)
							if p_idx != -1 and p_idx < next_idx:
								next_idx = p_idx
						opt_content = answer_content[idx+1:next_idx].strip()
						opt_text = opt_content
						explanation = ""
						if "#" in opt_content:
							opt_parts = opt_content.split("#", 1)
							opt_text = opt_parts[0].strip()
							explanation = opt_parts[1].strip()

						options.append({
							"text": opt_text,
							"is_correct": is_correct,
							"explanation": explanation
						})
						idx = next_idx
					else:
						idx += 1

				has_choice_prefix = "~" in answer_content
				if has_choice_prefix:
					q_type = "Choices"
					answers = options
				else:
					q_type = "User Input"
					answers = options

		questions.append({
			"question": q_text,
			"type": q_type,
			"answers": answers
		})

	return questions


@frappe.whitelist()
def get_question_banks():
	try:
		frappe.reload_doc("lms", "doctype", "lms_question_bank")
	except Exception:
		pass

	if "question_bank" not in frappe.db.get_table_columns("LMS Question"):
		frappe.db.add_column("LMS Question", "question_bank", "Data")

	data = frappe.db.sql("""
		SELECT question_bank, COUNT(*) as question_count 
		FROM `tabLMS Question` 
		WHERE question_bank IS NOT NULL AND question_bank != '' 
		GROUP BY question_bank
	""", as_dict=True)

	for row in data:
		bank_label = row.get("question_bank")
		if not frappe.db.exists("LMS Question Bank", bank_label):
			first_q_owner = frappe.db.get_value("LMS Question", {"question_bank": bank_label}, "owner") or "Administrator"
			doc = frappe.get_doc({
				"doctype": "LMS Question Bank",
				"bank_name": bank_label,
				"owner": first_q_owner,
				"is_shared": 0
			})
			doc.insert(ignore_permissions=True)

	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	
	allowed_banks = []
	for row in data:
		bank_label = row.get("question_bank")
		try:
			bank_doc = frappe.get_doc("LMS Question Bank", bank_label)
		except Exception:
			continue
		
		shared_with = bank_doc.shared_with
		is_shared = bank_doc.is_shared or 0
		
		if is_shared:
			shared_count = len([u.strip() for u in shared_with.split(",") if u.strip()]) if shared_with else 0
		else:
			shared_count = -1
		row["shared_count"] = shared_count
		row["is_shared"] = is_shared
		
		if user == "Administrator" or "System Manager" in user_roles or "Moderator" in user_roles:
			row["owner"] = bank_doc.owner
			row["shared_with"] = shared_with or ""
			allowed_banks.append(row)
			continue
			
		if bank_doc.owner == user:
			row["owner"] = bank_doc.owner
			row["shared_with"] = shared_with or ""
			allowed_banks.append(row)
			continue
			
		if is_shared:
			if not shared_with:
				row["owner"] = bank_doc.owner
				row["shared_with"] = ""
				allowed_banks.append(row)
			else:
				shared_users = [u.strip().lower() for u in shared_with.replace(",", " ").split() if u.strip()]
				if user.lower() in shared_users:
					row["owner"] = bank_doc.owner
					row["shared_with"] = shared_with
					allowed_banks.append(row)
				
	return allowed_banks


@frappe.whitelist()
def get_bank_questions(bank_label: str):
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	
	try:
		frappe.reload_doc("lms", "doctype", "lms_question_bank")
	except Exception:
		pass
		
	if frappe.db.exists("LMS Question Bank", bank_label):
		bank_doc = frappe.get_doc("LMS Question Bank", bank_label)
		is_allowed = False
		
		if user == "Administrator" or "System Manager" in user_roles or "Moderator" in user_roles:
			is_allowed = True
		elif bank_doc.owner == user:
			is_allowed = True
		elif bank_doc.is_shared:
			if not bank_doc.shared_with:
				is_allowed = True
			else:
				shared_users = [u.strip().lower() for u in bank_doc.shared_with.replace(",", " ").split() if u.strip()]
				if user.lower() in shared_users:
					is_allowed = True
				
		if not is_allowed:
			frappe.throw(_("You do not have permission to access this question bank."), frappe.PermissionError)

	return frappe.get_all(
		"LMS Question",
		filters={"question_bank": bank_label},
		fields=["name", "question", "type"]
	)


@frappe.whitelist()
def update_question_bank_sharing(bank_label: str, is_shared: int, shared_with: str = None):
	try:
		frappe.reload_doc("lms", "doctype", "lms_question_bank")
	except Exception:
		pass
		
	if not frappe.db.exists("LMS Question Bank", bank_label):
		frappe.throw(_("Question Bank does not exist."), frappe.DoesNotExistError)
		
	doc = frappe.get_doc("LMS Question Bank", bank_label)
	user = frappe.session.user
	if doc.owner != user and user != "Administrator":
		frappe.throw(_("Only the owner of the question bank can modify sharing settings."), frappe.PermissionError)
		
	doc.is_shared = is_shared
	doc.shared_with = shared_with if is_shared else ""
	doc.save(ignore_permissions=True)
	return {"status": "success"}


@frappe.whitelist()
def add_questions_to_quiz(quiz_name: str, question_names, marks: int = 1):
	roles = frappe.get_roles(frappe.session.user)
	if not any(r in roles for r in ["System Manager", "Moderator", "Course Creator"]):
		frappe.throw(_("You do not have permission to modify this quiz."), frappe.PermissionError)

	import json
	if isinstance(question_names, str):
		question_names = json.loads(question_names)

	quiz = frappe.get_doc("LMS Quiz", quiz_name)
	existing_questions = {q.question for q in quiz.questions}

	added_count = 0
	for q_name in question_names:
		if q_name not in existing_questions:
			quiz.append("questions", {
				"doctype": "LMS Quiz Question",
				"question": q_name,
				"marks": frappe.utils.cint(marks) or 1
			})
			added_count += 1

	if added_count > 0:
		quiz.save(ignore_permissions=True)

	return {"status": "success", "added_count": added_count}


@frappe.whitelist()
def delete_question_bank(bank_label: str):
	roles = frappe.get_roles(frappe.session.user)
	if not any(r in roles for r in ["System Manager", "Moderator", "Course Creator"]):
		frappe.throw(_("You do not have permission to delete question banks."), frappe.PermissionError)

	try:
		frappe.reload_doc("lms", "doctype", "lms_question_bank")
	except Exception:
		pass

	user = frappe.session.user
	if frappe.db.exists("LMS Question Bank", bank_label):
		doc = frappe.get_doc("LMS Question Bank", bank_label)
		if doc.owner != user and user != "Administrator":
			frappe.throw(_("Only the owner of the question bank can delete it."), frappe.PermissionError)
		frappe.delete_doc("LMS Question Bank", bank_label, ignore_permissions=True)

	questions = frappe.get_all("LMS Question", filters={"question_bank": bank_label}, pluck="name")
	for q in questions:
		frappe.delete_doc("LMS Question", q, ignore_permissions=True)

	return {"status": "success"}


@frappe.whitelist()
def delete_bank_question(question_name: str):
	roles = frappe.get_roles(frappe.session.user)
	if not any(r in roles for r in ["System Manager", "Moderator", "Course Creator"]):
		frappe.throw(_("You do not have permission to delete questions."), frappe.PermissionError)

	question_bank = frappe.db.get_value("LMS Question", question_name, "question_bank")
	user = frappe.session.user
	if question_bank:
		try:
			frappe.reload_doc("lms", "doctype", "lms_question_bank")
		except Exception:
			pass
		if frappe.db.exists("LMS Question Bank", question_bank):
			doc = frappe.get_doc("LMS Question Bank", question_bank)
			if doc.owner != user and user != "Administrator":
				frappe.throw(_("Only the owner of the question bank can delete questions from it."), frappe.PermissionError)

	frappe.delete_doc("LMS Question", question_name, ignore_permissions=True)
	return {"status": "success"}


@frappe.whitelist()
def get_all_students_across_batches(search_term=None, batch_filter=None, order_by=None, start=0, page_length=20):
	frappe.only_for("Moderator")

	start = cint(start)
	page_length = cint(page_length) or 20

	conditions = []
	values = {}

	without_batch_mode = (batch_filter == "__without_batch__")

	if without_batch_mode:
		# Special mode: LMS Students with no batch enrollment at all
		conditions_wb = []
		values_wb = {}

		if search_term:
			conditions_wb.append("(u.full_name LIKE %(search)s OR u.username LIKE %(search)s OR u.name LIKE %(search)s)")
			values_wb["search"] = f"%{search_term}%"

		query_base_wb = """
			FROM `tabUser` u
			INNER JOIN `tabHas Role` hr ON hr.parent = u.name AND hr.role = 'LMS Student' AND hr.parenttype = 'User'
			WHERE u.name NOT IN ('Administrator', 'Guest')
				AND NOT EXISTS (
					SELECT 1 FROM `tabLMS Batch Enrollment` env2
					WHERE env2.member = u.name
				)
		"""
		if conditions_wb:
			query_base_wb += " AND " + " AND ".join(conditions_wb)

		total_count = frappe.db.sql(f"SELECT COUNT(*) {query_base_wb}", values_wb)[0][0]

		sql_order_by_wb = "u.creation DESC"
		if order_by:
			parts = order_by.lower().split()
			sort_field = parts[0]
			direction = "DESC" if len(parts) > 1 and parts[1] == "desc" else "ASC"
			if sort_field == "member_name":
				sql_order_by_wb = f"u.full_name {direction}"
			elif sort_field == "creation":
				sql_order_by_wb = f"u.creation {direction}"
			elif sort_field == "last_active":
				sql_order_by_wb = f"u.last_active {direction}"

		select_wb = f"""
			SELECT
				u.name as member,
				u.full_name as member_name,
				u.username as username,
				u.user_image as user_image,
				u.last_active as last_active,
				u.creation as creation,
				u.enabled as enabled,
				NULL as batch,
				NULL as batch_title,
				NULL as enrollment_name
			{query_base_wb}
			ORDER BY {sql_order_by_wb}
			LIMIT {start}, {page_length}
		"""
		records_wb = frappe.db.sql(select_wb, values_wb, as_dict=True)

		from frappe.utils import format_datetime, get_datetime
		students_data = []
		for r in records_wb:
			raw_la = r.last_active
			students_data.append(frappe._dict({
				"name": r.enrollment_name or r.member,
				"email": r.member,
				"member_name": r.member_name or r.member,
				"member_username": r.username,
				"batch": None,
				"batch_title": _("No Batch"),
				"creation": r.creation,
				"last_active": format_datetime(raw_la, "dd MMM YY") if raw_la else "Never",
				"raw_last_active": raw_la or get_datetime("1970-01-01 00:00:00"),
				"user_image": r.user_image,
				"enabled": r.enabled if r.enabled is not None else 1,
				"progress": 0,
			}))

		all_batches = frappe.get_all(
			"LMS Batch",
			fields=["name", "title"],
			order_by="title asc",
		)
		batch_options = (
			[{"label": _("All Batches"), "value": ""}]
			+ [{"label": _("Without Batch"), "value": "__without_batch__"}]
			+ [{"label": b.title, "value": b.name} for b in all_batches]
		)
		return {
			"data": students_data,
			"total_count": total_count,
			"has_next_page": (start + page_length) < total_count,
			"batch_options": batch_options
		}

	if batch_filter and batch_filter != "__without_batch__":
		conditions.append("env.batch = %(batch)s")
		values["batch"] = batch_filter

	if search_term:
		conditions.append("(env.member_name LIKE %(search)s OR u.username LIKE %(search)s OR env.member LIKE %(search)s)")
		values["search"] = f"%{search_term}%"

	query_base = """
		FROM `tabLMS Batch Enrollment` env
		LEFT JOIN `tabUser` u ON env.member = u.name
		LEFT JOIN `tabLMS Batch` b ON env.batch = b.name
	"""
	if conditions:
		query_base += " WHERE " + " AND ".join(conditions)

	total_count_query = "SELECT COUNT(*) " + query_base
	total_count = frappe.db.sql(total_count_query, values)[0][0]

	sql_order_by = "env.creation DESC"
	is_progress_sort = False
	if order_by:
		parts = order_by.lower().split()
		sort_field = parts[0]
		direction = "DESC" if len(parts) > 1 and parts[1] == "desc" else "ASC"

		if sort_field == "member_name":
			sql_order_by = f"env.member_name {direction}"
		elif sort_field == "batch":
			sql_order_by = f"b.title {direction}"
		elif sort_field == "creation":
			sql_order_by = f"env.creation {direction}"
		elif sort_field == "last_active":
			sql_order_by = f"u.last_active {direction}"
		elif sort_field == "progress":
			is_progress_sort = True

	from frappe.utils import format_datetime, get_datetime

	if is_progress_sort:
		select_query = """
			SELECT 
				env.name as enrollment_name,
				env.member as member,
				env.member_name as member_name,
				env.batch as batch,
				env.creation as creation,
				u.last_active as last_active,
				u.user_image as user_image,
				u.username as username,
				u.full_name as full_name,
				u.enabled as enabled,
				b.title as batch_title
		""" + query_base
		records = frappe.db.sql(select_query, values, as_dict=True)
	else:
		select_query = """
			SELECT 
				env.name as enrollment_name,
				env.member as member,
				env.member_name as member_name,
				env.batch as batch,
				env.creation as creation,
				u.last_active as last_active,
				u.user_image as user_image,
				u.username as username,
				u.full_name as full_name,
				u.enabled as enabled,
				b.title as batch_title
		""" + query_base + f" ORDER BY {sql_order_by} LIMIT {start}, {page_length}"
		records = frappe.db.sql(select_query, values, as_dict=True)

	# Batch-fetch courses and assessments for the batches of these students
	batch_ids = list(set(r.batch for r in records))
	
	batch_courses = {}
	batch_assignments = {}
	batch_quizzes = {}
	batch_exercises = {}
	
	for b_id in batch_ids:
		courses = frappe.get_all("Batch Course", {"parent": b_id}, ["course"])
		batch_courses[b_id] = [c.course for c in courses]
		
		assessments = frappe.get_all(
			"LMS Assessment",
			filters={"parent": b_id},
			fields=["assessment_name", "assessment_type"],
		)
		batch_assignments[b_id] = [a.assessment_name for a in assessments if a.assessment_type == "LMS Assignment"]
		batch_quizzes[b_id] = [a.assessment_name for a in assessments if a.assessment_type == "LMS Quiz"]
		batch_exercises[b_id] = [a.assessment_name for a in assessments if a.assessment_type == "LMS Programming Exercise"]

	members = [r.member for r in records]
	
	# Fetch LMS Enrollments progress
	all_courses = []
	for courses in batch_courses.values():
		all_courses.extend(courses)
	all_courses = list(set(all_courses))
	
	enrollments_map = {}
	if members and all_courses:
		enrollments = frappe.get_all(
			"LMS Enrollment",
			filters={"course": ["in", all_courses], "member": ["in", members]},
			fields=["course", "member", "progress"]
		)
		for e in enrollments:
			enrollments_map[(e.member, e.course)] = e.progress or 0
			
	# Fetch Assignment Submissions
	all_assignments = []
	for assigns in batch_assignments.values():
		all_assignments.extend(assigns)
	all_assignments = list(set(all_assignments))
	
	assignment_submissions_map = {}
	if members and all_assignments:
		submissions = frappe.get_all(
			"LMS Assignment Submission",
			filters={"assignment": ["in", all_assignments], "member": ["in", members]},
			fields=["assignment", "member", "status"]
		)
		for s in submissions:
			if s.status == "Pass":
				assignment_submissions_map[(s.member, s.assignment)] = True
				
	# Fetch Programming Exercise Submissions
	all_exercises = []
	for exes in batch_exercises.values():
		all_exercises.extend(exes)
	all_exercises = list(set(all_exercises))
	
	exercise_submissions_map = {}
	if members and all_exercises:
		submissions = frappe.get_all(
			"LMS Programming Exercise Submission",
			filters={"exercise": ["in", all_exercises], "member": ["in", members]},
			fields=["exercise", "member", "status"]
		)
		for s in submissions:
			if s.status == "Pass":
				exercise_submissions_map[(s.member, s.exercise)] = True
				
	# Fetch Quiz Submissions
	all_quizzes = []
	for qz in batch_quizzes.values():
		all_quizzes.extend(qz)
	all_quizzes = list(set(all_quizzes))
	
	quiz_submissions_map = {}
	quiz_passing_percentages = {}
	if all_quizzes:
		quizzes_info = frappe.get_all(
			"LMS Quiz",
			filters={"name": ["in", all_quizzes]},
			fields=["name", "passing_percentage"]
		)
		for q in quizzes_info:
			quiz_passing_percentages[q.name] = q.passing_percentage or 0
			
	if members and all_quizzes:
		submissions = frappe.get_all(
			"LMS Quiz Submission",
			filters={"quiz": ["in", all_quizzes], "member": ["in", members]},
			fields=["quiz", "member", "percentage"]
		)
		for s in submissions:
			passing = quiz_passing_percentages.get(s.quiz, 0)
			if (s.percentage or 0) >= passing:
				quiz_submissions_map[(s.member, s.quiz)] = True

	students_data = []
	for r in records:
		raw_last_active = r.last_active
		formatted_last_active = format_datetime(raw_last_active, "dd MMM YY") if raw_last_active else "Never"

		details = frappe._dict({
			"name": r.enrollment_name,
			"email": r.member,
			"member_name": r.member_name or r.full_name or r.member,
			"member_username": r.username,
			"batch": r.batch,
			"batch_title": r.batch_title or r.batch,
			"creation": r.creation,
			"last_active": formatted_last_active,
			"raw_last_active": raw_last_active or get_datetime("1970-01-01 00:00:00"),
			"user_image": r.user_image,
			"enabled": r.enabled if r.enabled is not None else 1,
			"progress": 0,
		})

		# Calculate progress using the pre-fetched maps
		courses = batch_courses.get(r.batch, [])
		assigns = batch_assignments.get(r.batch, [])
		qz = batch_quizzes.get(r.batch, [])
		exes = batch_exercises.get(r.batch, [])
		
		total_course_progress = sum(enrollments_map.get((r.member, c), 0) for c in courses)
		average_course_progress = total_course_progress / len(courses) if courses else 0
		
		assessments_completed = 0
		total_assessments = len(assigns) + len(qz) + len(exes)
		
		for a in assigns:
			if assignment_submissions_map.get((r.member, a)):
				assessments_completed += 1
		for q in qz:
			if quiz_submissions_map.get((r.member, q)):
				assessments_completed += 1
		for e in exes:
			if exercise_submissions_map.get((r.member, e)):
				assessments_completed += 1
				
		average_assessments_progress = (assessments_completed / total_assessments * 100) if total_assessments else 0
		
		total_items = len(courses) + total_assessments
		if total_items:
			progress = ((average_course_progress * len(courses)) + (average_assessments_progress * total_assessments)) / total_items
		else:
			progress = 0
			
		details.progress = flt(progress, 2)
		students_data.append(details)

	if is_progress_sort:
		reverse_dir = (direction == "DESC")
		students_data.sort(key=lambda x: x.progress, reverse=reverse_dir)
		paginated_data = students_data[start:start + page_length]
	else:
		paginated_data = students_data

	all_batches = frappe.get_all(
		"LMS Batch",
		fields=["name", "title"],
		order_by="title asc",
	)
	batch_options = (
		[{"label": _("All Batches"), "value": ""}]
		+ [{"label": _("Without Batch"), "value": "__without_batch__"}]
		+ [{"label": b.title, "value": b.name} for b in all_batches]
	)

	return {
		"data": paginated_data,
		"total_count": total_count,
		"has_next_page": (start + page_length) < total_count,
		"batch_options": batch_options
	}


def enroll_student_in_batch(student_email, batch_name):
	if not frappe.db.exists("LMS Batch Enrollment", {"batch": batch_name, "member": student_email}):
		enrollment = frappe.new_doc("LMS Batch Enrollment")
		enrollment.update({
			"batch": batch_name,
			"member": student_email,
		})
		enrollment.flags.ignore_permissions = True
		enrollment.insert()
		
		# Send in-app notification
		try:
			batch_title = frappe.db.get_value("LMS Batch", batch_name, "title") or batch_name
			from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
			notification = frappe._dict(
				{
					"subject": frappe._("You have been enrolled in the batch {0}").format(batch_title),
					"email_content": "",
					"document_type": "LMS Batch",
					"document_name": batch_name,
					"from_user": frappe.session.user or "Administrator",
					"type": "Alert",
					"link": f"/batches/{batch_name}",
				}
			)
			make_notification_logs(notification, [student_email])
		except Exception as e:
			frappe.log_error(f"Failed to create notification log for batch enrollment: {str(e)}")
			
		return True
	return False


@frappe.whitelist()
def import_students_csv(file_content, batch=None):
	frappe.only_for("Moderator")
	
	if not file_content:
		frappe.throw(_("Please upload a CSV file."))

	import io
	import csv

	if isinstance(file_content, bytes):
		file_content = file_content.decode("utf-8")
		
	f = io.StringIO(file_content.strip())
	reader = csv.reader(f)
	
	headers = next(reader, None)
	if not headers:
		frappe.throw(_("CSV file is empty."))
		
	headers = [h.strip().lower() for h in headers]
	
	email_idx = -1
	name_idx = -1
	for idx, h in enumerate(headers):
		if "email" in h:
			email_idx = idx
		elif "name" in h or "full" in h:
			name_idx = idx
			
	if email_idx == -1:
		email_idx = 0
		
	created_users = 0
	skipped_users = 0
	enrolled_users = 0
	imported_users = []
	errors = []
	
	for row_idx, row in enumerate(reader, start=2):
		if not row:
			continue
		if len(row) <= email_idx:
			continue
			
		email = row[email_idx].strip()
		if not email:
			continue
			
		full_name = ""
		if name_idx != -1 and len(row) > name_idx:
			full_name = row[name_idx].strip()
			
		if not full_name:
			full_name = email.split("@")[0].capitalize()
			
		from frappe.utils import validate_email_address
		if not validate_email_address(email):
			errors.append(f"Row {row_idx}: Invalid email address '{email}'")
			continue
			
		try:
			user_exists = frappe.db.exists("User", email)
			if not user_exists:
				user = frappe.new_doc("User")
				user.update({
					"email": email,
					"first_name": full_name,
					"enabled": 1,
					"user_type": "Website User",
					"new_password": frappe.utils.random_string(10),
					"send_welcome_email": 1,
				})
				user.flags.ignore_permissions = True
				user.flags.ignore_password_policy = True
				user.insert()
				created_users += 1
				
				try:
					user.send_welcome_mail()
				except Exception as mail_err:
					frappe.log_error(f"Failed to send welcome email to {email}: {str(mail_err)}")
			else:
				skipped_users += 1
				
			imported_users.append({
				"email": email,
				"full_name": full_name,
				"is_new": not user_exists
			})

			if batch:
				if enroll_student_in_batch(email, batch):
					enrolled_users += 1
		except Exception as e:
			errors.append(f"Row {row_idx} ({email}): {str(e)}")
			
	return {
		"created": created_users,
		"skipped": skipped_users,
		"enrolled": enrolled_users,
		"imported_users": imported_users,
		"errors": errors
	}


@frappe.whitelist()
def assign_students_to_batch(students, batch):
	frappe.only_for("Moderator")
	
	if not batch:
		frappe.throw(_("Please select a batch."))
	if not students:
		frappe.throw(_("No students selected for assignment."))
		
	import json
	if isinstance(students, str):
		students = json.loads(students)
		
	assigned_count = 0
	errors = []
	
	for student_email in students:
		try:
			if not frappe.db.exists("User", student_email):
				errors.append(f"User '{student_email}' does not exist.")
				continue
				
			enroll_student_in_batch(student_email, batch)
			assigned_count += 1
		except Exception as e:
			errors.append(f"Failed to enroll '{student_email}': {str(e)}")
			
	return {
		"assigned_count": assigned_count,
		"errors": errors
	}


@frappe.whitelist()
def add_student_manually(email, full_name, batch=None):
	frappe.only_for("Moderator")
	
	if not email:
		frappe.throw(_("Email is required."))
	if not full_name:
		frappe.throw(_("Full Name is required."))
		
	from frappe.utils import validate_email_address
	if not validate_email_address(email):
		frappe.throw(_("Invalid email address."))
		
	user_exists = frappe.db.exists("User", email)
	is_new = not user_exists
	
	try:
		if is_new:
			user = frappe.new_doc("User")
			user.update({
				"email": email,
				"first_name": full_name,
				"enabled": 1,
				"user_type": "Website User",
				"new_password": frappe.utils.random_string(10),
				"send_welcome_email": 1,
			})
			user.flags.ignore_permissions = True
			user.flags.ignore_password_policy = True
			user.insert()
			
			try:
				user.send_welcome_mail()
			except Exception as mail_err:
				frappe.log_error(f"Failed to send welcome email to {email}: {str(mail_err)}")
				
		enrolled = False
		if batch:
			enrolled = enroll_student_in_batch(email, batch)
			
		return {
			"status": "success",
			"is_new": is_new,
			"enrolled": enrolled,
			"message": _("Student added successfully.")
		}
	except Exception as e:
		frappe.throw(str(e))



@frappe.whitelist()
def bulk_disable_student_accounts(emails):
	frappe.only_for("Moderator")

	import json
	if isinstance(emails, str):
		emails = json.loads(emails)

	if not emails:
		frappe.throw(_("No accounts selected."))

	disabled_count = 0
	errors = []
	for email in emails:
		try:
			if not frappe.db.exists("User", email):
				errors.append(f"User '{email}' does not exist.")
				continue
			frappe.db.set_value("User", email, "enabled", 0)
			disabled_count += 1
		except Exception as e:
			errors.append(f"Failed to disable '{email}': {str(e)}")

	frappe.db.commit()
	return {"disabled_count": disabled_count, "errors": errors}


@frappe.whitelist()
def bulk_toggle_student_accounts(emails, enabled):
	frappe.only_for("Moderator")

	import json
	if isinstance(emails, str):
		emails = json.loads(emails)

	if not emails:
		frappe.throw(_("No accounts selected."))

	enabled_val = 1 if frappe.utils.cint(enabled) else 0
	updated_count = 0
	errors = []
	for email in emails:
		try:
			if not frappe.db.exists("User", email):
				errors.append(f"User '{email}' does not exist.")
				continue
			frappe.db.set_value("User", email, "enabled", enabled_val)
			updated_count += 1
		except Exception as e:
			errors.append(f"Failed to update '{email}': {str(e)}")

	frappe.db.commit()
	return {"updated_count": updated_count, "errors": errors}


@frappe.whitelist()
def bulk_unenroll_students_from_batch(enrollment_names):
	frappe.only_for("Moderator")

	import json
	if isinstance(enrollment_names, str):
		enrollment_names = json.loads(enrollment_names)

	if not enrollment_names:
		frappe.throw(_("No enrollments selected."))

	unenrolled_count = 0
	errors = []
	for name in enrollment_names:
		try:
			if not frappe.db.exists("LMS Batch Enrollment", name):
				errors.append(f"Enrollment '{name}' does not exist.")
				continue
			frappe.delete_doc("LMS Batch Enrollment", name, ignore_permissions=True)
			unenrolled_count += 1
		except Exception as e:
			errors.append(f"Failed to unenroll '{name}': {str(e)}")

	frappe.db.commit()
	return {"unenrolled_count": unenrolled_count, "errors": errors}


@frappe.whitelist()
def toggle_student_account(email, enabled):
	frappe.only_for("Moderator")

	if not frappe.db.exists("User", email):
		frappe.throw(_("User '{0}' does not exist.").format(email))

	enabled_val = 1 if frappe.utils.cint(enabled) else 0
	frappe.db.set_value("User", email, "enabled", enabled_val)
	frappe.db.commit()
	return {"email": email, "enabled": enabled_val}


def check_library_permission():
	if frappe.session.user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	roles = frappe.get_roles(frappe.session.user)
	if not ("Course Creator" in roles or "Moderator" in roles or "System Manager" in roles):
		frappe.throw(_("You do not have permission to access Content Libraries."), frappe.PermissionError)


def clone_quiz(quiz_id):
	if not frappe.db.exists("LMS Quiz", quiz_id):
		return quiz_id
	quiz_doc = frappe.get_doc("LMS Quiz", quiz_id)
	cloned_quiz = frappe.copy_doc(quiz_doc)
	cloned_quiz.name = None
	cloned_quiz.title = f"{quiz_doc.title} (Copy)"
	cloned_quiz.insert(ignore_permissions=True)
	return cloned_quiz.name


def clone_assignment(assignment_id):
	if not frappe.db.exists("LMS Assignment", assignment_id):
		return assignment_id
	assignment_doc = frappe.get_doc("LMS Assignment", assignment_id)
	cloned_assignment = frappe.copy_doc(assignment_doc)
	cloned_assignment.name = None
	cloned_assignment.title = f"{assignment_doc.title} (Copy)"
	cloned_assignment.insert(ignore_permissions=True)
	return cloned_assignment.name


def clone_programming_exercise(exercise_id):
	if not frappe.db.exists("LMS Programming Exercise", exercise_id):
		return exercise_id
	exercise_doc = frappe.get_doc("LMS Programming Exercise", exercise_id)
	cloned_exercise = frappe.copy_doc(exercise_doc)
	cloned_exercise.name = None
	cloned_exercise.title = f"{exercise_doc.title} (Copy)"
	cloned_exercise.insert(ignore_permissions=True)
	return cloned_exercise.name


def clone_lesson(lesson_id, target_chapter, target_course):
	if not frappe.db.exists("Course Lesson", lesson_id):
		return lesson_id
	lesson_doc = frappe.get_doc("Course Lesson", lesson_id)
	cloned_lesson = frappe.copy_doc(lesson_doc)
	cloned_lesson.name = None
	cloned_lesson.chapter = target_chapter
	cloned_lesson.course = target_course
	cloned_lesson.title = f"{lesson_doc.title} (Copy)"
	
	# Clone nested quizzes/assignments/programming exercises in content blocks
	if cloned_lesson.content:
		try:
			content = json.loads(cloned_lesson.content)
			blocks_updated = False
			for block in content.get("blocks", []):
				if block.get("type") == "quiz":
					q_id = block.get("data", {}).get("quiz")
					if q_id:
						block["data"]["quiz"] = clone_quiz(q_id)
						blocks_updated = True
				elif block.get("type") == "assignment":
					a_id = block.get("data", {}).get("assignment")
					if a_id:
						block["data"]["assignment"] = clone_assignment(a_id)
						blocks_updated = True
				elif block.get("type") == "program":
					p_id = block.get("data", {}).get("exercise")
					if p_id:
						block["data"]["exercise"] = clone_programming_exercise(p_id)
						blocks_updated = True
			if blocks_updated:
				cloned_lesson.content = json.dumps(content)
		except Exception:
			pass

	# Clone nested quizzes/assignments/programming exercises in instructor_content blocks
	if cloned_lesson.instructor_content:
		try:
			content = json.loads(cloned_lesson.instructor_content)
			blocks_updated = False
			for block in content.get("blocks", []):
				if block.get("type") == "quiz":
					q_id = block.get("data", {}).get("quiz")
					if q_id:
						block["data"]["quiz"] = clone_quiz(q_id)
						blocks_updated = True
				elif block.get("type") == "assignment":
					a_id = block.get("data", {}).get("assignment")
					if a_id:
						block["data"]["assignment"] = clone_assignment(a_id)
						blocks_updated = True
				elif block.get("type") == "program":
					p_id = block.get("data", {}).get("exercise")
					if p_id:
						block["data"]["exercise"] = clone_programming_exercise(p_id)
						blocks_updated = True
			if blocks_updated:
				cloned_lesson.instructor_content = json.dumps(content)
		except Exception:
			pass

	# Clone quizzes inside quiz_id
	if cloned_lesson.quiz_id:
		q_ids = [q.strip() for q in cloned_lesson.quiz_id.split(",") if q.strip()]
		cloned_q_ids = [clone_quiz(qid) for qid in q_ids]
		cloned_lesson.quiz_id = ", ".join(cloned_q_ids)

	cloned_lesson.insert(ignore_permissions=True)
	return cloned_lesson.name


def create_wrapper_lesson(title, content_doctype, content_name, target_chapter, target_course):
	lesson_doc = frappe.new_doc("Course Lesson")
	lesson_doc.title = title
	lesson_doc.chapter = target_chapter
	lesson_doc.course = target_course
	
	if content_doctype == "LMS Quiz":
		lesson_doc.icon = "icon-quiz"
		lesson_doc.content = json.dumps({
			"blocks": [
				{
					"id": frappe.generate_hash(length=10),
					"type": "quiz",
					"data": {
						"quiz": content_name,
						"include_in_grading": 1
					}
				}
			]
		})
	elif content_doctype == "LMS Assignment":
		lesson_doc.icon = "icon-assignment"
		lesson_doc.content = json.dumps({
			"blocks": [
				{
					"id": frappe.generate_hash(length=10),
					"type": "assignment",
					"data": {
						"assignment": content_name,
						"include_in_grading": 1
					}
				}
			]
		})
	elif content_doctype == "LMS Programming Exercise":
		lesson_doc.icon = "icon-code"
		lesson_doc.content = json.dumps({
			"blocks": [
				{
					"id": frappe.generate_hash(length=10),
					"type": "program",
					"data": {
						"exercise": content_name,
						"include_in_grading": 1
					}
				}
			]
		})
	else:
		lesson_doc.icon = "icon-list"
		lesson_doc.content = json.dumps({
			"blocks": [
				{
					"id": frappe.generate_hash(length=10),
					"type": "paragraph",
					"data": {
						"text": f"Reference to {content_doctype} {content_name}"
					}
				}
			]
		})
		
	lesson_doc.insert(ignore_permissions=True)
	return lesson_doc.name


@frappe.whitelist()
def create_content_library(title, description=None, department=None, shared=0, shared_instructors=None):
	check_library_permission()
	if frappe.db.exists("Content Library", title):
		frappe.throw(_("A Content Library with the title '{0}' already exists.").format(title))
		
	lib = frappe.new_doc("Content Library")
	lib.library_name = title
	lib.description = description
	lib.department = department
	lib.shared = frappe.utils.cint(shared)
	lib.owner = frappe.session.user
	lib.status = "Draft"
	lib.version = 1
	
	if shared_instructors:
		if isinstance(shared_instructors, str):
			shared_instructors = json.loads(shared_instructors)
		for inst in shared_instructors:
			lib.append("shared_instructors", {
				"instructor": inst if isinstance(inst, str) else inst.get("instructor")
			})
			
	lib.insert(ignore_permissions=True)
	
	# Create initial version snapshot
	version_doc = frappe.new_doc("Content Library Version")
	version_doc.library = lib.name
	version_doc.version_number = 1
	version_doc.change_log = _("Initial creation")
	version_doc.timestamp = frappe.utils.now_datetime()
	version_doc.items_snapshot = json.dumps([])
	version_doc.insert(ignore_permissions=True)
	
	return lib.as_dict()


@frappe.whitelist()
def update_content_library(library_name, title=None, description=None, department=None, shared=0, shared_instructors=None, items=None, create_new_version=0, change_log=None):
	check_library_permission()
	if not frappe.db.exists("Content Library", library_name):
		frappe.throw(_("Content Library '{0}' does not exist.").format(library_name))
		
	lib = frappe.get_doc("Content Library", library_name)
	if not has_library_permission(lib, "write"):
		frappe.throw(_("You do not have permission to update this Content Library."), frappe.PermissionError)
	if title and title != lib.library_name:
		if frappe.db.exists("Content Library", title):
			frappe.throw(_("A Content Library with the title '{0}' already exists.").format(title))
		lib.library_name = title
		
	lib.description = description
	lib.department = department
	lib.shared = frappe.utils.cint(shared)
	
	if shared_instructors is not None:
		if isinstance(shared_instructors, str):
			shared_instructors = json.loads(shared_instructors)
		lib.shared_instructors = []
		for inst in shared_instructors:
			lib.append("shared_instructors", {
				"instructor": inst if isinstance(inst, str) else inst.get("instructor")
			})
	
	if items:
		if isinstance(items, str):
			items = json.loads(items)
		lib.items = []
		for item in items:
			lib.append("items", {
				"content_doctype": item.get("content_doctype"),
				"content_name": item.get("content_name"),
				"title": item.get("title")
			})
			
	if frappe.utils.cint(create_new_version):
		lib.version = (lib.version or 1) + 1
		
	lib.save(ignore_permissions=True)
	
	if frappe.utils.cint(create_new_version):
		version_doc = frappe.new_doc("Content Library Version")
		version_doc.library = lib.name
		version_doc.version_number = lib.version
		version_doc.change_log = change_log or _("Update version")
		version_doc.timestamp = frappe.utils.now_datetime()
		
		items_list = []
		for row in lib.items:
			items_list.append({
				"content_doctype": row.content_doctype,
				"content_name": row.content_name,
				"title": row.title
			})
		version_doc.items_snapshot = json.dumps(items_list)
		version_doc.insert(ignore_permissions=True)
		
	return lib.as_dict()


@frappe.whitelist()
def get_content_libraries():
	check_library_permission()
	user = frappe.session.user
	user_dept = None
	if frappe.get_meta("User").has_field("department"):
		user_dept = frappe.db.get_value("User", user, "department")
	
	my_libraries = frappe.get_all(
		"Content Library",
		filters={"owner": user},
		fields=["name", "library_name", "status", "version", "owner", "shared", "department", "description", "modified"],
		order_by="modified desc"
	)
	
	dept_filters = {"shared": 1}
	if user_dept:
		dept_filters = {"department": user_dept, "shared": 1}
	department_libraries_raw = frappe.get_all(
		"Content Library",
		filters=dept_filters,
		fields=["name", "library_name", "status", "version", "owner", "shared", "department", "description", "modified"],
		order_by="modified desc"
	)
	department_libraries_raw = [l for l in department_libraries_raw if l.owner != user]
	
	shared_libraries_raw = frappe.get_all(
		"Content Library",
		filters={"shared": 1, "owner": ["!=", user]},
		fields=["name", "library_name", "status", "version", "owner", "shared", "department", "description", "modified"],
		order_by="modified desc"
	)
	
	def has_library_access(lib_name):
		# check if specific instructors list is set and user is inside
		instructors = frappe.get_all("Course Instructor", filters={"parent": lib_name, "parenttype": "Content Library"}, pluck="instructor")
		return not instructors or user in instructors

	department_libraries = [l for l in department_libraries_raw if has_library_access(l.name)]
	shared_libraries = [l for l in shared_libraries_raw if has_library_access(l.name)]
	
	usage_counts = frappe.db.sql("""
		select library, count(*) as count
		from `tabCourse Content Link`
		group by library
		order by count desc
	""", as_dict=True)
	
	most_used_names = [r.library for r in usage_counts]
	most_used_libraries = []
	if most_used_names:
		most_used_libraries_raw = frappe.get_all(
			"Content Library",
			filters={"name": ["in", most_used_names]},
			fields=["name", "library_name", "status", "version", "owner", "shared", "department", "description", "modified"]
		)
		most_used_libraries = [l for l in most_used_libraries_raw if l.owner == user or has_library_access(l.name)]
		most_used_libraries.sort(key=lambda x: most_used_names.index(x.name))
		
	# Enrich libraries with owner details (avatars and full names)
	owners = set()
	for lib in my_libraries + department_libraries + shared_libraries + most_used_libraries:
		if lib.owner:
			owners.add(lib.owner)
	
	owner_details = {}
	if owners:
		users_data = frappe.get_all(
			"User",
			filters={"name": ["in", list(owners)]},
			fields=["name", "full_name", "user_image", "open_to", "username"]
		)
		for u in users_data:
			owner_details[u.name] = {
				"name": u.name,
				"full_name": u.full_name or u.name,
				"user_image": u.user_image,
				"open_to": u.open_to,
				"username": u.username or u.name
			}
			
	for lib in my_libraries + department_libraries + shared_libraries + most_used_libraries:
		lib["owner_info"] = owner_details.get(lib.owner) or {
			"name": lib.owner,
			"full_name": lib.owner,
			"username": lib.owner
		}

	return {
		"my_libraries": my_libraries,
		"department_libraries": department_libraries,
		"shared_libraries": shared_libraries,
		"most_used_libraries": most_used_libraries
	}



@frappe.whitelist()
def add_library_content_to_course(course, chapter, library, items, mode):
	if not can_modify_course(course):
		frappe.throw(_("You do not have permission to modify this course."), frappe.PermissionError)
		
	if isinstance(items, str):
		items = json.loads(items)
		
	lib_doc = frappe.get_doc("Content Library", library)
	if not has_library_permission(lib_doc, "read"):
		frappe.throw(_("You do not have permission to access this Content Library."), frappe.PermissionError)
	current_lib_version = lib_doc.version or 1
	
	existing_lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter}, pluck="lesson")
	inserted_links = []
	
	for idx_offset, item in enumerate(items):
		content_doctype = item.get("content_doctype")
		content_name = item.get("content_name")
		title = item.get("title") or content_name
		
		target_lesson_name = None
		
		if mode == "Linked":
			if content_doctype == "Course Lesson":
				target_lesson_name = content_name
			else:
				target_lesson_name = create_wrapper_lesson(title, content_doctype, content_name, chapter, course)
		elif mode == "Copied":
			if content_doctype == "Course Lesson":
				target_lesson_name = clone_lesson(content_name, chapter, course)
			elif content_doctype == "LMS Quiz":
				cloned_quiz = clone_quiz(content_name)
				target_lesson_name = create_wrapper_lesson(title, content_doctype, cloned_quiz, chapter, course)
			elif content_doctype == "LMS Assignment":
				cloned_assignment = clone_assignment(content_name)
				target_lesson_name = create_wrapper_lesson(title, content_doctype, cloned_assignment, chapter, course)
			elif content_doctype == "LMS Programming Exercise":
				cloned_exercise = clone_programming_exercise(content_name)
				target_lesson_name = create_wrapper_lesson(title, content_doctype, cloned_exercise, chapter, course)
			else:
				cloned_doc = frappe.copy_doc(frappe.get_doc(content_doctype, content_name))
				cloned_doc.name = None
				cloned_doc.insert(ignore_permissions=True)
				target_lesson_name = create_wrapper_lesson(title, content_doctype, cloned_doc.name, chapter, course)
		
		if target_lesson_name:
			ref_idx = len(existing_lessons) + idx_offset + 1
			new_ref = frappe.new_doc("Lesson Reference")
			new_ref.parent = chapter
			new_ref.parenttype = "Course Chapter"
			new_ref.parentfield = "lessons"
			new_ref.lesson = target_lesson_name
			new_ref.idx = ref_idx
			new_ref.insert(ignore_permissions=True)
			
			link_doc = frappe.new_doc("Course Content Link")
			link_doc.course = course
			link_doc.chapter = chapter
			link_doc.content_doctype = content_doctype
			link_doc.content_name = content_name
			link_doc.library = library
			link_doc.library_item = content_name
			link_doc.mode = mode
			link_doc.source_version = current_lib_version
			link_doc.insert(ignore_permissions=True)
			inserted_links.append(link_doc)
			
	from lms.lms.utils import calculate_course_completion_time
	frappe.db.set_value(
		"LMS Course",
		course,
		"estimated_completion_time",
		calculate_course_completion_time(course)
	)
	
	frappe.db.commit()
	return {"success": True, "inserted_count": len(inserted_links)}

def get_lesson_content_type_details(lesson_name):
	lesson_title = frappe.db.get_value("Course Lesson", lesson_name, "title")
	lesson_content = frappe.db.get_value("Course Lesson", lesson_name, "content")
	
	if lesson_content:
		try:
			content = json.loads(lesson_content)
			for block in content.get("blocks", []):
				btype = block.get("type")
				bdata = block.get("data", {})
				if btype == "quiz" and bdata.get("quiz"):
					quiz_id = bdata.get("quiz")
					quiz_title = frappe.db.get_value("LMS Quiz", quiz_id, "title") or quiz_id
					return {
						"content_doctype": "LMS Quiz",
						"content_name": quiz_id,
						"title": quiz_title
					}
				elif btype == "assignment" and bdata.get("assignment"):
					asg_id = bdata.get("assignment")
					asg_title = frappe.db.get_value("LMS Assignment", asg_id, "title") or asg_id
					return {
						"content_doctype": "LMS Assignment",
						"content_name": asg_id,
						"title": asg_title
					}
				elif btype == "program" and bdata.get("exercise"):
					ex_id = bdata.get("exercise")
					ex_title = frappe.db.get_value("LMS Programming Exercise", ex_id, "title") or ex_id
					return {
						"content_doctype": "LMS Programming Exercise",
						"content_name": ex_id,
						"title": ex_title
					}
		except Exception:
			pass
			
	return {
		"content_doctype": "Course Lesson",
		"content_name": lesson_name,
		"title": lesson_title
	}


@frappe.whitelist()
def convert_course_to_library(course_name, library_title):
	check_library_permission()
	if not can_modify_course(course_name):
		frappe.throw(_("You do not have permission to modify this course."), frappe.PermissionError)
		
	if frappe.db.exists("Content Library", library_title):
		frappe.throw(_("A Content Library with the title '{0}' already exists.").format(library_title))
		
	lib = frappe.new_doc("Content Library")
	lib.library_name = library_title
	lib.owner = frappe.session.user
	lib.status = "Published"
	lib.version = 1
	
	chapters = frappe.get_all("Course Chapter", filters={"course": course_name}, fields=["name", "title"], order_by="idx")
	
	for chapter in chapters:
		lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter.name}, fields=["lesson", "idx"], order_by="idx")
		for lesson_ref in lessons:
			details = get_lesson_content_type_details(lesson_ref.lesson)
			
			lib.append("items", {
				"content_doctype": details["content_doctype"],
				"content_name": details["content_name"],
				"title": details["title"]
			})
			
	lib.insert(ignore_permissions=True)
	
	version_doc = frappe.new_doc("Content Library Version")
	version_doc.library = lib.name
	version_doc.version_number = 1
	version_doc.change_log = _("Conversion from Course {0}").format(course_name)
	version_doc.timestamp = frappe.utils.now_datetime()
	
	items_list = []
	for row in lib.items:
		items_list.append({
			"content_doctype": row.content_doctype,
			"content_name": row.content_name,
			"title": row.title
		})
	version_doc.items_snapshot = json.dumps(items_list)
	version_doc.insert(ignore_permissions=True)
	
	for chapter in chapters:
		lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter.name}, fields=["lesson"], order_by="idx")
		for lesson_ref in lessons:
			details = get_lesson_content_type_details(lesson_ref.lesson)
			link_doc = frappe.new_doc("Course Content Link")
			link_doc.course = course_name
			link_doc.chapter = chapter.name
			link_doc.content_doctype = details["content_doctype"]
			link_doc.content_name = details["content_name"]
			link_doc.library = lib.name
			link_doc.library_item = details["content_name"]
			link_doc.mode = "Linked"
			link_doc.source_version = 1
			link_doc.insert(ignore_permissions=True)
			
	frappe.db.commit()
	return lib.as_dict()


@frappe.whitelist()
def get_library_usage(library_name):
	check_library_permission()
	lib = frappe.get_doc("Content Library", library_name)
	if not has_library_permission(lib, "read"):
		frappe.throw(_("You do not have permission to access this Content Library."), frappe.PermissionError)
		
	links = frappe.get_all(
		"Course Content Link",
		filters={"library": library_name},
		fields=["course", "mode"]
	)
	
	linked_count = sum(1 for l in links if l.mode == "Linked")
	copied_count = sum(1 for l in links if l.mode == "Copied")
	
	distinct_course_names = list(set(l.course for l in links))
	courses = []
	for cname in distinct_course_names:
		title = frappe.db.get_value("LMS Course", cname, "title") or cname
		courses.append({
			"name": cname,
			"title": title
		})
		
	return {
		"linked_count": linked_count,
		"copied_count": copied_count,
		"courses": courses
	}


@frappe.whitelist()
def get_library_versions(library_name):
	check_library_permission()
	lib = frappe.get_doc("Content Library", library_name)
	if not has_library_permission(lib, "read"):
		frappe.throw(_("You do not have permission to access this Content Library."), frappe.PermissionError)
		
	versions = frappe.get_all(
		"Content Library Version",
		filters={"library": library_name},
		fields=["name", "version_number", "change_log", "timestamp", "items_snapshot"],
		order_by="version_number desc"
	)
	return versions


@frappe.whitelist()
def restore_library_version(library_name, version_number):
	check_library_permission()
	lib = frappe.get_doc("Content Library", library_name)
	if not has_library_permission(lib, "write"):
		frappe.throw(_("You do not have permission to update this Content Library."), frappe.PermissionError)
		
	version_doc_name = frappe.db.exists("Content Library Version", {"library": library_name, "version_number": version_number})
	if not version_doc_name:
		frappe.throw(_("Version {0} for Content Library '{1}' not found.").format(version_number, library_name))
		
	version_doc = frappe.get_doc("Content Library Version", version_doc_name)
	items = json.loads(version_doc.items_snapshot)
	lib.items = []
	for item in items:
		lib.append("items", {
			"content_doctype": item.get("content_doctype"),
			"content_name": item.get("content_name"),
			"title": item.get("title")
		})
		
	lib.version = (lib.version or 1) + 1
	lib.save(ignore_permissions=True)
	
	new_version_doc = frappe.new_doc("Content Library Version")
	new_version_doc.library = lib.name
	new_version_doc.version_number = lib.version
	new_version_doc.change_log = _("Restored version {0}").format(version_number)
	new_version_doc.timestamp = frappe.utils.now_datetime()
	new_version_doc.items_snapshot = version_doc.items_snapshot
	new_version_doc.insert(ignore_permissions=True)
	
	frappe.db.commit()
	return lib.as_dict()


def propagate_lesson_update(doc, method=None):
	links = frappe.get_all(
		"Course Content Link",
		filters={"content_doctype": "Course Lesson", "content_name": doc.name, "mode": "Linked"},
		fields=["course"]
	)
	courses_to_update = set(l.course for l in links)
	if doc.course:
		courses_to_update.add(doc.course)
		
	from lms.lms.utils import calculate_course_completion_time
	for course in courses_to_update:
		try:
			frappe.db.set_value(
				"LMS Course",
				course,
				"estimated_completion_time",
				calculate_course_completion_time(course)
			)
		except Exception:
			pass


@frappe.whitelist()
def log_learning_activity(course: str, chapter: str = None, lesson: str = None):
	if frappe.session.user == "Guest":
		return {"status": "ignored", "reason": "guest_user"}

	if chapter and (chapter.isdigit() or len(chapter) <= 3):
		chapter_name = frappe.db.get_value("Chapter Reference", {"parent": course, "idx": chapter}, "chapter")
		if chapter_name:
			chapter = chapter_name
	
	if lesson and (lesson.isdigit() or len(lesson) <= 3) and chapter:
		lesson_name = frappe.db.get_value("Lesson Reference", {"parent": chapter, "idx": lesson}, "lesson")
		if lesson_name:
			lesson = lesson_name

	log = frappe.new_doc("LMS Page View Log")
	log.member = frappe.session.user
	log.course = course
	log.chapter = chapter
	log.lesson = lesson
	log.time_spent = 0.0
	log.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "success", "name": log.name}


@frappe.whitelist()
def log_learning_heartbeat(course: str, chapter: str = None, lesson: str = None):
	if frappe.session.user == "Guest":
		return {"status": "ignored", "reason": "guest_user"}

	if chapter and (chapter.isdigit() or len(chapter) <= 3):
		chapter_name = frappe.db.get_value("Chapter Reference", {"parent": course, "idx": chapter}, "chapter")
		if chapter_name:
			chapter = chapter_name
	
	if lesson and (lesson.isdigit() or len(lesson) <= 3) and chapter:
		lesson_name = frappe.db.get_value("Lesson Reference", {"parent": chapter, "idx": lesson}, "lesson")
		if lesson_name:
			lesson = lesson_name

	filters = {
		"member": frappe.session.user,
		"course": course,
	}
	if chapter:
		filters["chapter"] = chapter
	if lesson:
		filters["lesson"] = lesson

	recent_logs = frappe.get_all(
		"LMS Page View Log",
		filters=filters,
		fields=["name", "creation", "time_spent"],
		order_by="creation desc",
		limit=1,
	)

	if recent_logs:
		log_name = recent_logs[0].name
		new_time = (recent_logs[0].time_spent or 0.0) + 15.0
		frappe.db.set_value("LMS Page View Log", log_name, "time_spent", new_time, update_modified=True)
		frappe.db.commit()
		return {"status": "updated", "name": log_name, "time_spent": new_time}
	else:
		return log_learning_activity(course, chapter, lesson)


def get_student_streak(student: str) -> int:
	logs = frappe.db.sql("""
		select distinct date(creation) as act_date from `tabLMS Page View Log` where member = %s
		union
		select distinct date(modified) as act_date from `tabLMS Course Progress` where member = %s and status = 'Complete'
		order by act_date desc
	""", (student, student), as_dict=True)

	if not logs:
		return 0

	from frappe.utils import getdate, add_days
	today = getdate()
	yesterday = add_days(today, -1)

	dates = {getdate(r.act_date) for r in logs}

	if today not in dates and yesterday not in dates:
		return 0

	current_check = today if today in dates else yesterday
	streak = 0

	while current_check in dates:
		streak += 1
		current_check = add_days(current_check, -1)

	return streak


def get_student_time_spent(student: str, course: str = None) -> float:
	filters_pv = {"member": student}
	filters_video = {"member": student}
	if course:
		filters_pv["course"] = course
		filters_video["course"] = course

	pv_time = frappe.db.get_value("LMS Page View Log", filters_pv, "sum(time_spent)") or 0.0
	video_time = frappe.db.get_value("LMS Video Watch Duration", filters_video, "sum(duration)") or 0.0

	return round(pv_time + video_time, 2)


def get_course_assessments_and_content(course: str) -> dict:
	lessons = frappe.get_all(
		"Course Lesson",
		filters={"course": course, "exclude_from_course": 0},
		fields=["name", "title", "content", "chapter"]
	)

	quizzes = []
	assignments = []
	exercises = []
	lessons_list = []

	for lesson in lessons:
		lessons_list.append({
			"name": lesson.name,
			"title": lesson.title,
			"chapter": lesson.chapter
		})
		if not lesson.content:
			continue
		try:
			content = json.loads(lesson.content)
		except Exception:
			continue
		for block in content.get("blocks", []):
			btype = block.get("type")
			bdata = block.get("data", {})
			if btype == "quiz" and bdata.get("quiz"):
				quiz_id = bdata.get("quiz")
				quiz_title = frappe.db.get_value("LMS Quiz", quiz_id, "title") or quiz_id
				quizzes.append({
					"quiz": quiz_id,
					"title": quiz_title,
					"lesson": lesson.name,
					"chapter": lesson.chapter,
					"grading_category": bdata.get("grading_category"),
					"due_date": bdata.get("due_date")
				})
			elif btype == "assignment" and bdata.get("assignment"):
				asg_id = bdata.get("assignment")
				asg_title = frappe.db.get_value("LMS Assignment", asg_id, "title") or asg_id
				assignments.append({
					"assignment": asg_id,
					"title": asg_title,
					"lesson": lesson.name,
					"chapter": lesson.chapter,
					"grading_category": bdata.get("grading_category"),
					"due_date": bdata.get("due_date")
				})
			elif btype == "program" and bdata.get("exercise"):
				ex_id = bdata.get("exercise")
				ex_title = frappe.db.get_value("LMS Programming Exercise", ex_id, "title") or ex_id
				exercises.append({
					"exercise": ex_id,
					"title": ex_title,
					"lesson": lesson.name,
					"chapter": lesson.chapter,
					"grading_category": bdata.get("grading_category"),
					"due_date": bdata.get("due_date")
				})

	return {
		"lessons": lessons_list,
		"quizzes": quizzes,
		"assignments": assignments,
		"exercises": exercises
	}


def get_student_score_fallback(course: str, student: str) -> float:
	quizzes = frappe.get_all("LMS Quiz Submission", filters={"course": course, "member": student}, fields=["percentage"])
	assignments = frappe.get_all("LMS Assignment Submission", filters={"course": course, "member": student}, fields=["score"])

	scores = [q.percentage for q in quizzes if q.percentage is not None]
	scores.extend([a.score for a in assignments if a.score is not None])

	if scores:
		return round(sum(scores) / len(scores), 2)
	return 0.0


@frappe.whitelist()
def get_at_risk_details(member: str, course: str) -> dict:
	score = 0
	reasons = []

	last_pv = frappe.db.get_value("LMS Page View Log", {"member": member, "course": course}, "max(creation)")
	last_sub = frappe.db.get_value("LMS Quiz Submission", {"member": member, "course": course}, "max(creation)")

	from frappe.utils import get_datetime, now_datetime
	last_act = None
	if last_pv and last_sub:
		last_act = max(get_datetime(last_pv), get_datetime(last_sub))
	elif last_pv:
		last_act = get_datetime(last_pv)
	elif last_sub:
		last_act = get_datetime(last_sub)

	if last_act:
		days_inactive = (now_datetime() - last_act).days
		if days_inactive >= 14:
			score += 40
			reasons.append(_("No activity recorded for over 14 days ({0} days inactive).").format(days_inactive))
		elif days_inactive >= 7:
			score += 20
			reasons.append(_("No activity recorded for over 7 days ({0} days inactive).").format(days_inactive))
	else:
		enrollment_date = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "creation")
		if enrollment_date:
			days_since_enroll = (now_datetime() - get_datetime(enrollment_date)).days
			if days_since_enroll >= 7:
				score += 35
				reasons.append(_("No activity since enrollment {0} days ago.").format(days_since_enroll))

	avg_quiz = frappe.db.get_value("LMS Quiz Submission", {"member": member, "course": course}, "avg(percentage)") or 0.0
	if avg_quiz > 0 and avg_quiz < 60:
		score += 30
		reasons.append(_("Average quiz score is low ({0}%).").format(round(avg_quiz, 2)))

	progress = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "progress") or 0.0
	batch = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "enrollment_from_batch")
	if batch:
		start_date, end_date = frappe.db.get_value("LMS Batch", batch, ["start_date", "end_date"])
		if start_date and end_date:
			total_days = (get_datetime(end_date) - get_datetime(start_date)).days
			elapsed_days = (now_datetime().date() - get_datetime(start_date).date()).days
			if total_days > 0 and elapsed_days > 0:
				elapsed_pct = (elapsed_days / total_days) * 100
				if elapsed_pct >= 50 and progress < 15:
					score += 20
					reasons.append(_("Struggling with progress: Course is {0}% elapsed but completion is only {1}%.").format(round(elapsed_pct, 1), round(progress, 1)))
	else:
		enrollment_date = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "creation")
		if enrollment_date:
			days_since_enroll = (now_datetime() - get_datetime(enrollment_date)).days
			if days_since_enroll >= 15 and progress < 5:
				score += 15
				reasons.append(_("Stagnant progress: Completed only {0}% in {1} days since enrollment.").format(round(progress, 1), days_since_enroll))

	failed_quizzes = frappe.db.count("LMS Quiz Submission", {"member": member, "course": course, "percentage": ["<", 60]})
	if failed_quizzes >= 3:
		score += 10
		reasons.append(_("Failed {0} quiz attempts.").format(failed_quizzes))

	risk_level = "Low Risk"
	if score >= 70:
		risk_level = "High Risk"
	elif score >= 35:
		risk_level = "Medium Risk"

	return {
		"member": member,
		"course": course,
		"risk_score": score,
		"risk_level": risk_level,
		"reasons": reasons
	}


@frappe.whitelist()
def get_predictive_analytics(member: str, course: str) -> dict:
	from frappe.utils import get_datetime, now_datetime
	progress = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "progress") or 0.0

	last_pv = frappe.db.get_value("LMS Page View Log", {"member": member, "course": course}, "max(creation)")
	last_sub = frappe.db.get_value("LMS Quiz Submission", {"member": member, "course": course}, "max(creation)")
	last_asg = frappe.db.get_value("LMS Assignment Submission", {"member": member, "course": course}, "max(creation)")

	last_act = None
	for dt in [last_pv, last_sub, last_asg]:
		if dt:
			dt_val = get_datetime(dt)
			if not last_act or dt_val > last_act:
				last_act = dt_val

	if progress >= 100.0:
		comp_prob = 100.0
		factors_comp = [_("Course is already 100% completed.")]
	else:
		# Determine how long the student has been inactive
		no_activity_ever = last_act is None
		if last_act:
			active_days_ago = (now_datetime() - last_act).days
		else:
			# Fall back to days since enrollment as the inactivity baseline
			enrollment_date = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "creation")
			active_days_ago = (now_datetime() - get_datetime(enrollment_date)).days if enrollment_date else 99

		eng_factor = 1.0
		if active_days_ago > 14:
			eng_factor = 0.2
		elif active_days_ago > 7:
			eng_factor = 0.5
		elif active_days_ago > 3:
			eng_factor = 0.8

		avg_quiz = frappe.db.get_value("LMS Quiz Submission", {"member": member, "course": course}, "avg(percentage)") or 0.0
		perf_factor = 1.0
		if avg_quiz > 0 and avg_quiz < 60:
			perf_factor = 0.7

		comp_prob = progress + (eng_factor * perf_factor * (100.0 - progress))
		comp_prob = max(0.0, min(100.0, round(comp_prob, 2)))

		factors_comp = []
		if eng_factor < 1.0:
			if no_activity_ever:
				factors_comp.append(_("No learning activity recorded — enrolled {0} days ago with no engagement yet.").format(active_days_ago))
			else:
				factors_comp.append(_("Inactive for {0} days since last activity; this reduces completion momentum.").format(active_days_ago))
		else:
			factors_comp.append(_("Active study engagement maintains progress projection."))
		if perf_factor < 1.0:
			factors_comp.append(_("Struggling with quizzes (avg {0}%) might slow down module progression.").format(round(avg_quiz, 1)))

	avg_score = get_student_score_fallback(course, member)
	if avg_score > 0:
		if avg_score >= 80:
			pass_prob = 95.0
			factors_pass = [_("Excellent average grade ({0}%) indicates strong topic mastery.").format(round(avg_score, 1))]
		elif avg_score >= 60:
			pass_prob = 80.0
			factors_pass = [_("Good average grade ({0}%) meets standard passing criteria.").format(round(avg_score, 1))]
		else:
			pass_prob = 40.0
			factors_pass = [_("Struggling grade average ({0}%) is currently below standard pass rate.").format(round(avg_score, 1))]
	else:
		if progress > 0:
			pass_prob = 70.0
			factors_pass = [_("Progressing in coursework, but no quiz scores are logged yet.")]
		else:
			pass_prob = 50.0
			factors_pass = [_("No graded activities or progress submitted yet.")]

	dropout_prob = 10.0
	factors_drop = []

	# Use actual enrollment progress (not predicted comp_prob) to determine true completion
	if progress >= 100.0:
		dropout_prob = 0.0
		factors_drop = [_("No dropout risk — student has successfully completed the course.")]
	else:
		if last_act:
			days_inactive = (now_datetime() - last_act).days
			if days_inactive >= 14:
				dropout_prob += 60.0
				factors_drop.append(_("Critically inactive for {0} days.").format(days_inactive))
			elif days_inactive >= 7:
				dropout_prob += 30.0
				factors_drop.append(_("Inactive for {0} days.").format(days_inactive))
		else:
			enrollment_date = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course}, "creation")
			if enrollment_date:
				days_since_enroll = (now_datetime() - get_datetime(enrollment_date)).days
				if days_since_enroll >= 10:
					dropout_prob += 50.0
					factors_drop.append(_("Zero learning activity in the {0} days since enrollment.").format(days_since_enroll))

		if progress < 10.0 and dropout_prob > 20.0:
			dropout_prob += 10.0
			factors_drop.append(_("Stagnated at low course completion ({0}%).").format(round(progress, 1)))

		# Scale dropout by actual remaining course progress (not predicted probability)
		remaining = max(0.0, 1.0 - (progress / 100.0))
		dropout_prob = dropout_prob * remaining
		dropout_prob = max(5.0, min(95.0, round(dropout_prob, 2)))
		if not factors_drop:
			factors_drop.append(_("Consistent recent activity indicates low dropout risk."))

	return {
		"completion_probability": comp_prob,
		"factors_completion": factors_comp,
		"pass_probability": pass_prob,
		"factors_pass": factors_pass,
		"dropout_probability": dropout_prob,
		"factors_dropout": factors_drop
	}


def get_student_dashboard_metrics(student: str) -> dict:
	enrollments = frappe.get_all(
		"LMS Enrollment",
		filters={"member": student},
		fields=["name", "course", "progress"]
	)

	courses_data = []
	for env in enrollments:
		course_name = env.course
		course_title = frappe.db.get_value("LMS Course", course_name, "title") or course_name

		grade_info = get_student_grades(course_name, student)
		current_grade = grade_info.get("final_percentage", 0.0)
		grade_label = grade_info.get("final_grade", "N/A")

		if not grade_info.get("enable_grading_policy") or not current_grade:
			current_grade = get_student_score_fallback(course_name, student)
			grade_label = "Pass" if current_grade >= 50 else "Fail" if current_grade > 0 else "N/A"

		time_spent = get_student_time_spent(student, course_name)
		outline_data = get_course_assessments_and_content(course_name)
		total_lessons = len(outline_data["lessons"])

		completed_lessons_count = frappe.db.count("LMS Course Progress", {"member": student, "course": course_name, "status": "Complete"})
		lesson_completion_rate = round((completed_lessons_count / total_lessons * 100), 2) if total_lessons > 0 else 0.0

		quiz_subs = frappe.get_all(
			"LMS Quiz Submission",
			filters={"member": student, "course": course_name},
			fields=["quiz_title", "percentage", "creation"],
			order_by="creation asc"
		)
		quiz_trend = [{
			"quiz": q.quiz_title,
			"score": q.percentage,
			"date": frappe.utils.format_date(q.creation)
		} for q in quiz_subs]

		ex_subs = frappe.get_all(
			"LMS Programming Exercise Submission",
			filters={"member": student},
			fields=["exercise", "status"]
		)
		course_ex_names = [e["exercise"] for e in outline_data["exercises"]]
		course_ex_subs = [es for es in ex_subs if es.exercise in course_ex_names]

		passed_ex = len([es for es in course_ex_subs if es.status == "Passed"])
		failed_ex = len([es for es in course_ex_subs if es.status == "Failed"])

		missing_quizzes = []
		completed_quizzes = {q.quiz for q in frappe.get_all("LMS Quiz Submission", filters={"member": student, "course": course_name}, fields=["quiz"])}
		for q in outline_data["quizzes"]:
			if q["quiz"] not in completed_quizzes:
				missing_quizzes.append({"title": q["title"], "type": "Quiz", "due": q["due_date"]})

		missing_assignments = []
		completed_asgs = {a.assignment for a in frappe.get_all("LMS Assignment Submission", filters={"member": student, "course": course_name}, fields=["assignment"])}
		for a in outline_data["assignments"]:
			if a["assignment"] not in completed_asgs:
				missing_assignments.append({"title": a["title"], "type": "Assignment", "due": a["due_date"]})

		missing_exercises = []
		passed_exercises = {e.exercise for e in frappe.get_all("LMS Programming Exercise Submission", filters={"member": student, "status": "Passed"}, fields=["exercise"])}
		for e in outline_data["exercises"]:
			if e["exercise"] not in passed_exercises:
				missing_exercises.append({"title": e["title"], "type": "Programming Exercise", "due": e["due_date"]})

		missing_activities = missing_quizzes + missing_assignments + missing_exercises

		topic_scores = {}
		for qs in quiz_subs:
			chapter = None
			for q in outline_data["quizzes"]:
				if q["quiz"] == qs.quiz_title or q["title"] == qs.quiz_title:
					chapter = q["chapter"]
					break
			if chapter:
				topic_scores.setdefault(chapter, []).append(qs.percentage)

		asg_subs = frappe.get_all("LMS Assignment Submission", filters={"member": student, "course": course_name}, fields=["assignment_title", "score"])
		for as_doc in asg_subs:
			chapter = None
			for a in outline_data["assignments"]:
				if a["assignment"] == as_doc.assignment_title or a["title"] == as_doc.assignment_title:
					chapter = a["chapter"]
					break
			if chapter:
				topic_scores.setdefault(chapter, []).append(as_doc.score)

		topic_averages = []
		for t, scs in topic_scores.items():
			chapter_title = frappe.db.get_value("Course Chapter", t, "title") or t
			topic_averages.append({
				"topic": chapter_title,
				"avg_score": round(sum(scs) / len(scs), 2)
			})

		topic_averages.sort(key=lambda x: x["avg_score"], reverse=True)
		strongest_topics = topic_averages[:2]
		weakest_topics = sorted(topic_averages, key=lambda x: x["avg_score"])[:2]

		recommendations = []
		for wt in weakest_topics:
			chapter_id = wt["topic"]
			lessons_in_chapter = [l for l in outline_data["lessons"] if l["chapter"] == chapter_id or frappe.db.get_value("Course Chapter", l["chapter"], "title") == chapter_id]
			for lic in lessons_in_chapter:
				is_comp = frappe.db.exists("LMS Course Progress", {"member": student, "lesson": lic["name"], "status": "Complete"})
				if not is_comp:
					recommendations.append({
						"type": "review_lesson",
						"title": lic["title"],
						"reason": f"This lesson is in your weaker topic '{wt['topic']}'. Reviewing it will strengthen your understanding.",
						"course": course_name,
						"lesson": lic["name"]
					})
					break

		failed_subs = frappe.get_all(
			"LMS Quiz Submission",
			filters={"member": student, "course": course_name, "percentage": ["<", 60]},
			fields=["quiz", "quiz_title", "percentage"]
		)
		for fs in failed_subs:
			recommendations.append({
				"type": "retake_quiz",
				"title": fs.quiz_title,
				"reason": f"You scored {fs.percentage}% which is below the passing criteria. Consider retaking this quiz.",
				"quiz": fs.quiz
			})

		failed_asgs = frappe.get_all(
			"LMS Assignment Submission",
			filters={"member": student, "course": course_name, "score": ["<", 60]},
			fields=["assignment", "assignment_title", "score"]
		)
		for fa in failed_asgs:
			asg_title = fa.assignment_title or frappe.db.get_value("LMS Assignment", fa.assignment, "title") or fa.assignment
			recommendations.append({
				"type": "retake_assignment",
				"title": asg_title,
				"reason": f"You scored {fa.score}% which is below the passing criteria. Consider resubmitting this assignment.",
				"assignment": fa.assignment
			})

		failed_exs = frappe.get_all(
			"LMS Programming Exercise Submission",
			filters={"member": student, "status": "Failed"},
			fields=["exercise"]
		)
		course_ex_names = [e["exercise"] for e in outline_data["exercises"]]
		for fe in failed_exs:
			if fe.exercise in course_ex_names:
				ex_title = frappe.db.get_value("LMS Programming Exercise", fe.exercise, "title") or fe.exercise
				recommendations.append({
					"type": "retry_exercise",
					"title": ex_title,
					"reason": "Your submission did not pass all test cases. Retry the programming exercise to solve it.",
					"exercise": fe.exercise
				})

		courses_data.append({
			"course": course_name,
			"title": course_title,
			"progress": env.progress,
			"current_grade": current_grade,
			"grade_label": grade_label,
			"time_spent": time_spent,
			"lesson_completion_rate": lesson_completion_rate,
			"quiz_trend": quiz_trend,
			"passed_exercises": passed_ex,
			"failed_exercises": failed_ex,
			"missing_activities": missing_activities,
			"strongest_topics": strongest_topics,
			"weakest_topics": weakest_topics,
			"recommendations": recommendations[:4],
			"at_risk": get_at_risk_details(student, course_name),
			"predictions": get_predictive_analytics(student, course_name)
		})

	streak = get_student_streak(student)
	total_time = sum(c["time_spent"] for c in courses_data)
	completed_courses = len([c for c in courses_data if c["progress"] == 100])

	return {
		"student": student,
		"streak": streak,
		"total_time_spent": total_time,
		"completed_courses_count": completed_courses,
		"courses": courses_data
	}


def get_instructor_dashboard_metrics(course: str) -> dict:
	title = frappe.db.get_value("LMS Course", course, "title") or course

	enrollment_docs = frappe.get_all(
		"LMS Enrollment",
		filters={"course": course, "member_type": "Student"},
		fields=["member", "progress", "creation"]
	)
	enrollment_count = len(enrollment_docs)

	if not enrollment_count:
		return {
			"course": course,
			"title": title,
			"enrollment_count": 0,
			"active_students": 0,
			"inactive_students": 0,
			"completion_rate": 0.0,
			"average_grade": 0.0,
			"quizzes_stats": [],
			"at_risk_students": [],
			"difficult_lessons": [],
			"difficult_quizzes": [],
			"high_failure_questions": []
		}

	from frappe.utils import add_days, now_datetime
	seven_days_ago = add_days(now_datetime(), -7)

	active_pvs = {p.member for p in frappe.get_all("LMS Page View Log", filters={"course": course, "creation": [">=", seven_days_ago]}, fields=["member"])}
	active_subs = {s.member for s in frappe.get_all("LMS Quiz Submission", filters={"course": course, "creation": [">=", seven_days_ago]}, fields=["member"])}
	active_members = active_pvs.union(active_subs)

	active_count = len([e for e in enrollment_docs if e.member in active_members])
	inactive_count = enrollment_count - active_count

	completed_count = len([e for e in enrollment_docs if e.progress >= 100.0])
	completion_rate = round((completed_count / enrollment_count * 100), 2)

	student_scores = []
	for e in enrollment_docs:
		score = get_student_score_fallback(course, e.member)
		if score > 0:
			student_scores.append(score)
	avg_grade = round(sum(student_scores) / len(student_scores), 2) if student_scores else 0.0

	at_risk_students = []
	for e in enrollment_docs:
		risk_details = get_at_risk_details(e.member, course)
		if risk_details["risk_score"] >= 35:
			member_name = frappe.db.get_value("User", e.member, "full_name") or e.member
			at_risk_students.append({
				"username": e.member,
				"name": member_name,
				"progress": e.progress,
				"risk_score": risk_details["risk_score"],
				"risk_level": risk_details["risk_level"],
				"reasons": risk_details["reasons"]
			})
	at_risk_students.sort(key=lambda x: x["risk_score"], reverse=True)

	outline_data = get_course_assessments_and_content(course)
	difficult_lessons = []

	for lesson in outline_data["lessons"]:
		views = frappe.db.count("LMS Page View Log", {"course": course, "lesson": lesson["name"]})
		avg_time = frappe.db.get_value("LMS Page View Log", {"course": course, "lesson": lesson["name"]}, "avg(time_spent)") or 0.0
		comp_count = frappe.db.count("LMS Course Progress", {"course": course, "lesson": lesson["name"], "status": "Complete"})
		comp_rate = round((comp_count / enrollment_count * 100), 2) if enrollment_count > 0 else 0.0

		if (avg_time > 300 or comp_rate < 70) and views > 0:
			difficult_lessons.append({
				"lesson_name": lesson["name"],
				"title": lesson["title"],
				"views": views,
				"avg_time_spent": round(avg_time, 1),
				"completion_rate": comp_rate,
				"reason": _("Completion rate is {0}% (below 70%) with average study time of {1} mins.").format(round(comp_rate, 1), round(avg_time/60, 1))
			})

	difficult_quizzes = []
	for quiz in outline_data["quizzes"]:
		avg_score = frappe.db.get_value("LMS Quiz Submission", {"course": course, "quiz": quiz["quiz"]}, "avg(percentage)") or 0.0
		subs_count = frappe.db.count("LMS Quiz Submission", {"course": course, "quiz": quiz["quiz"]})
		failed_count = frappe.db.count("LMS Quiz Submission", {"course": course, "quiz": quiz["quiz"], "percentage": ["<", 60]})
		failure_rate = round((failed_count / subs_count * 100), 2) if subs_count > 0 else 0.0

		if (avg_score > 0 and avg_score < 65) or failure_rate > 30:
			difficult_quizzes.append({
				"quiz": quiz["title"],
				"type": "Quiz",
				"avg_score": round(avg_score, 1),
				"attempts": subs_count,
				"failure_rate": failure_rate,
				"reason": _("Average score is low ({0}%) and failure rate is {1}%.").format(round(avg_score, 1), round(failure_rate, 1))
			})

	for asg in outline_data["assignments"]:
		avg_score = frappe.db.get_value("LMS Assignment Submission", {"course": course, "assignment": asg["assignment"]}, "avg(score)") or 0.0
		subs_count = frappe.db.count("LMS Assignment Submission", {"course": course, "assignment": asg["assignment"]})
		failed_count = frappe.db.count("LMS Assignment Submission", {"course": course, "assignment": asg["assignment"], "score": ["<", 60]})
		failure_rate = round((failed_count / subs_count * 100), 2) if subs_count > 0 else 0.0

		if (avg_score > 0 and avg_score < 65) or failure_rate > 30:
			difficult_quizzes.append({
				"quiz": asg["title"],
				"type": "Assignment",
				"avg_score": round(avg_score, 1),
				"attempts": subs_count,
				"failure_rate": failure_rate,
				"reason": _("Average score is low ({0}%) and failure rate is {1}%.").format(round(avg_score, 1), round(failure_rate, 1))
			})

	for ex in outline_data["exercises"]:
		subs_count = frappe.db.count("LMS Programming Exercise Submission", {"exercise": ex["exercise"]})
		failed_count = frappe.db.count("LMS Programming Exercise Submission", {"exercise": ex["exercise"], "status": "Failed"})
		failure_rate = round((failed_count / subs_count * 100), 2) if subs_count > 0 else 0.0

		if failure_rate > 30 and subs_count > 0:
			difficult_quizzes.append({
				"quiz": ex["title"],
				"type": "Programming Exercise",
				"avg_score": round(100.0 - failure_rate, 1),
				"attempts": subs_count,
				"failure_rate": failure_rate,
				"reason": _("Failure rate is high ({0}%) over {1} attempts.").format(round(failure_rate, 1), subs_count)
			})

	high_failure_questions = []
	q_stats = frappe.db.sql("""
		select qr.question_name, qr.question, count(*) as attempts, sum(qr.is_correct) as correct_count
		from `tabLMS Quiz Result` qr
		join `tabLMS Quiz Submission` qs on qr.parent = qs.name
		where qs.course = %s
		group by qr.question_name, qr.question
	""", (course,), as_dict=True)

	for qs in q_stats:
		if qs.attempts >= 2:
			correct_rate = round((qs.correct_count / qs.attempts * 100), 2)
			if correct_rate < 40:
				high_failure_questions.append({
					"question_name": qs.question_name,
					"question_text": qs.question,
					"correct_rate": correct_rate,
					"attempts": qs.attempts,
					"reason": _("Correct answer rate is critically low at {0}% over {1} attempts.").format(correct_rate, qs.attempts)
				})

	quizzes_stats = []
	for quiz in outline_data["quizzes"]:
		avg_q = frappe.db.get_value("LMS Quiz Submission", {"course": course, "quiz": quiz["quiz"]}, "avg(percentage)") or 0.0
		quizzes_stats.append({
			"title": quiz["title"],
			"average": round(avg_q, 1)
		})

	for asg in outline_data["assignments"]:
		avg_asg = frappe.db.get_value("LMS Assignment Submission", {"course": course, "assignment": asg["assignment"]}, "avg(score)") or 0.0
		quizzes_stats.append({
			"title": asg["title"],
			"average": round(avg_asg, 1)
		})

	return {
		"course": course,
		"title": title,
		"enrollment_count": enrollment_count,
		"active_students": active_count,
		"inactive_students": inactive_count,
		"completion_rate": completion_rate,
		"average_grade": avg_grade,
		"quizzes_stats": quizzes_stats,
		"at_risk_students": at_risk_students,
		"difficult_lessons": difficult_lessons,
		"difficult_quizzes": difficult_quizzes,
		"high_failure_questions": high_failure_questions
	}


def get_batch_dashboard_metrics(batch: str) -> dict:
	batch_title = frappe.db.get_value("LMS Batch", batch, "title") or batch

	students = [s.member for s in frappe.get_all("LMS Batch Enrollment", filters={"batch": batch}, fields=["member"])]
	courses = [c.course for c in frappe.get_all("Batch Course", filters={"parent": batch}, fields=["course"])]

	if not students or not courses:
		return {
			"batch": batch,
			"title": batch_title,
			"completion_rate": 0.0,
			"average_grade": 0.0,
			"progress_distribution": {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0},
			"top_performers": [],
			"at_risk_learners": [],
			"comparisons": []
		}

	total_progress = 0
	total_grades = []
	student_metrics = []

	buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

	for std in students:
		std_name = frappe.db.get_value("User", std, "full_name") or std
		std_progress = []
		std_grades = []

		for crs in courses:
			prog = frappe.db.get_value("LMS Enrollment", {"member": std, "course": crs}, "progress") or 0.0
			std_progress.append(prog)

			grade = get_student_score_fallback(crs, std)
			if grade > 0:
				std_grades.append(grade)

		avg_prog = sum(std_progress) / len(std_progress) if std_progress else 0.0
		avg_grd = sum(std_grades) / len(std_grades) if std_grades else 0.0

		total_progress += avg_prog
		if avg_grd > 0:
			total_grades.append(avg_grd)

		if avg_prog <= 20:
			buckets["0-20"] += 1
		elif avg_prog <= 40:
			buckets["21-40"] += 1
		elif avg_prog <= 60:
			buckets["41-60"] += 1
		elif avg_prog <= 80:
			buckets["61-80"] += 1
		else:
			buckets["81-100"] += 1

		student_metrics.append({
			"username": std,
			"name": std_name,
			"progress": round(avg_prog, 2),
			"grade": round(avg_grd, 2)
		})

	batch_avg_progress = round(total_progress / len(students), 2)
	batch_avg_grade = round(sum(total_grades) / len(total_grades), 2) if total_grades else 0.0

	student_metrics.sort(key=lambda x: (x["progress"], x["grade"]), reverse=True)
	top_performers = student_metrics[:5]

	at_risk_learners = []
	for std in students:
		max_risk = {"risk_score": 0, "risk_level": "Low Risk", "reasons": []}
		for crs in courses:
			risk = get_at_risk_details(std, crs)
			if risk["risk_score"] > max_risk["risk_score"]:
				max_risk = risk

		if max_risk["risk_score"] >= 35:
			std_name = frappe.db.get_value("User", std, "full_name") or std
			at_risk_learners.append({
				"username": std,
				"name": std_name,
				"risk_score": max_risk["risk_score"],
				"risk_level": max_risk["risk_level"],
				"reasons": max_risk["reasons"]
			})
	at_risk_learners.sort(key=lambda x: x["risk_score"], reverse=True)

	comparisons = []
	for crs in courses:
		current_batch_prog_list = [frappe.db.get_value("LMS Enrollment", {"member": s, "course": crs}, "progress") or 0.0 for s in students]
		current_batch_crs_prog = sum(current_batch_prog_list) / len(students) if students else 0.0

		other_batches = frappe.get_all(
			"Batch Course",
			filters={"course": crs, "parent": ["!=", batch]},
			fields=["parent"]
		)
		other_batches_data = []
		for ob in other_batches[:2]:
			ob_name = ob.parent
			ob_title = frappe.db.get_value("LMS Batch", ob_name, "title") or ob_name
			ob_stds = [s.member for s in frappe.get_all("LMS Batch Enrollment", filters={"batch": ob_name}, fields=["member"])]
			if ob_stds:
				ob_prog_list = [frappe.db.get_value("LMS Enrollment", {"member": s, "course": crs}, "progress") or 0.0 for s in ob_stds]
				ob_avg_prog = sum(ob_prog_list) / len(ob_prog_list)
				other_batches_data.append({
					"batch_title": ob_title,
					"average_progress": round(ob_avg_prog, 2)
				})

		comparisons.append({
			"course_title": frappe.db.get_value("LMS Course", crs, "title") or crs,
			"current_batch_title": batch_title,
			"current_batch_progress": round(current_batch_crs_prog, 2),
			"comparison_batches": other_batches_data
		})

	return {
		"batch": batch,
		"title": batch_title,
		"completion_rate": batch_avg_progress,
		"average_grade": batch_avg_grade,
		"progress_distribution": buckets,
		"top_performers": top_performers,
		"at_risk_learners": at_risk_learners,
		"comparisons": comparisons
	}


def get_department_dashboard_metrics(department: str) -> dict:
	courses = frappe.get_all(
		"LMS Course",
		filters={"category": department, "published": 1},
		fields=["name", "title"]
	)

	if not courses:
		return {
			"department": department,
			"course_completion_rates": [],
			"average_performance": [],
			"faculty_performance": [],
			"student_engagement_trends": []
		}

	course_completion_rates = []
	average_performance = []
	faculty_performance = {}

	for course in courses:
		cname = course.name
		ctitle = course.title

		enrollments = frappe.get_all("LMS Enrollment", filters={"course": cname, "member_type": "Student"}, fields=["member", "progress"])
		ecount = len(enrollments)
		if ecount > 0:
			completed = len([e for e in enrollments if e.progress >= 100.0])
			comp_rate = round((completed / ecount * 100), 2)
			course_completion_rates.append({"course": ctitle, "completion_rate": comp_rate, "enrollments": ecount})

			grades = [get_student_score_fallback(cname, e.member) for e in enrollments]
			grades = [g for g in grades if g > 0]
			avg_grade = round(sum(grades) / len(grades), 2) if grades else 0.0
			average_performance.append({"course": ctitle, "average_grade": avg_grade})
		else:
			course_completion_rates.append({"course": ctitle, "completion_rate": 0.0, "enrollments": 0})
			average_performance.append({"course": ctitle, "average_grade": 0.0})

		instructors = get_instructors("LMS Course", cname)
		for inst in instructors:
			inst_name = frappe.db.get_value("User", inst, "full_name") or inst
			faculty_performance.setdefault(inst, {"name": inst_name, "courses": 0, "total_enrollments": 0})
			faculty_performance[inst]["courses"] += 1
			faculty_performance[inst]["total_enrollments"] += ecount

	faculty_list = []
	for f_id, f_data in faculty_performance.items():
		faculty_list.append({
			"instructor": f_data["name"],
			"courses_count": f_data["courses"],
			"enrollments": f_data["total_enrollments"]
		})

	from frappe.utils import add_days, now_datetime
	activity_trends = []
	course_names = [c.name for c in courses]
	
	if course_names:
		for i in range(6, -1, -1):
			target_date = add_days(now_datetime().date(), -i)
			active_users = frappe.db.sql("""
				select count(distinct member) from `tabLMS Page View Log`
				where course in %s and date(creation) = %s
			""", (tuple(course_names), target_date))[0][0] or 0

			activity_trends.append({
				"date": frappe.utils.format_date(target_date),
				"active_users": active_users
			})

	return {
		"department": department,
		"course_completion_rates": course_completion_rates,
		"average_performance": average_performance,
		"faculty_performance": faculty_list,
		"student_engagement_trends": activity_trends
	}


def get_admin_dashboard_metrics() -> dict:
	total_enrollments = frappe.db.count("LMS Enrollment")

	from frappe.utils import add_days, now_datetime
	thirty_days_ago = add_days(now_datetime(), -30)

	active_learners = frappe.db.sql("""
		select count(distinct member) from (
			select member from `tabLMS Page View Log` where creation >= %s
			union
			select member from `tabLMS Quiz Submission` where creation >= %s
		) as active_members
	""", (thirty_days_ago, thirty_days_ago))[0][0] or 0

	completed_enrollments = frappe.db.count("LMS Enrollment", {"progress": [">=", 100.0]})
	overall_completion_rate = round((completed_enrollments / total_enrollments * 100), 2) if total_enrollments > 0 else 0.0

	popular_courses = frappe.db.sql("""
		select course, count(*) as count
		from `tabLMS Enrollment`
		group by course
		order by count desc
		limit 5
	""", as_dict=True)

	popular_list = []
	for pc in popular_courses:
		ctitle = frappe.db.get_value("LMS Course", pc.course, "title") or pc.course
		popular_list.append({"course": ctitle, "enrollments": pc.count})

	lowest_completion_courses = frappe.db.sql("""
		select course, avg(progress) as avg_prog, count(*) as ecount
		from `tabLMS Enrollment`
		group by course
		having ecount >= 5
		order by avg_prog asc
		limit 5
	""", as_dict=True)

	lowest_list = []
	for lc in lowest_completion_courses:
		ctitle = frappe.db.get_value("LMS Course", lc.course, "title") or lc.course
		lowest_list.append({"course": ctitle, "completion_rate": round(lc.avg_prog, 2), "enrollments": lc.ecount})

	courses = frappe.get_all("LMS Course", filters={"published": 1}, fields=["name", "title"])
	perf_list = []
	for c in courses:
		enrollments = frappe.get_all("LMS Enrollment", filters={"course": c.name}, fields=["member"])
		scores = []
		for e in enrollments:
			sc = get_student_score_fallback(c.name, e.member)
			if sc > 0:
				scores.append(sc)
		if scores:
			avg_sc = sum(scores) / len(scores)
			perf_list.append({"course": c.title, "average_grade": round(avg_sc, 2), "students_evaluated": len(scores)})

	perf_list.sort(key=lambda x: x["average_grade"], reverse=True)
	highest_perf_list = perf_list[:5]

	risk_list = []
	for c in courses:
		enrollments = frappe.get_all("LMS Enrollment", filters={"course": c.name}, fields=["member"])
		if len(enrollments) >= 3:
			at_risk_cnt = 0
			for e in enrollments:
				risk = get_at_risk_details(e.member, c.name)
				if risk["risk_score"] >= 35:
					at_risk_cnt += 1
			pct_risk = round((at_risk_cnt / len(enrollments) * 100), 2)
			risk_list.append({"course": c.title, "risk_percentage": pct_risk, "at_risk_count": at_risk_cnt, "enrollments": len(enrollments)})

	risk_list.sort(key=lambda x: x["risk_percentage"], reverse=True)
	highest_risk_courses = risk_list[:5]

	signup_trends = []
	for i in range(6, -1, -1):
		target_date = add_days(now_datetime().date(), -i)
		signups = frappe.db.count("User", {"creation": ["like", f"{target_date}%"]})
		signup_trends.append({
			"date": frappe.utils.format_date(target_date),
			"signups": signups
		})

	return {
		"total_enrollments": total_enrollments,
		"active_learners": active_learners,
		"overall_completion_rate": overall_completion_rate,
		"popular_courses": popular_list,
		"lowest_completion_courses": lowest_list,
		"highest_performing_courses": highest_perf_list,
		"highest_risk_courses": highest_risk_courses,
		"signup_trends": signup_trends
	}


def calculate_dashboard_data(dashboard_type: str, reference_name: str) -> dict:
	if dashboard_type == "Student":
		return get_student_dashboard_metrics(reference_name)
	elif dashboard_type == "Instructor":
		return get_instructor_dashboard_metrics(reference_name)
	elif dashboard_type == "Batch":
		return get_batch_dashboard_metrics(reference_name)
	elif dashboard_type == "Department":
		return get_department_dashboard_metrics(reference_name)
	elif dashboard_type == "Administrative":
		return get_admin_dashboard_metrics()
	else:
		frappe.throw(_("Invalid dashboard type."))


def save_dashboard_to_cache(dashboard_type: str, reference_name: str, data: dict):
	ref = reference_name or "global"
	try:
		cache_name = frappe.db.get_value(
			"LMS Analytics Cache",
			{"cache_type": dashboard_type, "reference_name": ref},
			"name"
		)

		serialized_data = json.dumps(data, default=str)

		if cache_name:
			frappe.db.set_value(
				"LMS Analytics Cache",
				cache_name,
				{
					"data": serialized_data,
					"last_updated": frappe.utils.now_datetime()
				},
				update_modified=True
			)
		else:
			cache_doc = frappe.new_doc("LMS Analytics Cache")
			cache_doc.cache_type = dashboard_type
			cache_doc.reference_name = ref
			cache_doc.data = serialized_data
			cache_doc.last_updated = frappe.utils.now_datetime()
			cache_doc.insert(ignore_permissions=True)

		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(title="LMS Analytics Cache Deadlock", message=frappe.get_traceback())


@frappe.whitelist(allow_guest=True)
def get_analytics_dashboard(dashboard_type: str, reference_name: str = None) -> dict:
	if frappe.session.user == "Guest":
		dashboard_type = "Administrative"
		reference_name = "global"

	ref = reference_name or "global"

	if dashboard_type == "Student":
		roles = frappe.get_roles()
		is_privileged = any(r in roles for r in ["System Manager", "Course Creator", "Moderator", "Batch Evaluator"])
		if not is_privileged and ref != frappe.session.user:
			ref = frappe.session.user

	cache_doc = frappe.db.get_value(
		"LMS Analytics Cache",
		{"cache_type": dashboard_type, "reference_name": ref},
		["data", "last_updated"],
		as_dict=True
	)

	if cache_doc and cache_doc.data:
		from frappe.utils import get_datetime, now_datetime
		last_up = get_datetime(cache_doc.last_updated)
		if (now_datetime() - last_up).total_seconds() < 3600:
			return json.loads(cache_doc.data)

	data = calculate_dashboard_data(dashboard_type, ref)
	save_dashboard_to_cache(dashboard_type, ref, data)
	return data


@frappe.whitelist()
def update_analytics_cache():
	from frappe.utils import add_days, now_datetime
	thirty_days_ago = add_days(now_datetime(), -30)
	ninety_days_ago = add_days(now_datetime(), -90)

	admin_data = get_admin_dashboard_metrics()
	save_dashboard_to_cache("Administrative", "global", admin_data)

	categories = frappe.get_all("LMS Category", fields=["name"])
	for cat in categories:
		try:
			dep_data = get_department_dashboard_metrics(cat.name)
			save_dashboard_to_cache("Department", cat.name, dep_data)
		except Exception:
			pass

	active_courses = [c.course for c in frappe.get_all(
		"LMS Enrollment",
		filters={"modified": [">=", ninety_days_ago]},
		fields=["course"],
		distinct=True
	)]
	for ac in active_courses:
		if ac:
			try:
				course_data = get_instructor_dashboard_metrics(ac)
				save_dashboard_to_cache("Instructor", ac, course_data)
			except Exception:
				pass

	active_batches = [b.batch for b in frappe.get_all(
		"LMS Batch Enrollment",
		filters={"creation": [">=", ninety_days_ago]},
		fields=["batch"],
		distinct=True
	)]
	for ab in active_batches:
		if ab:
			try:
				batch_data = get_batch_dashboard_metrics(ab)
				save_dashboard_to_cache("Batch", ab, batch_data)
			except Exception:
				pass

	pvs = {p.member for p in frappe.get_all("LMS Page View Log", filters={"creation": [">=", thirty_days_ago]}, fields=["member"])}
	subs = {s.member for s in frappe.get_all("LMS Quiz Submission", filters={"creation": [">=", thirty_days_ago]}, fields=["member"])}
	active_students = pvs.union(subs)
	for ast in active_students:
		if ast:
			try:
				student_data = get_student_dashboard_metrics(ast)
				save_dashboard_to_cache("Student", ast, student_data)
			except Exception:
				pass


@frappe.whitelist()
def get_instructor_analytics_courses():
	user = frappe.session.user
	roles = frappe.get_roles(user)

	if any(role in roles for role in ["Course Evaluator", "Moderator", "System Manager", "Administrator"]):
		courses = frappe.get_all(
			"LMS Course",
			filters={"published": 1},
			fields=["name", "title"],
			order_by="title asc",
			limit=100
		)
	else:
		course_names = frappe.get_all(
			"Course Instructor",
			filters={"instructor": user, "parenttype": "LMS Course"},
			pluck="parent"
		)
		if not course_names:
			return []
		courses = frappe.get_all(
			"LMS Course",
			filters={"name": ["in", course_names], "published": 1},
			fields=["name", "title"],
			order_by="title asc",
			limit=100
		)
	return courses


@frappe.whitelist()
def get_instructor_analytics_batches():
	user = frappe.session.user
	roles = frappe.get_roles(user)

	if any(role in roles for role in ["Batch Evaluator", "Moderator", "System Manager", "Administrator"]):
		batches = frappe.get_all(
			"LMS Batch",
			filters={"published": 1},
			fields=["name", "title"],
			order_by="title asc",
			limit=100
		)
	else:
		batch_names = frappe.get_all(
			"Course Instructor",
			filters={"instructor": user, "parenttype": "LMS Batch"},
			pluck="parent"
		)
		if not batch_names:
			return []
		batches = frappe.get_all(
			"LMS Batch",
			filters={"name": ["in", batch_names], "published": 1},
			fields=["name", "title"],
			order_by="title asc",
			limit=100
		)
	return batches


@frappe.whitelist()
def get_lms_staff_users(txt: str = "") -> list:
	"""
	Returns users who hold at least one LMS staff role:
	  Course Creator, Course Evaluator, Moderator, Batch Evaluator.
	Used in the Share Question Bank dialog to restrict the recipient list.
	Returns: [{ value: email, label: full_name, description: email }]
	"""
	lms_roles = ["Course Creator", "Course Evaluator", "Moderator", "Batch Evaluator"]

	# Get all user emails that have at least one of the required roles
	txt_like = "%" + (txt or "") + "%"
	eligible_emails = frappe.db.sql(
		"""
		SELECT DISTINCT u.name AS email, u.full_name
		FROM `tabUser` u
		INNER JOIN `tabHas Role` hr ON hr.parent = u.name
		WHERE hr.role IN ({roles})
		  AND u.enabled = 1
		  AND u.name != 'Administrator'
		  AND (
			u.name LIKE %s
			OR u.full_name LIKE %s
		  )
		ORDER BY u.full_name
		LIMIT 20
		""".format(roles=", ".join(["%s"] * len(lms_roles))),
		tuple(lms_roles) + (txt_like, txt_like),
		as_dict=True,
	)

	return [
		{
			"value": row.email,
			"label": row.full_name or row.email,
			"description": row.email,
		}
		for row in eligible_emails
	]


@frappe.whitelist(allow_guest=True)
def get_public_platform_stats() -> dict:

	"""
	Returns aggregated, non-sensitive platform statistics for guest / non-logged-in visitors.
	No personal or instructor-specific data is included.
	"""
	from frappe.utils import add_days, today

	# Total published courses
	total_courses = frappe.db.count("LMS Course", {"published": 1})

	# Total registered members (LMS Member)
	total_members = frappe.db.count("User", {"enabled": 1, "user_type": "Website User"})

	# Total enrollments across all courses
	total_enrollments = frappe.db.count("LMS Enrollment")

	# Active learners in the last 30 days (users with a page view in last 30 days)
	thirty_days_ago = add_days(today(), -30)
	active_learners = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT member) FROM `tabLMS Page View Log`
		WHERE creation >= %s
		""",
		(thirty_days_ago,),
	)[0][0] or 0

	# Platform-wide completion rate
	total_with_progress = frappe.db.sql(
		"SELECT COUNT(*) FROM `tabLMS Enrollment`"
	)[0][0] or 0
	completed = frappe.db.sql(
		"SELECT COUNT(*) FROM `tabLMS Enrollment` WHERE progress >= 100"
	)[0][0] or 0
	completion_rate = round((completed / total_with_progress * 100), 1) if total_with_progress else 0.0

	# Top 5 most-enrolled published courses
	popular_courses = frappe.db.sql(
		"""
		SELECT c.title AS course, COUNT(e.name) AS enrollments
		FROM `tabLMS Enrollment` e
		INNER JOIN `tabLMS Course` c ON c.name = e.course
		WHERE c.published = 1
		GROUP BY e.course
		ORDER BY enrollments DESC
		LIMIT 5
		""",
		as_dict=True,
	)

	# Total published batches
	total_batches = frappe.db.count("LMS Batch", {"published": 1})

	# Total quiz submissions (engagement signal)
	total_quiz_submissions = frappe.db.count("LMS Quiz Submission")

	# Total certificates issued
	total_certificates = frappe.db.count("LMS Certificate")

	return {
		"total_courses": total_courses,
		"total_members": total_members,
		"total_enrollments": total_enrollments,
		"active_learners_30d": active_learners,
		"completion_rate": completion_rate,
		"popular_courses": popular_courses,
		"total_batches": total_batches,
		"total_quiz_submissions": total_quiz_submissions,
		"total_certificates": total_certificates,
	}



def check_content_before_save(content_doctype: str, content_name: str) -> dict:
	check_library_permission()
	is_shared = False
	usage_count = 0
	has_submissions = False

	# Check Linked Course Content Links count
	usage_count = frappe.db.count("Course Content Link", {
		"content_doctype": content_doctype,
		"content_name": content_name,
		"mode": "Linked"
	})
	if usage_count > 0:
		is_shared = True

	# Also check submissions/attempts
	if content_doctype == "LMS Quiz":
		has_submissions = frappe.db.count("LMS Quiz Submission", {"quiz": content_name}) > 0
	elif content_doctype == "LMS Assignment":
		has_submissions = frappe.db.count("LMS Assignment Submission", {"assignment": content_name}) > 0
	elif content_doctype == "LMS Programming Exercise":
		has_submissions = frappe.db.count("LMS Programming Exercise Submission", {"exercise": content_name}) > 0
	elif content_doctype == "Peer Review Rubric":
		assignments = frappe.get_all("LMS Assignment", filters={"peer_review_rubric": content_name}, pluck="name")
		if assignments:
			has_submissions = frappe.db.count("LMS Assignment Submission", {"assignment": ["in", assignments]}) > 0


	return {
		"is_shared": is_shared,
		"usage_count": usage_count,
		"has_submissions": has_submissions
	}


def update_lesson_blocks_content(lesson_doc, doctype, old_name, new_name):
	import json
	updated = False
	if lesson_doc.content:
		try:
			content = json.loads(lesson_doc.content)
			for block in content.get("blocks", []):
				btype = block.get("type")
				bdata = block.get("data", {})
				if doctype == "LMS Quiz" and btype == "quiz" and bdata.get("quiz") == old_name:
					block["data"]["quiz"] = new_name
					updated = True
				elif doctype == "LMS Assignment" and btype == "assignment" and bdata.get("assignment") == old_name:
					block["data"]["assignment"] = new_name
					updated = True
				elif doctype == "LMS Programming Exercise" and btype == "program" and bdata.get("exercise") == old_name:
					block["data"]["exercise"] = new_name
					updated = True
			if updated:
				lesson_doc.content = json.dumps(content)
		except Exception:
			pass
	return updated


@frappe.whitelist()
def create_new_content_version(content_doctype: str, content_name: str, change_log: str = None, doc_data: str = None) -> dict:
	check_library_permission()
	original_doc = frappe.get_doc(content_doctype, content_name)
	root_parent = original_doc.get("parent_version") or original_doc.name
	
	new_doc = frappe.copy_doc(original_doc)
	new_doc.version_number = frappe.utils.cint(original_doc.get("version_number") or 1) + 1
	new_doc.parent_version = root_parent
	new_doc.created_from_version = original_doc.name
	new_doc.version_notes = change_log
	new_doc.is_current_version = 1
	
	if doc_data:
		import json
		data = json.loads(doc_data)
		for k, v in data.items():
			new_doc.set(k, v)
			
	# Deactivate older versions in the family
	frappe.db.set_value(content_doctype, {"parent_version": root_parent}, "is_current_version", 0)
	frappe.db.set_value(content_doctype, root_parent, "is_current_version", 0)
	
	new_doc.insert(ignore_permissions=True)
	
	return {
		"new_name": new_doc.name,
		"version_number": new_doc.version_number
	}


@frappe.whitelist()
def list_versions(content_doctype: str, content_name: str) -> list:
	check_library_permission()
	if not frappe.db.exists(content_doctype, content_name):
		return []
	doc = frappe.get_doc(content_doctype, content_name)
	root_parent = doc.get("parent_version") or doc.name
	
	# Safer two-step lookup to avoid complex OR conditions in get_all
	v1 = frappe.get_all(
		content_doctype,
		filters={"parent_version": root_parent},
		fields=["name", "version_number", "version_notes", "is_current_version", "modified", "owner"]
	)
	v2 = frappe.get_all(
		content_doctype,
		filters={"name": root_parent},
		fields=["name", "version_number", "version_notes", "is_current_version", "modified", "owner"]
	)
	
	seen = set()
	merged = []
	for v in (v2 + v1):
		if v.name not in seen:
			seen.add(v.name)
			merged.append(v)
			
	merged.sort(key=lambda x: x.get("version_number") or 1)
	return merged


@frappe.whitelist()
def compare_versions(content_doctype: str, version1: str, version2: str) -> dict:
	check_library_permission()
	doc1 = frappe.get_doc(content_doctype, version1)
	doc2 = frappe.get_doc(content_doctype, version2)
	
	diff = {}
	exclude_fields = {
		"name", "creation", "modified", "modified_by", "owner", 
		"docstatus", "idx", "version_number", "parent_version", 
		"created_from_version", "version_notes", "is_current_version"
	}
	
	for field in doc1.meta.fields:
		fname = field.fieldname
		if fname in exclude_fields:
			continue
		val1 = doc1.get(fname)
		val2 = doc2.get(fname)
		if val1 != val2:
			diff[fname] = {
				"label": field.label or fname,
				"v1": val1,
				"v2": val2
			}
	return diff


@frappe.whitelist()
def upgrade_course_content(course: str, chapter: str, content_doctype: str, old_name: str, new_name: str) -> dict:
	check_library_permission()
	new_ver = frappe.db.get_value(content_doctype, new_name, "version_number") or 1
	
	if content_doctype == "Course Lesson":
		frappe.db.set_value(
			"Lesson Reference",
			{"parent": chapter, "parenttype": "Course Chapter", "lesson": old_name},
			"lesson",
			new_name
		)
		frappe.db.set_value(
			"Course Content Link",
			{
				"course": course,
				"chapter": chapter,
				"content_doctype": content_doctype,
				"content_name": old_name
			},
			{
				"content_name": new_name,
				"source_version": new_ver
			}
		)
	else:
		lessons = frappe.get_all(
			"Course Lesson",
			filters={"course": course, "chapter": chapter},
			fields=["name", "content"]
		)
		for lesson in lessons:
			lesson_doc = frappe.get_doc("Course Lesson", lesson.name)
			if update_lesson_blocks_content(lesson_doc, content_doctype, old_name, new_name):
				is_shared = check_content_before_save("Course Lesson", lesson.name)["is_shared"]
				if is_shared:
					cloned_lesson = frappe.copy_doc(lesson_doc)
					cloned_lesson.title = f"{lesson_doc.title} (Cloned)"
					cloned_lesson.insert(ignore_permissions=True)
					
					frappe.db.set_value(
						"Lesson Reference",
						{"parent": chapter, "parenttype": "Course Chapter", "lesson": lesson.name},
						"lesson",
						cloned_lesson.name
					)
					
					frappe.db.set_value(
						"Course Content Link",
						{
							"course": course,
							"chapter": chapter,
							"content_doctype": "Course Lesson",
							"content_name": lesson.name
						},
						"content_name",
						cloned_lesson.name
					)
				else:
					lesson_doc.save(ignore_permissions=True)
					
		frappe.db.set_value(
			"Course Content Link",
			{
				"course": course,
				"chapter": chapter,
				"content_doctype": content_doctype,
				"content_name": old_name
			},
			{
				"content_name": new_name,
				"source_version": new_ver
			}
		)
	return {"status": "success"}


@frappe.whitelist()
def upgrade_multiple_courses(courses: str, content_doctype: str, old_name: str, new_name: str) -> dict:
	check_library_permission()
	import json
	courses_list = json.loads(courses)
	for c in courses_list:
		course = c.get("course")
		chapter = c.get("chapter")
		upgrade_course_content(
			course=course,
			chapter=chapter,
			content_doctype=content_doctype,
			old_name=c.get("content_name") or old_name,
			new_name=new_name
		)
	return {"status": "success"}


@frappe.whitelist()
def retrieve_usage_information(content_doctype: str, name: str) -> dict:
	check_library_permission()
	if not frappe.db.exists(content_doctype, name):
		return {"courses": []}
	doc = frappe.get_doc(content_doctype, name)
	root_parent = doc.get("parent_version") or doc.name
	
	v1 = frappe.get_all(content_doctype, filters={"parent_version": root_parent}, fields=["name"])
	v2 = frappe.get_all(content_doctype, filters={"name": root_parent}, fields=["name"])
	all_names = list(set([v.name for v in v1 + v2]))
	
	links = frappe.get_all(
		"Course Content Link",
		filters={
			"content_doctype": content_doctype,
			"content_name": ["in", all_names]
		},
		fields=["name", "course", "chapter", "content_name", "source_version"]
	)
	
	courses_usage = []
	for link in links:
		course_title = frappe.db.get_value("LMS Course", link.course, "title") or link.course
		active_ver = link.source_version
		if not active_ver:
			active_ver = frappe.db.get_value(content_doctype, link.content_name, "version_number") or 1
			
		courses_usage.append({
			"course": link.course,
			"course_title": course_title,
			"chapter": link.chapter,
			"content_name": link.content_name,
			"active_version": frappe.utils.cint(active_ver)
		})
	return {"courses": courses_usage}


@frappe.whitelist()
def retrieve_version_history(content_doctype: str, name: str) -> list:
	return list_versions(content_doctype, name)


@frappe.whitelist()
def get_upgrade_candidates() -> list:
	check_library_permission()
	
	links = frappe.get_all(
		"Course Content Link",
		filters={"mode": "Linked"},
		fields=["name", "course", "chapter", "content_doctype", "content_name", "source_version", "library"]
	)
	
	candidates = []
	for link in links:
		if not frappe.db.exists(link.content_doctype, link.content_name):
			continue
		doc = frappe.get_doc(link.content_doctype, link.content_name)
		root_parent = doc.get("parent_version") or link.content_name
		
		latest_docs = frappe.get_all(
			link.content_doctype,
			filters={"parent_version": root_parent, "is_current_version": 1},
			fields=["name", "version_number", "title" if link.content_doctype != "LMS Assessment" else "name"],
			limit=1
		)
		if not latest_docs:
			latest_docs = frappe.get_all(
				link.content_doctype,
				filters={"name": root_parent, "is_current_version": 1},
				fields=["name", "version_number", "title" if link.content_doctype != "LMS Assessment" else "name"],
				limit=1
			)
			
		if latest_docs:
			latest = latest_docs[0]
			current_ver = frappe.utils.cint(link.source_version or doc.get("version_number") or 1)
			latest_ver = frappe.utils.cint(latest.version_number)
			
			if latest_ver > current_ver:
				course_title = frappe.db.get_value("LMS Course", link.course, "title") or link.course
				title_field = "title" if link.content_doctype != "LMS Assessment" else "name"
				item_title = doc.get(title_field) or link.content_name
				candidates.append({
					"link_name": link.name,
					"course": link.course,
					"course_title": course_title,
					"chapter": link.chapter,
					"content_doctype": link.content_doctype,
					"content_name": link.content_name,
					"current_version": current_ver,
					"latest_version": latest_ver,
					"latest_name": latest.name,
					"title": item_title
				})
	return candidates


@frappe.whitelist()
def get_most_reused_content() -> list:
	check_library_permission()
	
	links = frappe.get_all(
		"Course Content Link",
		filters={"mode": "Linked"},
		fields=["course", "content_doctype", "content_name"]
	)
	
	reuse_map = {}
	for link in links:
		if not frappe.db.exists(link.content_doctype, link.content_name):
			continue
			
		root_parent = frappe.db.get_value(link.content_doctype, link.content_name, "parent_version") or link.content_name
		
		group_key = (link.content_doctype, root_parent)
		if group_key not in reuse_map:
			title_field = "title" if link.content_doctype != "LMS Assessment" else "name"
			title = frappe.db.get_value(link.content_doctype, root_parent, title_field) or root_parent
			reuse_map[group_key] = {
				"root_name": root_parent,
				"title": title,
				"content_doctype": link.content_doctype,
				"courses": set()
			}
			
		course_title = frappe.db.get_value("LMS Course", link.course, "title") or link.course
		reuse_map[group_key]["courses"].add(course_title)

	res = []
	for key, val in reuse_map.items():
		val["courses"] = list(val["courses"])
		val["course_count"] = len(val["courses"])
		res.append(val)
		
	res.sort(key=lambda x: x["course_count"], reverse=True)
	return res


@frappe.whitelist()
def get_peer_review_rubrics() -> list:
	user = frappe.session.user
	if "System Manager" in frappe.get_roles(user) or "Moderator" in frappe.get_roles(user):
		return frappe.get_all("Peer Review Rubric", fields=["name", "title", "description", "is_public", "owner"])
	
	return frappe.get_all(
		"Peer Review Rubric",
		filters=[
			["is_public", "=", 1],
			"or",
			["owner", "=", user]
		],
		fields=["name", "title", "description", "is_public", "owner"]
	)


def get_rubric_permission_query_conditions(user) -> str:
	if not user:
		user = frappe.session.user
	if "System Manager" in frappe.get_roles(user) or "Moderator" in frappe.get_roles(user):
		return ""
	return f"(is_public = 1 or owner = {frappe.db.escape(user)})"


def has_rubric_permission(doc, ptype=None, user=None) -> bool:
	if not user:
		user = frappe.session.user
	if "System Manager" in frappe.get_roles(user) or "Moderator" in frappe.get_roles(user):
		return True
	
	if ptype == "read":
		return doc.is_public == 1 or doc.owner == user
	
	# For write/delete/create, only the owner can modify their rubrics
	return doc.owner == user


def get_library_permission_query_conditions(user) -> str:
	if not user:
		user = frappe.session.user
	if "System Manager" in frappe.get_roles(user) or "Moderator" in frappe.get_roles(user):
		return ""
	
	escaped_user = frappe.db.escape(user)
	return f"""(
		owner = {escaped_user}
		or (
			shared = 1
			and (
				not exists (
					select 1 from `tabCourse Instructor`
					where parent = `tabContent Library`.name
					and parenttype = 'Content Library'
				)
				or exists (
					select 1 from `tabCourse Instructor`
					where parent = `tabContent Library`.name
					and parenttype = 'Content Library'
					and instructor = {escaped_user}
				)
			)
		)
	)"""


def has_library_permission(doc, ptype=None, user=None) -> bool:
	if not user:
		user = frappe.session.user
	if "System Manager" in frappe.get_roles(user) or "Moderator" in frappe.get_roles(user):
		return True

	if ptype == "create":
		return True

	if doc.owner == user:
		return True

	if ptype == "read":
		if not doc.shared:
			return False
		instructors = [d.instructor for d in doc.get("shared_instructors") or []]
		return not instructors or user in instructors

	if ptype in ("write", "delete"):
		if doc.shared:
			instructors = [d.instructor for d in doc.get("shared_instructors") or []]
			if instructors and user in instructors:
				return True
		return False

	return False


def _assign_for_submission(submission, assignment):
	if not assignment.enable_peer_review:
		return

	existing_count = frappe.db.count("Peer Review Assignment", {"submission": submission.name, "status": ["!=", "Cancelled"]})
	needed = (assignment.reviews_required or 3) - existing_count
	if needed <= 0:
		return

	course = assignment.course
	member = submission.member

	enrolled_students = frappe.get_all("LMS Enrollment", {"course": course}, pluck="member")

	reviewer_pool = []
	if assignment.reviewer_assignment_method == "Group-Based":
		batches = frappe.get_all("Batch Course", {"course": course}, pluck="parent")
		if batches:
			member_batch = frappe.db.get_value("LMS Batch Enrollment", {"member": member, "batch": ["in", batches]}, "batch")
			if member_batch:
				reviewer_pool = frappe.get_all("LMS Batch Enrollment", {"batch": member_batch}, pluck="member")

	if not reviewer_pool:
		reviewer_pool = enrolled_students

	reviewer_pool = [r for r in reviewer_pool if r != member]

	already_assigned = frappe.get_all("Peer Review Assignment", {"submission": submission.name, "status": ["!=", "Cancelled"]}, pluck="reviewer")
	reviewer_pool = [r for r in reviewer_pool if r not in already_assigned]

	if not reviewer_pool:
		return

	assigned_counts = {}
	for r in reviewer_pool:
		assigned_counts[r] = frappe.db.count("Peer Review Assignment", {"reviewer": r, "assignment": assignment.name})

	reviewer_pool.sort(key=lambda r: assigned_counts.get(r, 0))

	selected_reviewers = reviewer_pool[:needed]

	for reviewer in selected_reviewers:
		pr_asg = frappe.new_doc("Peer Review Assignment")
		pr_asg.update({
			"assignment": assignment.name,
			"submission": submission.name,
			"reviewer": reviewer,
			"reviewee": member,
			"status": "Pending",
			"due_date": frappe.utils.add_days(frappe.utils.nowdate(), 7)
		})
		pr_asg.insert(ignore_permissions=True)


@frappe.whitelist()
def assign_peer_reviewers_for_submission(submission_name):
	sub_doc = frappe.get_doc("LMS Assignment Submission", submission_name)
	assignment_doc = frappe.get_doc("LMS Assignment", sub_doc.assignment)
	_assign_for_submission(sub_doc, assignment_doc)


@frappe.whitelist()
def assign_peer_reviewers(submission_name=None, assignment_name=None):
	from lms.lms.utils import has_moderator_role, has_evaluator_role, has_course_instructor_role
	user = frappe.session.user

	if submission_name:
		sub_doc = frappe.get_doc("LMS Assignment Submission", submission_name)
		asg_doc = frappe.get_doc("LMS Assignment", sub_doc.assignment)
		if not (has_moderator_role() or has_evaluator_role() or has_course_instructor_role()):
			frappe.throw(_("Not authorized to assign peer reviewers."), frappe.PermissionError)
		_assign_for_submission(sub_doc, asg_doc)
		return "Success"

	elif assignment_name:
		asg_doc = frappe.get_doc("LMS Assignment", assignment_name)
		if not (has_moderator_role() or has_evaluator_role() or has_course_instructor_role()):
			frappe.throw(_("Not authorized to assign peer reviewers."), frappe.PermissionError)
		submissions = frappe.get_all("LMS Assignment Submission", {"assignment": assignment_name})
		for sub in submissions:
			sub_doc = frappe.get_doc("LMS Assignment Submission", sub.name)
			_assign_for_submission(sub_doc, asg_doc)
		return "Success"


@frappe.whitelist()
def submit_peer_review(
	assignment_id,
	score,
	strengths=None,
	areas_for_improvement=None,
	recommendations=None,
	general_feedback=None,
	criteria_feedback=None
):
	asg_doc = frappe.get_doc("Peer Review Assignment", assignment_id)
	if asg_doc.reviewer != frappe.session.user:
		frappe.throw(_("You are not authorized to submit this peer review."), frappe.PermissionError)

	if asg_doc.status == "Completed":
		frappe.throw(_("This review has already been submitted."))

	if isinstance(criteria_feedback, str):
		criteria_feedback = json.loads(criteria_feedback)

	sub_doc = frappe.new_doc("Peer Review Submission")
	sub_doc.update({
		"review_assignment": assignment_id,
		"reviewer": frappe.session.user,
		"submission": asg_doc.submission,
		"score": flt(score),
		"strengths": strengths,
		"areas_for_improvement": areas_for_improvement,
		"recommendations": recommendations,
		"general_feedback": general_feedback
	})

	for cf in (criteria_feedback or []):
		sub_doc.append("criteria_feedback", {
			"criterion": cf.get("criterion"),
			"score": flt(cf.get("score")),
			"comments": cf.get("comments")
		})

	sub_doc.insert(ignore_permissions=True)

	asg_doc.status = "Completed"
	asg_doc.save(ignore_permissions=True)

	recalculate_assignment_submission_score(asg_doc.submission)

	return sub_doc.name


def recalculate_assignment_submission_score(submission_name):
	sub_doc = frappe.get_doc("LMS Assignment Submission", submission_name)
	assignment_doc = frappe.get_doc("LMS Assignment", sub_doc.assignment)

	if sub_doc.peer_review_overridden:
		sub_doc.is_peer_reviewed = 1
		sub_doc.save(ignore_permissions=True)
		return

	reviews = frappe.get_all(
		"Peer Review Submission",
		{"submission": submission_name},
		["score"]
	)

	if not reviews:
		sub_doc.peer_review_score = 0
		sub_doc.is_peer_reviewed = 0
		sub_doc.save(ignore_permissions=True)
		return

	scores = [r.score for r in reviews]
	agg_method = assignment_doc.grade_aggregation_method or "Average"

	if agg_method == "Average":
		final_score = sum(scores) / len(scores)
	elif agg_method == "Median":
		sorted_scores = sorted(scores)
		n = len(sorted_scores)
		if n % 2 == 1:
			final_score = sorted_scores[n // 2]
		else:
			final_score = (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2.0
	elif agg_method == "Weighted":
		final_score = sum(scores) / len(scores)
	else:
		final_score = sum(scores) / len(scores)

	sub_doc.peer_review_score = final_score
	sub_doc.is_peer_reviewed = 1

	sub_doc.score = int(final_score)
	sub_doc.status = "Pass" if final_score >= 50 else "Fail"

	sub_doc.save(ignore_permissions=True)


@frappe.whitelist()
def override_peer_review_score(submission_name, score):
	sub_doc = frappe.get_doc("LMS Assignment Submission", submission_name)
	asg_doc = frappe.get_doc("LMS Assignment", sub_doc.assignment)
	from lms.lms.utils import has_moderator_role, has_evaluator_role, has_course_instructor_role
	if not (has_moderator_role() or has_evaluator_role() or has_course_instructor_role()):
		frappe.throw(_("Not authorized to override score."), frappe.PermissionError)

	sub_doc.peer_review_override_score = flt(score)
	sub_doc.peer_review_overridden = 1
	sub_doc.score = int(score)
	sub_doc.status = "Pass" if score >= 50 else "Fail"
	sub_doc.save(ignore_permissions=True)
	return "Success"


@frappe.whitelist()
def remove_peer_review(review_name):
	review_doc = frappe.get_doc("Peer Review Submission", review_name)
	submission_name = review_doc.submission
	asg_name = review_doc.review_assignment

	sub_doc = frappe.get_doc("LMS Assignment Submission", submission_name)
	asg_doc = frappe.get_doc("LMS Assignment", sub_doc.assignment)
	from lms.lms.utils import has_moderator_role, has_evaluator_role, has_course_instructor_role
	if not (has_moderator_role() or has_evaluator_role() or has_course_instructor_role()):
		frappe.throw(_("Not authorized to remove review."), frappe.PermissionError)

	frappe.delete_doc("Peer Review Submission", review_name, force=True)

	if frappe.db.exists("Peer Review Assignment", asg_name):
		frappe.db.set_value("Peer Review Assignment", asg_name, "status", "Pending")

	recalculate_assignment_submission_score(submission_name)
	return "Success"


@frappe.whitelist()
def request_peer_review_revision(review_assignment_name):
	asg_doc = frappe.get_doc("Peer Review Assignment", review_assignment_name)
	sub_doc = frappe.get_doc("LMS Assignment Submission", asg_doc.submission)
	asg_meta_doc = frappe.get_doc("LMS Assignment", sub_doc.assignment)
	from lms.lms.utils import has_moderator_role, has_evaluator_role, has_course_instructor_role
	if not (has_moderator_role() or has_evaluator_role() or has_course_instructor_role()):
		frappe.throw(_("Not authorized to request review revision."), frappe.PermissionError)

	existing_sub = frappe.db.get_value("Peer Review Submission", {"review_assignment": review_assignment_name}, "name")
	if existing_sub:
		frappe.delete_doc("Peer Review Submission", existing_sub, force=True)

	asg_doc.status = "Pending"
	asg_doc.save(ignore_permissions=True)

	from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
	notification = frappe._dict({
		"subject": _("Instructor has requested a revision on your peer review for {0}").format(
			frappe.bold(asg_meta_doc.title)
		),
		"document_type": "Peer Review Assignment",
		"document_name": asg_doc.name,
		"from_user": frappe.session.user,
		"type": "Alert",
		"link": get_lms_route(f"assignment-submission/{asg_meta_doc.name}/{asg_doc.submission}")
	})
	make_notification_logs(notification, [asg_doc.reviewer])

	recalculate_assignment_submission_score(asg_doc.submission)
	return "Success"


@frappe.whitelist()
def get_assigned_peer_reviews(user=None) -> list:
	if not user:
		user = frappe.session.user

	assignments = frappe.get_all(
		"Peer Review Assignment",
		filters={"reviewer": user},
		fields=["name", "assignment", "submission", "reviewee", "status", "due_date"]
	)

	for asg in assignments:
		asg.assignment_title = frappe.db.get_value("LMS Assignment", asg.assignment, "title")
		asg.reviewee_name = frappe.db.get_value("User", asg.reviewee, "full_name")

		if asg.status == "Completed":
			asg.review_submission = frappe.db.get_value(
				"Peer Review Submission",
				{"review_assignment": asg.name},
				["name", "score"],
				as_dict=True
			)

	return assignments


@frappe.whitelist()
def get_peer_reviews_for_submission(submission_name) -> list:
	sub_doc = frappe.get_doc("LMS Assignment Submission", submission_name)
	assignment_doc = frappe.get_doc("LMS Assignment", sub_doc.assignment)

	is_instructor = False
	from lms.lms.utils import has_moderator_role, has_evaluator_role, has_course_instructor_role
	if has_moderator_role() or has_evaluator_role() or has_course_instructor_role():
		is_instructor = True

	reviews = frappe.get_all(
		"Peer Review Submission",
		filters={"submission": submission_name},
		fields=["name", "reviewer", "score", "strengths", "areas_for_improvement", "recommendations", "general_feedback", "review_assignment"]
	)

	idx = 1
	for r in reviews:
		r.criteria_feedback = frappe.get_all(
			"Peer Review Submission Criterion",
			filters={"parent": r.name},
			fields=["criterion", "score", "comments"]
		)

		if assignment_doc.anonymous_reviews and not is_instructor and r.reviewer != frappe.session.user:
			r.reviewer_name = f"Reviewer #{idx}"
			r.reviewer = ""
		else:
			r.reviewer_name = frappe.db.get_value("User", r.reviewer, "full_name")

		idx += 1

	return reviews


@frappe.whitelist()
def get_reviewer_stats(assignment_name) -> list:
	asg_doc = frappe.get_doc("LMS Assignment", assignment_name)
	from lms.lms.utils import has_moderator_role, has_evaluator_role, has_course_instructor_role
	if not (has_moderator_role() or has_evaluator_role() or has_course_instructor_role()):
		frappe.throw(_("Not authorized to view reviewer statistics."), frappe.PermissionError)

	all_assignments = frappe.get_all(
		"Peer Review Assignment",
		filters={"assignment": assignment_name},
		fields=["name", "reviewer", "status", "due_date", "submission"]
	)

	stats = {}
	for a in all_assignments:
		rev = a.reviewer
		if rev not in stats:
			stats[rev] = {
				"reviewer": rev,
				"reviewer_name": frappe.db.get_value("User", rev, "full_name"),
				"assigned": 0,
				"completed": 0,
				"pending": 0,
				"timely": 0,
				"late": 0,
				"total_comment_length": 0,
				"reviews": []
			}

		s = stats[rev]
		s["assigned"] += 1

		if a.status == "Completed":
			s["completed"] += 1
			rev_sub = frappe.get_all(
				"Peer Review Submission",
				filters={"review_assignment": a.name},
				fields=["name", "creation", "score", "general_feedback", "strengths", "areas_for_improvement", "recommendations"]
			)
			if rev_sub:
				sub = rev_sub[0]
				s["reviews"].append(sub)

				if a.due_date and sub.creation.date() <= a.due_date:
					s["timely"] += 1
				else:
					s["late"] += 1

				comment_text = (sub.general_feedback or "") + (sub.strengths or "") + (sub.areas_for_improvement or "") + (sub.recommendations or "")
				s["total_comment_length"] += len(comment_text)
		else:
			s["pending"] += 1

	sub_averages = {}
	subs = frappe.get_all("Peer Review Submission", filters={"submission": ["in", [a.submission for a in all_assignments]]}, fields=["submission", "score"])
	for sub in subs:
		if sub.submission not in sub_averages:
			sub_averages[sub.submission] = []
		sub_averages[sub.submission].append(sub.score)

	for k, v in sub_averages.items():
		sub_averages[k] = sum(v) / len(v) if v else 0

	result = []
	for rev, s in stats.items():
		deviations = []
		completed_assignments = [a for a in all_assignments if a.reviewer == rev and a.status == "Completed"]
		for a in completed_assignments:
			rev_sub_score = frappe.db.get_value("Peer Review Submission", {"review_assignment": a.name}, "score")
			avg_score = sub_averages.get(a.submission, 0)
			if rev_sub_score is not None:
				deviations.append(abs(rev_sub_score - avg_score))

		s["avg_deviation"] = sum(deviations) / len(deviations) if deviations else 0
		s["completion_rate"] = (s["completed"] / s["assigned"] * 100) if s["assigned"] > 0 else 0
		s["avg_comment_length"] = (s["total_comment_length"] / s["completed"]) if s["completed"] > 0 else 0
		result.append(s)

	return result


@frappe.whitelist()
def get_content_usage_info(content_doctype: str) -> dict:
	import json

	items = frappe.get_all(content_doctype, fields=["name", "owner"])

	users = frappe.get_all("User", fields=["name", "full_name", "first_name", "username"])
	user_names = {}
	for u in users:
		val = u.get("full_name") or u.get("first_name") or u.get("username") or u.get("name")
		user_names[u.get("name")] = val

	if content_doctype == "Peer Review Rubric":
		usage_info = {}
		for item in items:
			item_name = item.get("name")
			item_owner = item.get("owner")
			usage_info[item_name] = {
				"created_by": user_names.get(item_owner) or item_owner or "",
				"assignments": []
			}
		assignments = frappe.get_all(
			"LMS Assignment",
			filters={"peer_review_rubric": ["is", "set"]},
			fields=["name", "title", "peer_review_rubric"]
		)
		for assignment in assignments:
			rubric_name = assignment.get("peer_review_rubric")
			if rubric_name in usage_info:
				assignment_title = assignment.get("title") or assignment.get("name")
				if assignment_title not in usage_info[rubric_name]["assignments"]:
					usage_info[rubric_name]["assignments"].append(assignment_title)
		return usage_info

	links = frappe.get_all(
		"Course Content Link",
		filters={"content_doctype": content_doctype},
		fields=["content_name", "course"]
	)

	courses = frappe.get_all("LMS Course", fields=["name", "title"])
	course_titles = {c.get("name"): c.get("title") for c in courses}

	old_refs = []
	
	# 1. Check legacy/field-based references in Course Lesson
	if content_doctype == "LMS Quiz":
		lessons = frappe.get_all("Course Lesson", filters={"quiz_id": ["is", "set"]}, fields=["quiz_id", "course"])
		for lesson in lessons:
			quiz_id = lesson.get("quiz_id")
			course = lesson.get("course")
			if quiz_id and course:
				for q_id in [q.strip() for q in quiz_id.split(",") if q.strip()]:
					old_refs.append({"content_name": q_id, "course": course})
	elif content_doctype == "LMS Assignment":
		lessons = frappe.get_all("Course Lesson", filters={"question": ["is", "set"]}, fields=["question", "course"])
		for lesson in lessons:
			question = lesson.get("question")
			course = lesson.get("course")
			if question and course:
				old_refs.append({"content_name": question, "course": course})

	# 2. Check Gutenberg/Editor block-based references in Course Lesson
	lessons_with_content = frappe.get_all("Course Lesson", filters={"content": ["is", "set"]}, fields=["content", "course"])
	for lesson in lessons_with_content:
		content_str = lesson.get("content")
		course = lesson.get("course")
		if content_str and course:
			try:
				content_data = json.loads(content_str)
				for block in content_data.get("blocks", []):
					btype = block.get("type")
					bdata = block.get("data", {})
					if content_doctype == "LMS Quiz" and btype == "quiz":
						qid = bdata.get("quiz")
						if qid:
							old_refs.append({"content_name": qid, "course": course})
					elif content_doctype == "LMS Assignment" and btype == "assignment":
						aid = bdata.get("assignment")
						if aid:
							old_refs.append({"content_name": aid, "course": course})
					elif content_doctype == "LMS Programming Exercise" and btype == "program":
						eid = bdata.get("exercise")
						if eid:
							old_refs.append({"content_name": eid, "course": course})
			except Exception:
				pass

	all_links = links + old_refs

	usage_info = {}
	for item in items:
		item_name = item.get("name")
		item_owner = item.get("owner")
		usage_info[item_name] = {
			"created_by": user_names.get(item_owner) or item_owner or "",
			"courses": []
		}

	for link in all_links:
		c_name = link.get("content_name")
		c_course = link.get("course")
		if c_name in usage_info:
			course_title = course_titles.get(c_course) or c_course
			if course_title not in usage_info[c_name]["courses"]:
				usage_info[c_name]["courses"].append(course_title)

	return usage_info

