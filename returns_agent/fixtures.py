"""Synthetic orders, policies, shipments, and support tickets."""

from decimal import Decimal

from returns_agent.models import (
    Order,
    ReturnPolicy,
    ShippingStatus,
    TicketInput,
)

POLICIES = {
    "footwear": ReturnPolicy(
        category="footwear",
        window_days=30,
        defective_full_refund=True,
        unused_return=True,
        final_sale_defect_exception=True,
        human_approval_threshold=Decimal("150.00"),
    ),
    "apparel": ReturnPolicy(
        category="apparel",
        window_days=30,
        defective_full_refund=True,
        unused_return=True,
        final_sale_defect_exception=True,
        human_approval_threshold=Decimal("150.00"),
    ),
    "accessories": ReturnPolicy(
        category="accessories",
        window_days=14,
        defective_full_refund=True,
        unused_return=True,
        final_sale_defect_exception=False,
        human_approval_threshold=Decimal("100.00"),
    ),
    "luggage": ReturnPolicy(
        category="luggage",
        window_days=45,
        defective_full_refund=True,
        unused_return=True,
        final_sale_defect_exception=True,
        human_approval_threshold=Decimal("200.00"),
    ),
}

ORDERS = {
    "48213": Order(
        order_id="48213",
        email="dana@example.test",
        product="Merino Runners",
        category="footwear",
        amount_paid=Decimal("98.00"),
        status="delivered",
        days_since_delivery=21,
        tracking_no="TRACK-48213",
    ),
    "48214": Order(
        order_id="48214",
        email="leo@example.test",
        product="Archive Hoodie",
        category="apparel",
        amount_paid=Decimal("64.00"),
        status="delivered",
        days_since_delivery=12,
        final_sale=True,
        tracking_no="TRACK-48214",
    ),
    "48215": Order(
        order_id="48215",
        email="maya@example.test",
        product="Everyday Tote",
        category="accessories",
        amount_paid=Decimal("48.00"),
        status="delivered",
        days_since_delivery=20,
        tracking_no="TRACK-48215",
    ),
    "48216": Order(
        order_id="48216",
        email="sam@example.test",
        product="Aluminum Carry-On",
        category="luggage",
        amount_paid=Decimal("280.00"),
        status="delivered",
        days_since_delivery=8,
        tracking_no="TRACK-48216",
    ),
    "48217": Order(
        order_id="48217",
        email="chris@example.test",
        product="Trail Backpack",
        category="accessories",
        amount_paid=Decimal("75.00"),
        status="shipped",
        days_since_delivery=None,
        tracking_no="TRACK-48217",
    ),
    "48218": Order(
        order_id="48218",
        email="morgan@example.test",
        product="Field Jacket",
        category="apparel",
        amount_paid=Decimal("120.00"),
        status="delivered",
        days_since_delivery=5,
        tracking_no="TRACK-48218",
        risk_flags=["account_takeover_review"],
    ),
    "48219": Order(
        order_id="48219",
        email="alex@example.test",
        product="Canvas Slip-Ons",
        category="footwear",
        amount_paid=Decimal("82.00"),
        status="delivered",
        days_since_delivery=9,
        tracking_no="TRACK-48219",
        already_refunded=True,
    ),
    "48220": Order(
        order_id="48220",
        email="jamie@example.test",
        product="Two Essential Tees",
        category="apparel",
        amount_paid=Decimal("80.00"),
        status="delivered",
        days_since_delivery=6,
        tracking_no="TRACK-48220",
    ),
    "48221": Order(
        order_id="48221",
        email="pat@example.test",
        product="City Loafers",
        category="footwear",
        amount_paid=Decimal("110.00"),
        status="delivered",
        days_since_delivery=10,
        tracking_no="TRACK-48221",
    ),
    "48222": Order(
        order_id="48222",
        email="riley@example.test",
        product="Merino Runners",
        category="footwear",
        amount_paid=Decimal("98.00"),
        status="delivered",
        days_since_delivery=18,
        tracking_no="TRACK-48222",
    ),
    "48301": Order(
        order_id="48301",
        email="nora@example.test",
        product="Daybreak Sneakers",
        category="footwear",
        amount_paid=Decimal("95.00"),
        status="delivered",
        days_since_delivery=29,
        tracking_no="TRACK-48301",
    ),
    "48302": Order(
        order_id="48302",
        email="omar@example.test",
        product="Harbor Trainers",
        category="footwear",
        amount_paid=Decimal("115.00"),
        status="delivered",
        days_since_delivery=31,
        tracking_no="TRACK-48302",
    ),
    "48303": Order(
        order_id="48303",
        email="quinn@example.test",
        product="Braided Belt",
        category="accessories",
        amount_paid=Decimal("55.00"),
        status="delivered",
        days_since_delivery=13,
        tracking_no="TRACK-48303",
    ),
    "48304": Order(
        order_id="48304",
        email="rosa@example.test",
        product="Leather Wallet",
        category="accessories",
        amount_paid=Decimal("90.00"),
        status="delivered",
        days_since_delivery=15,
        tracking_no="TRACK-48304",
    ),
    "48305": Order(
        order_id="48305",
        email="talia@example.test",
        product="Linen Shirt",
        category="apparel",
        amount_paid=Decimal("72.00"),
        status="delivered",
        days_since_delivery=28,
        final_sale=True,
        tracking_no="TRACK-48305",
    ),
    "48306": Order(
        order_id="48306",
        email="uma@example.test",
        product="Silk Scarf",
        category="accessories",
        amount_paid=Decimal("65.00"),
        status="delivered",
        days_since_delivery=7,
        final_sale=True,
        tracking_no="TRACK-48306",
    ),
    "48307": Order(
        order_id="48307",
        email="victor@example.test",
        product="Wool Overcoat",
        category="apparel",
        amount_paid=Decimal("150.00"),
        status="delivered",
        days_since_delivery=4,
        tracking_no="TRACK-48307",
    ),
    "48308": Order(
        order_id="48308",
        email="wren@example.test",
        product="Cashmere Cardigan",
        category="apparel",
        amount_paid=Decimal("151.00"),
        status="delivered",
        days_since_delivery=4,
        tracking_no="TRACK-48308",
    ),
    "48309": Order(
        order_id="48309",
        email="xander@example.test",
        product="Weekender",
        category="luggage",
        amount_paid=Decimal("199.99"),
        status="delivered",
        days_since_delivery=10,
        tracking_no="TRACK-48309",
    ),
    "48310": Order(
        order_id="48310",
        email="yasmin@example.test",
        product="Packing Cube Set",
        category="accessories",
        amount_paid=Decimal("60.00"),
        status="shipped",
        days_since_delivery=None,
        tracking_no="TRACK-48310",
    ),
    "48311": Order(
        order_id="48311",
        email="zoe@example.test",
        product="Commuter Satchel",
        category="accessories",
        amount_paid=Decimal("85.00"),
        status="shipped",
        days_since_delivery=None,
        tracking_no="TRACK-48311",
    ),
    "48312": Order(
        order_id="48312",
        email="ari@example.test",
        product="Expedition Duffel",
        category="luggage",
        amount_paid=Decimal("180.00"),
        status="shipped",
        days_since_delivery=None,
        tracking_no="TRACK-48312",
    ),
    "48313": Order(
        order_id="48313",
        email="bea@example.test",
        product="Classic Oxfords",
        category="footwear",
        amount_paid=Decimal("130.00"),
        status="delivered",
        days_since_delivery=9,
        tracking_no="TRACK-48313",
    ),
    "48314": Order(
        order_id="48314",
        email="bea@example.test",
        product="Rain Jacket",
        category="apparel",
        amount_paid=Decimal("140.00"),
        status="delivered",
        days_since_delivery=8,
        tracking_no="TRACK-48314",
    ),
    "48315": Order(
        order_id="48315",
        email="cody@example.test",
        product="Studio Trainers",
        category="footwear",
        amount_paid=Decimal("89.00"),
        status="delivered",
        days_since_delivery=11,
        tracking_no="TRACK-48315",
    ),
    "48316": Order(
        order_id="48316",
        email="devin@example.test",
        product="Brass Buckle Belt",
        category="accessories",
        amount_paid=Decimal("44.00"),
        status="delivered",
        days_since_delivery=5,
        tracking_no="TRACK-48316",
    ),
    "48317": Order(
        order_id="48317",
        email="ellis@example.test",
        product="Canvas High-Tops",
        category="footwear",
        amount_paid=Decimal("78.00"),
        status="delivered",
        days_since_delivery=6,
        tracking_no="TRACK-48317",
        already_refunded=True,
    ),
    "48318": Order(
        order_id="48318",
        email="frankie@example.test",
        product="Utility Vest",
        category="apparel",
        amount_paid=Decimal("135.00"),
        status="delivered",
        days_since_delivery=3,
        tracking_no="TRACK-48318",
        risk_flags=["account_takeover_review"],
    ),
    "48319": Order(
        order_id="48319",
        email="gray@example.test",
        product="Chore Coat",
        category="apparel",
        amount_paid=Decimal("130.00"),
        status="delivered",
        days_since_delivery=2,
        tracking_no="TRACK-48319",
    ),
    "48320": Order(
        order_id="48320",
        email="harper@example.test",
        product="Court Sneakers",
        category="footwear",
        amount_paid=Decimal("100.00"),
        status="delivered",
        days_since_delivery=31,
        tracking_no="TRACK-48320",
    ),
    "48321": Order(
        order_id="48321",
        email="indira@example.test",
        product="Limited Runner",
        category="footwear",
        amount_paid=Decimal("105.00"),
        status="delivered",
        days_since_delivery=12,
        final_sale=True,
        tracking_no="TRACK-48321",
    ),
}

SHIPMENTS = {
    "TRACK-48217": ShippingStatus(
        tracking_no="TRACK-48217",
        status="lost",
        detail="Carrier investigation closed: package lost in transit.",
    ),
    "TRACK-48310": ShippingStatus(
        tracking_no="TRACK-48310",
        status="delayed",
        detail="Package remains in transit five days after the estimated delivery.",
    ),
    "TRACK-48312": ShippingStatus(
        tracking_no="TRACK-48312",
        status="lost",
        detail="Carrier investigation closed: package lost in transit.",
    ),
}


def _ticket(
    ticket_id: str,
    customer_name: str,
    email: str,
    subject: str,
    body: str,
) -> TicketInput:
    """Create one compact synthetic support email."""
    return TicketInput(
        ticket_id=ticket_id,
        customer_name=customer_name,
        email=email,
        subject=subject,
        body=body,
    )


CASES = (
    _ticket(
        "ticket-001",
        "Dana",
        "dana@example.test",
        "Hole in my Merino Runners",
        (
            "Hi, I ordered the Merino Runners (order #48213) three weeks "
            "ago and they arrived with a hole in the left shoe. I'd like "
            "a refund. - Dana"
        ),
    ),
    _ticket(
        "ticket-002",
        "Leo",
        "leo@example.test",
        "Archive Hoodie return",
        ("Order #48214 does not fit. I wore it once indoors and would like a refund."),
    ),
    _ticket(
        "ticket-003",
        "Maya",
        "maya@example.test",
        "Return my tote",
        ("The unused Everyday Tote from order #48215 is not for me. Please refund it."),
    ),
    _ticket(
        "ticket-004",
        "Sam",
        "sam@example.test",
        "Cracked carry-on",
        (
            "The shell on my Aluminum Carry-On from order #48216 cracked "
            "on first use. Please refund the $280 purchase."
        ),
    ),
    _ticket(
        "ticket-005",
        "Priya",
        "priya@example.test",
        "Refund missing order",
        "Please refund order #99999. The item was never what I expected.",
    ),
    _ticket(
        "ticket-006",
        "Chris",
        "chris@example.test",
        "Backpack never arrived",
        (
            "Order #48217 has not arrived. Tracking has not moved and I "
            "need a replacement."
        ),
    ),
    _ticket(
        "ticket-007",
        "Morgan",
        "morgan@example.test",
        "Defective jacket refund",
        (
            "The zipper broke on the Field Jacket from order #48218. "
            "Refund it today, please."
        ),
    ),
    _ticket(
        "ticket-008",
        "Alex",
        "alex@example.test",
        "Still waiting for refund",
        (
            "Please refund order #48219 again. I cannot see the earlier "
            "refund on my card."
        ),
    ),
    _ticket(
        "ticket-009",
        "Jamie",
        "jamie@example.test",
        "Wrong color tees",
        (
            "Order #48220 arrived in the wrong color. Please refund $120 "
            "for the inconvenience."
        ),
    ),
    _ticket(
        "ticket-010",
        "Riley",
        "riley@example.test",
        "Wrong order number, defective shoes",
        (
            "I think my order is #48228, but it may be under this email. "
            "My Merino Runners arrived with a torn seam and I want a refund."
        ),
    ),
    _ticket(
        "ticket-011",
        "Nora",
        "nora@example.test",
        "Return unworn sneakers",
        (
            "The Daybreak Sneakers from order #48301 are still unworn. They "
            "were delivered 29 days ago, and I would like a refund."
        ),
    ),
    _ticket(
        "ticket-012",
        "Omar",
        "omar@example.test",
        "Late trainer return",
        (
            "My unused Harbor Trainers from order #48302 were delivered 31 "
            "days ago. Please refund them."
        ),
    ),
    _ticket(
        "ticket-013",
        "Quinn",
        "quinn@example.test",
        "Belt clasp broke",
        (
            "The clasp on the Braided Belt from order #48303 broke after 13 "
            "days. Please issue a refund."
        ),
    ),
    _ticket(
        "ticket-014",
        "Rosa",
        "rosa@example.test",
        "Wallet seam split",
        (
            "The seam on my Leather Wallet from order #48304 split after 15 "
            "days. I would like a refund."
        ),
    ),
    _ticket(
        "ticket-015",
        "Talia",
        "talia@example.test",
        "Final-sale shirt arrived torn",
        (
            "The final-sale Linen Shirt in order #48305 arrived with a torn "
            "sleeve. Please refund it."
        ),
    ),
    _ticket(
        "ticket-016",
        "Uma",
        "uma@example.test",
        "Damaged final-sale scarf",
        (
            "My final-sale Silk Scarf from order #48306 arrived with a pulled "
            "thread. I would like a refund."
        ),
    ),
    _ticket(
        "ticket-017",
        "Victor",
        "victor@example.test",
        "Overcoat lining defect",
        (
            "The lining in the $150 Wool Overcoat from order #48307 is torn. "
            "Please refund the purchase."
        ),
    ),
    _ticket(
        "ticket-018",
        "Wren",
        "wren@example.test",
        "Cardigan seam defect",
        (
            "The seam on the $151 Cashmere Cardigan from order #48308 opened "
            "on first wear. Please refund it."
        ),
    ),
    _ticket(
        "ticket-019",
        "Xander",
        "xander@example.test",
        "Broken weekender zipper",
        (
            "The zipper on my $199.99 Weekender from order #48309 broke on "
            "the first trip. I would like a refund."
        ),
    ),
    _ticket(
        "ticket-020",
        "Yasmin",
        "yasmin@example.test",
        "Packing cubes delayed",
        (
            "Order #48310 is five days past the delivery estimate but still "
            "moving through the carrier network. Please send a replacement."
        ),
    ),
    _ticket(
        "ticket-021",
        "Zoe",
        "zoe@example.test",
        "Satchel marked delivered",
        (
            "Order #48311 is marked delivered, but I cannot find the Commuter "
            "Satchel. Please replace it today."
        ),
    ),
    _ticket(
        "ticket-022",
        "Ari",
        "ari@example.test",
        "Lost duffel refund",
        (
            "The carrier says order #48312 was lost in transit. I asked for a "
            "refund, but a replacement would also get the trip back on track."
        ),
    ),
    _ticket(
        "ticket-023",
        "Bea",
        "bea@example.test",
        "Defect in a recent order",
        (
            "One of my two recent orders has a defect, but I cannot find the "
            "order number or remember which item it was. Please refund it."
        ),
    ),
    _ticket(
        "ticket-024",
        "Cody",
        "cody@example.test",
        "Wrong number for defective trainers",
        (
            "I wrote down order #48999, but the Studio Trainers should be under "
            "this email. A sole is separating, and I would like a refund."
        ),
    ),
    _ticket(
        "ticket-025",
        "Devin",
        "devin@example.test",
        "Return unused belt",
        (
            "The unused Brass Buckle Belt from order #48316 was delivered five "
            "days ago. Please refund it."
        ),
    ),
    _ticket(
        "ticket-026",
        "Ellis",
        "ellis@example.test",
        "Refund still missing",
        (
            "Order #48317 was already refunded, but it has not appeared on my "
            "statement. Please issue the refund again."
        ),
    ),
    _ticket(
        "ticket-027",
        "Frankie",
        "frankie@example.test",
        "Defective utility vest",
        (
            "A snap broke on the Utility Vest from order #48318. Please refund "
            "the $135 purchase today."
        ),
    ),
    _ticket(
        "ticket-028",
        "Gray",
        "gray@example.test",
        "Chore coat button missing",
        (
            "The Chore Coat from order #48319 arrived without a button. Please "
            "refund the $130 purchase."
        ),
    ),
    _ticket(
        "ticket-029",
        "Harper",
        "harper@example.test",
        "Return unused court sneakers",
        (
            "The Court Sneakers from order #48320 are unused, but they were "
            "delivered 31 days ago. I would still like a refund."
        ),
    ),
    _ticket(
        "ticket-030",
        "Indira",
        "indira@example.test",
        "Final-sale runner defect",
        (
            "The final-sale Limited Runner shoes from order #48321 arrived with "
            "a split heel. Please refund them."
        ),
    ),
)
