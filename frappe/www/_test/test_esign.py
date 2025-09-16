import unittest
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.www.esign import get_signature_fields, validate_signature_permission
from unittest.mock import patch, MagicMock


class TestESign(FrappeTestCase):
	"""Test E-Signature functionality"""

	def setUp(self):
		self.test_doctype = "Test DocType"
		self.test_doc_name = "TEST-001"

	def test_get_signature_fields_non_submittable(self):
		"""Test signature field detection for non-submittable documents"""
		# Mock document and meta
		mock_doc = MagicMock()
		mock_doc.get.return_value = None  # Empty signature field
		
		mock_meta = MagicMock()
		mock_meta.is_submittable = False
		
		# Mock signature field
		mock_field = MagicMock()
		mock_field.fieldtype = "Signature"
		mock_field.fieldname = "test_signature"
		mock_field.label = "Test Signature"
		mock_field.description = "Test description"
		
		mock_meta.fields = [mock_field]
		
		result = get_signature_fields(mock_doc, mock_meta)
		
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["fieldname"], "test_signature")
		self.assertEqual(result[0]["label"], "Test Signature")

	def test_get_signature_fields_submittable_with_allow_on_submit(self):
		"""Test signature field detection for submittable documents with allow_on_submit"""
		# Mock document and meta
		mock_doc = MagicMock()
		mock_doc.get.return_value = None  # Empty signature field
		
		mock_meta = MagicMock()
		mock_meta.is_submittable = True
		
		# Mock signature field with allow_on_submit
		mock_field = MagicMock()
		mock_field.fieldtype = "Signature"
		mock_field.fieldname = "test_signature"
		mock_field.label = "Test Signature"
		mock_field.description = "Test description"
		mock_field.allow_on_submit = True
		
		mock_meta.fields = [mock_field]
		
		result = get_signature_fields(mock_doc, mock_meta)
		
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["fieldname"], "test_signature")

	def test_get_signature_fields_submittable_without_allow_on_submit(self):
		"""Test signature field detection for submittable documents without allow_on_submit"""
		# Mock document and meta
		mock_doc = MagicMock()
		mock_doc.get.return_value = None  # Empty signature field
		
		mock_meta = MagicMock()
		mock_meta.is_submittable = True
		
		# Mock signature field without allow_on_submit
		mock_field = MagicMock()
		mock_field.fieldtype = "Signature"
		mock_field.fieldname = "test_signature"
		mock_field.label = "Test Signature"
		mock_field.description = "Test description"
		mock_field.allow_on_submit = False
		
		mock_meta.fields = [mock_field]
		
		result = get_signature_fields(mock_doc, mock_meta)
		
		self.assertEqual(len(result), 0)

	def test_get_signature_fields_with_existing_signature(self):
		"""Test that fields with existing signatures are not included"""
		# Mock document and meta
		mock_doc = MagicMock()
		mock_doc.get.return_value = "existing_signature_data"  # Has signature
		
		mock_meta = MagicMock()
		mock_meta.is_submittable = False
		
		# Mock signature field
		mock_field = MagicMock()
		mock_field.fieldtype = "Signature"
		mock_field.fieldname = "test_signature"
		mock_field.label = "Test Signature"
		
		mock_meta.fields = [mock_field]
		
		result = get_signature_fields(mock_doc, mock_meta)
		
		self.assertEqual(len(result), 0)

	def test_get_signature_fields_non_signature_fields(self):
		"""Test that non-signature fields are not included"""
		# Mock document and meta
		mock_doc = MagicMock()
		mock_doc.get.return_value = None
		
		mock_meta = MagicMock()
		mock_meta.is_submittable = False
		
		# Mock non-signature field
		mock_field = MagicMock()
		mock_field.fieldtype = "Data"
		mock_field.fieldname = "test_data"
		
		mock_meta.fields = [mock_field]
		
		result = get_signature_fields(mock_doc, mock_meta)
		
		self.assertEqual(len(result), 0)

	@patch('frappe.www.esign.validate_print_permission')
	def test_validate_signature_permission_with_print_permission(self, mock_validate_print):
		"""Test signature permission validation with valid print permission"""
		mock_doc = MagicMock()
		mock_validate_print.return_value = None  # No exception = valid permission
		
		# Should not raise exception
		validate_signature_permission(mock_doc, None)
		mock_validate_print.assert_called_once_with(mock_doc)

	@patch('frappe.www.esign.validate_print_permission')
	@patch('frappe.www.esign.validate_key')
	def test_validate_signature_permission_with_valid_key(self, mock_validate_key, mock_validate_print):
		"""Test signature permission validation with valid key when print permission fails"""
		mock_doc = MagicMock()
		mock_validate_print.side_effect = Exception("Permission denied")
		mock_validate_key.return_value = True  # Valid key
		
		# Should not raise exception
		validate_signature_permission(mock_doc, "valid_key")
		mock_validate_key.assert_called_once_with("valid_key", mock_doc)

	@patch('frappe.www.esign.validate_print_permission')
	@patch('frappe.throw')
	def test_validate_signature_permission_no_key(self, mock_throw, mock_validate_print):
		"""Test signature permission validation fails without key"""
		mock_doc = MagicMock()
		mock_validate_print.side_effect = Exception("Permission denied")
		
		validate_signature_permission(mock_doc, None)
		
		mock_throw.assert_called_once()

	@patch('frappe.www.esign.validate_print_permission')
	@patch('frappe.www.esign.validate_key')
	@patch('frappe.throw')
	def test_validate_signature_permission_invalid_key(self, mock_throw, mock_validate_key, mock_validate_print):
		"""Test signature permission validation fails with invalid key"""
		mock_doc = MagicMock()
		mock_validate_print.side_effect = Exception("Permission denied")
		mock_validate_key.return_value = False  # Invalid key
		
		validate_signature_permission(mock_doc, "invalid_key")
		
		mock_throw.assert_called_once()


if __name__ == "__main__":
	unittest.main()