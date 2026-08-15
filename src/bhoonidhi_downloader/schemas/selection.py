"""A single satellite/sensor/product selection for a search.

The portal searches on a flat list of ``dispName`` tokens
(``EOS-06_OCM(GAC)_L2C-Chlorophyll``, ``ResourceSat-2A_LISS3`` ...). Each
token is one product. A :class:`Selection` names how far down that
hierarchy the user wants to narrow:

    satellite only            every sensor, every product
    satellite + sensor        every product under that sensor
    satellite + product       that product, sensor resolved from it
    satellite + sensor + product   exactly that one product

Several selections combine into one search — the portal fans them out
server-side into a single request. Resolving a selection against the
archive manifest (validity, product lookup) lives in
``core.search.utils``; this module only models and parses it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from bhoonidhi_downloader.exceptions import BhoonidhiValidationError


class Selection(BaseModel):
    """One satellite[/sensor[/product]] target within a search."""

    satellite: str = Field(description="Satellite name, e.g. ResourceSat-2A")
    sensor: str | None = Field(default=None, description="Sensor name, e.g. LISS3")
    product: str | None = Field(
        default=None,
        description="Product token — the dispName suffix, e.g. L2C-Chlorophyll",
    )

    def label(self) -> str:
        """Human-readable ``Sat/Sensor/Product`` label, omitting empty parts."""
        return "/".join(p for p in (self.satellite, self.sensor, self.product) if p)


def parse_sat_token(token: str) -> Selection:
    """Parse one ``SAT[:SEN[:PROD]]`` token into a :class:`Selection`.

    Colons separate the three levels; an empty middle field means "sensor
    omitted", so ``EOS-06::L2C-Chlorophyll`` is a product with the sensor
    left for the resolver to fill in. Whitespace around each field is
    trimmed.

    Raises:
        BhoonidhiValidationError: if the satellite is empty or the token
            has more than three colon-separated fields.
    """
    parts = [p.strip() for p in token.split(":")]
    if len(parts) > 3:
        raise BhoonidhiValidationError(
            f"Invalid --sat '{token}': expected SAT[:SEN[:PROD]], "
            f"got {len(parts)} colon-separated fields."
        )

    satellite = parts[0]
    if not satellite:
        raise BhoonidhiValidationError(
            f"Invalid --sat '{token}': satellite name is empty."
        )

    sensor = parts[1] if len(parts) >= 2 and parts[1] else None
    product = parts[2] if len(parts) >= 3 and parts[2] else None
    return Selection(satellite=satellite, sensor=sensor, product=product)


def parse_sat_tokens(
    tokens: list[str] | None, legacy_sensor: str | None = None
) -> list[Selection]:
    """Parse repeatable ``--sat`` tokens into a list of selections.

    ``legacy_sensor`` supports the older ``--sat SAT --sen SEN`` form: it
    is only valid alongside exactly one plain (colon-free) ``--sat``, and
    fills in that selection's sensor. Combining ``--sen`` with several
    ``--sat`` tokens or with a token that already carries its own
    sensor/product is rejected, since the pairing would be ambiguous.

    Raises:
        BhoonidhiValidationError: on malformed tokens or an ambiguous
            ``--sen`` combination.
    """
    if not tokens:
        raise BhoonidhiValidationError("At least one --sat is required.")

    selections = [parse_sat_token(t) for t in tokens]

    if legacy_sensor:
        if len(selections) != 1:
            raise BhoonidhiValidationError(
                "--sen only works with a single --sat. Attach the sensor "
                "directly instead, e.g. --sat SAT:SENSOR."
            )
        sole = selections[0]
        if sole.sensor or sole.product:
            raise BhoonidhiValidationError(
                f"--sen conflicts with --sat '{tokens[0]}', which already "
                f"names a sensor/product. Use one form, not both."
            )
        sole.sensor = legacy_sensor

    return selections
