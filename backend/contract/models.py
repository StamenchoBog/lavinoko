"""The shape of every JSON file the backend writes to frontend/static/data/.

This is the single definition of the data contract. The frontend's TypeScript types and its
runtime check are generated from it (see generate.py); the backend validates its output against it
before writing, so a file that breaks the contract is never published.

Conventions:
- A field that is sometimes left out is `T | Omitted = None`: optional in the contract, never null.
- A field that is always present but may be null is `T | None` with no default.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import TypeAliasType

Omitted = SkipJsonSchema[None]


class Model(BaseModel):
    # Strict and closed: the backend must not write a field the contract does not know about.
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


Compass = TypeAliasType("Compass", Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
Level = TypeAliasType("Level", Literal["none", "attention", "serious"])
FlagLevel = TypeAliasType("FlagLevel", Literal["attention", "serious"])
WindLevel = TypeAliasType("WindLevel", Literal["850hPa", "800hPa", "700hPa"])
FlagPeriod = TypeAliasType("FlagPeriod", Literal["past", "next"])
LonLat = TypeAliasType("LonLat", tuple[float, float])
Range = TypeAliasType("Range", tuple[float, float])


class Names(Model):
    """A name in both page languages."""

    mk: str
    en: str


class Wind(Model):
    max_kmh: float | None
    gust_max_kmh: float | None
    from_: Compass | None = Field(alias="from")
    loads: Compass | None = Field(description="Slopes the wind loads with snow: the lee side, opposite `from`.")


# --- Weather summaries -------------------------------------------------------------------------


class Overnight(Model):
    """The last 12 hours: the patrol's morning question."""

    snow_cm: float
    rain_mm: float
    temp_min_c: float | None
    wind: Wind


class Past72(Model):
    snow_cm: float
    snow_24h_cm: float
    wind_24h_max_kmh: float | None
    temp_24h_min_c: float | None
    rain_mm: float
    temp_min_c: float | None
    temp_max_c: float | None
    wind: Wind


class Next72(Model):
    snow_cm: float
    snow_24h_cm: float
    rain_mm: float
    temp_min_c: float | None
    temp_max_c: float | None
    freezing_level_min_m: float | None
    freezing_level_max_m: float | None
    wind: Wind


class Now(Model):
    temp_c: float | None
    wind_kmh: float | None
    wind_from: Compass | None
    freezing_level_m: float | None
    model_snow_depth_cm: int


class Day(Model):
    date: str
    when: Literal["past", "today", "future"]
    snow_cm: float
    rain_mm: float
    temp_min_c: float | None
    temp_max_c: float | None
    wind_max_kmh: float | None
    gust_max_kmh: float | None
    wind_from: Compass | None
    freezing_min_m: float | None
    freezing_max_m: float | None


class Spread(Model):
    """Lowest and highest value across the models that confirmed the alerts."""

    models: list[str]
    snow_next72_cm: Range
    snow_past72_cm: Range
    wind_next72_kmh: Range


# --- Flags: one type per code, each with the numbers its sentence uses -------------------------


class FlagBase(Model):
    level: FlagLevel
    agree: int | Omitted = Field(default=None, description="With model agreement: how many models raise this flag.")
    models: int | Omitted = Field(default=None, description="With model agreement: out of how many models.")


class HeavySnowComingFlag(FlagBase):
    code: Literal["heavy_snow_coming"]
    snow_cm: float
    snow_24h_cm: float


class RecentHeavySnowFlag(FlagBase):
    code: Literal["recent_heavy_snow"]
    snow_cm: float


class WindDriftingFlag(FlagBase):
    code: Literal["wind_drifting"]
    period: FlagPeriod
    snow_cm: float
    wind_kmh: float
    from_: Compass | None = Field(alias="from")
    loads: Compass | None


class StrongWindFlag(FlagBase):
    code: Literal["strong_wind"]
    period: FlagPeriod
    wind_kmh: float
    gust_kmh: float | None
    from_: Compass | None = Field(alias="from")


class RainOnSnowFlag(FlagBase):
    code: Literal["rain_on_snow"]
    rain_mm: float


class WarmingAfterSnowFlag(FlagBase):
    code: Literal["warming_after_snow"]
    snow_cm: float
    temp_max_c: float | None


Flag = TypeAliasType(
    "Flag",
    Annotated[
        HeavySnowComingFlag
        | RecentHeavySnowFlag
        | WindDriftingFlag
        | StrongWindFlag
        | RainOnSnowFlag
        | WarmingAfterSnowFlag,
        Field(discriminator="code"),
    ],
)


# --- weather.json ------------------------------------------------------------------------------


class WeatherPoint(Model):
    id: str
    name: Names
    lon: float
    lat: float
    elevation: int
    wind_level: WindLevel
    past12: Overnight
    past72: Past72
    next72: Next72
    now: Now
    spread: Spread | None
    days: list[Day]
    flags: list[Flag]


class PlaceSources(Model):
    location: str
    elevation: str
    checked: str


class Headline(Model):
    """For the overview list: the place's highest point, the most exposed."""

    elevation: int
    snow_next72_cm: float
    snow_past72_cm: float
    wind_next72: Wind
    flag_count: int


class Place(Model):
    id: str
    kind: Literal["resort", "touring"]
    pilot: bool
    name: Names
    range: Names
    center: LonLat
    sources: PlaceSources
    level: Level
    headline: Headline
    points: list[WeatherPoint]


class Health(Model):
    models: dict[str, str] = Field(
        description='Per consensus model: "ok", or why it was not used for alerts in this run.'
    )
    consensus: bool = Field(
        description="False when fewer than 2 models were healthy: alerts come from the blended forecast alone."
    )


class Thresholds(Model):
    """Limits for the plain weather facts behind the flags. Not avalanche danger criteria."""

    heavy_snow_24h_cm: float
    heavy_snow_72h_cm: float
    recent_snow_72h_cm: float
    drift_snow_24h_cm: float
    drift_wind_kmh: float
    strong_wind_kmh: float
    rain_on_snow_mm: float
    warming_after_snow_cm: float
    warming_temp_c: float


class Weather(Model):
    """weather.json: the summary for every place, as shown on the page."""

    issued_utc: str
    source: str
    source_url: str
    kind: Literal["forecast_model"]
    health: Health
    thresholds: Thresholds
    places: list[Place]


# --- hourly/<place>.json -----------------------------------------------------------------------


class HourlyPoint(Model):
    """Hourly series from 72 h before to 72 h after `now_index`, for the chart."""

    id: str
    elevation: int
    time: list[str]
    now_index: int
    snow_cm: list[float | None]
    rain_mm: list[float | None]
    temp_c: list[float | None]
    wind_kmh: list[float | None]
    wind_dir: list[int | None]
    freezing_m: list[int | None]


class Hourly(Model):
    """hourly/<place>.json: loaded only when someone opens that place."""

    issued_utc: str
    points: list[HourlyPoint]


# --- sources.json (copied from config/sources.json) --------------------------------------------


class Source(Model):
    id: str
    name: str
    used_for: Names
    licence: str
    credit: str
    url: str
    terms_url: str
    notes: str | Omitted = None
    checked: str


class Sources(Model):
    """sources.json: the source register, so the page can show credits and licences."""

    comment: str | Omitted = Field(default=None, alias="_comment")
    sources: list[Source]


# --- terrain/metadata.json ---------------------------------------------------------------------


class TerrainLayer(Model):
    country: str
    detail: str


class TerrainLayers(Model):
    slope: TerrainLayer
    aspect: TerrainLayer
    relief: TerrainLayer
    contours: TerrainLayer


class SlopeLegendItem(Model):
    label: str
    rgba: tuple[int, int, int, int]


class AspectLegendItem(Model):
    label: Compass
    rgb: tuple[int, int, int]


class TerrainStats(Model):
    elevation_min_m: int
    elevation_max_m: int


class TerrainMeta(Model):
    """terrain/metadata.json: where the terrain tiles are and how to read them."""

    bounds: tuple[float, float, float, float]
    center: LonLat
    layers: TerrainLayers
    country_zooms: tuple[int, int]
    detail_zooms: tuple[int, int]
    resolution_m: float
    source: str
    slope_legend: list[SlopeLegendItem]
    aspect_legend: list[AspectLegendItem]
    stats: TerrainStats


# The files the frontend reads, by the name the generated code uses for them.
ROOTS: dict[str, type[Model]] = {
    "weather": Weather,
    "hourly": Hourly,
    "sources": Sources,
    "terrain": TerrainMeta,
}
