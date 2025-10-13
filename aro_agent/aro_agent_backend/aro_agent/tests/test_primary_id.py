from aro_agent.agents.storage import _primary_id_from_row

def test_primary_id_doi_cleaning():
    """
    Tests that the DOI is correctly cleaned and lowercased when extracting the primary ID.
    """
    r = {"doi":"https://doi.org/10.1145/1234/ABC", "arxiv_id":None}
    assert _primary_id_from_row(r) == "10.1145/1234/abc"

def test_primary_id_arxiv_fallback():
    """
    Tests that the arXiv ID is used as a fallback when the DOI is not available.
    """
    r = {"doi":"", "arxiv_id":"2401.12345"}
    assert _primary_id_from_row(r) == "arxiv:2401.12345".lower()
