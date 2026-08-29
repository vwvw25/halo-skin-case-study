"""Halo Skin product catalogue — the source of per-SKU cost for contribution-margin maths.

In a live deployment this would come from the brand's finance system or Shopify's
cost-per-item; here it is reference data shared by the fixture generator and the transform layer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Product:
    sku: str
    title: str
    price: float
    unit_cost: float
    line: str  # "core" | "premium"
    product_id: int


CATALOG: tuple[Product, ...] = (
    Product("HALO-CLEANSE-150", "Gentle Gel Cleanser 150ml", 24.0, 5.4, "core", 8101),
    Product("HALO-TONER-200", "Hydrating Essence Toner 200ml", 28.0, 6.1, "core", 8102),
    Product("HALO-NIACIN-30", "10% Niacinamide Serum 30ml", 32.0, 6.6, "core", 8103),
    Product("HALO-HA-30", "Hyaluronic Acid Serum 30ml", 34.0, 6.9, "core", 8104),
    Product("HALO-SPF-50", "Daily Mineral SPF 50", 30.0, 7.2, "core", 8105),
    Product("HALO-MOIST-50", "Barrier Repair Moisturiser 50ml", 38.0, 8.3, "core", 8106),
    Product("HALO-RETINAL-30", "Encapsulated Retinal Serum 30ml", 68.0, 12.8, "premium", 8201),
    Product("HALO-VITC-30", "15% Vitamin C + Ferulic 30ml", 62.0, 11.5, "premium", 8202),
    Product("HALO-PEPTIDE-30", "Multi-Peptide Firming Serum 30ml", 74.0, 13.9, "premium", 8203),
    Product("HALO-EYE-15", "Peptide Eye Concentrate 15ml", 58.0, 10.4, "premium", 8204),
)

BY_SKU: dict[str, Product] = {p.sku: p for p in CATALOG}
PREMIUM_SKUS: frozenset[str] = frozenset(p.sku for p in CATALOG if p.line == "premium")


def unit_cost(sku: str) -> float:
    product = BY_SKU.get(sku)
    return product.unit_cost if product else 0.0
