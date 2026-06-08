# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from lms.lms.utils import has_course_instructor_role, has_moderator_role


class LMSAssignment(Document):
	def validate(self):
		self.validate_grading_category()

	def validate_grading_category(self):
		if self.course:
			course_doc = frappe.get_doc("LMS Course", self.course)
			if getattr(course_doc, "enable_grading_policy", False):
				if not self.grading_category:
					frappe.throw(
						frappe._("Grading Category is required because Grading Policy is enabled in Course {0}.").format(self.course)
					)
				# Find this category in the course grading categories
				cat_settings = None
				for cat in getattr(course_doc, "grading_categories", []):
					if cat.category_name == self.grading_category:
						cat_settings = cat
						break

				if cat_settings:
					limit = getattr(cat_settings, "number_of_assessments", 0) or 0
					if limit > 0:
						# Count current quizzes in this category
						quiz_count = frappe.db.count("LMS Quiz", {
							"course": self.course,
							"grading_category": self.grading_category
						})
						# Count current assignments in this category (excluding this one)
						assignment_count = frappe.db.count("LMS Assignment", {
							"course": self.course,
							"grading_category": self.grading_category,
							"name": ["!=", self.name]
						})
						if (quiz_count + assignment_count) >= limit:
							frappe.throw(
								frappe._("The category '{0}' has reached its limit of {1} assessment(s) in Course {2}.").format(
									self.grading_category, limit, self.course
								)
							)
				else:
					frappe.throw(
						frappe._("The grading category '{0}' is not defined in Course {1}.").format(
							self.grading_category, self.course
						)
					)
