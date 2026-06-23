# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import json
import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.api import (
	submit_peer_review,
	override_peer_review_score,
	request_peer_review_revision,
	get_assigned_peer_reviews,
	get_peer_reviews_for_submission,
	get_reviewer_stats,
	assign_peer_reviewers
)

class TestPeerReview(BaseTestUtils):
	def setUp(self):
		super().setUp()
		
		# Set up users
		self.student1 = self._create_user("student1@example.com", "Student", "One", ["LMS Student"])
		self.student2 = self._create_user("student2@example.com", "Student", "Two", ["LMS Student"])
		self.student3 = self._create_user("student3@example.com", "Student", "Three", ["LMS Student"])
		self.instructor = self._create_user("instructor@example.com", "Instructor", "User", ["Course Creator"])
		
		# Create Course
		self.course = self._create_course(title="Peer Review Course", instructor=self.instructor.email)
		
		# Enroll students
		self._create_enrollment(self.student1.email, self.course.name)
		self._create_enrollment(self.student2.email, self.course.name)
		self._create_enrollment(self.student3.email, self.course.name)
		
		# Create Rubric
		self.rubric = frappe.new_doc("Peer Review Rubric")
		self.rubric.title = "Research Rubric"
		self.rubric.description = "Rubric for evaluation of research proposal"
		self.rubric.append("criteria", {
			"criterion_name": "Problem Statement",
			"max_score": 20,
			"weight": 2.0,
			"description": "Clear problem statement"
		})
		self.rubric.append("criteria", {
			"criterion_name": "Methodology",
			"max_score": 30,
			"weight": 3.0,
			"description": "Clear methodology"
		})
		self.rubric.save()
		self.cleanup_items.append(("Peer Review Rubric", self.rubric.name))
		
		# Create Assignment
		self.assignment = self._create_assignment(title="Research Proposal")
		self.assignment.course = self.course.name
		self.assignment.enable_peer_review = 1
		self.assignment.peer_review_rubric = self.rubric.name
		self.assignment.reviews_required = 2
		self.assignment.anonymous_reviews = 1
		self.assignment.reviewer_assignment_method = "Random"
		self.assignment.grade_aggregation_method = "Average"
		self.assignment.save()

	def test_peer_review_workflow(self):
		# Student 1 submits the assignment
		submission = frappe.new_doc("LMS Assignment Submission")
		submission.update({
			"assignment": self.assignment.name,
			"member": self.student1.email,
			"answer": "This is student 1's research proposal.",
			"status": "Not Graded"
		})
		submission.insert()
		self.cleanup_items.append(("LMS Assignment Submission", submission.name))
		
		# Trigger reviewer assignment
		frappe.set_user("Administrator")
		assign_peer_reviewers(submission_name=submission.name)
		
		# Verify assignments
		assignments = frappe.get_all(
			"Peer Review Assignment",
			filters={"submission": submission.name},
			fields=["name", "reviewer", "status"]
		)
		
		self.assertEqual(len(assignments), 2)
		reviewers = [a.reviewer for a in assignments]
		self.assertIn(self.student2.email, reviewers)
		self.assertIn(self.student3.email, reviewers)
		
		# Submit review from Student 2
		asg2 = [a for a in assignments if a.reviewer == self.student2.email][0]
		frappe.set_user(self.student2.email)
		
		criteria_feedback = [
			{"criterion": "Problem Statement", "score": 15, "comments": "Good job"},
			{"criterion": "Methodology", "score": 25, "comments": "Methodology is sound"}
		]
		
		# Score out of 100 calculation:
		# ((15/20 * 2) + (25/30 * 3)) / (2 + 3) * 100 = (1.5 + 2.5) / 5 * 100 = 4 / 5 * 100 = 80%
		submit_peer_review(
			assignment_id=asg2.name,
			score=80.0,
			strengths="Good structure",
			areas_for_improvement="Needs more detail",
			recommendations="Refine section 3",
			general_feedback="Overall a strong submission",
			criteria_feedback=json.dumps(criteria_feedback)
		)
		
		# Verify Student 2 assignment status is completed
		asg2_doc = frappe.get_doc("Peer Review Assignment", asg2.name)
		self.assertEqual(asg2_doc.status, "Completed")
		
		# Verify score updated on submission (since only 1 review is completed, avg is 80)
		sub_doc = frappe.get_doc("LMS Assignment Submission", submission.name)
		self.assertEqual(sub_doc.peer_review_score, 80.0)
		self.assertEqual(sub_doc.score, 80)
		self.assertEqual(sub_doc.status, "Pass")
		
		# Submit review from Student 3
		asg3 = [a for a in assignments if a.reviewer == self.student3.email][0]
		frappe.set_user(self.student3.email)
		
		submit_peer_review(
			assignment_id=asg3.name,
			score=90.0,
			strengths="Excellent writing",
			criteria_feedback=[]
		)
		
		# Average score should now be (80 + 90) / 2 = 85
		sub_doc.reload()
		self.assertEqual(sub_doc.peer_review_score, 85.0)
		self.assertEqual(sub_doc.score, 85)
		self.assertEqual(sub_doc.status, "Pass")
		
		# Retrieve reviews for student (anonymous)
		frappe.set_user(self.student1.email)
		student_feedback = get_peer_reviews_for_submission(submission.name)
		self.assertEqual(len(student_feedback), 2)
		# Reviewers names should be masked
		self.assertEqual(student_feedback[0].reviewer_name, "Reviewer #1")
		self.assertEqual(student_feedback[0].reviewer, "")
		
		# Retrieve reviews for instructor (non-anonymous)
		frappe.set_user(self.instructor.email)
		instructor_feedback = get_peer_reviews_for_submission(submission.name)
		self.assertEqual(len(instructor_feedback), 2)
		rev_names = [f.reviewer_name for f in instructor_feedback]
		self.assertIn(self.student2.full_name, rev_names)
		
		# Test Instructor Override
		override_peer_review_score(submission.name, 95.0)
		sub_doc.reload()
		self.assertEqual(sub_doc.peer_review_overridden, 1)
		self.assertEqual(sub_doc.score, 95)
		
		# Test Request Revision
		request_peer_review_revision(asg2.name)
		asg2_doc.reload()
		self.assertEqual(asg2_doc.status, "Pending")

	def test_rubric_visibility_permissions(self):
		# Create a private rubric owned by Instructor
		frappe.set_user(self.instructor.email)
		rubric_private = frappe.new_doc("Peer Review Rubric")
		rubric_private.title = "Private Instructor Rubric"
		rubric_private.is_public = 0
		rubric_private.save()
		self.cleanup_items.append(("Peer Review Rubric", rubric_private.name))
		
		# Create a public rubric owned by Instructor
		rubric_public = frappe.new_doc("Peer Review Rubric")
		rubric_public.title = "Public Instructor Rubric"
		rubric_public.is_public = 1
		rubric_public.save()
		self.cleanup_items.append(("Peer Review Rubric", rubric_public.name))
		
		# Instructor should see both rubrics when getting
		frappe.set_user(self.instructor.email)
		rubrics_inst = frappe.get_list("Peer Review Rubric")
		rubric_names_inst = [r.name for r in rubrics_inst]
		self.assertIn(rubric_private.name, rubric_names_inst)
		self.assertIn(rubric_public.name, rubric_names_inst)
		
		# Student should only see the public rubric, not the private rubric
		frappe.set_user(self.student1.email)
		rubrics_stud = frappe.get_list("Peer Review Rubric")
		rubric_names_stud = [r.name for r in rubrics_stud]
		self.assertNotIn(rubric_private.name, rubric_names_stud)
		self.assertIn(rubric_public.name, rubric_names_stud)
