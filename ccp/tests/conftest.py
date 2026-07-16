import pytest

import ccp

# Modules dominated by full compressor calculations (Impeller.convert_from,
# Evaluation, Streamlit AppTest) where single tests take minutes. They are
# auto-marked as "slow" so the development loop can skip them with:
#   uv run pytest ccp/tests -m "not slow"
SLOW_TEST_FILES = (
    "test_app.py",
    "test_compressor.py",
    "test_evaluation.py",
    "test_impeller.py",
)


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.name in SLOW_TEST_FILES:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def restore_global_config():
    """Restore global ccp.config settings after each test.

    Some tests set ccp.config.EOS or ccp.config.POLYTROPIC_METHOD; without a
    reset that leaks into every test that runs afterwards in the same process
    and shifts their results (e.g. the historical test_impeller failures when
    run in the same process as test_point).
    """
    eos = ccp.config.EOS
    polytropic_method = ccp.config.POLYTROPIC_METHOD
    yield
    ccp.config.EOS = eos
    ccp.config.POLYTROPIC_METHOD = polytropic_method
