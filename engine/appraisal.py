"""Pure calculation engine. No I/O - every function is unit-testable."""
from . import knowledge as K
from . import overrides as O

# kg CO2 avoided per kg of material recycled (indicative, published LCA ranges)
IMPACT = {"aluminium": 9.0, "iron": 1.5, "copper": 3.5, "gold": 16.0, "silver": 5.0,
          "palladium": 30.0, "lithium": 2.0, "cobalt": 4.0, "nickel": 5.0,
          "neodymium": 8.0, "tin": 2.0, "lead": 1.0, "zinc": 2.0}
ORGANIC_IMPACT = 0.5


def _r(x, n=2):
    return round(float(x), n)


def electronic_appraisal(key, quantity=1.0, weight_kg=None, costs=None, prices=None):
    """Mineral recovery appraisal for one device / lot / tonne."""
    d = K.DEVICES[key]
    unit_kg = O.device_weight(key, d["avg_weight_g"]) / 1000.0
    total_kg = float(weight_kg) if weight_kg else unit_kg * float(quantity)
    total_kg = max(total_kg, 1e-6)
    override = dict(costs or {})
    # layer: shipped defaults < user's saved settings < this request's payload
    costs = O.costs(dict(K.DEFAULT_COSTS, **override))
    # Processing cost depends on the recovery ROUTE, not just weight: refining a
    # PCB for precious metal is far costlier per kg than shredding a steel fridge.
    # Only apply the route default when the caller hasn't overridden it.
    if "processing" not in override:
        costs["processing"] = O.processing(key, K.PROCESSING.get(key, K.DEFAULT_PROCESSING))

    rows, gross = [], 0.0
    yields = O.device_yields(key, d["yields"])
    for metal, kg_per_t in sorted(yields.items(),
                                  key=lambda kv: -kv[1] * K.METALS[kv[0]]["price_inr_per_kg"]):
        m = K.METALS[metal]
        default_price = O.metal_price(metal, m["price_inr_per_kg"])
        price = float((prices or {}).get(metal, default_price))
        recovery = O.metal_recovery(metal, m["recovery"])
        in_feed = kg_per_t / 1000.0 * total_kg          # kg of metal in this feed
        recovered = in_feed * recovery
        value = recovered * price
        gross += value
        precious = m["precious"]
        rows.append(dict(
            metal=metal, name=m["name"], symbol=m["symbol"], precious=precious,
            yield_per_tonne=_r(kg_per_t, 4 if precious else 2),
            yield_unit="g/t" if precious else "kg/t",
            yield_display=_r(kg_per_t * (1000 if precious else 1), 3 if precious else 2),
            in_feed=_r(in_feed * (1000 if precious else 1), 4 if precious else 4),
            in_feed_unit="g" if precious else "kg",
            recovery=recovery, price=_r(price, 2),
            price_unit="Rs/kg",            # `price` is always per kilogram
            price_display=_r(price / (1000 if precious else 1), 2),
            price_display_unit="Rs/g" if precious else "Rs/kg",
            value=_r(value, 2), source=m["source"]))

    cost_total = sum(costs.values()) * total_kg
    net = gross - cost_total
    scale = 1000.0 / total_kg                              # multiplier to reach 1 tonne

    is_el = bool(d.get("is_electronic", True))
    return dict(
        kind=("e-waste" if is_el else "metal"), is_electronic=is_el,
        key=key, label=d["label"], note=d.get("note", ""),
        hazardous=bool(d.get("hazardous")),
        bin=d.get("bin"), decomposition=d.get("decomposition"),
        unit_weight_g=_r(O.device_weight(key, d["avg_weight_g"]), 2),
        quantity=_r(quantity, 3),
        total_kg=_r(total_kg, 4),
        components=[dict(name=n, share=s, carries=c) for n, s, c in d["components"]],
        minerals=rows,
        gross=_r(gross), costs={k: _r(v * total_kg) for k, v in costs.items()},
        cost_total=_r(cost_total), net=_r(net),
        margin=_r((net / gross * 100) if gross else 0.0, 1),
        per_unit=_r(gross - sum(costs.values()) * unit_kg) if gross else 0.0,
        per_tonne_gross=_r(gross * scale), per_tonne_net=_r(net * scale),
        co2_saved_kg=_r(sum(O.impact(r["metal"], IMPACT.get(r["metal"], 0.0))
                            * (r["in_feed"] / (1000 if r["precious"] else 1))
                            for r in rows), 2),
        price_date=K.PRICE_DATE)


def waste_appraisal(key, weight_g, rate_override=None):
    """General-waste valuation and disposal guidance."""
    d = K.ITEMS[key]
    kg = max(float(weight_g), 0.0) / 1000.0
    rate = float(rate_override if rate_override is not None
                 else O.item_rate(key, d["rate_inr_per_kg"]))
    gross = kg * rate

    mats = []
    for name, share, rec, becomes in d["materials"]:
        mats.append(dict(name=name, share=share, recyclable=rec, becomes=becomes,
                         kg=_r(kg * share / 100.0, 4)))

    organic = d["bin"] == "wet"
    co2 = kg * O.item_rate("_co2_" + ("wet" if organic else "dry"),
                           ORGANIC_IMPACT if organic else 1.2)

    return dict(
        kind="waste", is_electronic=False, key=key, label=d["label"],
        note=d.get("note", ""),
        hazardous=bool(d.get("hazardous")), bin=d["bin"],
        decomposition=d["decomposition"], decomposition_short=d["decomposition"],
        unit_weight_g=O.item_weight(key, d["avg_weight_g"]), total_kg=_r(kg, 4),
        rate=_r(rate, 2), gross=_r(gross, 2), net=_r(gross, 2),
        materials=mats, co2_saved_kg=_r(co2, 2), price_date=K.PRICE_DATE,
        advice=_bin_advice(d["bin"], bool(d.get("hazardous"))))


def _bin_advice(bin_, hazardous):
    if hazardous:
        return ["Do not open, puncture or burn this item.",
                "Keep it out of the household bin.",
                "Hand it to an authorised collector or a hazardous-waste drive."]
    return {
        "wet": ["Goes in the WET / biodegradable bin.",
                "Keep it free of plastic and metal.",
                "Best home outcome: compost it or feed a biogas plant."],
        "dry": ["Goes in the DRY bin.",
                "Rinse off food residue and let it dry first.",
                "Flatten to save collection space."],
        "recyclable": ["Goes in the RECYCLABLE / dry bin.",
                       "Rinse and squash before you bin it.",
                       "Keep it dry - wet recyclables get rejected at sorting."],
    }.get(bin_, ["Follow your local municipal segregation rules."])


def appraise(key, weight_g=None, quantity=1.0, costs=None, prices=None, rate=None):
    if key in K.DEVICES:
        return electronic_appraisal(key, quantity=quantity,
                                    weight_kg=(weight_g / 1000.0 if weight_g else None),
                                    costs=costs, prices=prices)
    d = K.ITEMS.get(key)
    w = weight_g if weight_g is not None else (O.item_weight(key, d["avg_weight_g"]) if d else 100.0)
    return waste_appraisal(key, w, rate)
