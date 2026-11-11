"""Script and shot cues for the detailed rooftop-solar explainer."""

# Narrative sources and scope are recorded in docs/SOLAR_PRODUCTION.md.
# Keep each scene on one physical idea so narration can drive its duration.
SOLAR_MECHANISMS = [
    ("Look closely at this ordinary roof. The silver lines on each solar cell are tiny current collectors.",
     "house", "appear", "establish", "A solar roof, up close"),
    ("The panels sit on rails above the roof. That gap leaves room for air to move underneath.",
     "panels", "assemble", "overhead", "Roof rails and air gap"),
    ("Zoom in on one cell. Light passes through the front surface and reaches the silicon, beneath the metal grid.",
     "pv_cell", "appear", "section", "Enlarged silicon cell"),
    ("An absorbed photon can free an electron, leaving a hole. A hole is a missing electron that acts like a positive charge.",
     "pv_light", "flow", "section", "Photon creates a pair"),
    ("An electric field at the junction separates the pair. Electrons and holes move toward opposite sides before they can recombine.",
     "pv_carriers", "flow", "section", "Junction separates charge"),
    ("Metal contacts collect the charge. Join cells in series, and their voltages add. The module sends direct current down the conduit.",
     "panels", "highlight", "detail", "Series cells add voltage"),
    ("One leaf can matter. In a series path, a shaded cell can limit the current through the unshaded cells too.",
     "pv_shade", "appear", "overhead", "One shaded cell can limit current"),
    ("A bypass diode gives current a path around a shaded group. The other groups can still produce, but the bypassed group loses voltage.",
     "pv_bypass", "flow", "section", "Bypass trades voltage for current"),
    ("The inverter tracks the operating voltage that gives the panels the most power. Then it converts the direct current into alternating current.",
     "inverter", "appear", "detail", "Track power, then convert DC to AC"),
    ("At the distribution panel, breakers protect the separate circuits. Solar can supply the porch light and other loads as they draw power.",
     "distribution", "appear", "detail", "Distribution and circuit protection"),
    ("If generation exceeds demand, a system allowed to export can send the surplus out. The meter measures the exchange in both directions.",
     "grid", "flow", "section", "Meter measures import and export"),
    ("A battery can shift energy into the evening. Backup during a blackout also needs equipment that can safely isolate the home from the grid.",
     "battery", "appear", "overhead", "Storage and backup are different"),
]

SOLAR_EXTRA = [
    "The grid has a trade-off. Thicker contacts carry current better, but they also block more light from reaching the cell.",
    "Airflow matters because hot silicon cells usually produce less voltage. A hotter roof does not automatically mean more solar power.",
    "The dark front surface reduces reflected light. More light entering the silicon gives the cell more opportunities to generate charge.",
    "Not every photon can create a mobile pair. Photons with too little energy can pass through, while some energy becomes heat.",
    "Some carriers still recombine before reaching a contact. That loss helps explain why the cell cannot convert all incoming light into electricity.",
    "The silver fingers gather charge locally. Wider busbars connect groups of fingers and carry current to the next cell.",
    "The exact loss depends on which cells are shaded, how the module is wired, and how the inverter operates the string.",
    "The bypass diode protects a group of cells, so a small shadow can switch out more than the one cell it covers.",
    "As sunlight and temperature change, the best operating voltage changes too. Tracking it helps the inverter harvest available power.",
    "The two sides serve different jobs. The inverter converts power, while a breaker opens a circuit if it carries too much current.",
    "The utility meter sees the difference between what the home consumes and what solar supplies. It does not directly measure every panel.",
    "A battery has two separate limits. Power determines how many loads it can serve at once. Energy determines how long it can keep serving them.",
]
