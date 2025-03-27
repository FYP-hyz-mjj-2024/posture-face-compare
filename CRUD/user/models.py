# Basic
import os

# Packages
from sqlalchemy import Column, String, Boolean, DateTime, func, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text
from dotenv import load_dotenv

# Root reference
from database import Base

load_dotenv()

"""
Bitwise permission (from lowest to highest)
0 - Read permission: Permission to read content from database.
1 - Write permission: Permission to write content to database.
2 - Update permission: Permission to update content, including self user profile to database.
3 - Delete permission: Permission to delete content, including self user profile from database.
4 - Reserved
5 - Reserved
6 - Permission to delete users.
7 - Permission to grant user permission. (Super User)
"""
NO_PERMISSIONS = 0
READ = 1 << 0
WRITE = 1 << 1
DELETE = 1 << 2
UPDATE = 1 << 3
RESERVE_1 = 1 << 4
RESERVE_2 = 1 << 5
DELETE_USERS = 1 << 6
GRANT_PERMISSION = 1 << 7


class User(Base):
    """
    User model representing a user in the system.

    Attributes:
        id (UUID): Auto-generated UUID for the user.
        created_at (DateTime): Timestamp of when the user was registered, with timezone information.
        email (String): Unique email address of the user.
        password_hash (String): Hashed password of the user.
        name (String): Username or nickname of the user.
        is_verified (Boolean): Flag indicating whether the user's email has been verified.
        permissions (SmallInteger): Bitwise permissions assigned to the user.
    """

    __tablename__ = "users"

    # Auto-generated Fields
    id = Column(UUID(as_uuid=True),
                primary_key=True,
                default=text("uuid_generate_v4()"),
                server_default=text("uuid_generate_v4()"),
                index=True)

    created_at = Column(DateTime(timezone=True),
                        default=func.now(),
                        server_default=func.now(),
                        nullable=False)

    # Manually-written Fields
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)

    # Verification Fields
    is_verified = Column(Boolean, default=bool(os.getenv("DEFAULT_VERIFIED")))

    permissions = Column(SmallInteger,
                         default=(READ | WRITE | DELETE | UPDATE),
                         nullable=False)

    def check_permission(self, permission: int) -> bool:
        """
        Check if the user have a specific permission.
        :param permission: Permission bit code.
        :return: True if the user has the permission, else false.
        """
        if permission < 0 or permission > 255:
            raise ValueError("Invalid Permission: Permission code must be between 0 and 7.")
        return self.permissions & permission != 0

    def grant_permission(self, permission: int) -> int:
        """
        Grant permission to this user.
        :param permission: Permission to be granted.
        :return: The permission status after granting.
        """
        if permission < 0 or permission > 255:
            raise ValueError("Invalid Permission: Permission code must be between 0 and 7.")

        if permission & (permission - 1) != 0:
            raise ValueError("Multiple Permission: Can only grant one permission at a time.")

        self.permissions |= permission
        return self.permissions

    def revoke_permission(self, permission: int) -> int:
        """
        Revoke permission of this uer.
        :param permission: Permission to be revoked.
        :return: The permission status after revoking.
        """
        if permission < 0 or permission > 255:
            raise ValueError("Invalid Permission: Permission code must be between 0 and 7.")

        if permission & (permission - 1) != 0:
            raise ValueError("Multiple Permission: Can only grant one permission at a time.")

        self.permissions &= ~permission
        return self.permissions


'''
def check_permission(user_permission: int, permission: int) -> bool:
    """
    Check if the user have a specific permission.
    :param user_permission: User current permission.
    :param permission: Test permission.
    :return: True if the user has the permission, else false.
    """
    if permission < 0 or permission > 255:
        raise ValueError("Invalid Permission: Permission code must be between 0 and 7.")
    return user_permission & permission != 0


def add_permission(user_permission: int, permission: int) -> int:
    """
    Grant permission to this user.
    :param user_permission: User current permission.
    :param permission: Permission to be granted.
    :return: The permission status after granting.
    """
    if permission < 0 or permission > 255:
        raise ValueError("Invalid Permission: Permission code must be between 0 and 7.")

    if permission & (permission - 1) != 0:
        raise ValueError("Multiple Permission: Can only grant one permission at a time.")

    user_permission |= permission
    return user_permission


def remove_permission(user_permission: int, permission: int) -> int:
    """
    Revoke permission of this uer.
    :param user_permission: User current permission.
    :param permission: Permission to be revoked.
    :return: The permission status after revoking.
    """
    if permission < 0 or permission > 255:
        raise ValueError("Invalid Permission: Permission code must be between 0 and 7.")

    if permission & (permission - 1) != 0:
        raise ValueError("Multiple Permission: Can only grant one permission at a time.")

    user_permission &= ~permission
    return user_permission
'''