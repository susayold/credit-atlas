from scripts.accept_nmdb_market_query_grid import build_query_grid


def test_query_grid_covers_published_weights_markets_geographies_and_suppression_edge():
    catalog = {
        "products": [
            {
                "product": "new_annual", "first_year": 1998, "last_year": 2025,
                "markets": ["All Mortgages", "Jumbo Market"],
                "series": [{"series_id": "AVE_INTRATE", "supported_weights": ["VALUE1", "VALUE2"]}],
                "geographies": [
                    {"geo_level": "National", "geo_id": "USA"},
                    {"geo_level": "State", "geo_id": "AK"},
                ],
            },
            {
                "product": "outstanding_quarterly", "first_year": 2013, "last_year": 2026,
                "markets": ["All Mortgages"],
                "series": [{"series_id": "AVE_INTRATE", "supported_weights": ["VALUE1", "VALUE2"]}],
                "geographies": [{"geo_level": "National", "geo_id": "USA"}],
            },
        ]
    }
    groups = [
        {"product": "new_annual", "geography_level": "National", "geography_id": "USA", "geography_name": "United States", "market": "All Mortgages", "series_id": "AVE_INTRATE", "first_year": 1998, "last_year": 2025, "row_count": 28, "value1_rows": 28, "value2_rows": 28, "suppressed_rows": 0},
        {"product": "new_annual", "geography_level": "State", "geography_id": "AK", "geography_name": "Alaska", "market": "All Mortgages", "series_id": "AVE_INTRATE", "first_year": 1998, "last_year": 2025, "row_count": 28, "value1_rows": 28, "value2_rows": 28, "suppressed_rows": 0},
        {"product": "new_annual", "geography_level": "State", "geography_id": "AK", "geography_name": "Alaska", "market": "Jumbo Market", "series_id": "AVE_INTRATE", "first_year": 1999, "last_year": 2025, "row_count": 27, "value1_rows": 21, "value2_rows": 21, "suppressed_rows": 6},
        {"product": "outstanding_quarterly", "geography_level": "National", "geography_id": "USA", "geography_name": "United States", "market": "All Mortgages", "series_id": "AVE_INTRATE", "first_year": 2013, "last_year": 2026, "row_count": 54, "value1_rows": 54, "value2_rows": 54, "suppressed_rows": 0},
    ]

    api, xlsx, tags = build_query_grid(catalog, groups)

    assert len([key for key in api if api[key]["product"] == "new_annual" and "series-weight" in tags[key]]) == 2
    assert len([key for key in api if api[key]["product"] == "outstanding_quarterly" and "series-weight" in tags[key]]) == 2
    assert {api[key]["market"] for key in api if api[key]["product"] == "new_annual" and "market" in tags[key]} == {"All Mortgages", "Jumbo Market"}
    assert {api[key]["geo_level"] for key in api if api[key]["product"] == "new_annual" and "geography-level" in tags[key]} == {"National", "State"}
    assert any("quality-edge" in labels for labels in tags.values())
    assert any("quality-edge" in tags[key] for key in xlsx)
    assert set(xlsx) <= set(api)
