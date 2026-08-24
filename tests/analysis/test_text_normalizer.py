from app.analysis.text_normalizer import normalize_finance_text


def test_normalize_finance_text_removes_speaker_noise_and_markers():
    text = (
        "\ud53c\ud574\uc790: \uac80\ucc30 + \uc0ac\uce6d "
        "(\uc7a1\uc74c) \uc0dd\ub7b5 \uc3d0-"
    )

    assert normalize_finance_text(text) == "\uac80\ucc30 \uc0ac\uce6d \uc0dd\ub7b5"


def test_normalize_finance_text_merges_spaced_digits():
    assert normalize_finance_text("\uc8fc\ubbfc\ubc88\ud638 1 2 3 4 5") == "\uc8fc\ubbfc\ubc88\ud638 12345"


def test_normalize_finance_text_merges_consecutive_dual_notation():
    assert normalize_finance_text("\uacc4\uc88c 1/\uc77c 2/\uc774") == "\uacc4\uc88c 12"


def test_normalize_finance_text_removes_filler_markup_only():
    assert normalize_finance_text("\uc544/ \uc800\ub294 \uc74c/\uc694") == "\uc800\ub294 \uc694"


def test_normalize_finance_text_keeps_clean_text():
    text = "\uac80\ucc30\uc744 \uc0ac\uce6d\ud558\uc5ec \uc1a1\uae08\uc744 \uc694\uad6c\ud569\ub2c8\ub2e4."

    assert normalize_finance_text(text) == text
