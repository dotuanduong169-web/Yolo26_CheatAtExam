"""Gói CRUD truy vấn DB. Re-export để import gọn từ crud."""

from crud.user_crud import (
    admin_update_user,
    create_user,
    get_user_by_id,
    get_user_by_username,
    list_users,
    update_user_password,
    update_user_profile,
)

from crud.device_crud import (
    create_device,
    delete_device,
    get_device_by_id,
    list_devices,
    update_device,
)

from crud.session_crud import (
    create_session,
    delete_session_cascade,
    end_session,
    get_monthly_session_count_by_user,
    get_session_by_id,
    get_session_count_by_user,
    get_sessions_by_user,
    get_sessions_with_event_count,
)

from crud.event_crud import (
    count_events_by_session,
    count_pending_by_session,
    create_event,
    create_evidence,
    get_event_by_id,
    list_events_by_session,
    verify_event,
)

from crud.statistics_crud import (
    create_statistics,
    get_stats_by_session,
)

__all__ = [
    "admin_update_user",
    "create_user",
    "get_user_by_id",
    "get_user_by_username",
    "list_users",
    "update_user_password",
    "update_user_profile",
    "create_device",
    "delete_device",
    "get_device_by_id",
    "list_devices",
    "update_device",
    "create_session",
    "delete_session_cascade",
    "end_session",
    "get_monthly_session_count_by_user",
    "get_session_by_id",
    "get_session_count_by_user",
    "get_sessions_by_user",
    "get_sessions_with_event_count",
    "count_events_by_session",
    "count_pending_by_session",
    "create_event",
    "create_evidence",
    "get_event_by_id",
    "list_events_by_session",
    "verify_event",
    "create_statistics",
    "get_stats_by_session",
]
