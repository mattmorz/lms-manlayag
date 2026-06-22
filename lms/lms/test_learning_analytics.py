# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import unittest
import frappe
from lms.lms.lms.api import (
	log_learning_activity,
	log_learning_heartbeat,
	get_at_risk_details,
	get_predictive_analytics,
	get_analytics_dashboard,
	update_analytics_cache
)

class TestLearningAnalytics(unittest.TestCase):
	def setUp(self):
		frappe.db.delete("LMS Page View Log")
		frappe.db.delete("LMS Analytics Cache")
		
		# Create test course and enrollments if they don't exist
		self.course_name = "test-analytics-course"
		if not frappe.db.exists("LMS Course", self.course_name):
			course = frappe.new_doc("LMS Course")
			course.title = "Test Analytics Course"
			course.short_introduction = "Intro"
			course.description = "Detailed Description"
			course.published = 1
			course.insert(ignore_permissions=True)
			
		self.student = "Administrator" # Using Administrator as test user session
		frappe.session.user = self.student
		
		if not frappe.db.exists("LMS Enrollment", {"course": self.course_name, "member": self.student}):
			enroll = frappe.new_doc("LMS Enrollment")
			enroll.course = self.course_name
			enroll.member = self.student
			enroll.member_type = "Student"
			enroll.progress = 10.0
			enroll.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.delete("LMS Page View Log")
		frappe.db.delete("LMS Analytics Cache")

	def test_telemetry_and_heartbeats(self):
		# Test initial page view creation
		res = log_learning_activity(self.course_name)
		self.assertEqual(res.get("status"), "success")
		log_name = res.get("name")
		self.assertTrue(frappe.db.exists("LMS Page View Log", log_name))
		
		# Verify initial time spent is 0
		initial_time = frappe.db.get_value("LMS Page View Log", log_name, "time_spent")
		self.assertEqual(initial_time, 0.0)
		
		# Test heartbeat update
		res_hb = log_learning_heartbeat(self.course_name)
		self.assertEqual(res_hb.get("status"), "updated")
		self.assertEqual(res_hb.get("name"), log_name)
		self.assertEqual(res_hb.get("time_spent"), 15.0)
		
		# Verify database state
		db_time = frappe.db.get_value("LMS Page View Log", log_name, "time_spent")
		self.assertEqual(db_time, 15.0)

	def test_at_risk_detection(self):
		# Create fresh activity log to verify low risk classification
		log_learning_activity(self.course_name)
		risk = get_at_risk_details(self.student, self.course_name)
		
		self.assertEqual(risk.get("member"), self.student)
		self.assertEqual(risk.get("course"), self.course_name)
		self.assertIn(risk.get("risk_level"), ["Low Risk", "Medium Risk"]) # Dependent on dates

	def test_predictive_analytics(self):
		pred = get_predictive_analytics(self.student, self.course_name)
		
		self.assertIn("completion_probability", pred)
		self.assertIn("pass_probability", pred)
		self.assertIn("dropout_probability", pred)
		self.assertTrue(len(pred.get("factors_completion")) > 0)

	def test_dashboard_caching(self):
		# Trigger dashboard generation
		data = get_analytics_dashboard("Student", self.student)
		self.assertEqual(data.get("student"), self.student)
		
		# Verify database record exists in cache
		self.assertTrue(frappe.db.exists("LMS Analytics Cache", {"cache_type": "Student", "reference_name": self.student}))
		
		# Trigger update cache job
		update_analytics_cache()
		self.assertTrue(frappe.db.exists("LMS Analytics Cache", {"cache_type": "Administrative", "reference_name": "global"}))
