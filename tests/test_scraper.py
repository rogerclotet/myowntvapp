import pytest

from app.services.scraper import StreamScraper, format_event_time


class StubLogoService:
    """Logo lookups hit TheSportsDB; tests record the call instead."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def get_logos_for_match(
        self, home_team: str, away_team: str
    ) -> tuple[str | None, str | None]:
        self.calls.append((home_team, away_team))
        return f"{home_team}.png", f"{away_team}.png"


@pytest.fixture
def logos() -> StubLogoService:
    return StubLogoService()


@pytest.fixture
def scraper(logos: StubLogoService) -> StreamScraper:
    return StreamScraper(logos)


def test_utc_timestamp_renders_as_eastern_wall_time() -> None:
    # 00:10 UTC on Mar 14 is the previous evening in New York.
    assert format_event_time("2026-03-14T00:10:00Z") == "Fri March 13th 8:10 PM EDT"


def test_winter_timestamp_is_labelled_est() -> None:
    assert format_event_time("2026-01-14T00:10:00Z") == "Tue January 13th 7:10 PM EST"


@pytest.mark.parametrize(
    ("timestamp", "expected_day"),
    [
        ("2026-01-01T18:00:00Z", "1st"),
        ("2026-01-02T18:00:00Z", "2nd"),
        ("2026-01-03T18:00:00Z", "3rd"),
        ("2026-01-04T18:00:00Z", "4th"),
        ("2026-01-11T18:00:00Z", "11th"),
        ("2026-01-12T18:00:00Z", "12th"),
        ("2026-01-13T18:00:00Z", "13th"),
        ("2026-01-21T18:00:00Z", "21st"),
        ("2026-01-22T18:00:00Z", "22nd"),
        ("2026-01-23T18:00:00Z", "23rd"),
    ],
)
def test_day_ordinal_suffixes(timestamp: str, expected_day: str) -> None:
    formatted = format_event_time(timestamp)

    assert formatted is not None
    assert f"January {expected_day}" in formatted


def test_surrounding_whitespace_is_tolerated() -> None:
    assert format_event_time("  2026-01-14T00:10:00Z  ") == "Tue January 13th 7:10 PM EST"


@pytest.mark.parametrize(
    "value",
    ["", "Live Now", "2026-01-14T00:10:00+00:00", "not-a-date-Z", "2026-13-45T99:99:99Z"],
)
def test_non_utc_or_unparseable_input_returns_none(value: str) -> None:
    assert format_event_time(value) is None


async def test_at_separator_maps_away_then_home(scraper: StreamScraper) -> None:
    event = await scraper._parse_and_enrich_event(
        event_id="e1",
        title="Boston Bruins @ New York Rangers",
        url="https://thetvapp.to/event/e1/x",
        category="nhl",
    )

    assert event.away_team == "Boston Bruins"
    assert event.home_team == "New York Rangers"


async def test_vs_separator_maps_home_then_away(scraper: StreamScraper) -> None:
    event = await scraper._parse_and_enrich_event(
        event_id="e2",
        title="Real Madrid vs Barcelona",
        url="https://thetvapp.to/event/e2/x",
        category="soccer",
    )

    assert event.home_team == "Real Madrid"
    assert event.away_team == "Barcelona"


async def test_title_gains_the_formatted_event_time(scraper: StreamScraper) -> None:
    event = await scraper._parse_and_enrich_event(
        event_id="e3",
        title="Boston Bruins @ New York Rangers\n    2026-01-14T00:10:00Z",
        url="https://thetvapp.to/event/e3/x",
        category="nhl",
    )

    assert event.title == "Boston Bruins @ New York Rangers\nTue January 13th 7:10 PM EST"


async def test_unparseable_second_line_leaves_the_title_alone(scraper: StreamScraper) -> None:
    event = await scraper._parse_and_enrich_event(
        event_id="e4",
        title="Boston Bruins @ New York Rangers\n    Starting soon",
        url="https://thetvapp.to/event/e4/x",
        category="nhl",
    )

    assert event.title == "Boston Bruins @ New York Rangers"


async def test_logos_are_attached_for_parsed_matchups(
    scraper: StreamScraper, logos: StubLogoService
) -> None:
    event = await scraper._parse_and_enrich_event(
        event_id="e5",
        title="Boston Bruins @ New York Rangers",
        url="https://thetvapp.to/event/e5/x",
        category="nhl",
    )

    assert logos.calls == [("New York Rangers", "Boston Bruins")]
    assert event.home_logo == "New York Rangers.png"
    assert event.away_logo == "Boston Bruins.png"


async def test_titles_without_a_matchup_skip_logo_lookup(
    scraper: StreamScraper, logos: StubLogoService
) -> None:
    event = await scraper._parse_and_enrich_event(
        event_id="tv1",
        title="ESPN",
        url="https://thetvapp.to/tv/espn/x",
        category="tv",
    )

    assert logos.calls == []
    assert event.home_team is None
    assert event.away_team is None
    assert event.title == "ESPN"
