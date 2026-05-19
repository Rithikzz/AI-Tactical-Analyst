from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import numpy as np

from .config import MODEL_PATH, REPO_ROOT

# Ensure repo root on sys.path for football_analysis imports
import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from football_analysis.camera_movement_estimator import CameraMovementEstimator
from football_analysis.game_intelligence import analyze_match
from football_analysis.player_ball_assigner import PlayerBallAssigner
from football_analysis.speed_and_distance_estimator import SpeedAndDistance_Estimator
from football_analysis.team_assigner import TeamAssigner
from football_analysis.trackers import Tracker
from football_analysis.utils.video_utils import get_video_fps, read_video, save_video
from football_analysis.view_transformer import ViewTransformer


def _align_pipeline_lengths(video_frames, tracks, camera_movement_per_frame):
    players_len = len(tracks.get("players", []))
    referees_len = len(tracks.get("referees", []))
    ball_len = len(tracks.get("ball", []))
    movement_len = len(camera_movement_per_frame)
    frames_len = len(video_frames)

    target_len = min(frames_len, players_len, referees_len, ball_len, movement_len)
    if target_len <= 0:
        raise ValueError("No valid frames to process after aligning video and tracking outputs.")

    if target_len != frames_len:
        video_frames = video_frames[:target_len]
    if target_len != players_len:
        tracks["players"] = tracks["players"][:target_len]
    if target_len != referees_len:
        tracks["referees"] = tracks["referees"][:target_len]
    if target_len != ball_len:
        tracks["ball"] = tracks["ball"][:target_len]
    if target_len != movement_len:
        camera_movement_per_frame = camera_movement_per_frame[:target_len]

    return video_frames, tracks, camera_movement_per_frame


def run_full_pipeline(video_path: Path, output_path: Path) -> Tuple[Path, Dict]:
    if not video_path.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    video_frames = read_video(str(video_path))
    if not video_frames:
        raise ValueError(f"No frames were read from: {video_path}")

    video_fps = get_video_fps(str(video_path), default_fps=24.0)

    tracker = Tracker(str(MODEL_PATH))
    tracks = tracker.get_object_tracks(video_frames, read_from_stub=False)
    tracker.add_position_to_tracks(tracks)

    camera_movement_estimator = CameraMovementEstimator(video_frames[0])
    camera_movement_per_frame = camera_movement_estimator.get_camera_movement(
        video_frames,
        read_from_stub=False,
    )

    video_frames, tracks, camera_movement_per_frame = _align_pipeline_lengths(
        video_frames,
        tracks,
        camera_movement_per_frame,
    )
    camera_movement_estimator.add_adjust_positions_to_tracks(tracks, camera_movement_per_frame)

    view_transformer = ViewTransformer()
    view_transformer.add_transformed_position_to_tracks(tracks)

    tracks["ball"] = tracker.interpolate_ball_positions(tracks["ball"])

    speed_and_distance_estimator = SpeedAndDistance_Estimator(frame_rate=video_fps)
    speed_and_distance_estimator.add_speed_and_distance_to_tracks(tracks)

    team_assigner = TeamAssigner()
    if tracks["players"]:
        team_assigner.assign_team_color(video_frames[0], tracks["players"][0])

    for frame_num, player_track in enumerate(tracks["players"]):
        for player_id, track in player_track.items():
            team = team_assigner.get_player_team(
                video_frames[frame_num],
                track["bbox"],
                player_id,
            )
            tracks["players"][frame_num][player_id]["team"] = team
            tracks["players"][frame_num][player_id]["team_color"] = team_assigner.team_colors[team]

    player_assigner = PlayerBallAssigner()
    team_ball_control = []
    last_known_team = 1
    for frame_num, player_track in enumerate(tracks["players"]):
        ball_bbox = tracks["ball"][frame_num].get(1, {}).get("bbox")
        if ball_bbox is None:
            team_ball_control.append(last_known_team)
            continue

        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)
        if assigned_player != -1:
            tracks["players"][frame_num][assigned_player]["has_ball"] = True
            current_team = tracks["players"][frame_num][assigned_player].get("team", last_known_team)
            team_ball_control.append(current_team)
            last_known_team = current_team
        else:
            team_ball_control.append(last_known_team)

    team_ball_control = np.array(team_ball_control)

    output_video_frames = tracker.draw_annotations(video_frames, tracks, team_ball_control)
    output_video_frames = camera_movement_estimator.draw_camera_movement(
        output_video_frames, camera_movement_per_frame
    )
    output_video_frames = speed_and_distance_estimator.draw_speed_and_distance(
        output_video_frames, tracks
    )

    save_video(output_video_frames, str(output_path))

    analytics = analyze_match(tracks, team_ball_control, fps=video_fps, verbose=False)
    analytics["video_fps"] = video_fps
    analytics["frame_count"] = len(video_frames)
    return output_path, analytics
