"""seed drug reference rows

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-20 00:00:00.000000

Dummy data for masterdrug, gpidesc and gpilist until the real vendor feeds are
loaded. Built around the NDCs and GPIs the seeded prior_auths already carry, so
the member PA search resolves a name for every seeded row.

Idempotent: rows already present are left alone.

"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_masterdrug = sa.table(
    "masterdrug",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("ndcupchri", sa.String(11)),
    sa.column("gpi", sa.String(14)),
    sa.column("gpigenname", sa.String(60)),
    sa.column("proddescabbrev", sa.String(25)),
    sa.column("prodname", sa.String(25)),
    sa.column("manuname", sa.String(30)),
    sa.column("manuabbrev", sa.String(10)),
    sa.column("labelercode", sa.String(5)),
    sa.column("strength", sa.Numeric()),
    sa.column("strengthuom", sa.String(12)),
    sa.column("dosageform", sa.String(4)),
    sa.column("packagesize", sa.Numeric(8, 3)),
    sa.column("pkgsizeuom", sa.String(2)),
    sa.column("pkgqty", sa.Numeric(12, 3)),
    sa.column("rxotcind", sa.String(1)),
    sa.column("brandcode", sa.String(1)),
    sa.column("multisource", sa.String(1)),
    sa.column("maintdrugcode", sa.String(1)),
    sa.column("deaclasscode", sa.String(5)),
    sa.column("therclasscode", sa.String(6)),
    sa.column("gsn", sa.String(6)),
    sa.column("dispunitcode", sa.String(1)),
    sa.column("statusflag", sa.String(1)),
    sa.column("extradrug", sa.String(1)),
    sa.column("awppkgprice", sa.Numeric()),
    sa.column("awpunitprice", sa.Numeric()),
    sa.column("awpeffdate", sa.Date()),
    sa.column("wacunitprice", sa.Numeric()),
    sa.column("wacpkgprice", sa.Numeric()),
    sa.column("mddbfile", sa.String(30)),
    sa.column("mddbdate", sa.DateTime()),
    sa.column("alastchange", sa.DateTime()),
)

_gpidesc = sa.table(
    "gpidesc",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("gpi", sa.String(14)),
    sa.column("gpigenname", sa.String(60)),
)

_gpilist = sa.table(
    "gpilist",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("gpi", sa.String(15)),
    sa.column("name", sa.String(60)),
)

_LOAD_FILE = "MDDB_SEED_20260820.TXT"
_LOADED_AT = datetime(2026, 8, 20, 3, 0, 0)
_PRICE_EFFECTIVE = date(2026, 8, 1)

# WAC runs below AWP by the customary markup.
_WAC_OF_AWP = Decimal("0.8333")


# (ndc, gpi, generic name, description, brand name, manufacturer, abbrev,
#  strength, uom, form, package size, awp unit price, brand code, rx/otc,
#  maintenance, DEA class, therapeutic class, GSN)
_DRUGS = [
    # ── Adalimumab: three packages, one GPI ───────────────────────────────────
    ("00074580302", "66000015100315", "ADALIMUMAB", "HUMIRA PEN 40MG/0.4", "HUMIRA", "ABBVIE INC", "ABBVIE", "40", "MG/0.4ML", "SOAJ", "2", "3904.62", "B", "R", "Y", None, "661000", "062512"),  # noqa: E501
    ("00074580301", "66000015100315", "ADALIMUMAB", "HUMIRA PEN 40MG/0.8", "HUMIRA", "ABBVIE INC", "ABBVIE", "40", "MG/0.8ML", "SOAJ", "2", "3904.62", "B", "R", "Y", None, "661000", "062512"),  # noqa: E501
    ("00074580303", "66000015100315", "ADALIMUMAB", "HUMIRA 40MG/0.4 SYR", "HUMIRA", "ABBVIE INC", "ABBVIE", "40", "MG/0.4ML", "SOSY", "2", "3904.62", "B", "R", "Y", None, "661000", "062512"),  # noqa: E501
    # ── Metformin ────────────────────────────────────────────────────────────
    ("00093108256", "27600030010320", "METFORMIN HCL", "METFORMIN 500MG TAB", "METFORMIN HCL", "TEVA PHARMACEUTICALS USA", "TEVA", "500", "MG", "TAB", "500", "0.09", "G", "R", "Y", None, "276000", "017304"),  # noqa: E501
    ("00093108201", "27600030010320", "METFORMIN HCL", "METFORMIN 500MG TAB", "METFORMIN HCL", "TEVA PHARMACEUTICALS USA", "TEVA", "500", "MG", "TAB", "100", "0.09", "G", "R", "Y", None, "276000", "017304"),  # noqa: E501
    ("00093108205", "27600030010320", "METFORMIN HCL", "METFORMIN 850MG TAB", "METFORMIN HCL", "TEVA PHARMACEUTICALS USA", "TEVA", "850", "MG", "TAB", "1000", "0.12", "G", "R", "Y", None, "276000", "017305"),  # noqa: E501
    # ── Insulin glargine ─────────────────────────────────────────────────────
    ("00088502005", "27100010100330", "INSULIN GLARGINE", "LANTUS SOLN 100U/ML", "LANTUS", "SANOFI-AVENTIS US LLC", "SANOFI", "100", "UNIT/ML", "SOLN", "10", "28.53", "B", "R", "Y", None, "271000", "034821"),  # noqa: E501
    ("00088502001", "27100010100330", "INSULIN GLARGINE", "LANTUS SOLOSTAR PEN", "LANTUS SOLOSTAR", "SANOFI-AVENTIS US LLC", "SANOFI", "100", "UNIT/ML", "SOAJ", "15", "31.40", "B", "R", "Y", None, "271000", "034821"),  # noqa: E501
    ("00088502002", "27100010100330", "INSULIN GLARGINE", "LANTUS VIAL 10ML", "LANTUS", "SANOFI-AVENTIS US LLC", "SANOFI", "100", "UNIT/ML", "SOLN", "10", "28.53", "B", "R", "Y", None, "271000", "034821"),  # noqa: E501
    # ── Albuterol ────────────────────────────────────────────────────────────
    ("00173068220", "44200010206920", "ALBUTEROL SULFATE", "VENTOLIN HFA 18GM", "VENTOLIN HFA", "GLAXOSMITHKLINE", "GSK", "90", "MCG", "AERO", "18", "3.21", "B", "R", "N", None, "442000", "004815"),  # noqa: E501
    ("00173068224", "44200010206920", "ALBUTEROL SULFATE", "VENTOLIN HFA 8GM", "VENTOLIN HFA", "GLAXOSMITHKLINE", "GSK", "90", "MCG", "AERO", "8", "3.21", "B", "R", "N", None, "442000", "004815"),  # noqa: E501
    # ── Hydrocodone/APAP: schedule II ────────────────────────────────────────
    ("00406012405", "65991002100310", "HYDROCODONE/ACETAMINOPHEN", "HYDROCOD/APAP 5-325", "HYDROCODONE-APAP", "MALLINCKRODT INC", "MALLINCK", "5", "MG-MG", "TAB", "100", "0.28", "G", "R", "N", "C2", "659910", "062843"),  # noqa: E501
    ("00406012401", "65991002100310", "HYDROCODONE/ACETAMINOPHEN", "HYDROCOD/APAP 5-325", "HYDROCODONE-APAP", "MALLINCKRODT INC", "MALLINCK", "5", "MG-MG", "TAB", "500", "0.28", "G", "R", "N", "C2", "659910", "062843"),  # noqa: E501
    ("00406012410", "65991002100310", "HYDROCODONE/ACETAMINOPHEN", "HYDROCOD/APAP 10-325", "HYDROCODONE-APAP", "MALLINCKRODT INC", "MALLINCK", "10", "MG-MG", "TAB", "100", "0.41", "G", "R", "N", "C2", "659910", "062845"),  # noqa: E501
    # ── Sertraline ───────────────────────────────────────────────────────────
    ("00185006601", "58160040100310", "SERTRALINE HCL", "SERTRALINE 50MG TAB", "SERTRALINE HCL", "EON LABS INC", "EON LABS", "50", "MG", "TAB", "30", "0.35", "G", "R", "Y", None, "581600", "022618"),  # noqa: E501
    ("00185006605", "58160040100310", "SERTRALINE HCL", "SERTRALINE 100MG TAB", "SERTRALINE HCL", "EON LABS INC", "EON LABS", "100", "MG", "TAB", "30", "0.44", "G", "R", "Y", None, "581600", "022619"),  # noqa: E501
    # ── Montelukast ──────────────────────────────────────────────────────────
    ("00006071154", "44600020100320", "MONTELUKAST SODIUM", "SINGULAIR 10MG TAB", "SINGULAIR", "MERCK SHARP & DOHME", "MERCK", "10", "MG", "TAB", "30", "6.82", "B", "R", "Y", None, "446000", "029231"),  # noqa: E501
    ("00006071131", "44600020100320", "MONTELUKAST SODIUM", "SINGULAIR 5MG CHEW", "SINGULAIR", "MERCK SHARP & DOHME", "MERCK", "5", "MG", "TABC", "30", "6.82", "B", "R", "Y", None, "446000", "029230"),  # noqa: E501
    # ── Omeprazole ───────────────────────────────────────────────────────────
    ("00378512093", "49270060000320", "OMEPRAZOLE", "OMEPRAZOLE DR 20MG", "OMEPRAZOLE", "MYLAN PHARMACEUTICALS", "MYLAN", "20", "MG", "CAPD", "1000", "0.42", "G", "R", "Y", None, "492700", "008412"),  # noqa: E501
    ("00378512001", "49270060000320", "OMEPRAZOLE", "OMEPRAZOLE DR 40MG", "OMEPRAZOLE", "MYLAN PHARMACEUTICALS", "MYLAN", "40", "MG", "CAPD", "30", "0.68", "G", "R", "Y", None, "492700", "008413"),  # noqa: E501
    # ── Gabapentin ───────────────────────────────────────────────────────────
    ("00115129701", "72600030000320", "GABAPENTIN", "GABAPENTIN 300MG CAP", "GABAPENTIN", "AMNEAL PHARMACEUTICALS", "AMNEAL", "300", "MG", "CAP", "100", "0.31", "G", "R", "Y", None, "726000", "017644"),  # noqa: E501
    ("00115129703", "72600030000320", "GABAPENTIN", "GABAPENTIN 600MG TAB", "GABAPENTIN", "AMNEAL PHARMACEUTICALS", "AMNEAL", "600", "MG", "TAB", "100", "0.52", "G", "R", "Y", None, "726000", "017645"),  # noqa: E501
    # ── Levothyroxine, brand GPI ─────────────────────────────────────────────
    ("00074668001", "28100010100310", "LEVOTHYROXINE SODIUM", "SYNTHROID 50MCG TAB", "SYNTHROID", "ABBVIE INC", "ABBOTT", "50", "MCG", "TAB", "90", "1.06", "B", "R", "Y", None, "281000", "004512"),  # noqa: E501
    ("00074668003", "28100010100310", "LEVOTHYROXINE SODIUM", "SYNTHROID 100MCG TAB", "SYNTHROID", "ABBVIE INC", "ABBOTT", "100", "MCG", "TAB", "90", "1.06", "B", "R", "Y", None, "281000", "004514"),  # noqa: E501
    # ── Atorvastatin, brand ──────────────────────────────────────────────────
    ("00071015523", "39400010100310", "ATORVASTATIN CALCIUM", "LIPITOR 20MG TAB", "LIPITOR", "PARKE-DAVIS DIV OF PFIZER", "PARKE-DAV", "20", "MG", "TAB", "90", "6.24", "B", "R", "Y", None, "394000", "017732"),  # noqa: E501
    ("00071015510", "39400010100310", "ATORVASTATIN CALCIUM", "LIPITOR 10MG TAB", "LIPITOR", "PARKE-DAVIS DIV OF PFIZER", "PARKE-DAV", "10", "MG", "TAB", "90", "6.24", "B", "R", "Y", None, "394000", "017731"),  # noqa: E501
    ("00071015540", "39400010100310", "ATORVASTATIN CALCIUM", "LIPITOR 40MG TAB", "LIPITOR", "PARKE-DAVIS DIV OF PFIZER", "PARKE-DAV", "40", "MG", "TAB", "90", "9.35", "B", "R", "Y", None, "394000", "017733"),  # noqa: E501
    # ── Amoxicillin ──────────────────────────────────────────────────────────
    ("00093417401", "01200010100320", "AMOXICILLIN", "AMOXICILLIN 500MG CAP", "AMOXICILLIN", "TEVA PHARMACEUTICALS USA", "TEVA", "500", "MG", "CAP", "100", "0.22", "G", "R", "N", None, "012000", "001642"),  # noqa: E501
    ("00093417405", "01200010100320", "AMOXICILLIN", "AMOXICILLIN 250MG CAP", "AMOXICILLIN", "TEVA PHARMACEUTICALS USA", "TEVA", "250", "MG", "CAP", "100", "0.16", "G", "R", "N", None, "012000", "001641"),  # noqa: E501
    # ── Amlodipine ───────────────────────────────────────────────────────────
    ("00591036305", "33200030100310", "AMLODIPINE BESYLATE", "AMLODIPINE 5MG TAB", "AMLODIPINE BESYLATE", "ACTAVIS PHARMA INC", "ACTAVIS", "5", "MG", "TAB", "90", "0.18", "G", "R", "Y", None, "332000", "017015"),  # noqa: E501
    ("00591036301", "33200030100310", "AMLODIPINE BESYLATE", "AMLODIPINE 10MG TAB", "AMLODIPINE BESYLATE", "ACTAVIS PHARMA INC", "ACTAVIS", "10", "MG", "TAB", "90", "0.24", "G", "R", "Y", None, "332000", "017016"),  # noqa: E501
    # ── Levothyroxine, generic GPI ───────────────────────────────────────────
    ("00781505701", "28100010100315", "LEVOTHYROXINE SODIUM", "LEVOTHYROXINE 75MCG", "LEVOTHYROXINE SODIUM", "SANDOZ INC", "SANDOZ", "75", "MCG", "TAB", "90", "0.42", "G", "R", "Y", None, "281000", "004513"),  # noqa: E501
    ("00781505710", "28100010100315", "LEVOTHYROXINE SODIUM", "LEVOTHYROXINE 125MCG", "LEVOTHYROXINE SODIUM", "SANDOZ INC", "SANDOZ", "125", "MCG", "TAB", "90", "0.42", "G", "R", "Y", None, "281000", "004516"),  # noqa: E501
    # ── One prefix, two GPIs: the pair outvotes the single ────────────────────
    ("00093721410", "39400010100310", "ATORVASTATIN CALCIUM", "ATORVASTATIN 10MG TAB", "ATORVASTATIN CALCIUM", "TEVA PHARMACEUTICALS USA", "TEVA", "10", "MG", "TAB", "90", "0.62", "G", "R", "Y", None, "394000", "017731"),  # noqa: E501
    ("00093721430", "39400010100310", "ATORVASTATIN CALCIUM", "ATORVASTATIN 20MG TAB", "ATORVASTATIN CALCIUM", "TEVA PHARMACEUTICALS USA", "TEVA", "20", "MG", "TAB", "90", "0.71", "G", "R", "Y", None, "394000", "017732"),  # noqa: E501
    ("00093721490", "39400010100999", "ATORVASTATIN/EZETIMIBE", "ATORVAST/EZETIMIBE", "ATORVASTATIN-EZETIMIBE", "TEVA PHARMACEUTICALS USA", "TEVA", "10", "MG-MG", "TAB", "30", "4.18", "G", "R", "Y", None, "394000", "071204"),  # noqa: E501
    # ── Rounding out the therapeutic classes ─────────────────────────────────
    ("00378180101", "36100010100320", "LISINOPRIL", "LISINOPRIL 10MG TAB", "LISINOPRIL", "MYLAN PHARMACEUTICALS", "MYLAN", "10", "MG", "TAB", "100", "0.14", "G", "R", "Y", None, "361000", "004825"),  # noqa: E501
    ("00054327763", "22100010100320", "PREDNISONE", "PREDNISONE 10MG TAB", "PREDNISONE", "ROXANE LABORATORIES", "ROXANE", "10", "MG", "TAB", "100", "0.16", "G", "R", "N", None, "221000", "008021"),  # noqa: E501
    ("00904582161", "66100010100320", "IBUPROFEN", "IBUPROFEN 200MG TAB", "IBUPROFEN", "MAJOR PHARMACEUTICALS", "MAJOR", "200", "MG", "TAB", "100", "0.05", "G", "O", "N", None, "661000", "004312"),  # noqa: E501
    ("00002751501", "27200065100320", "DULAGLUTIDE", "TRULICITY 1.5MG PEN", "TRULICITY", "ELI LILLY AND COMPANY", "LILLY", "1.5", "MG/0.5ML", "SOAJ", "2", "320.16", "B", "R", "Y", None, "272000", "072841"),  # noqa: E501
]

# GPI -> generic name, for every GPI the drugs above carry.
_GPI_DESCRIPTIONS = [
    ("01200010100320", "AMOXICILLIN"),
    ("22100010100320", "PREDNISONE"),
    ("27100010100330", "INSULIN GLARGINE"),
    ("27200065100320", "DULAGLUTIDE"),
    ("27600030010320", "METFORMIN HCL"),
    ("28100010100310", "LEVOTHYROXINE SODIUM"),
    ("28100010100315", "LEVOTHYROXINE SODIUM"),
    ("33200030100310", "AMLODIPINE BESYLATE"),
    ("36100010100320", "LISINOPRIL"),
    ("39400010100310", "ATORVASTATIN CALCIUM"),
    ("39400010100999", "ATORVASTATIN/EZETIMIBE"),
    ("44200010206920", "ALBUTEROL SULFATE"),
    ("44600020100320", "MONTELUKAST SODIUM"),
    ("49270060000320", "OMEPRAZOLE"),
    ("58160040100310", "SERTRALINE HCL"),
    ("65991002100310", "HYDROCODONE/ACETAMINOPHEN"),
    ("66000015100315", "ADALIMUMAB"),
    ("66100010100320", "IBUPROFEN"),
    ("72600030000320", "GABAPENTIN"),
]

# Class-level GPIs, keyed with the leading "G" the table uses. Two digits is a
# therapeutic class, four a drug group, six a drug class.
_GPI_CLASSES = [
    ("G01", "ANTI-INFECTIVE AGENTS"),
    ("G0120", "PENICILLINS"),
    ("G22", "CORTICOSTEROIDS"),
    ("G27", "ENDOCRINE AND METABOLIC AGENTS"),
    ("G2710", "INSULINS"),
    ("G2720", "ANTIDIABETICS - INCRETIN MIMETICS"),
    ("G2760", "ANTIDIABETICS - BIGUANIDES"),
    ("G28", "THYROID AGENTS"),
    ("G33", "CARDIOVASCULAR AGENTS"),
    ("G3320", "CALCIUM CHANNEL BLOCKERS"),
    ("G36", "ACE INHIBITORS"),
    ("G39", "ANTIHYPERLIPIDEMICS"),
    ("G3940", "HMG COA REDUCTASE INHIBITORS"),
    ("G394000", "STATINS - SINGLE ENTITY"),
    ("G44", "RESPIRATORY AGENTS"),
    ("G4420", "BETA ADRENERGIC AGENTS"),
    ("G4460", "LEUKOTRIENE MODIFIERS"),
    ("G49", "GASTROINTESTINAL AGENTS"),
    ("G4927", "PROTON PUMP INHIBITORS"),
    ("G58", "PSYCHOTHERAPEUTIC AGENTS"),
    ("G5816", "SSRI ANTIDEPRESSANTS"),
    ("G65", "ANALGESICS - ANTI-INFLAMMATORY"),
    ("G6599", "NARCOTIC ANALGESIC COMBINATIONS"),
    ("G66", "BIOLOGICAL AND IMMUNOLOGIC AGENTS"),
    ("G72", "NEUROMUSCULAR AGENTS"),
]


def _drug_row(seed: tuple) -> dict:
    (
        ndc, gpi, gen_name, description, prod_name, manufacturer, abbrev,
        strength, uom, form, package_size, awp_unit, brand_code, rx_otc,
        maintenance, dea_class, ther_class, gsn,
    ) = seed

    unit_price = Decimal(awp_unit)
    size = Decimal(package_size)
    return {
        "id": uuid.uuid4(),
        "ndcupchri": ndc,
        "gpi": gpi,
        "gpigenname": gen_name,
        "proddescabbrev": description,
        "prodname": prod_name,
        "manuname": manufacturer,
        "manuabbrev": abbrev,
        "labelercode": ndc[:5],
        "strength": Decimal(strength),
        "strengthuom": uom,
        "dosageform": form,
        "packagesize": size,
        "pkgsizeuom": "EA",
        "pkgqty": size,
        "rxotcind": rx_otc,
        "brandcode": brand_code,
        # Multi-source where a generic exists for the molecule.
        "multisource": "Y" if brand_code == "G" else "N",
        "maintdrugcode": maintenance,
        "deaclasscode": dea_class,
        "therclasscode": ther_class,
        "gsn": gsn,
        "dispunitcode": "1",
        "statusflag": "A",
        "extradrug": "N",
        "awpunitprice": unit_price,
        "awppkgprice": (unit_price * size).quantize(Decimal("0.01")),
        "awpeffdate": _PRICE_EFFECTIVE,
        "wacunitprice": (unit_price * _WAC_OF_AWP).quantize(Decimal("0.01")),
        "wacpkgprice": (unit_price * size * _WAC_OF_AWP).quantize(Decimal("0.01")),
        "mddbfile": _LOAD_FILE,
        "mddbdate": _LOADED_AT,
        "alastchange": _LOADED_AT,
    }


def _existing(bind, table: str, column: str) -> set[str]:
    rows = bind.execute(sa.text(f"SELECT {column} FROM {table}")).fetchall()  # noqa: S608
    return {value for (value,) in rows if value is not None}


def upgrade() -> None:
    bind = op.get_bind()

    known_ndcs = _existing(bind, "masterdrug", "ndcupchri")
    drugs = [
        _drug_row(seed) for seed in _DRUGS if seed[0] not in known_ndcs
    ]
    if drugs:
        op.bulk_insert(_masterdrug, drugs)

    known_gpis = _existing(bind, "gpidesc", "gpi")
    descriptions = [
        {"id": uuid.uuid4(), "gpi": gpi, "gpigenname": name}
        for gpi, name in _GPI_DESCRIPTIONS
        if gpi not in known_gpis
    ]
    if descriptions:
        op.bulk_insert(_gpidesc, descriptions)

    known_classes = _existing(bind, "gpilist", "gpi")
    classes = [
        {"id": uuid.uuid4(), "gpi": gpi, "name": name}
        for gpi, name in _GPI_CLASSES
        if gpi not in known_classes
    ]
    if classes:
        op.bulk_insert(_gpilist, classes)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        _gpilist.delete().where(
            _gpilist.c.gpi.in_([gpi for gpi, _name in _GPI_CLASSES])
        )
    )
    bind.execute(
        _gpidesc.delete().where(
            _gpidesc.c.gpi.in_([gpi for gpi, _name in _GPI_DESCRIPTIONS])
        )
    )
    bind.execute(
        _masterdrug.delete().where(
            _masterdrug.c.ndcupchri.in_([seed[0] for seed in _DRUGS])
        )
    )
