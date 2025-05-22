"""
Unit tests for the PermissionsManager class.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# Add the parent directory to sys.path to allow importing from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from permissions import PermissionsManager, PermissionsConfigError


class TestPermissionsManager(unittest.TestCase):
    """Test cases for the PermissionsManager class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary rules file for testing
        self.temp_rules_fd, self.temp_rules_path = tempfile.mkstemp(suffix='.json')
        
        # Sample valid permissions rules for testing
        self.valid_rules = {
            "roles": {
                "admin": {
                    "description": "Full access to all system functions and data.",
                    "permissions": [
                        {"action": "read", "resource_privacy": ["Highly Confidential", "Confidential", "General"]},
                        {"action": "write", "resource_privacy": ["Highly Confidential", "Confidential", "General"]},
                        {"action": "delete", "resource_privacy": ["Highly Confidential", "Confidential", "General"]},
                        {"action": "classify", "resource_privacy": ["Highly Confidential", "Confidential", "General"]},
                        {"action": "summarize", "resource_privacy": ["Highly Confidential", "Confidential", "General"]},
                        {"action": "tag_file", "resource_privacy": ["Highly Confidential", "Confidential", "General"]}
                    ]
                },
                "editor": {
                    "description": "Can read and write general and confidential data, but not highly confidential. Cannot delete.",
                    "permissions": [
                        {"action": "read", "resource_privacy": ["Confidential", "General"]},
                        {"action": "write", "resource_privacy": ["Confidential", "General"]},
                        {"action": "classify", "resource_privacy": ["Confidential", "General"]},
                        {"action": "summarize", "resource_privacy": ["Confidential", "General"]},
                        {"action": "tag_file", "resource_privacy": ["Confidential", "General"]}
                    ]
                },
                "viewer": {
                    "description": "Can only read data with general privacy level.",
                    "permissions": [
                        {"action": "read", "resource_privacy": ["General"]}
                    ]
                }
            },
            "privacy_levels": [
                "Highly Confidential",
                "Confidential",
                "General"
            ],
            "actions": [
                "read",
                "write",
                "delete",
                "classify",
                "summarize",
                "tag_file"
            ]
        }
        
        # Write the valid rules to the temporary file
        with open(self.temp_rules_path, 'w') as f:
            json.dump(self.valid_rules, f)
        
        # Initialize a PermissionsManager with the temporary rules file
        self.permissions_manager = PermissionsManager(self.temp_rules_path)
    
    def tearDown(self):
        """Clean up after each test."""
        # Close and remove the temporary file
        os.close(self.temp_rules_fd)
        os.unlink(self.temp_rules_path)
    
    def test_initialization_success(self):
        """Test successful initialization with a valid rules file."""
        # This is implicitly tested in setUp, so we just verify the manager exists
        self.assertIsNotNone(self.permissions_manager)
        self.assertEqual(self.permissions_manager.rules_file_path, self.temp_rules_path)
    
    def test_initialization_file_not_found(self):
        """Test initialization failure when the rules file is not found."""
        non_existent_path = "/path/to/nonexistent/file.json"
        with self.assertRaises(FileNotFoundError):
            PermissionsManager(non_existent_path)
    
    def test_initialization_invalid_json(self):
        """Test initialization failure when the rules file contains invalid JSON."""
        # Create a temporary file with invalid JSON
        invalid_json_fd, invalid_json_path = tempfile.mkstemp(suffix='.json')
        with open(invalid_json_path, 'w') as f:
            f.write("This is not valid JSON")
        
        try:
            with self.assertRaises(PermissionsConfigError):
                PermissionsManager(invalid_json_path)
        finally:
            # Clean up
            os.close(invalid_json_fd)
            os.unlink(invalid_json_path)
    
    def test_initialization_missing_required_section(self):
        """Test initialization failure when the rules file is missing a required section."""
        # Create a temporary file with rules missing the 'actions' section
        incomplete_rules_fd, incomplete_rules_path = tempfile.mkstemp(suffix='.json')
        incomplete_rules = self.valid_rules.copy()
        del incomplete_rules['actions']
        
        with open(incomplete_rules_path, 'w') as f:
            json.dump(incomplete_rules, f)
        
        try:
            with self.assertRaises(PermissionsConfigError):
                PermissionsManager(incomplete_rules_path)
        finally:
            # Clean up
            os.close(incomplete_rules_fd)
            os.unlink(incomplete_rules_path)
    
    def test_admin_permissions(self):
        """Test permission checks for the admin role."""
        # Admin should have full access
        self.assertTrue(self.permissions_manager.can_user_perform_action("admin", "read", "Highly Confidential"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("admin", "write", "General"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("admin", "delete", "Highly Confidential"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("admin", "classify", "Confidential"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("admin", "summarize", "General"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("admin", "tag_file", "Highly Confidential"))
    
    def test_editor_permissions(self):
        """Test permission checks for the editor role."""
        # Editor can access Confidential and General, but not Highly Confidential
        self.assertTrue(self.permissions_manager.can_user_perform_action("editor", "read", "Confidential"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("editor", "write", "General"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("editor", "classify", "Confidential"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("editor", "summarize", "General"))
        self.assertTrue(self.permissions_manager.can_user_perform_action("editor", "tag_file", "Confidential"))
        
        # Editor cannot access Highly Confidential or delete resources
        self.assertFalse(self.permissions_manager.can_user_perform_action("editor", "read", "Highly Confidential"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("editor", "write", "Highly Confidential"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("editor", "delete", "Confidential"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("editor", "delete", "General"))
    
    def test_viewer_permissions(self):
        """Test permission checks for the viewer role."""
        # Viewer can only read General resources
        self.assertTrue(self.permissions_manager.can_user_perform_action("viewer", "read", "General"))
        
        # Viewer cannot access Confidential or Highly Confidential resources
        self.assertFalse(self.permissions_manager.can_user_perform_action("viewer", "read", "Confidential"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("viewer", "read", "Highly Confidential"))
        
        # Viewer cannot perform other actions
        self.assertFalse(self.permissions_manager.can_user_perform_action("viewer", "write", "General"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("viewer", "delete", "General"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("viewer", "classify", "General"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("viewer", "summarize", "General"))
        self.assertFalse(self.permissions_manager.can_user_perform_action("viewer", "tag_file", "General"))
    
    def test_undefined_role(self):
        """Test permission check with an undefined role."""
        self.assertFalse(self.permissions_manager.can_user_perform_action("guest", "read", "General"))
    
    def test_undefined_action(self):
        """Test permission check with an undefined action."""
        self.assertFalse(self.permissions_manager.can_user_perform_action("admin", "execute", "General"))
    
    def test_undefined_privacy_level(self):
        """Test permission check with an undefined privacy level."""
        self.assertFalse(self.permissions_manager.can_user_perform_action("admin", "read", "Public"))
    
    def test_get_defined_roles(self):
        """Test retrieving the list of defined roles."""
        roles = self.permissions_manager.get_defined_roles()
        self.assertListEqual(sorted(roles), sorted(["admin", "editor", "viewer"]))
    
    def test_get_defined_privacy_levels(self):
        """Test retrieving the list of defined privacy levels."""
        privacy_levels = self.permissions_manager.get_defined_privacy_levels()
        self.assertListEqual(sorted(privacy_levels), sorted(["Highly Confidential", "Confidential", "General"]))
    
    def test_get_defined_actions(self):
        """Test retrieving the list of defined actions."""
        actions = self.permissions_manager.get_defined_actions()
        self.assertListEqual(sorted(actions), sorted(["read", "write", "delete", "classify", "summarize", "tag_file"]))


if __name__ == '__main__':
    unittest.main()