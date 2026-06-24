# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class PeerReviewRubric(Document):
	def validate(self):
		if not self.is_new():
			# Check if there are assignments referencing this rubric
			assignments = frappe.get_all("LMS Assignment", filters={"peer_review_rubric": self.name}, pluck="name")
			if assignments:
				# Check if those assignments have submissions
				has_submissions = frappe.db.count("LMS Assignment Submission", {"assignment": ["in", assignments]}) > 0
				if has_submissions:
					frappe.throw(frappe._("Cannot modify Rubric because there are already student submissions for assignments using this rubric."))

