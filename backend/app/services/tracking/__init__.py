"""Modular face/speaker tracking. Renderer uses the Tracker interface only."""
from app.services.tracking.base import Tracker, TrackResult, get_tracker

__all__ = ["Tracker", "TrackResult", "get_tracker"]
