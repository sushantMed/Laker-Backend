"""seed subscriber rows

Revision ID: e2b3c4d5f6a7
Revises: d819b99fe534
Create Date: 2026-08-20 00:00:00.000000

Dummy cardholders for the SUBSCRIBER lookup, one row per (subscribernum,
personcode) pair the seeded prior_auths carry. Without them the subscriber PA
search verifies against an empty table and 404s on every request.

Names come from the seeded members where one exists; the rest are invented.

Idempotent: rows already present are left alone.

"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2b3c4d5f6a7"
down_revision: Union[str, Sequence[str], None] = "d819b99fe534"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_subscriber = sa.table(
    "SUBSCRIBER",
    sa.column("SUBSCRIBERNUM", sa.String(45)),
    sa.column("PERSONCODE", sa.String(2)),
    sa.column("CLIENTCODE", sa.String(10)),
    sa.column("LASTNAME", sa.String(25)),
    sa.column("FIRSTNAME", sa.String(25)),
    sa.column("DOB", sa.DateTime()),
    sa.column("GENDER", sa.String(1)),
    sa.column("RELCODE", sa.String(2)),
    sa.column("STATUS", sa.String(1)),
    sa.column("ADDR1", sa.String(55)),
    sa.column("CITY", sa.String(20)),
    sa.column("STATE", sa.String(2)),
    sa.column("ZIP", sa.String(11)),
    sa.column("HOMEPHONE", sa.String(10)),
    sa.column("DATEENTERED", sa.DateTime()),
)

_CLIENT_CODE = "CLI001"
_ENTERED = datetime(2026, 1, 2, 9, 0, 0)

# (subscribernum, personcode, lastname, firstname, dob, gender, city, state, zip)
_SUBSCRIBERS = [
    # The Martinez family -- INS001 carries four person codes.
    ("INS001", "01", "MARTINEZ", "CARLOS", "1978-04-12", "M", "CHICAGO", "IL", "60601"),
    ("INS001", "02", "MARTINEZ", "SOFIA", "1980-09-25", "F", "CHICAGO", "IL", "60601"),
    ("INS001", "03", "MARTINEZ", "LUCAS", "2008-03-07", "M", "CHICAGO", "IL", "60601"),
    ("INS001", "04", "MARTINEZ", "ISABELLA", "2011-11-19", "F", "CHICAGO", "IL", "60601"),  # noqa: E501
    ("INS002", "01", "THOMPSON", "JAMES", "1975-06-30", "M", "PEORIA", "IL", "61602"),
    ("INS002", "02", "THOMPSON", "SARAH", "1977-02-14", "F", "PEORIA", "IL", "61602"),
    ("INS003", "01", "NGUYEN", "MINH", "1990-08-18", "M", "SPRINGFIELD", "IL", "62704"),
    # Cardholders the prior_auths reference but no member row describes.
    ("INS013", "01", "OKAFOR", "ADAEZE", "1982-05-03", "F", "AURORA", "IL", "60505"),
    ("INS014", "01", "PATEL", "RAVI", "1969-12-11", "M", "NAPERVILLE", "IL", "60540"),
    ("INS015", "01", "KOWALSKI", "ANNA", "1986-07-22", "F", "JOLIET", "IL", "60432"),
    ("INS016", "01", "RIVERA", "DIEGO", "1993-01-30", "M", "ELGIN", "IL", "60120"),
    ("INS017", "01", "BRENNAN", "MAEVE", "1971-09-09", "F", "ROCKFORD", "IL", "61101"),
    ("INS018", "01", "OSEI", "KWAME", "1988-04-17", "M", "CICERO", "IL", "60804"),
    ("INS019", "01", "LARSEN", "INGRID", "1965-03-26", "F", "EVANSTON", "IL", "60201"),
    ("INS020", "01", "HAMMOND", "GRACE", "1979-10-05", "F", "DECATUR", "IL", "62521"),
    ("INS021", "01", "FERREIRA", "TIAGO", "1991-06-14", "M", "BLOOMINGTON", "IL", "61701"),  # noqa: E501
    ("INS022", "01", "WHITFIELD", "MARCUS", "1974-08-28", "M", "CHAMPAIGN", "IL", "61820"),  # noqa: E501
    ("INS023", "01", "DELACROIX", "CLAIRE", "1983-02-07", "F", "SKOKIE", "IL", "60076"),
    ("INS024", "01", "YAMADA", "KENJI", "1996-11-02", "M", "OAK PARK", "IL", "60301"),
]


def _row(seed: tuple) -> dict:
    subscribernum, personcode, lastname, firstname, dob, gender, city, state, zip_ = seed
    return {
        "SUBSCRIBERNUM": subscribernum,
        "PERSONCODE": personcode,
        "CLIENTCODE": _CLIENT_CODE,
        "LASTNAME": lastname,
        "FIRSTNAME": firstname,
        "DOB": datetime.strptime(dob, "%Y-%m-%d"),
        "GENDER": gender,
        # 01 is the cardholder, 02 a spouse, anything above a dependent.
        "RELCODE": personcode,
        "STATUS": "A",
        "ADDR1": f"{100 + int(personcode)} MAIN ST",
        "CITY": city,
        "STATE": state,
        "ZIP": zip_,
        "HOMEPHONE": "3125550100",
        "DATEENTERED": _ENTERED,
    }


def upgrade() -> None:
    bind = op.get_bind()
    existing = {
        (subscribernum, personcode)
        for subscribernum, personcode in bind.execute(
            sa.text('SELECT "SUBSCRIBERNUM", "PERSONCODE" FROM "SUBSCRIBER"')
        ).fetchall()
    }

    rows = [_row(seed) for seed in _SUBSCRIBERS if (seed[0], seed[1]) not in existing]
    if rows:
        op.bulk_insert(_subscriber, rows)


def downgrade() -> None:
    bind = op.get_bind()
    for subscribernum, personcode, *_rest in _SUBSCRIBERS:
        bind.execute(
            sa.text(
                'DELETE FROM "SUBSCRIBER" WHERE "SUBSCRIBERNUM" = :s '
                'AND "PERSONCODE" = :p AND "CLIENTCODE" = :c'
            ),
            {"s": subscribernum, "p": personcode, "c": _CLIENT_CODE},
        )
