"""Tests for the ccp Streamlit application pages.

These tests use Streamlit's AppTest framework to load example .ccp files
and run the calculations for each page, verifying that no exceptions occur
and that the expected output objects are created.
"""

import json
import os
import zipfile

import pytest

import ccp
from ccp.compressor import BackToBack, StraightThrough

os.environ["CCP_STANDALONE"] = "1"

from streamlit.testing.v1 import AppTest

TIMEOUT = 300
APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
PAGES_DIR = os.path.join(APP_DIR, "pages")


def load_ccp_file(ccp_path):
    """Extract session state and auxiliary data from a .ccp file.

    Returns
    -------
    session_data : dict
        Filtered session state (no internal Streamlit keys).
    csv_files : dict
        Mapping of csv filename to content bytes.
    toml_files : dict
        Mapping of toml base name to raw string content.
    """
    session_data = {}
    csv_files = {}
    toml_files = {}

    with zipfile.ZipFile(ccp_path) as z:
        for name in z.namelist():
            if name.endswith(".json"):
                session_data = json.loads(z.read(name))
            elif name.endswith(".csv"):
                csv_files[name] = z.read(name)
            elif name.endswith(".toml"):
                toml_files[name] = z.read(name).decode("utf-8")

    skip_prefixes = ("FormSubmitter", "my_form", "uploaded", "form", "table")
    filtered = {
        k: v for k, v in session_data.items() if not k.startswith(skip_prefixes)
    }
    return filtered, csv_files, toml_files


def populate_session_state(at, session_data):
    """Pre-populate an AppTest instance's session_state."""
    for k, v in session_data.items():
        at.session_state[k] = v


# ---------------------------------------------------------------------------
# Straight-Through
# ---------------------------------------------------------------------------


class TestStraightThrough:
    page_path = os.path.join(PAGES_DIR, "1_straight_through.py")
    example_path = os.path.join(APP_DIR, "example_straight.ccp")

    def test_page_loads_without_error(self):
        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        at.run(timeout=TIMEOUT)
        assert not at.exception

    def test_calculate_with_example_file(self):
        session_data, _, _ = load_ccp_file(self.example_path)

        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        populate_session_state(at, session_data)
        at.run(timeout=TIMEOUT)
        assert not at.exception

        # Find and click the "Calculate" button
        calc_buttons = [b for b in at.button if b.label == "Calculate"]
        assert calc_buttons, "Calculate button not found"
        calc_buttons[0].click().run(timeout=TIMEOUT)
        assert not at.exception

        # Verify StraightThrough object was created
        assert isinstance(at.session_state["straight_through"], StraightThrough)


# ---------------------------------------------------------------------------
# Back-to-Back
# ---------------------------------------------------------------------------


class TestBackToBack:
    page_path = os.path.join(PAGES_DIR, "2_back_to_back.py")
    example_path = os.path.join(APP_DIR, "example_back_to_back.ccp")

    def test_page_loads_without_error(self):
        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        at.run(timeout=TIMEOUT)
        assert not at.exception

    def test_calculate_with_example_file(self):
        session_data, _, _ = load_ccp_file(self.example_path)

        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        populate_session_state(at, session_data)
        at.run(timeout=TIMEOUT)
        assert not at.exception

        calc_buttons = [b for b in at.button if b.label == "Calculate"]
        assert calc_buttons, "Calculate button not found"
        calc_buttons[0].click().run(timeout=TIMEOUT)
        assert not at.exception

        assert isinstance(at.session_state["back_to_back"], BackToBack)


# ---------------------------------------------------------------------------
# Curves Conversion
# ---------------------------------------------------------------------------


class TestCurvesConversion:
    page_path = os.path.join(PAGES_DIR, "3_curves_conversion.py")
    example_path = os.path.join(APP_DIR, "curves-conversion-example.ccp")

    def test_page_loads_without_error(self):
        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        at.run(timeout=TIMEOUT)
        assert not at.exception

    def test_load_and_convert_with_example_file(self):
        session_data, csv_files, toml_files = load_ccp_file(self.example_path)

        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        populate_session_state(at, session_data)

        # Populate CSV files in session state (as the file loader would)
        csv_items = sorted(csv_files.items())
        for i, (name, content) in enumerate(csv_items, start=1):
            at.session_state[f"curves_file_{i}"] = {
                "name": name,
                "content": content,
            }

        at.run(timeout=TIMEOUT)
        assert not at.exception

        # Click "Load Original Curves"
        load_buttons = [b for b in at.button if b.label == "Load Original Curves"]
        assert load_buttons, "Load Original Curves button not found"
        load_buttons[0].click().run(timeout=TIMEOUT)
        assert not at.exception

        original_imp = at.session_state["original_impeller"]
        assert original_imp is not None, "original_impeller not created"
        assert len(original_imp.points) > 0

        # Click "Convert Curves"
        convert_buttons = [b for b in at.button if b.label == "Convert Curves"]
        assert convert_buttons, "Convert Curves button not found"
        convert_buttons[0].click().run(timeout=TIMEOUT)
        assert not at.exception

        converted_imp = at.session_state["converted_impeller"]
        assert converted_imp is not None, "converted_impeller not created"
        assert len(converted_imp.points) > 0


# ---------------------------------------------------------------------------
# Online Monitoring - Load Curves
# ---------------------------------------------------------------------------


class TestOnlineMonitoring:
    page_path = os.path.join(PAGES_DIR, "4_online_monitoring.py")
    example_path = os.path.join(APP_DIR, "example_online.ccp")

    @pytest.fixture(autouse=True)
    def _enable_testing_mode(self):
        """The online monitoring page requires TESTING_MODE (checked via sys.argv)
        to bypass the pandaspi dependency."""
        import sys

        marker = "testing=True"
        if marker not in sys.argv:
            sys.argv.append(marker)
        yield
        if marker in sys.argv:
            sys.argv.remove(marker)

    def test_page_loads_without_error(self):
        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        at.run(timeout=TIMEOUT)
        assert not at.exception

    def test_load_curves_with_example_file(self):
        session_data, csv_files, toml_files = load_ccp_file(self.example_path)

        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        populate_session_state(at, session_data)

        # Populate CSV files for case A
        csv_items = sorted(csv_files.items())
        for i, (name, content) in enumerate(csv_items, start=1):
            at.session_state[f"curves_file_{i}_case_A"] = {
                "name": name,
                "content": content,
            }

        at.run(timeout=TIMEOUT)
        assert not at.exception

        # Click "Load Curves for Case A"
        load_buttons = [
            b for b in at.button if b.label == "Load Curves for Case A"
        ]
        assert load_buttons, "Load Curves for Case A button not found"
        load_buttons[0].click().run(timeout=TIMEOUT)
        assert not at.exception

        impeller_a = at.session_state["impeller_case_A"]
        assert impeller_a is not None, "impeller_case_A not created"
        assert len(impeller_a.points) > 0


# ---------------------------------------------------------------------------
# Performance Evaluation
# ---------------------------------------------------------------------------


class TestPerformanceEvaluation:
    page_path = os.path.join(PAGES_DIR, "5_performance_evaluation.py")
    example_path = os.path.join(APP_DIR, "example_online.ccp")

    @pytest.fixture(autouse=True)
    def _enable_testing_mode(self):
        """The performance evaluation page requires TESTING_MODE (checked via sys.argv)
        to bypass the pandaspi dependency."""
        import sys

        marker = "testing=True"
        if marker not in sys.argv:
            sys.argv.append(marker)
        yield
        if marker in sys.argv:
            sys.argv.remove(marker)

    def test_page_loads_without_error(self):
        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        at.run(timeout=TIMEOUT)
        assert not at.exception

    def test_load_curves_with_example_file(self):
        session_data, csv_files, toml_files = load_ccp_file(self.example_path)

        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        populate_session_state(at, session_data)

        # Populate CSV files for case A
        csv_items = sorted(csv_files.items())
        for i, (name, content) in enumerate(csv_items, start=1):
            at.session_state[f"curves_file_{i}_case_A"] = {
                "name": name,
                "content": content,
            }

        at.run(timeout=TIMEOUT)
        assert not at.exception

        # Click "Load Curves for Case A"
        load_buttons = [
            b for b in at.button if b.label == "Load Curves for Case A"
        ]
        assert load_buttons, "Load Curves for Case A button not found"
        load_buttons[0].click().run(timeout=TIMEOUT)
        assert not at.exception

        impeller_a = at.session_state["impeller_case_A"]
        assert impeller_a is not None, "impeller_case_A not created"
        assert len(impeller_a.points) > 0

    def test_run_evaluation_with_example_file(self):
        session_data, csv_files, toml_files = load_ccp_file(self.example_path)

        at = AppTest.from_file(self.page_path, default_timeout=TIMEOUT)
        populate_session_state(at, session_data)

        # Populate CSV files for case A
        csv_items = sorted(csv_files.items())
        for i, (name, content) in enumerate(csv_items, start=1):
            at.session_state[f"curves_file_{i}_case_A"] = {
                "name": name,
                "content": content,
            }

        at.run(timeout=TIMEOUT)
        assert not at.exception

        # Click "Load Curves for Case A"
        load_buttons = [
            b for b in at.button if b.label == "Load Curves for Case A"
        ]
        assert load_buttons, "Load Curves for Case A button not found"
        load_buttons[0].click().run(timeout=TIMEOUT)
        assert not at.exception

        assert at.session_state["impeller_case_A"] is not None

        # Trigger evaluation via session state (simulates "Run Evaluation" button on_click)
        at.session_state["_trigger_evaluation"] = "run"
        at.run(timeout=TIMEOUT)
        assert not at.exception

        assert "hist_evaluation" in at.session_state, "hist_evaluation not in session_state"
        evaluation = at.session_state["hist_evaluation"]
        assert evaluation is not None, "hist_evaluation not created"
        assert hasattr(evaluation, "df"), "evaluation has no df attribute"
        assert len(evaluation.df) > 0, "evaluation df is empty"
