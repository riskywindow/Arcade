from __future__ import annotations

import pytest

from atlas_env_helpdesk import HelpdeskService, WikiDocumentNotFoundError


def test_list_wiki_documents_returns_seeded_corpus() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    documents = service.list_wiki_documents()

    assert documents.seed == "seed-phase3-demo"
    assert len(documents.documents) == 8
    assert documents.documents[0].slug == "contractor-vpn-access-policy"


def test_get_wiki_document_returns_seeded_detail() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    document = service.get_wiki_document("travel-lockout-recovery")

    assert document.title == "Travel Lockout Recovery SOP"
    assert "MFA bypasses" in document.body


def test_search_wiki_documents_returns_stable_ranked_matches() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    response = service.search_wiki_documents("travel mfa")

    assert response.query == "travel mfa"
    assert response.results
    assert response.results[0].document.slug == "travel-lockout-recovery"
    assert set(response.results[0].matched_terms) == {"travel", "mfa"}


def test_get_wiki_document_raises_for_unknown_slug() -> None:
    service = HelpdeskService.seeded("seed-phase3-demo")

    with pytest.raises(WikiDocumentNotFoundError):
        service.get_wiki_document("missing-doc")
