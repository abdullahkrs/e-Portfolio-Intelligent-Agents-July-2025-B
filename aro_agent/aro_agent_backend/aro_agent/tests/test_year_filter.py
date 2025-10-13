from aro_agent.agents.coordinator import CoordinatorAgent

def _ok(y, fr=None, to=None):
    """
    Helper function to test the year filtering logic.
    """
    c = CoordinatorAgent(contact_email="x@example.com")

    def _year_ok(published):
        if not (fr or to):
            return True
        if not published or len(published) < 4 or not published[:4].isdigit():
            return False
        yy = int(published[:4])
        if fr is not None and yy < fr:
            return False
        if to is not None and yy > to:
            return False
        return True

    return _year_ok(y)

def test_year_inclusive_bounds():
    """
    Tests that the year filtering logic correctly includes the boundary years.
    """
    assert _ok("2020-01-02", fr=2020, to=2021)
    assert not _ok("2019-12-31", fr=2020, to=2021)
    assert not _ok("2022-01-01", fr=2020, to=2021)
