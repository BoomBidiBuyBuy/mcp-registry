from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from storage import Base
from constants import DEFAULT_SYSTEM_PROMPT_MAX_LENGTH


class MCPService(Base):
    __tablename__ = "mcp_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    endpoint: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    requires_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Authorization method used when requires_authorization is True.
    # Allowed values: "Basic" or "Bearer". Empty string when not required.
    method_authorization: Mapped[str] = mapped_column(
        String(32), default="", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    tools: Mapped[list["MCPTool"]] = relationship(
        "MCPTool", cascade="all, delete-orphan", back_populates="service"
    )


class MCPTool(Base):
    __tablename__ = "mcp_tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    service_name: Mapped[str] = mapped_column(
        ForeignKey("mcp_services.service_name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), default="", nullable=False)

    service: Mapped[MCPService] = relationship("MCPService", back_populates="tools")

    # Optional roles that are allowed to use this tool
    roles: Mapped[list["MCPRole"]] = relationship(
        "MCPRole",
        secondary="mcp_tool_roles",
        back_populates="tools",
    )

    __table_args__ = (
        UniqueConstraint("service_name", "name", name="uq_tool_per_service"),
    )


class MCPRole(Base):
    __tablename__ = "mcp_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # Optional long string to set default system prompt for agents using this role
    default_system_prompt: Mapped[str] = mapped_column(
        String(DEFAULT_SYSTEM_PROMPT_MAX_LENGTH), default="", nullable=False
    )

    # Reverse relationships
    tools: Mapped[list["MCPTool"]] = relationship(
        "MCPTool",
        secondary="mcp_tool_roles",
        back_populates="roles",
    )
    users: Mapped[list["MCPUser"]] = relationship("MCPUser", back_populates="role")


class MCPToolRole(Base):
    __tablename__ = "mcp_tool_roles"
    """Association (join) table between MCPTool and MCPRole.

    This model backs the many-to-many relation used by `MCPTool.roles` and
    `MCPRole.tools`. Application code typically manipulates those high-level
    relationships; SQLAlchemy inserts/deletes rows here implicitly. The unique
    constraint prevents duplicate tool-role pairs. CASCADE deletes ensure
    associations are removed if the linked tool or role is deleted.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tool_id: Mapped[int] = mapped_column(
        ForeignKey("mcp_tools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("mcp_roles.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (UniqueConstraint("tool_id", "role_id", name="uq_role_per_tool"),)


class MCPUser(Base):
    __tablename__ = "mcp_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # External/user-provided identifier (e.g., subject, username). Unique for easy lookup.
    user_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # Tokens relationship
    tokens: Mapped[list["UserAccessToken"]] = relationship(
        "UserAccessToken", cascade="all, delete-orphan", back_populates="user"
    )

    # Optional single role for the user
    role_id_fk: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("mcp_roles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role: Mapped["MCPRole | None"] = relationship("MCPRole", back_populates="users")


class UserAccessToken(Base):
    __tablename__ = "user_access_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Reference user by internal pk
    user_id_fk: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mcp_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Reference service by stable service_name to avoid endpoint churn
    service_name: Mapped[str] = mapped_column(
        ForeignKey("mcp_services.service_name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Actual token value
    token: Mapped[str] = mapped_column(String(2048), nullable=False)

    # When token was created/updated
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped[MCPUser] = relationship("MCPUser", back_populates="tokens")
    service: Mapped[MCPService] = relationship("MCPService")

    __table_args__ = (
        # One token per user per service
        UniqueConstraint(
            "user_id_fk", "service_name", name="uq_token_per_user_service"
        ),
    )
