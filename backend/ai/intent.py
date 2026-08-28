"""Intent detection and product understanding.

Deliberately rule-based. Intent routing decides which retrieval filters and which response
sections apply -- it is control flow, not content -- so a deterministic classifier is both
cheaper and easier to reason about than a model call, and it works with no API key. The
LLM refines the *product profile* when available (`enrich_product`), because free-text
product descriptions genuinely need language understanding.
"""
from __future__ import annotations

import re

from backend.models.schemas import ProductUnderstanding
from backend.retrieval.text import extract_standard_numbers, tokenize

# Order matters: the first pattern that matches wins. `product_standard` is checked before
# `certification` because "I manufacture X, which standards apply?" contains certification
# vocabulary ("apply") but is squarely a standards-discovery question, and routing it to
# certification suppresses the standard recommendations the user actually asked for.
INTENT_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("compare", ("compare", "difference between", "versus", " vs ")),
    ("product_standard", ("i manufacture", "i make", "i produce", "we manufacture",
                          "we make", "we produce", "which standard", "what standard",
                          "applicable standard", "standards apply", "standard applies",
                          "standards may apply")),
    ("hallmarking", ("hallmark", "hallmarking", "huid", "carat", "karat", "jewellery",
                     "jewelry", "gold", "silver", "purity", "assay", "fineness")),
    ("laboratory", ("laboratory", "lab ", "labs", "test my", "where can i test",
                    "testing facility", "recognised lab", "recognized lab", "where to test",
                    "get it tested", "get my product tested")),
    ("compliance", ("checklist", "compliance", "steps to comply", "what do i need to do")),
    ("consumer", ("complaint", "consumer", "fake", "counterfeit", "how do i check",
                  "is it genuine", "bis care")),
    ("certification", ("certification", "certificate", "certify", "isi mark", "licence",
                       "license", "crs", "registration", "fmcs", "qco",
                       "certification scheme", "how do i get bis")),
    ("standard_lookup", ("explain is", "what is is", "scope of", "clause")),
]

PRODUCT_TRIGGERS = (
    "i manufacture", "i make", "i produce", "we manufacture", "we make", "we produce",
    "my product", "our product", "i am making", "manufacturing",
)

MATERIALS = {
    "stainless steel": ["stainless", "ss304", "ss 304"],
    "steel": ["steel", "mild steel"],
    "aluminium": ["aluminium", "aluminum"],
    "copper": ["copper"],
    "brass": ["brass"],
    "plastic": ["plastic", "polymer", "polypropylene", "polycarbonate", "pvc", "abs"],
    "glass": ["glass"],
    "wood": ["wood", "wooden", "timber"],
    "gold": ["gold"],
    "silver": ["silver"],
    "textile": ["textile", "fabric", "cotton"],
    "cement": ["cement", "concrete"],
    "rubber": ["rubber", "elastomer"],
}

CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Precious metal - jewellery", ("jewellery", "jewelry", "ornament", "necklace", "ring", "bangle")),
    ("Food-contact household product", ("lunch box", "tiffin", "utensil", "cookware", "bottle",
                                        "flask", "container", "plate", "bowl", "kitchen", "casserole")),
    ("Electrical appliance", ("appliance", "heater", "iron", "mixer", "grinder", "fan", "geyser", "kettle")),
    ("Electrical cable", ("cable", "wire", "conductor", "wiring")),
    ("Electrical accessory", ("switch", "socket", "plug", "outlet", "mcb", "holder")),
    ("Lighting product", ("led", "lamp", "bulb", "luminaire", "light")),
    ("Children's product", ("toy", "toys", "pram", "stroller", "cradle")),
    ("Personal protective equipment", ("helmet", "gloves", "goggles", "safety shoe", "mask")),
    ("Food and beverage", ("packaged water", "drinking water", "beverage", "juice", "food product")),
    ("Construction material", ("cement", "brick", "tile", "steel bar", "tmt", "aggregate")),
    ("Raw material - metal", ("sheet", "strip", "coil", "billet", "ingot")),
]

INDUSTRY_BY_CATEGORY = {
    "Precious metal - jewellery": "Gems and jewellery",
    "Food-contact household product": "Household and kitchenware",
    "Electrical appliance": "Electrical and electronics",
    "Electrical cable": "Electrical and electronics",
    "Electrical accessory": "Electrical and electronics",
    "Lighting product": "Electrical and electronics",
    "Children's product": "Toys and juvenile products",
    "Personal protective equipment": "Automotive and safety equipment",
    "Food and beverage": "Food processing",
    "Construction material": "Cement and construction",
    "Raw material - metal": "Metals and metal products",
}

TARGET_USERS = {
    "school children": ("school", "children", "kids", "student"),
    "infants": ("infant", "baby", "toddler"),
    "industrial users": ("industrial", "factory", "plant"),
    "general consumers": ("consumer", "household", "home", "domestic"),
}

USE_HINTS = {
    "carrying and storing food": ("lunch box", "tiffin", "carry food", "food storage"),
    "cooking and serving food": ("cooking", "serving", "utensil", "cookware"),
    "drinking water storage": ("water bottle", "drinking", "flask"),
    "electrical installation": ("wiring", "installation", "panel"),
    "personal protection": ("helmet", "protection", "safety"),
    "play by children": ("toy", "play"),
    "construction": ("construction", "building", "concrete"),
}

PRODUCT_NOUN_RE = re.compile(
    r"(?:i|we)\s+(?:manufacture|make|produce|am making|are making|sell)\s+(.{3,80}?)"
    r"(?:\.|,|\bfor\b|\bwhich\b|\bwhat\b|$)",
    re.IGNORECASE,
)


def detect_intent(message: str) -> str:
    text = (message or "").lower()

    if extract_standard_numbers(message) and any(
        k in text for k in ("explain", "what is", "scope", "clause", "about", "simple", "summar")
    ):
        return "standard_lookup"

    for intent, keywords in INTENT_PATTERNS:
        if any(k in text for k in keywords):
            return intent

    if extract_standard_numbers(message):
        return "standard_lookup"
    return "general"


def looks_like_product_description(message: str) -> bool:
    text = (message or "").lower()
    if any(t in text for t in PRODUCT_TRIGGERS):
        return True
    # A noun-heavy sentence with a known material or category is very likely a product.
    return bool(_find_materials(text)) and bool(_find_category(text))


def _find_materials(text: str) -> list[str]:
    found: list[str] = []
    for canonical, variants in MATERIALS.items():
        if any(v in text for v in variants):
            found.append(canonical)
    # "stainless steel" implies "steel"; keep only the most specific.
    if "stainless steel" in found and "steel" in found:
        found.remove("steel")
    return found


def _find_category(text: str) -> str:
    for category, keywords in CATEGORY_RULES:
        if any(k in text for k in keywords):
            return category
    return ""


def _find_target_user(text: str) -> str:
    for label, keywords in TARGET_USERS.items():
        if any(k in text for k in keywords):
            return label
    return ""


def _find_use(text: str) -> str:
    for label, keywords in USE_HINTS.items():
        if any(k in text for k in keywords):
            return label
    return ""


def _find_product_name(message: str, text: str) -> str:
    m = PRODUCT_NOUN_RE.search(message)
    if m:
        return " ".join(m.group(1).split()).strip(" .,").title()

    # Fall back to the longest known category keyword present in the text.
    best = ""
    for _category, keywords in CATEGORY_RULES:
        for k in keywords:
            if k in text and len(k) > len(best):
                best = k
    return best.title()


def understand_product(description: str) -> ProductUnderstanding:
    """Rule-based product profile. Refined by the LLM when one is configured."""
    text = (description or "").lower()
    materials = _find_materials(text)
    category = _find_category(text)

    characteristics: list[str] = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(mm|cm|ml|litre|liter|l|kg|g|v|w|a)\b", text):
        characteristics.append(f"{match.group(1)} {match.group(2)}")
    for word in ("insulated", "vacuum", "double wall", "leak proof", "airtight",
                 "rechargeable", "portable", "food grade"):
        if word in text:
            characteristics.append(word)

    return ProductUnderstanding(
        product=_find_product_name(description, text),
        category=category,
        materials=materials,
        intended_use=_find_use(text),
        industry=INDUSTRY_BY_CATEGORY.get(category, ""),
        target_user=_find_target_user(text),
        characteristics=characteristics[:6],
        notes="Extracted from the description you provided; correct anything that is wrong.",
    )


def build_retrieval_query(message: str, product: ProductUnderstanding | None) -> str:
    """Expand the raw question with the extracted product profile.

    Retrieval quality on "I make lunch boxes" improves markedly once the query also
    carries "food-contact household product", "stainless steel" and "food storage",
    because those are the words the scope clauses actually use.
    """
    parts = [message]
    if product:
        parts.extend(
            [
                product.product,
                product.category,
                " ".join(product.materials),
                product.intended_use,
                product.industry,
                " ".join(product.characteristics),
            ]
        )
    query = " ".join(p for p in parts if p)
    return query if tokenize(query) else message
