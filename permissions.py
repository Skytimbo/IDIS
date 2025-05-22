"""
Permissions Model Module for Intelligent Document Insight System (IDIS)

This module provides the PermissionsManager class which handles role-based access control
for IDIS, determining which roles can access resources with different privacy levels.
"""

import json
import logging
from typing import Dict, List, Optional, Any


# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class PermissionsConfigError(Exception):
    """Custom exception for permissions configuration errors."""
    pass


class PermissionsManager:
    """
    Manages role-based permissions for accessing resources with different privacy levels.
    
    The PermissionsManager loads permissions rules from a JSON configuration file
    and provides methods to check if a user with a specific role is allowed to
    perform an action on a resource with a given privacy level.
    """
    
    def __init__(self, rules_file_path: str):
        """
        Initialize the Permissions Manager with the path to the rules file.
        
        Args:
            rules_file_path: Path to the JSON file containing permission rules
            
        Raises:
            FileNotFoundError: If the rules file doesn't exist
            PermissionsConfigError: If the rules file contains invalid JSON or is missing required fields
        """
        self.logger = logging.getLogger('PermissionsManager')
        self.rules_file_path = rules_file_path
        self.rules = self._load_rules(rules_file_path)
        
        # Validate that required sections exist in the rules
        required_sections = ['roles', 'privacy_levels', 'actions']
        for section in required_sections:
            if section not in self.rules:
                error_msg = f"Missing required section '{section}' in permissions rules"
                self.logger.error(error_msg)
                raise PermissionsConfigError(error_msg)
    
    def _load_rules(self, rules_file_path: str) -> Dict[str, Any]:
        """
        Load and parse the JSON rules file.
        
        Args:
            rules_file_path: Path to the JSON file containing permission rules
            
        Returns:
            Parsed rules as a dictionary
            
        Raises:
            FileNotFoundError: If the rules file doesn't exist
            PermissionsConfigError: If the rules file contains invalid JSON
        """
        try:
            with open(rules_file_path, 'r') as file:
                try:
                    rules = json.load(file)
                    self.logger.info(f"Successfully loaded permissions rules from {rules_file_path}")
                    return rules
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON in permissions rules file: {e}"
                    self.logger.error(error_msg)
                    raise PermissionsConfigError(error_msg) from e
        except FileNotFoundError:
            error_msg = f"Permissions rules file not found: {rules_file_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
    
    def can_user_perform_action(self, user_role: str, action: str, resource_privacy_level: str) -> bool:
        """
        Check if a user with the given role can perform the specified action on a resource
        with the given privacy level.
        
        Args:
            user_role: The role of the user (e.g., "admin", "editor", "viewer")
            action: The action to perform (e.g., "read", "write", "delete")
            resource_privacy_level: The privacy level of the resource
                                    (e.g., "Highly Confidential", "Confidential", "General")
            
        Returns:
            True if the user can perform the action, False otherwise
        """
        # Check if the user role exists
        if user_role not in self.rules['roles']:
            self.logger.warning(f"Undefined user role: {user_role}")
            return False
        
        # Check if the action is defined
        if action not in self.rules['actions']:
            self.logger.warning(f"Undefined action: {action}")
            return False
        
        # Check if the privacy level is defined
        if resource_privacy_level not in self.rules['privacy_levels']:
            self.logger.warning(f"Undefined privacy level: {resource_privacy_level}")
            return False
        
        # Get the permission rules for the user role
        role_permissions = self.rules['roles'][user_role]['permissions']
        
        # Check if the user has permission to perform the action on a resource with the given privacy level
        for permission in role_permissions:
            if permission['action'] == action and resource_privacy_level in permission['resource_privacy']:
                self.logger.debug(f"Permission granted: role={user_role}, action={action}, privacy={resource_privacy_level}")
                return True
        
        self.logger.debug(f"Permission denied: role={user_role}, action={action}, privacy={resource_privacy_level}")
        return False
    
    def get_defined_roles(self) -> List[str]:
        """
        Get a list of all defined user roles.
        
        Returns:
            List of role names
        """
        return list(self.rules['roles'].keys())
    
    def get_defined_privacy_levels(self) -> List[str]:
        """
        Get a list of all defined privacy levels.
        
        Returns:
            List of privacy level names
        """
        return self.rules['privacy_levels']
    
    def get_defined_actions(self) -> List[str]:
        """
        Get a list of all defined actions.
        
        Returns:
            List of action names
        """
        return self.rules['actions']