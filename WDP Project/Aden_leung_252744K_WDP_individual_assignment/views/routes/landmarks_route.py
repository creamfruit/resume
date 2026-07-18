# Import Flask routing utilities for landmark APIs.
from flask import Blueprint, request, jsonify
# Import landmark data access module with backward-compatible names.
import views.landmark as landmark_module
# Import admin guard for protected write endpoints.
from views.routes.admin_utils import require_admin

# All endpoints will start with /api/landmarks
# This Blueprint groups landmark CRUD APIs.
landmarks_bp = Blueprint("landmarks", __name__, url_prefix="/api/landmarks")


# Resolve the Landmark class regardless of module naming convention.
def _get_landmark_class():
    """
    Your views/landmark.py might define Landmark (capital) or landmark (lower).
    This helper grabs whichever exists.
    """
    # Try standard class name first for clarity.
    if hasattr(landmark_module, "Landmark"):
        return landmark_module.Landmark
    # Fall back to legacy naming if needed.
    if hasattr(landmark_module, "landmark"):
        return landmark_module.landmark
    raise ImportError("No Landmark class found in views/landmark.py (expected Landmark or landmark)")


# Return all landmarks with their metadata and options.
@landmarks_bp.get("/")
def get_all_landmarks():
    try:
        # Resolve the appropriate data access function name.
        # supports either getAllLandmarksDB or get_all_landmarks_db naming
        if hasattr(landmark_module, "getAllLandmarksDB"):
            landmarks_db = landmark_module.getAllLandmarksDB()
        else:
            landmarks_db = landmark_module.get_all_landmarks_db()

        # Serialize model objects for API output.
        landmarks_list = [obj.to_dict() for obj in landmarks_db]
        return jsonify({"success": True, "landmarks": landmarks_list, "count": len(landmarks_list)}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Return a single landmark by id.
@landmarks_bp.get("/<int:landmark_id>")
def get_landmark(landmark_id):
    try:
        # Resolve the appropriate data access function name.
        if hasattr(landmark_module, "getLandmarkDB"):
            landmark_db = landmark_module.getLandmarkDB(landmark_id)
        else:
            landmark_db = landmark_module.get_landmark_db(landmark_id)

        # Guard against missing records.
        if not landmark_db:
            return jsonify({"success": False, "error": "Landmark not found"}), 404

        return jsonify({"success": True, "landmark": landmark_db.to_dict()}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Create a new landmark (admin-only).
@landmarks_bp.post("/")
def create_landmark():
    _, err = require_admin()
    if err:
        return err
    try:
        # Parse and validate request payload.
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        LandmarkCls = _get_landmark_class()

        # Construct model instance from request payload.
        # If your class has from_dict
        if hasattr(LandmarkCls, "from_dict"):
            landmark_obj = LandmarkCls.from_dict(data)
        else:
            # fallback: construct manually
            landmark_obj = LandmarkCls(**data)

        # Run model-level validation when available.
        if hasattr(landmark_obj, "validate"):
            landmark_obj.validate()

        # Persist to the database using the available function name.
        if hasattr(landmark_module, "createLandmarkDB"):
            landmark_db = landmark_module.createLandmarkDB(landmark_obj)
        else:
            landmark_db = landmark_module.create_landmark_db(landmark_obj)

        # Return the created resource.
        return jsonify({
            "success": True,
            "message": "Landmark created successfully",
            "landmark": landmark_db.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({"success": False, "error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Update an existing landmark (admin-only).
@landmarks_bp.put("/<int:landmark_id>")
def update_landmark(landmark_id):
    _, err = require_admin()
    if err:
        return err
    try:
        # Parse and validate payload.
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        LandmarkCls = _get_landmark_class()
        landmark_obj = LandmarkCls.from_dict(data) if hasattr(LandmarkCls, "from_dict") else LandmarkCls(**data)

        # Persist updates using the resolved function name.
        if hasattr(landmark_module, "updateLandmarkDB"):
            landmark_db = landmark_module.updateLandmarkDB(landmark_id, landmark_obj)
        else:
            landmark_db = landmark_module.update_landmark_db(landmark_id, landmark_obj)

        # Return 404 if the record does not exist.
        if not landmark_db:
            return jsonify({"success": False, "error": "Landmark not found"}), 404

        return jsonify({
            "success": True,
            "message": "Landmark updated successfully",
            "landmark": landmark_db.to_dict()
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Delete a landmark record (admin-only).
@landmarks_bp.delete("/<int:landmark_id>")
def delete_landmark(landmark_id):
    _, err = require_admin()
    if err:
        return err
    try:
        # Perform deletion via the resolved data access function.
        if hasattr(landmark_module, "deleteLandmarkDB"):
            success = landmark_module.deleteLandmarkDB(landmark_id)
        else:
            success = landmark_module.delete_landmark_db(landmark_id)

        # Return 404 if deletion target is missing.
        if not success:
            return jsonify({"success": False, "error": "Landmark not found"}), 404

        return jsonify({"success": True, "message": "Landmark deleted successfully"}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Create a landmark from explicit map coordinates (admin-only).
@landmarks_bp.post("/coordinates")
def save_landmark_with_coordinates():
    _, err = require_admin()
    if err:
        return err
    try:
        data = request.get_json(silent=True) or {}

        # Validate required fields for coordinate-based creation.
        required_fields = ["name", "icon", "story", "question", "correct_answer", "x_coord", "y_coord"]
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({"success": False, "error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        LandmarkCls = _get_landmark_class()

        # Construct the landmark instance explicitly from payload values.
        landmark_obj = LandmarkCls(
            name=data["name"],
            icon=data["icon"],
            story=data["story"],
            question=data["question"],
            correct_answer=data["correct_answer"],
            x_coord=float(data["x_coord"]),
            y_coord=float(data["y_coord"]),
            points_value=data.get("points_value", 10),
        )

        # Run model validation if available.
        if hasattr(landmark_obj, "validate"):
            landmark_obj.validate()

        # Persist to the database using the resolved function name.
        if hasattr(landmark_module, "createLandmarkDB"):
            landmark_db = landmark_module.createLandmarkDB(landmark_obj)
        else:
            landmark_db = landmark_module.create_landmark_db(landmark_obj)

        # Return the created resource with coordinates.
        return jsonify({
            "success": True,
            "message": "Landmark saved with coordinates",
            "landmark": landmark_db.to_dict()
        }), 201

    except ValueError as e:
        return jsonify({"success": False, "error": f"Invalid data: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
