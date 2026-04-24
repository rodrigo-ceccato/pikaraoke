"""Owner management routes for queue control."""

from __future__ import annotations

import json
from urllib.parse import unquote

import flask_babel
from flask import flash, redirect, render_template, request, url_for
from flask_smorest import Blueprint

from pikaraoke.lib.current_app import (
    broadcast_event,
    get_karaoke_instance,
    get_site_name,
)

_ = flask_babel.gettext

manage_bp = Blueprint("manage", __name__)


def _validate_youtube_url(url: str) -> str | None:
    """Validate YouTube URL format. Returns None if invalid."""
    if not url:
        return None
    if "youtube.com/watch?v=" in url or "youtu.be/" in url:
        return url
    return None


@manage_bp.route("/manage")
def manage():
    """Owner queue management page."""
    k = get_karaoke_instance()
    site_name = get_site_name()
    return render_template(
        "manage.html",
        queue=k.queue_manager.queue,
        site_title=site_name,
        title="Manage Queue",
    )


@manage_bp.route("/manage/add", methods=["POST"])
def add_song():
    """Add a song to the queue for a specific user."""
    k = get_karaoke_instance()

    youtube_url = _validate_youtube_url(request.form.get("youtube_url", ""))
    if not youtube_url:
        flash(_("Invalid YouTube URL"), "is-danger")
        return redirect(url_for("manage.manage"))

    username = request.form.get("username", "").strip()
    if not username:
        flash(_("Username is required"), "is-danger")
        return redirect(url_for("manage.manage"))

    semitones = request.form.get("semitones", 0, type=int)
    result = k.queue_manager.enqueue_for_user(youtube_url, username, semitones)

    if result[0]:
        flash(result[1], "is-success")
    else:
        flash(result[1], "is-danger")

    broadcast_event("queue_update")
    return redirect(url_for("manage.manage"))


@manage_bp.route("/manage/clear", methods=["POST"])
def clear_queue_action():
    """Clear all songs from the queue."""
    k = get_karaoke_instance()
    k.queue_manager.queue_clear()
    flash(_("Queue cleared!"), "is-warning")
    broadcast_event("skip", "clear queue")
    return redirect(url_for("manage.manage"))


@manage_bp.route("/manage/reorder", methods=["POST"])
def reorder():
    """Reorder queue items."""
    k = get_karaoke_instance()
    old_index = request.form.get("old_index", type=int)
    new_index = request.form.get("new_index", type=int)

    if old_index is not None and new_index is not None:
        k.queue_manager.reorder(old_index, new_index)

    return redirect(url_for("manage.manage"))


@manage_bp.route("/manage/delete/<path:song>", methods=["POST"])
def delete_song(song):
    """Delete a song from the queue."""
    k = get_karaoke_instance()
    song_path = unquote(song)
    success = k.queue_manager.queue_edit(song_path, "delete")

    if success:
        flash(_("Song removed from queue"), "is-success")
    else:
        flash(_("Error removing song"), "is-danger")

    return redirect(url_for("manage.manage"))


@manage_bp.route("/manage/move/<path:song>/<action>", methods=["POST"])
def move_song(song, action):
    """Move a song in the queue (top/bottom/up/down)."""
    k = get_karaoke_instance()
    song_path = unquote(song)
    success = False

    if action == "top":
        success = k.queue_manager.move_to_top(song_path)
    elif action == "bottom":
        success = k.queue_manager.move_to_bottom(song_path)
    elif action in ("up", "down"):
        success = k.queue_manager.queue_edit(song_path, action)

    if success:
        flash(_("Song moved"), "is-success")

    return redirect(url_for("manage.manage"))