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
    tokens: list[str] | None,
    sensor: str | None = None,
    product: str | None = None,
) -> list[Selection]:
    """Parse repeatable ``--sat`` tokens, plus ``--sen`` and ``--prod``.

    ``--sat SAT --sen SEN --prod PROD`` is the same selection as
    ``--sat SAT:SEN:PROD``. ``--sen`` and ``--prod`` belong to one
    satellite, so they need exactly one plain (colon-free) ``--sat``;
    several satellites are given as packed tokens instead.

    Raises:
        BhoonidhiValidationError: on malformed tokens, or ``--sen`` /
            ``--prod`` next to several ``--sat`` or a packed one.
    """
    if not tokens:
        raise BhoonidhiValidationError("At least one --sat is required.")

    selections = [parse_sat_token(t) for t in tokens]

    if sensor or product:
        if len(selections) != 1:
            raise BhoonidhiValidationError(
                "--sen and --prod work with a single --sat. To search "
                "several satellites, give each one as --sat SAT:SEN:PROD."
            )
        sole = selections[0]
        if sole.sensor or sole.product:
            raise BhoonidhiValidationError(
                f"--sat '{tokens[0]}' already names a sensor or product, so "
                "--sen and --prod can't be added to it. Use one form."
            )
        sole.sensor = sensor.strip() if sensor else None
        sole.product = product.strip() if product else None

    return selections


def product_token(disp_name: str, satellite: str, sensor: str) -> str:
    """The product part of a ``dispName``: whatever follows ``sat_sensor_``.

    ``EOS-06_OCM(GAC)_L2C-Chlorophyll`` under sensor ``OCM(GAC)`` gives
    ``L2C-Chlorophyll``; a bare ``ResourceSat-2A_AWIFS`` (no suffix) gives
    ``""``, and that product is selected as :data:`OTHERS`. Product tokens can themselves contain
    underscores (``JPSS1_VIIRS_Imagery_L1`` -> ``Imagery_L1``), so this
    strips the known ``satellite_sensor_`` prefix rather than splitting
    on ``_``.

    This is the exact split ``core.search.utils.resolve_selections`` uses
    to match a ``--sat SAT:SEN:PROD`` token back to a dispName — anywhere
    a product token is shown to a user (archive browsing, search results)
    should go through this function so the two can never drift apart.
    """
    prefix = f"{satellite}_{sensor}_"
    if disp_name.startswith(prefix):
        return disp_name[len(prefix) :]
    return ""


# The product value for a dispName with no suffix (``ResourceSat-2_AWIFS``).
# The portal labels every such product "Others", and a sensor has at most
# one of them, so the value always points at a single product.
OTHERS = "Others"


def sat_value(satellite: str, sensor: str, product: str) -> str:
    """Build the ``--sat`` string that selects exactly this product.

    ``product`` is the token from :func:`product_token`, or :data:`OTHERS`
    for a suffix-less product that shares its sensor with named ones. An
    empty string stops the value at ``SAT:SEN``, which is exact only when
    the sensor has that single product. Callers embedding this in a shell example
    still need to quote it themselves when the sensor or product
    contains parentheses, e.g. ``"EOS-06:OCM(GAC):L2C-Chlorophyll"``.
    """
    if product:
        return f"{satellite}:{sensor}:{product}"
    return f"{satellite}:{sensor}"
