"""News sentiment lexicon tests (offline)."""

from collectors.news_sentiment import aggregate_sentiment, score_headline


def test_positive_headline():
    assert score_headline("Company beats earnings, shares surge on strong growth") > 0.3


def test_negative_headline():
    assert score_headline("Stock plunges after earnings miss and layoffs") < -0.3


def test_neutral_headline():
    assert abs(score_headline("Company announces quarterly report date")) < 0.1


def test_negation_flips_sign():
    plain = score_headline("Company profits")
    negated = score_headline("Company fails profits")   # "fails" negates next word
    assert plain > 0
    assert negated < plain


def test_empty_input():
    assert score_headline("") == 0.0
    result = aggregate_sentiment([])
    assert result["label"] == "no_data"
    assert result["article_count"] == 0


def test_aggregate_counts_and_label():
    headlines = [
        "Shares surge after record profit",
        "Analyst upgrades stock to buy",
        "Company faces lawsuit and investigation",
    ]
    result = aggregate_sentiment(headlines)
    assert result["article_count"] == 3
    assert result["positive"] == 2
    assert result["negative"] == 1
    assert -1 <= result["sentiment_score"] <= 1
