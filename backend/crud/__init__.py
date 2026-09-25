"""
CRUD package — database access functions.

Re-exports all CRUD operations for convenient imports::

    from crud import create_user, get_session_by_id
"""

from crud.user_crud import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_password,
    update_user_profile,
)

from crud.session_crud import (
    create_session,
    delete_session_cascade,
    end_session,
    get_monthly_session_count_by_user,
    get_session_by_id,
    get_session_count_by_user,
    get_sessions_by_user,
    get_sessions_with_frame_count,
)

from crud.frame_crud import (
    create_frame,
    get_frame_by_id,
    get_frames_by_session,
)

from crud.ai_result_crud import (
    create_ai_result,
    get_ai_results_by_frame,
    get_ai_results_by_frames,
    update_ai_result_label,
)

from crud.statistics_crud import (
    create_statistics,
    get_stats_by_session,
    recalculate_statistics_for_frame,
)

__all__ = [
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "update_user_password",
    "update_user_profile",
    "create_session",
    "delete_session_cascade",
    "end_session",
    "get_monthly_session_count_by_user",
    "get_session_by_id",
    "get_session_count_by_user",
    "get_sessions_by_user",
    "get_sessions_with_frame_count",
    "create_frame",
    "get_frame_by_id",
    "get_frames_by_session",
    "create_ai_result",
    "get_ai_results_by_frame",
    "get_ai_results_by_frames",
    "update_ai_result_label",
    "create_statistics",
    "get_stats_by_session",
    "recalculate_statistics_for_frame",
]
