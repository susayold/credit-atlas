from scripts.audit_nsmo_key_item_versions import normalized


def test_questionnaire_item_matching_ignores_line_breaks_and_typographic_quotes():
    assert normalized("Lenders shouldn’t care about any\nlate payments") == "lenders shouldn't care about any late payments"
