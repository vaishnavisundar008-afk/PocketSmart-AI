"""Deterministic recommendation fallbacks for PocketSmart AI."""

from __future__ import annotations

from urllib.parse import quote_plus


PLATFORM_URLS = {
    "Amazon": "https://www.amazon.com/s?k={query}",
    "Flipkart": "https://www.flipkart.com/search?q={query}",
    "IKEA": "https://www.ikea.com/search/?q={query}",
    "Swiggy": "https://www.swiggy.com/search?query={query}",
    "Zomato": "https://www.zomato.com/search?query={query}",
    "OYO": "https://www.oyorooms.com/search/?location={query}",
}


def _item(
    name: str,
    category: str,
    price: float,
    platform: str,
    reason: str,
    quantity: int = 1,
) -> dict[str, object]:
    query = quote_plus(name)
    return {
        "name": name,
        "category": category,
        "price": round(price, 2),
        "quantity": quantity,
        "platform": platform,
        "reason": reason,
        "url": PLATFORM_URLS[platform].format(query=query),
    }


def build_fallback(
    planner: str,
    budget: float,
    currency: str = "USD",
    **preferences: object,
) -> dict[str, object]:
    """Create useful, clearly estimated recommendations without external APIs."""
    if budget <= 0:
        raise ValueError("budget must be greater than zero")

    if planner == "home":
        items = preferences.get("items") or ["Lighting", "Storage", "Soft furnishings"]
        requested = []
        for entry in items:
            if isinstance(entry, dict):
                name = str(entry.get("name", "")).strip()
                quantity = max(1, min(20, int(entry.get("quantity") or 1)))
            else:
                name = str(entry).strip()
                quantity = 1
            if name:
                requested.append((name, quantity))
        requested = requested[:8] or [("Lighting", 1), ("Storage", 1), ("Soft furnishings", 1)]
        per_unit = budget * 0.82 / sum(quantity for _, quantity in requested)
        style = str(preferences.get("style") or "versatile")
        recommendations = [
            _item(
                name,
                "Home",
                per_unit,
                "IKEA" if index % 2 == 0 else "Amazon",
                f"A practical {style} option to cover your {name.lower()} needs.",
                quantity,
            )
            for index, (name, quantity) in enumerate(requested)
        ]
        summary = "A room-by-room starter plan with room left for delivery and finishing touches."
        allocations = [{"category": "Home essentials", "amount": round(budget * 0.82, 2), "rationale": "Core furniture and decor."}]
        insights = ["Prices are planning estimates; confirm current availability and delivery costs with the retailer."]
    elif planner == "party":
        event = str(preferences.get("event_type") or "gathering")
        guests = max(1, int(preferences.get("guests") or 1))
        city = str(preferences.get("city") or "your area")
        allocations = [
            {"category": "Food & drinks", "amount": round(budget * 0.42, 2), "rationale": "Prioritize guest comfort and a dependable menu."},
            {"category": "Venue", "amount": round(budget * 0.25, 2), "rationale": "Keep the venue proportionate to the guest count."},
            {"category": "Decor", "amount": round(budget * 0.18, 2), "rationale": "Focus spending on a few high-impact details."},
            {"category": "Entertainment", "amount": round(budget * 0.15, 2), "rationale": "Reserve a modest amount for music or activities."},
        ]
        recommendations = [
            _item(f"{event.title()} catering for {guests}", "Food & drinks", budget * 0.42, "Swiggy", "Compare local menus and set a per-person cap."),
            _item(f"Small event space in {city}", "Venue", budget * 0.25, "OYO", "Look for a venue sized for your guest list."),
            _item(f"Reusable {event} table and room decor", "Decor", budget * 0.18, "Amazon", "A focused decor set keeps setup simple."),
            _item("Playlist and group activity kit", "Entertainment", budget * 0.15, "Zomato", "Use a low-cost activity plan and protect the food budget."),
        ]
        summary = f"A balanced {event} plan for {guests} guests, with clear caps for each major cost."
        insights = ["Venue and catering estimates vary by city, date, and headcount; confirm quotes before booking."]
    elif planner == "jewelry":
        occasion = str(preferences.get("occasion") or "special occasion")
        style = str(preferences.get("style") or "classic")
        recommendations = [
            _item(f"{style.title()} earrings for {occasion}", "Earrings", budget * 0.34, "Amazon", "A versatile focal piece matched to your selected style."),
            _item(f"Coordinated {style} necklace", "Necklace", budget * 0.29, "Flipkart", "A complementary piece that leaves room in the budget."),
            _item("Minimal matching bracelet", "Bracelet", budget * 0.17, "Amazon", "A subtle finishing detail within the planned spend."),
        ]
        allocations = [{"category": "Jewelry set", "amount": round(budget * 0.8, 2), "rationale": "Use coordinated pieces while reserving a buffer for fit and shipping."}]
        summary = f"A coordinated {style} direction for {occasion}, with a 20% buffer left unallocated."
        insights = ["Image matching is unavailable in local fallback mode; add a Gemini API key to enable outfit-aware analysis."]
    else:
        raise ValueError(f"Unknown planner: {planner}")

    return {
        "planner": planner,
        "summary": summary,
        "budget": round(budget, 2),
        "currency": currency,
        "allocations": allocations,
        "recommendations": recommendations,
        "insights": insights,
        "source": "fallback",
    }