from credit_atlas.nsmo_questionnaires import normalize_question_text, split_question_blocks


def test_normalization_only_standardizes_typography_and_whitespace():
    assert normalize_question_text("What’s  the “rate”\u00ad?") == 'what\'s the "rate"?'


def test_split_question_blocks_keeps_answer_scale_and_removes_footer_numbers():
    blocks = split_question_blocks(
        "1. How important was the rate?\nVery important Somewhat Not at all\n"
        "11\n2. Did you refinance?\nYes No\n12"
    )
    assert [row["question_number"] for row in blocks] == [1, 2]
    assert "Very important Somewhat Not at all" in blocks[0]["text"]
    assert "12" not in blocks[1]["text"]
