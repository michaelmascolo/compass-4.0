"""Teacher product phase (i)+(ii) backend tests.

Covers:
- GET /api/teacher/assignments (shape + counts)
- POST /api/teacher-configs -> /activate -> /create-session linkage
- POST /api/assignments/{code}/start (student join by code)
- GET /api/teacher/assignments/{config_id}/sessions
- Regression: POST /api/sessions + POST /api/sessions/{id}/interact
"""
import os
import re
import time
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://dev-converse.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

# Minimal valid teacher configuration payload
VALID_CFG = {
    "classContext": {"course": "ELA", "gradeLevel": 9, "ageRange": "14-15", "classSection": ""},
    "assignment": {
        "title": "TEST_Argue social media",
        "directions": "Take a position on whether social media improves or harms teen friendships.",
        "purpose": "Practice forming and defending a claim.",
        "audience": "Classmates and teacher",
        "genre": "position paper",
        "requiredLength": "600 words",
        "dueDate": "",
        "stages": ["Plan", "Draft", "Revise", "Submit"],
        "revisionCycles": 2,
    },
    "learning": {
        "objectives": ["Form a clear claim", "Support with reasons and evidence"],
        "requiredContentKnowledge": [], "requiredReadings": [], "standards": [], "teacherRubric": "",
    },
    "guidance": {
        "scaffoldingLevel": "adaptive-moderate", "questionExplanationBalance": "balanced",
        "feedbackPriorities": ["purpose", "evidence", "organization"],
        "instructionalEmphases": [], "grammarEmphasis": "moderate",
        "mechanicsEmphasis": "moderate", "modelsEnabled": True,
    },
    "classroom": {"workMode": "individual", "norms": "", "approvedAccommodations": [],
                   "teacherPrompts": [], "teacherExemplars": [], "teacherNotes": ""},
    "gradeCalibration": {"profile": "grade-9", "profileVersion": "1.0"},
}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def created_config(s):
    r = s.post(f"{API}/teacher-configs", json=VALID_CFG, timeout=30)
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg.get("id")
    assert cfg.get("code") and re.fullmatch(r"[A-Z0-9]{6}", cfg["code"]), f"bad code: {cfg.get('code')}"
    assert cfg.get("teacher_id") == "local-teacher"
    # Activate
    r2 = s.post(f"{API}/teacher-configs/{cfg['id']}/activate", timeout=30)
    assert r2.status_code == 200, r2.text
    assert r2.json().get("status") == "active"
    return r2.json()


# -------- list_teacher_assignments shape --------
class TestListAssignments:
    def test_shape_and_contains_created(self, s, created_config):
        r = s.get(f"{API}/teacher/assignments", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["teacher_id"] == "local-teacher"
        assert isinstance(data["assignment_count"], int)
        assert isinstance(data["student_total"], int)
        assert isinstance(data["assignments"], list)
        # Find our newly-created assignment
        match = next((a for a in data["assignments"] if a["id"] == created_config["id"]), None)
        assert match is not None, "Newly created assignment not present in list"
        for k in ("id", "code", "status", "title", "student_count", "active_count", "last_activity"):
            assert k in match, f"missing key {k} in assignment summary"
        assert match["code"] == created_config["code"]
        assert match["status"] == "active"
        assert isinstance(match["student_count"], int)
        assert isinstance(match["active_count"], int)


# -------- student-join-by-code --------
class TestStudentJoinByCode:
    def test_join_by_code_creates_linked_session(self, s, created_config):
        # Baseline count from list endpoint
        base = s.get(f"{API}/teacher/assignments", timeout=30).json()
        base_row = next(a for a in base["assignments"] if a["id"] == created_config["id"])
        base_count = base_row["student_count"]

        code = created_config["code"]
        r = s.post(f"{API}/assignments/{code}/start",
                   json={"student_name": "TEST_Student"}, timeout=60)
        assert r.status_code == 200, r.text
        sess = r.json()
        assert sess["config_id"] == created_config["id"], "config_id linkage broken"
        assert sess["assignment_code"] == code, "assignment_code linkage broken"
        assert sess["teacher_id"] == "local-teacher"
        assert sess["student_name"] == "TEST_Student"

        # student_count should increment by 1
        after = s.get(f"{API}/teacher/assignments", timeout=30).json()
        after_row = next(a for a in after["assignments"] if a["id"] == created_config["id"])
        assert after_row["student_count"] == base_count + 1, (
            f"expected {base_count+1}, got {after_row['student_count']}"
        )

    def test_join_unknown_code_returns_404(self, s):
        r = s.post(f"{API}/assignments/ZZZZZZ/start",
                   json={"student_name": "Nobody"}, timeout=15)
        assert r.status_code == 404


# -------- create-session-from-config linkage --------
class TestCreateSessionFromConfig:
    def test_create_session_carries_linkage(self, s, created_config):
        r = s.post(f"{API}/teacher-configs/{created_config['id']}/create-session",
                   json={"student_name": "Ada"}, timeout=60)
        assert r.status_code == 200, r.text
        sess = r.json()
        assert sess["config_id"] == created_config["id"]
        assert sess["assignment_code"] == created_config["code"]
        assert sess["teacher_id"] == "local-teacher"
        assert sess["student_name"] == "Ada"


# -------- per-assignment sessions list --------
class TestListAssignmentSessions:
    def test_returns_assignment_and_students(self, s, created_config):
        # Ensure at least one student session exists for this assignment
        # (parallel test workers may not have run join yet).
        s.post(f"{API}/assignments/{created_config['code']}/start",
               json={"student_name": "TEST_ListSessionsStudent"}, timeout=60)
        r = s.get(f"{API}/teacher/assignments/{created_config['id']}/sessions", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "assignment" in data and "students" in data
        assert data["assignment"]["id"] == created_config["id"]
        assert isinstance(data["students"], list)
        assert len(data["students"]) >= 1
        st = data["students"][0]
        for k in ("session_id", "student_name", "turn_count", "revision_count"):
            assert k in st, f"missing field {k} in student row"
        assert isinstance(st["turn_count"], int)
        assert isinstance(st["revision_count"], int)

    def test_unknown_assignment_404(self, s):
        r = s.get(f"{API}/teacher/assignments/does-not-exist/sessions", timeout=15)
        assert r.status_code == 404


# -------- Validation on activate --------
class TestActivateValidation:
    def test_activate_missing_required_fails(self, s):
        empty = {
            "classContext": {"course": "ELA", "gradeLevel": 9, "ageRange": "14-15", "classSection": ""},
            "assignment": {"title": "", "directions": "", "purpose": "", "audience": "", "genre": "",
                            "requiredLength": "", "dueDate": "", "stages": ["Plan", "Draft"], "revisionCycles": 0},
            "learning": {"objectives": [], "requiredContentKnowledge": [], "requiredReadings": [],
                          "standards": [], "teacherRubric": ""},
            "guidance": {"scaffoldingLevel": "adaptive-moderate", "questionExplanationBalance": "balanced",
                          "feedbackPriorities": [], "instructionalEmphases": [], "grammarEmphasis": "moderate",
                          "mechanicsEmphasis": "moderate", "modelsEnabled": True},
            "classroom": {"workMode": "individual", "norms": "", "approvedAccommodations": [],
                           "teacherPrompts": [], "teacherExemplars": [], "teacherNotes": ""},
            "gradeCalibration": {"profile": "grade-9", "profileVersion": "1.0"},
        }
        r = s.post(f"{API}/teacher-configs", json=empty, timeout=30)
        assert r.status_code == 200
        cid = r.json()["id"]
        r2 = s.post(f"{API}/teacher-configs/{cid}/activate", timeout=30)
        assert r2.status_code == 422
        detail = r2.json().get("detail", {})
        assert detail.get("valid") is False
        assert isinstance(detail.get("errors"), list) and len(detail["errors"]) >= 1


# -------- Regression: existing sessions / interact --------
class TestRegressionSessions:
    def test_create_and_interact(self, s):
        payload = {
            "assignment": "TEST_Regression short",
            "assignment_prompt": "Write one sentence about anything you know.",
            "pedagogical_purpose": "Practice putting an idea into words.",
            "current_writing_task": "Draft one sentence.",
            "teacher_notes": "",
        }
        r = s.post(f"{API}/sessions", json=payload, timeout=60)
        assert r.status_code == 200, r.text
        sid = r.json()["id"]

        r2 = s.post(f"{API}/sessions/{sid}/interact",
                    json={"kind": "writing", "content": "Rain makes the roof sound busy."},
                    timeout=90)
        assert r2.status_code == 200, r2.text
        sess = r2.json()
        assert "turns" in sess and len(sess["turns"]) >= 1
