import math

import numpy as np

TASK_NAME = "puzzlemix_escape"
FULL_SCENE = True


def scene_room(payload):
    return payload["scene"], "full_scene"


def question_id(payload, source_path):
    return payload["level"]


def initial_camera(payload):
    from _escape import CAM_H
    from _explore import quat_from

    start = payload["start"]
    x, y = start["xy"]
    position = np.array([x, y, CAM_H], dtype=float)
    rotation = quat_from(math.radians(start["yaw_deg"]), 0)
    pose = {"position": position.tolist(), "quaternion_xyzw": rotation.tolist()}
    return position, rotation, {"camera_pose": pose}


def build_env_objects(payload):
    return []


def build_system_prompt(payload, threshold, min_steps, camera_info=None):
    return "Open the unlocked exit door to escape."


def parse_model_output(parsed):
    raise RuntimeError("PuzzleMixEscape decisions must be executed by the escape-room environment")


def score(payload, final_answer, camera_info=None):
    raise RuntimeError("PuzzleMixEscape success must come from the exit-door state")
