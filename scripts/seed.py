"""Seed the Epigen demo database with one invented person: Sam Rivera.

6 months of synthetic history (never real people):
- shopping: 40 memories (purchases with price/category/date/outcome,
  budget rules, brand likes/dislikes, a pattern of regretting
  clothing over $150)
- family: 25 memories (apartment saving goal with partner, target date
  and amount, partner preferences, kid expenses)

Each memory: id, angle, text, created_at, salience (0-1),
source (manual/photo/outcome), embedding.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.embeddings import embed
from app.store import DB_PATH, connect

# (id_suffix, created_at, salience, source, text)
SHOPPING: list[tuple[str, str, float, str, str]] = [
    ("001", "2026-05-03", 0.90, "manual",
     "Budget rule: $200/month max on clothing after overspending in April."),
    ("002", "2026-05-06", 0.40, "manual",
     "Bought Muji white tees 3-pack, $36, clothing. Kept, wears constantly."),
    ("003", "2026-05-10", 0.70, "manual",
     "Brand like: Patagonia. Durable, good warranty, worth paying for."),
    ("004", "2026-05-11", 0.45, "manual",
     "Bought Levi's 501 jeans, $69, clothing. Kept, good fit."),
    ("005", "2026-05-15", 0.60, "manual",
     "Bought Nike running shoes, $120, shoes. Kept, runs 3x a week in them."),
    ("006", "2026-05-18", 0.60, "manual",
     "Brand like: Muji basics. Cheap, neutral, never regrets them."),
    ("007", "2026-05-22", 0.50, "manual",
     "Bought Uniqlo wool sweater, $89, clothing. Kept."),
    ("008", "2026-05-28", 0.60, "manual",
     "Bought trendy fast-fashion shirt, $45, clothing. Regretted: shrank after one wash."),
    ("009", "2026-06-01", 0.75, "manual",
     "Bought Patagonia fleece, $139, clothing. Loved, wears it weekly."),
    ("010", "2026-06-02", 0.70, "manual",
     "Brand dislike: Shein/Temu fast fashion. Bad stitching, wrong sizes twice."),
    ("011", "2026-06-07", 0.90, "manual",
     "Bought designer denim jacket, $189, clothing. Regretted: too stiff, never worn, resold at a loss."),
    ("012", "2026-06-12", 0.30, "manual",
     "Bought Costco bulk groceries, $210, groceries. Kept."),
    ("013", "2026-06-18", 0.85, "manual",
     "Bought leather boots, $165, shoes. Returned: gave blisters within a day."),
    ("014", "2026-06-20", 0.55, "manual",
     "Fabric preference: wool and cotton over polyester; polyester jackets make him sweat."),
    ("015", "2026-06-25", 0.60, "manual",
     "Bought Kindle Paperwhite, $150, electronics. Loved, reads daily."),
    ("016", "2026-06-29", 0.40, "manual",
     "Bought sunglasses, $130, accessories. Kept."),
    ("017", "2026-07-02", 0.45, "manual",
     "Bought linen summer shirt, $75, clothing. Kept."),
    ("018", "2026-07-09", 0.95, "manual",
     "Bought premium rain shell, $210, clothing. Regretted: leaked at the seams; returned late so only a partial refund."),
    ("019", "2026-07-12", 0.85, "manual",
     "Budget rule: sleep on any clothing purchase over $100 for 48 hours before buying."),
    ("020", "2026-07-16", 0.30, "manual",
     "Bought Muji storage boxes, $58, home. Kept."),
    ("021", "2026-07-23", 0.85, "manual",
     "Bought cashmere sweater, $159, clothing. Regretted: pilled after two washes."),
    ("022", "2026-07-30", 0.30, "manual",
     "Bought gym shorts, $40, clothing. Kept."),
    ("023", "2026-08-05", 0.70, "manual",
     "Bought espresso maker, $249, home. Loved: saves coffee-shop money."),
    ("024", "2026-08-11", 0.95, "photo",
     "Photo of the wool overcoat bought for $320, clothing. Regretted: too warm for the Bay Area, worn twice."),
    ("025", "2026-08-18", 0.30, "manual",
     "Bought bedsheets, $80, home. Kept."),
    ("026", "2026-08-24", 0.50, "manual",
     "Bought trail runners, $135, shoes. Kept."),
    ("027", "2026-08-30", 0.55, "manual",
     "Bought noise-cancelling earbuds, $199, electronics. Kept for the commute."),
    ("028", "2026-09-01", 0.90, "manual",
     "Budget rule: clothing budget cut to $150/month until the apartment deposit is saved."),
    ("029", "2026-09-06", 0.90, "manual",
     "Bought corduroy jacket, $175, clothing. Returned: fit was off; glad the 48-hour rule almost stopped the purchase."),
    ("030", "2026-09-12", 0.25, "manual",
     "Bought Muji socks 5-pack, $30, clothing. Kept."),
    ("031", "2026-09-19", 0.40, "manual",
     "Bought cast-iron skillet, $65, home. Kept."),
    ("032", "2026-09-25", 0.60, "manual",
     "Bought merino hoodie, $148, clothing. Kept: just under the regret line, wears it often."),
    ("033", "2026-09-30", 0.70, "manual",
     "Returned a $140 polyester jacket: too sweaty. Confirmed the wool/cotton preference."),
    ("034", "2026-10-02", 0.45, "manual",
     "Bought dress shirt, $95, clothing. Kept for interviews."),
    ("035", "2026-10-08", 0.90, "manual",
     "Bought down vest, $185, clothing. Regretted: zipper broke, warranty fight."),
    ("036", "2026-10-14", 0.40, "manual",
     "Bought board games, $70, entertainment. Kept for family game nights."),
    ("037", "2026-10-18", 0.50, "manual",
     "Bought Patagonia rain pants, $129, clothing. Kept."),
    ("038", "2026-10-20", 0.35, "manual",
     "Bought winter gloves $55 and scarf $35, clothing. Kept."),
    ("039", "2026-10-26", 0.65, "manual",
     "Bought secondhand bike, $230, transport. Loved."),
    ("040", "2026-10-30", 0.80, "photo",
     "Photo: tried on a $180 wool jacket at the mall and walked away; felt like the $189 denim jacket mistake."),
]

FAMILY: list[tuple[str, str, float, str, str]] = [
    ("001", "2026-05-05", 0.80, "manual",
     "Sam and partner Alex decided to save for a 2-bedroom apartment near Lake Merritt, Oakland."),
    ("002", "2026-05-12", 0.70, "manual",
     "Alex prefers a quiet top-floor unit with laundry in the building."),
    ("003", "2026-05-20", 0.85, "manual",
     "Apartment target: $15,000 for security deposit plus first months and moving costs."),
    ("004", "2026-05-25", 0.70, "manual",
     "Daughter Lily (9) needs a school laptop, about $450, before the fall term."),
    ("005", "2026-06-05", 0.30, "manual",
     "Sunday video call with mom; she sends recipes."),
    ("006", "2026-06-08", 0.60, "manual",
     "Alex hates wall-to-wall carpet; wants hardwood or laminate floors."),
    ("007", "2026-06-15", 0.90, "manual",
     "Apartment target move date: September 2027, before Lily's new school year."),
    ("008", "2026-06-30", 0.55, "manual",
     "Alex wants a kitchen with a gas stove for weekend cooking."),
    ("009", "2026-07-05", 0.65, "manual",
     "Lily's summer camp deposit, $300, due in March 2027."),
    ("010", "2026-07-10", 0.80, "manual",
     "Apartment savings: $4,200 of $15,000 so far; auto-transfer $800/month."),
    ("011", "2026-07-18", 0.35, "manual",
     "Family game night on Fridays; current favorite is Ticket to Ride."),
    ("012", "2026-07-22", 0.70, "manual",
     "Alex vetoed neighborhoods far from BART; commute must stay under 40 minutes."),
    ("013", "2026-08-08", 0.80, "manual",
     "Dentist says Lily may need braces: estimate $2,000-$3,000 in 2027."),
    ("014", "2026-08-15", 0.60, "manual",
     "Paused $500 of apartment savings to cover a car repair; back on track in September."),
    ("015", "2026-08-20", 0.60, "manual",
     "Emergency fund at $3,000; goal is $5,000."),
    ("016", "2026-08-28", 0.60, "manual",
     "Alex prefers secondhand furniture to keep cash for the deposit."),
    ("017", "2026-09-02", 0.40, "manual",
     "School supplies plus a new backpack, about $120, bought in August."),
    ("018", "2026-09-15", 0.75, "manual",
     "Alex's birthday is November 20; agreed to keep gifts under $50 this year, apartment first."),
    ("019", "2026-09-20", 0.80, "manual",
     "Apartment savings: $7,100 of $15,000; current roommate situation ends August 2027."),
    ("020", "2026-09-28", 0.50, "manual",
     "Agreed with Alex: date night twice a month, max $60 each."),
    ("021", "2026-10-01", 0.50, "manual",
     "Lily outgrew her winter boots; a new pair, about $70, needed before December."),
    ("022", "2026-10-05", 0.90, "manual",
     "House rule: any purchase over $150 must be weighed against the apartment fund."),
    ("023", "2026-10-12", 0.85, "manual",
     "Alex said no big clothing splurges until the apartment deposit is saved."),
    ("024", "2026-10-22", 0.35, "photo",
     "Photo: Lily's science-fair shortlist; volcano kit costs $40 of her project budget."),
    ("025", "2026-10-25", 0.85, "manual",
     "Apartment savings on track: $8,600 saved, $6,400 to go by September 2027."),
]


def build_memories() -> list[dict]:
    mems: list[dict] = []
    for suffix, created_at, salience, source, text in SHOPPING:
        mems.append({
            "id": f"mem_shopping_{suffix}",
            "angle": "shopping",
            "text": text,
            "created_at": f"{created_at}T12:00:00+00:00",
            "salience": salience,
            "source": source,
            "embedding": embed(text),
        })
    for suffix, created_at, salience, source, text in FAMILY:
        mems.append({
            "id": f"mem_family_{suffix}",
            "angle": "family",
            "text": text,
            "created_at": f"{created_at}T12:00:00+00:00",
            "salience": salience,
            "source": source,
            "embedding": embed(text),
        })
    return mems


def main(db_path: str = DB_PATH) -> list[dict]:
    import json

    from app.store import save_memory

    mems = build_memories()
    conn = connect(db_path)
    conn.execute("DELETE FROM memories")
    for mem in mems:
        save_memory(conn, mem)
    conn.commit()
    n_shop = sum(1 for m in mems if m["angle"] == "shopping")
    n_fam = sum(1 for m in mems if m["angle"] == "family")
    print(f"Seeded {len(mems)} memories ({n_shop} shopping, {n_fam} family) -> {db_path}")
    conn.close()
    return mems


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DB_PATH)
