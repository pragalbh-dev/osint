"""Shared FastAPI dependencies for the route handlers."""

from __future__ import annotations

from fastapi import Request

from chanakya.api.state import AppState


def get_state(request: Request) -> AppState:
    """The one live :class:`AppState`, stashed on ``app.state`` by ``create_app``."""
    state: AppState = request.app.state.chanakya
    return state
