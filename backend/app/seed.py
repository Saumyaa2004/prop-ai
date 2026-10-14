"""
Prop AI - seed fictional demonstration properties.

Every listing here is FICTIONAL demo data for development and testing.
Run from the backend folder with:  python -m app.seed

Safe to run repeatedly: listings whose listing_code already exists are skipped.
"""

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Property

# Integer math only: int(1.38 * 10_000_000) gives 13_799_999 because of
# floating-point rounding. Write prices in lakh instead (1.38 crore = 138 lakh).
LAKH = 100_000


def _listing(
    code: str,
    title: str,
    note: str,
    *,
    listing_type: str,
    property_type: str,
    bedrooms: int,
    bathrooms: int,
    area_sqft: int,
    price_inr: int,
    locality: str,
    furnishing: str,
    amenities: list[str],
    status: str = "available",
    available_from: date | None = None,
) -> dict[str, Any]:
    """Build one listing dict with the shared defaults filled in."""
    return {
        "listing_code": code,
        "title": title,
        "description": note,  # fictional; the site footer and is_demo_data say so
        "listing_type": listing_type,
        "property_type": property_type,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "area_sqft": area_sqft,
        "price_inr": price_inr,
        "city": "Mumbai",
        "locality": locality,
        "furnishing": furnishing,
        "amenities": amenities,
        "status": status,
        "available_from": available_from,
        "is_demo_data": True,
    }


DEMO_PROPERTIES: list[dict[str, Any]] = [
    # ---------- FOR SALE (price_inr = total price) ----------
    _listing(
        "PAI-DEMO-001", "Lakeview Residency 2BHK", "Ready-to-move flat near Powai Lake.",
        listing_type="sale", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=780, price_inr=145 * LAKH, locality="Powai",
        furnishing="semi_furnished", amenities=["parking", "lift", "security", "power_backup"],
    ),
    _listing(
        "PAI-DEMO-002", "Hiranandani Gardens 2BHK", "Corner unit with a large balcony.",
        listing_type="sale", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=850, price_inr=138 * LAKH, locality="Powai",
        furnishing="unfurnished", amenities=["parking", "balcony", "lift", "security", "gym"],
    ),
    _listing(
        "PAI-DEMO-003", "Skyline Towers 2BHK", "Premium tower with resort-style amenities.",
        listing_type="sale", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=910, price_inr=185 * LAKH, locality="Powai",
        furnishing="semi_furnished",
        amenities=["parking", "balcony", "gym", "swimming_pool", "clubhouse", "lift", "security"],
    ),
    _listing(
        "PAI-DEMO-004", "Green Heights 2BHK", "Well-priced flat in an older society. No parking.",
        listing_type="sale", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=760, price_inr=132 * LAKH, locality="Powai",
        furnishing="unfurnished", amenities=["lift", "security"],
    ),
    _listing(
        "PAI-DEMO-005", "Lakeside Grand 3BHK", "Spacious family home with lake views.",
        listing_type="sale", property_type="apartment", bedrooms=3, bathrooms=3,
        area_sqft=1250, price_inr=275 * LAKH, locality="Powai",
        furnishing="semi_furnished",
        amenities=["parking", "balcony", "gym", "swimming_pool", "clubhouse", "lift", "security"],
    ),
    _listing(
        "PAI-DEMO-006", "Lokhandwala Park 2BHK", "Close to Andheri West metro station.",
        listing_type="sale", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=820, price_inr=149 * LAKH, locality="Andheri West",
        furnishing="semi_furnished", amenities=["parking", "balcony", "lift", "security"],
    ),
    _listing(
        "PAI-DEMO-007", "Marol Residency 2BHK", "Near the airport and business parks.",
        listing_type="sale", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=750, price_inr=128 * LAKH, locality="Andheri East",
        furnishing="unfurnished", amenities=["parking", "lift", "security", "power_backup"],
    ),
    _listing(
        "PAI-DEMO-008", "Versova Studio-Plus 1BHK", "Compact flat, walking distance to the beach.",
        listing_type="sale", property_type="apartment", bedrooms=1, bathrooms=1,
        area_sqft=520, price_inr=98 * LAKH, locality="Andheri West",
        furnishing="semi_furnished", amenities=["lift", "security"],
    ),
    _listing(
        "PAI-DEMO-009", "Carter Road Sky Penthouse", "Sea-facing duplex penthouse.",
        listing_type="sale", property_type="penthouse", bedrooms=4, bathrooms=5,
        area_sqft=2600, price_inr=1250 * LAKH, locality="Bandra West",
        furnishing="fully_furnished",
        amenities=["parking", "balcony", "gym", "swimming_pool", "lift", "security", "power_backup"],
    ),
    _listing(
        "PAI-DEMO-010", "Sun Hills Villa", "Independent villa with a private garden.",
        listing_type="sale", property_type="villa", bedrooms=4, bathrooms=4,
        area_sqft=2400, price_inr=420 * LAKH, locality="Thane West",
        furnishing="semi_furnished", amenities=["parking", "garden", "security", "power_backup"],
        status="under_offer",
    ),
    _listing(
        "PAI-DEMO-011", "Oberoi Link 2BHK", "Recently sold; kept to test status filtering.",
        listing_type="sale", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=800, price_inr=135 * LAKH, locality="Goregaon East",
        furnishing="unfurnished", amenities=["parking", "balcony", "lift"],
        status="sold",
    ),
    # ---------- FOR RENT (price_inr = monthly rent) ----------
    _listing(
        "PAI-DEMO-012", "Powai Vista 1BHK Rental", "Furnished flat ideal for working professionals.",
        listing_type="rent", property_type="apartment", bedrooms=1, bathrooms=1,
        area_sqft=540, price_inr=42_000, locality="Powai",
        furnishing="fully_furnished", amenities=["parking", "balcony", "lift", "security"],
        available_from=date(2026, 11, 1),
    ),
    _listing(
        "PAI-DEMO-013", "Hillside Court 2BHK Rental", "Family-friendly society with a pool.",
        listing_type="rent", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=820, price_inr=65_000, locality="Powai",
        furnishing="semi_furnished",
        amenities=["parking", "balcony", "gym", "swimming_pool", "lift", "security"],
        available_from=date(2026, 11, 15),
    ),
    _listing(
        "PAI-DEMO-014", "IIT Gate Studio Rental", "Compact studio near the IIT campus.",
        listing_type="rent", property_type="studio", bedrooms=0, bathrooms=1,
        area_sqft=380, price_inr=32_000, locality="Powai",
        furnishing="fully_furnished", amenities=["lift", "security", "power_backup"],
        available_from=date(2026, 10, 20),
    ),
    _listing(
        "PAI-DEMO-015", "Shade 1BHK Rental", "Budget-friendly rental. No parking.",
        listing_type="rent", property_type="apartment", bedrooms=1, bathrooms=1,
        area_sqft=500, price_inr=44_000, locality="Powai",
        furnishing="semi_furnished", amenities=["balcony", "lift", "security"],
        available_from=date(2026, 11, 1),
    ),
    _listing(
        "PAI-DEMO-016", "Four Bungalows 2BHK Rental", "Fully furnished, close to cafes and metro.",
        listing_type="rent", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=800, price_inr=75_000, locality="Andheri West",
        furnishing="fully_furnished", amenities=["parking", "balcony", "lift", "security", "gym"],
        available_from=date(2026, 12, 1),
    ),
    _listing(
        "PAI-DEMO-017", "Chembur Greens 2BHK Rental", "Currently rented; kept to test status filtering.",
        listing_type="rent", property_type="apartment", bedrooms=2, bathrooms=2,
        area_sqft=780, price_inr=52_000, locality="Chembur",
        furnishing="semi_furnished", amenities=["parking", "lift", "security"],
        status="rented",
    ),
]


def seed_properties() -> None:
    """Insert demo listings, skipping any listing_code that already exists."""
    with SessionLocal() as session:
        statement = (
            insert(Property)
            .values(DEMO_PROPERTIES)
            .on_conflict_do_nothing(index_elements=["listing_code"])
        )
        result = session.execute(statement)
        session.commit()
        total = session.scalar(select(func.count()).select_from(Property))

    print(f"Inserted {result.rowcount} new demo properties. Total in database: {total}.")


if __name__ == "__main__":
    seed_properties()