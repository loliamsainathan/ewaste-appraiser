"""Materials, device and pricing knowledge base for E-Waste Value Appraiser.

All metal prices are Indian market rates captured on 2026-11-07 with the source
recorded. Recovery yields are per tonne of feed and come from published
e-waste / PCB assay literature (UNEP StEP class data); they are stored as
kilograms per tonne so every metal uses one unit.
"""

PRICE_DATE = "2026-11-07"

# ----------------------------------------------------------------- metals
# price_inr_per_kg  | recovery = typical hydrometallurgical / smelting yield
METALS = {
    "gold": dict(name="Gold", symbol="Au", price_inr_per_kg=14_200 * 1000, recovery=0.95,
                 precious=True, source="livemint.com/gold-prices"),
    "silver": dict(name="Silver", symbol="Ag", price_inr_per_kg=184 * 1000, recovery=0.90,
                   precious=True, source="livemint.com/silver-prices"),
    "palladium": dict(name="Palladium", symbol="Pd", price_inr_per_kg=2_950 * 1000, recovery=0.90,
                      precious=True, source="goldbroker.com/charts/palladium-price/inr"),
    "copper": dict(name="Copper", symbol="Cu", price_inr_per_kg=1_350.0, recovery=0.90,
                   precious=False, source="upstox.com/mcx-copper-price"),
    "aluminium": dict(name="Aluminium", symbol="Al", price_inr_per_kg=263.0, recovery=0.90,
                      precious=False, source="metalscost.com"),
    "cobalt": dict(name="Cobalt", symbol="Co", price_inr_per_kg=3_410.0, recovery=0.80,
                   precious=False, source="metalscost.com"),
    "nickel": dict(name="Nickel", symbol="Ni", price_inr_per_kg=1_366.0, recovery=0.85,
                   precious=False, source="metalscost.com"),
    "lithium": dict(name="Lithium", symbol="Li", price_inr_per_kg=1_168.0, recovery=0.65,
                    precious=False, source="metalscost.com"),
    "neodymium": dict(name="Neodymium", symbol="Nd", price_inr_per_kg=11_805.0, recovery=0.70,
                      precious=False, source="metalscost.com"),
    "tin": dict(name="Tin", symbol="Sn", price_inr_per_kg=3_959.0, recovery=0.70,
                precious=False, source="metalscost.com"),
    "lead": dict(name="Lead", symbol="Pb", price_inr_per_kg=160.8, recovery=0.90,
                 precious=False, source="metalscost.com"),
    "zinc": dict(name="Zinc", symbol="Zn", price_inr_per_kg=319.0, recovery=0.80,
                 precious=False, source="metalscost.com"),
    "iron": dict(name="Iron / steel", symbol="Fe", price_inr_per_kg=30.0, recovery=0.95,
                 precious=False, source="Indian scrap market (indicative)"),
}

# default cost model, INR per kg of feed (India defaults, user editable)
DEFAULT_COSTS = dict(collection=25.0, transport=8.0, processing=120.0)

# Processing cost per kg depends on the recovery ROUTE, not just the weight.
# Refining a PCB for precious metals is far costlier per kg than shredding a
# steel appliance for scrap. Indicative Indian-market figures (Rs/kg).
DEFAULT_PROCESSING = 120.0
GENERIC_KEYS = ("ewaste_generic", "waste_generic")

PROCESSING = {
    # precious-metal refining (acid / thermal routes)
    "motherboard": 120.0, "smartphone": 120.0, "laptop": 120.0, "ram": 120.0,
    "cpu": 120.0, "hdd": 120.0, "adapter": 120.0, "remote": 120.0,
    # hydrometallurgical battery recovery
    "liion_battery": 60.0,
    # leaded glass - specialist handling, inherently a net cost
    "crt": 45.0,
    # shredding + ferrous / non-ferrous separation
    "tv_led": 18.0, "appliance": 18.0,
    # stripping / baling
    "copper_wire": 15.0,
}

# ------------------------------------------------------- e-waste profiles
# yields: kg of metal per tonne (1000 kg) of that device
# components: (name, share % of device mass, what it carries)
DEVICES = {
    "motherboard": dict(
        label="Desktop motherboard / PCB", is_electronic=True, avg_weight_g=600,
        yields=dict(gold=0.25, silver=1.0, palladium=0.10, copper=200, aluminium=20,
                    iron=30, tin=10, lead=5, zinc=5),
        components=[("Fibreglass substrate", 55, "Copper tracks, resin"),
                    ("CPU socket / VRM", 8, "Gold, copper"),
                    ("Capacitors", 8, "Aluminium, tantalum"),
                    ("Connectors & slots", 12, "Gold fingers, copper, tin"),
                    ("Solder", 5, "Tin, lead"),
                    ("Chipset / ICs", 12, "Gold, silver, palladium")],
        note="Highest-grade fraction in consumer e-waste."),
    "smartphone": dict(
        label="Smartphone", is_electronic=True, avg_weight_g=180,
        yields=dict(gold=0.30, silver=1.0, palladium=0.10, copper=130, aluminium=40,
                    iron=30, lithium=14, cobalt=28, nickel=10, neodymium=0.3),
        components=[("Main PCB", 25, "Gold, silver, palladium, copper"),
                    ("Li-ion battery", 25, "Lithium, cobalt, nickel, graphite"),
                    ("Display assembly", 20, "Glass, indium, rare earths"),
                    ("Casing", 20, "Aluminium or plastic"),
                    ("Camera & sensors", 5, "Copper, gold, rare earths"),
                    ("Vibration motor / speaker", 5, "Neodymium, copper")],
        note="Per-kg gold content rivals high-grade ore."),
    "laptop": dict(
        label="Laptop / notebook", is_electronic=True, avg_weight_g=2200,
        yields=dict(gold=0.20, silver=0.80, palladium=0.08, copper=150, aluminium=100,
                    iron=200, lithium=10, cobalt=20, nickel=8, neodymium=0.2),
        components=[("Motherboard", 12, "Gold, silver, palladium, copper"),
                    ("Battery pack", 20, "Lithium, cobalt, nickel"),
                    ("Display", 18, "Glass, indium"),
                    ("Storage drive", 8, "Aluminium, neodymium magnet, copper"),
                    ("Casing", 22, "Aluminium / magnesium / plastic"),
                    ("Keyboard & chassis", 12, "Plastic, steel"),
                    ("Cooling / heatsink", 8, "Copper, aluminium")],
        note="Mixed fraction; battery is the value driver."),
    "liion_battery": dict(
        label="Lithium-ion battery", is_electronic=True, avg_weight_g=45,
        yields=dict(lithium=20, cobalt=150, nickel=80, copper=70, aluminium=50, iron=100),
        components=[("Cathode", 30, "Lithium, cobalt, nickel"),
                    ("Anode", 15, "Graphite, copper foil"),
                    ("Current collectors", 12, "Copper, aluminium foil"),
                    ("Electrolyte", 15, "Lithium salts"),
                    ("Casing & safety", 28, "Steel, aluminium, plastics")],
        hazardous=True,
        note="Fire risk if punctured. Never charge a swollen cell."),
    "copper_wire": dict(
        label="Copper cable / wire", is_electronic=False, avg_weight_g=100,
        yields=dict(copper=600),
        components=[("Copper conductor", 60, "Copper"),
                    ("Insulation", 40, "PVC / rubber")],
        note="Stripping the insulation roughly doubles the price.",
        bin="recyclable",
        decomposition="Copper does not degrade; insulation persists 500+ years"),
    "ram": dict(
        label="RAM module / memory stick", is_electronic=True, avg_weight_g=25,
        yields=dict(gold=0.30, silver=0.50, copper=150, tin=20),
        components=[("PCB substrate", 65, "Copper tracks"),
                    ("Gold edge connector", 8, "Gold"),
                    ("Memory ICs", 20, "Gold, silver"),
                    ("Solder & passives", 7, "Tin, copper")],
        note="Edge connectors carry visible gold plating."),
    "cpu": dict(
        label="CPU / processor", is_electronic=True, avg_weight_g=12,
        yields=dict(gold=0.50, silver=1.5, palladium=0.20, copper=100),
        components=[("Silicon die", 10, "Gold, silver, palladium"),
                    ("Package / substrate", 40, "Gold bond wires, copper"),
                    ("Pins / pads", 25, "Gold plating"),
                    ("Heat spreader", 25, "Copper, nickel")],
        note="Richest single component by weight."),
    "hdd": dict(
        label="Hard disk drive", is_electronic=True, avg_weight_g=450,
        yields=dict(aluminium=300, iron=200, copper=20, neodymium=20, silver=0.05,
                    gold=0.10),
        components=[("Aluminium chassis", 45, "Aluminium"),
                    ("Platters", 12, "Aluminium, cobalt alloy"),
                    ("Voice coil magnet", 5, "Neodymium, praseodymium"),
                    ("PCB", 6, "Gold, silver, copper"),
                    ("Motor & steel", 32, "Iron, copper")],
        note="The magnet is one of the best neodymium sources in e-waste."),
    "tv_led": dict(
        label="LED / LCD television", is_electronic=True, avg_weight_g=12000,
        yields=dict(iron=100, copper=20, aluminium=10, silver=0.02, gold=0.01, tin=2),
        components=[("Panel / glass", 45, "Glass, indium, liquid crystal"),
                    ("Steel & stand", 25, "Iron"),
                    ("Driver PCBs", 8, "Copper, gold, silver"),
                    ("Plastic housing", 18, "ABS / PS"),
                    ("Cabling", 4, "Copper")],
        note="Low metal value per kg; handle the panel carefully."),
    "appliance": dict(
        label="Large appliance (washer / fridge)", is_electronic=True, avg_weight_g=60000,
        yields=dict(iron=600, copper=30, aluminium=20),
        components=[("Steel body", 60, "Iron"),
                    ("Motor / compressor", 15, "Copper, iron"),
                    ("Wiring", 5, "Copper"),
                    ("Plastics", 20, "PP / ABS")],
        note="Value is almost entirely bulk steel."),
    "crt": dict(
        label="CRT monitor / old TV", is_electronic=True, avg_weight_g=20000,
        yields=dict(iron=50, copper=20, lead=20, aluminium=10),
        components=[("Leaded glass funnel", 45, "Lead, glass"),
                    ("Copper yoke & wiring", 10, "Copper"),
                    ("Steel frame", 25, "Iron"),
                    ("Electronics", 10, "Copper, tin, gold trace"),
                    ("Plastics", 10, "ABS")],
        hazardous=True,
        note="Contains leaded glass. Do not break the tube."),
    "adapter": dict(
        label="Power adapter / charger", is_electronic=True, avg_weight_g=120,
        yields=dict(copper=200, iron=50, gold=0.05, aluminium=20),
        components=[("Transformer winding", 35, "Copper"),
                    ("PCB", 20, "Copper, gold, tin"),
                    ("Plastic shell", 35, "ABS / PC"),
                    ("Cable", 10, "Copper")],
        note="Copper winding is the main value."),
    # Fallback profile: used when the vision model names something that is not in
    # the catalogue. Deliberately conservative - a mixed small-electronics assay.
    # Hidden from the model's catalogue list so it never short-circuits a specific ID.
    "ewaste_generic": dict(
        label="Mixed electronic item", is_electronic=True, avg_weight_g=250,
        yields=dict(gold=0.15, silver=0.6, palladium=0.05, copper=90,
                    aluminium=50, iron=90, tin=8, nickel=3),
        components=[("Circuit board", 30, "Gold, silver, palladium, copper"),
                    ("Wiring & motors", 25, "Copper, iron"),
                    ("Casing", 30, "Plastic or aluminium"),
                    ("Other", 15, "Mixed")],
        note="Generic mixed-electronics estimate - pick a specific item if you can."),
    "remote": dict(
        label="TV remote control", is_electronic=True, avg_weight_g=90,
        yields=dict(iron=30, copper=20, zinc=10),
        components=[("Plastic shell", 55, "ABS"),
                    ("PCB", 15, "Copper, tin, silver"),
                    ("Contacts & springs", 20, "Iron, copper"),
                    ("Battery contacts", 10, "Zinc, nickel")],
        note="Low value; recycle rather than bin."),
}

# ------------------------------------------------------------ general waste
# bin: wet | dry | recyclable | hazardous
ITEMS = {
    # Fallback profile for non-electronic items the catalogue does not cover.
    "waste_generic": dict(
        label="Other general waste", is_electronic=False, avg_weight_g=100,
        bin="dry", decomposition="Varies by material", rate_inr_per_kg=8.0,
        materials=[("Mixed material", 100, True, "Depends on composition")]),
    "pet_bottle": dict(
        label="PET water bottle", is_electronic=False, avg_weight_g=25,
        bin="recyclable", decomposition="~450 years", rate_inr_per_kg=25.0,
        materials=[("PET plastic", 92, True, "Polyester fibre / new flakes"),
                   ("HDPE cap", 5, True, "New caps / crates"),
                   ("Label & adhesive", 3, False, "Residue")]),
    "hdpe_bottle": dict(
        label="HDPE bottle (milk / detergent)", is_electronic=False, avg_weight_g=40,
        bin="recyclable", decomposition="~100+ years", rate_inr_per_kg=40.0,
        materials=[("HDPE plastic", 100, True, "Pipes, crates, new bottles")]),
    "alu_can": dict(
        label="Aluminium drink can", is_electronic=False, avg_weight_g=15,
        bin="recyclable", decomposition="~200 years", rate_inr_per_kg=150.0,
        materials=[("Aluminium", 100, True, "New cans - 95% less energy")]),
    "tin_can": dict(
        label="Steel / tin food can", is_electronic=False, avg_weight_g=50,
        bin="recyclable", decomposition="~50 years", rate_inr_per_kg=25.0,
        materials=[("Steel", 96, True, "New steel"),
                   ("Tin coating", 2, True, "Recovered tin"),
                   ("Label", 2, False, "Residue")]),
    "cardboard": dict(
        label="Cardboard box", is_electronic=False, avg_weight_g=200,
        bin="recyclable", decomposition="~2 months", rate_inr_per_kg=12.0,
        materials=[("Paper fibre", 94, True, "New cartons"),
                   ("Adhesive / tape", 6, False, "Residue")]),
    "newspaper": dict(
        label="Newspaper / paper", is_electronic=False, avg_weight_g=150,
        bin="recyclable", decomposition="~6 weeks", rate_inr_per_kg=15.0,
        materials=[("Paper fibre", 100, True, "Recycled paper")]),
    "glass_bottle": dict(
        label="Glass bottle", is_electronic=False, avg_weight_g=300,
        bin="recyclable", decomposition="~1 million years", rate_inr_per_kg=5.0,
        materials=[("Soda-lime glass", 100, True, "New glass containers")]),
    "fruit_peel": dict(
        label="Fruit / vegetable peel", is_electronic=False, avg_weight_g=120,
        bin="wet", decomposition="2-5 weeks", rate_inr_per_kg=0.0,
        materials=[("Organic matter", 100, True, "Compost / biogas")]),
    "food_scraps": dict(
        label="Cooked food waste", is_electronic=False, avg_weight_g=150,
        bin="wet", decomposition="1-2 weeks", rate_inr_per_kg=0.0,
        materials=[("Organic matter", 100, True, "Compost / biogas")]),
    "garden_waste": dict(
        label="Leaves / garden waste", is_electronic=False, avg_weight_g=300,
        bin="wet", decomposition="~6 months", rate_inr_per_kg=0.0,
        materials=[("Organic matter", 100, True, "Compost / mulch")]),
    "plastic_bag": dict(
        label="Plastic carry bag (LDPE)", is_electronic=False, avg_weight_g=8,
        bin="dry", decomposition="~500+ years", rate_inr_per_kg=20.0,
        materials=[("LDPE film", 100, True, "Carry bags, bin liners")]),
    "multilayer_pouch": dict(
        label="Multilayer snack / milk pouch", is_electronic=False, avg_weight_g=6,
        bin="dry", decomposition="~500+ years", rate_inr_per_kg=10.0,
        materials=[("PET film", 30, False, "Hard to separate"),
                   ("Polyethylene", 55, False, "Hard to separate"),
                   ("Aluminium foil", 15, True, "Recoverable after delamination")],
        note="Multi-layer laminate - most kerbside programs reject it."),
    "tetrapak": dict(
        label="Tetra Pak carton", is_electronic=False, avg_weight_g=25,
        bin="dry", decomposition="~100 years", rate_inr_per_kg=8.0,
        materials=[("Paper fibre", 70, True, "Recycled board"),
                   ("Polyethylene", 25, True, "Plastic pellets"),
                   ("Aluminium foil", 5, True, "Aluminium")]),
    "thermocol": dict(
        label="Thermocol / EPS foam", is_electronic=False, avg_weight_g=10,
        bin="dry", decomposition="~500+ years", rate_inr_per_kg=15.0,
        materials=[("Expanded polystyrene", 100, True, "Compacted EPS blocks")]),
    "paper_cup": dict(
        label="Paper cup (laminated)", is_electronic=False, avg_weight_g=10,
        bin="dry", decomposition="~100 years", rate_inr_per_kg=8.0,
        materials=[("Paper fibre", 88, True, "Recycled board"),
                   ("PE lining", 12, False, "Residue")]),
    "brass": dict(
        label="Brass fitting / tap", is_electronic=False, avg_weight_g=80,
        bin="recyclable", decomposition="Does not degrade", rate_inr_per_kg=450.0,
        materials=[("Copper", 60, True, "New brass"),
                   ("Zinc", 38, True, "New brass"),
                   ("Other", 2, False, "Residue")]),
    "tyre": dict(
        label="Rubber tyre", is_electronic=False, avg_weight_g=9000,
        bin="dry", decomposition="~2000 years", rate_inr_per_kg=10.0,
        materials=[("Rubber", 70, True, "Crumb rubber"),
                   ("Steel belt", 20, True, "Scrap steel"),
                   ("Textile", 10, False, "Residue")]),
    "paint_tin": dict(
        label="Paint / chemical tin", is_electronic=False, avg_weight_g=500,
        bin="hazardous", decomposition="Does not degrade", rate_inr_per_kg=0.0,
        materials=[("Steel", 60, True, "Recycled steel if cleaned"),
                   ("Paint residue", 40, False, "Hazardous waste")],
        hazardous=True,
        note="Do not puncture or burn. Hand to an authorised collector."),
    "cfl_tubelight": dict(
        label="CFL / tube light", is_electronic=False, avg_weight_g=120,
        bin="hazardous", decomposition="Does not degrade", rate_inr_per_kg=0.0,
        materials=[("Glass", 70, False, "Mercury contaminated"),
                   ("Mercury vapour", 1, False, "Hazardous"),
                   ("Metal & phosphor", 29, True, "Recoverable")],
        hazardous=True,
        note="Contains mercury. Never break it indoors."),
    "medical_waste": dict(
        label="Medical waste / syringe", is_electronic=False, avg_weight_g=15,
        bin="hazardous", decomposition="Does not degrade", rate_inr_per_kg=0.0,
        materials=[("Plastic", 70, False, "Infectious waste"),
                   ("Steel needle", 20, False, "Sharps"),
                   ("Biological", 10, False, "Infectious waste")],
        hazardous=True,
        note="Biohazard. Use a sharps box and authorised disposal only."),
}


def catalog():
    """Flat, searchable catalog of everything the app knows."""
    out = []
    for key, d in DEVICES.items():
        out.append(dict(key=key, label=d["label"],
                        kind=("e-waste" if d.get("is_electronic", True) else "metal"),
                        is_electronic=d["is_electronic"], avg_weight_g=d["avg_weight_g"],
                        hazardous=d.get("hazardous", False)))
    for key, d in ITEMS.items():
        out.append(dict(key=key, label=d["label"], kind="waste",
                        is_electronic=False, avg_weight_g=d["avg_weight_g"],
                        hazardous=d.get("hazardous", False)))
    return sorted(out, key=lambda x: (not x["is_electronic"], x["label"]))


def get(key):
    if key in DEVICES:
        d = dict(DEVICES[key]); d["key"] = key
        d["kind"] = "e-waste" if d.get("is_electronic", True) else "metal"
        return d
    if key in ITEMS:
        d = dict(ITEMS[key]); d["kind"] = "waste"; d["key"] = key; return d
    return None
