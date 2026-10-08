"""Handwriting practice sheets built from the letters cut out of the scanned page."""
import json, os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GLYPHS = os.path.join(HERE, "glyphs")
META = json.load(open(os.path.join(GLYPHS, "meta.json")))
pdfmetrics.registerFont(TTFont("SimHei", r"C:\Windows\Fonts\simhei.ttf"))

OUT = r"C:\Users\voyag\Desktop\练字\字帖_All the Letters and Numerals.pdf"
W, H = A4
M = 40                      # side margin
U = 12                      # one line-gap unit (top->mid->base->bottom)
ROW = 3 * U + 16            # row height incl. gap

BLUE = HexColor("#5BB8E6")
RED = HexColor("#E0457B")
BLACK = (26, 26, 26)
GREEN = (107, 179, 62)
ORANGE = (240, 127, 45)
TRACE = (196, 196, 196)

_cache = {}


def glyph(ch, rgb):
    """Scanned glyph tinted to rgb, as an ImageReader (cached)."""
    key = (ch, rgb)
    if key not in _cache:
        a = Image.open(os.path.join(GLYPHS, META[ch]["file"])).getchannel("A")
        a = a.resize((a.width // 2, a.height // 2), Image.LANCZOS)
        im = Image.new("RGBA", a.size, rgb + (255,))
        im.putalpha(a)
        _cache[key] = ImageReader(im)
    return _cache[key]


def guide(c, y):
    """Draw four-line guide; y = baseline."""
    x0, x1 = M, W - M
    c.setLineWidth(0.8)
    c.setStrokeColor(BLUE)
    c.line(x0, y + 2 * U, x1, y + 2 * U)
    c.line(x0, y - U, x1, y - U)
    c.setDash(5, 4)
    c.line(x0, y + U, x1, y + U)
    c.setDash()
    c.setStrokeColor(RED)
    c.line(x0, y, x1, y)


# Marks the scan has no glyph for are drawn as strokes in line units (baseline 0,
# x-height 1, cap 2), upright, then slanted and stroked like the scanned letters.
SLANT = 0.33                # measured from the scan's I, l, 1, T
STROKE = 0.15               # stroke width in line units


def _omega(c):
    c.arc(0.2, 0.38, 1.5, 2.02, -55, 290)
    for x0, foot in ((1.22, 1.55), (0.48, 0.15)):
        c.line(x0, 0.53, x0, 0); c.line(x0, 0, foot, 0)


DRAWN = {   # char: (advance in line units, drawing function)
    ",": (0.4, lambda c: c.line(0.15, 0.1, 0.0, -0.35)),
    ".": (0.45, lambda c: c.circle(0.1, 0.08, 0.06, stroke=1, fill=1)),
    "'": (0.45, lambda c: c.line(0.15, 2.0, 0.08, 1.55)),
    "-": (1.0, lambda c: c.line(-0.1, 0.9, 0.45, 0.9)),
    "/": (1.3, lambda c: c.line(0.1, -0.15, 0.5, 2.05)),
    "·": (0.75, lambda c: c.circle(0.15, 0.9, 0.06, stroke=1, fill=1)),
    "°": (1.15, lambda c: c.circle(0.3, 1.7, 0.25)),
    "(": (1.0, lambda c: c.arc(0.15, -0.75, 1.35, 2.35, 115, 130)),
    ")": (1.1, lambda c: c.arc(-0.6, -0.75, 0.6, 2.35, -65, 130)),
    "⁻": (0.6, lambda c: c.line(0.05, 1.65, 0.45, 1.65)),
    "μ": (0.0, lambda c: c.line(0.07, 0.95, 0.07, -1.0)),   # tail; the "u" glyph follows
    "Ω": (2.0, _omega),
}
SUPER = {"²": "2", "³": "3"}
SUB = {chr(0x2080 + d): str(d) for d in range(10)}   # ₀-₉


def draw_mark(c, ch, x, y, u, rgb):
    c.saveState()
    c.translate(x, y); c.transform(1, 0, SLANT, 1, 0, 0); c.scale(u, u)
    c.setStrokeColorRGB(*[v / 255 for v in rgb]); c.setFillColorRGB(*[v / 255 for v in rgb])
    c.setLineWidth(STROKE); c.setLineCap(1); c.setLineJoin(1)
    DRAWN[ch][1](c)
    c.restoreState()


def text(c, x, y, s, color, gap=0.12, u=U):
    """Write s (string or list of glyph names) with scanned glyphs; returns end x.

    color is an rgb tuple or a callable mapping each char to one; u is the line unit."""
    for ch in s:
        if ch == " ":
            x += 0.7 * u
            continue
        rgb = color(ch) if callable(color) else color
        if ch in SUPER:
            x = text(c, x - 0.1 * u, y + 1.0 * u, SUPER[ch], rgb, gap, 0.5 * u)
            continue
        if ch in SUB:
            x = text(c, x - 0.05 * u, y - 0.4 * u, SUB[ch], rgb, gap, 0.5 * u)
            continue
        if ch in DRAWN:
            draw_mark(c, ch, x, y, u, rgb)
            if ch == "μ":
                x = text(c, x, y, "u", rgb, gap, u)
            x += DRAWN[ch][0] * u
            continue
        m = META[ch]
        c.drawImage(glyph(ch, rgb), x, y + (m["top"] - m["h"]) * u,
                    m["w"] * u, m["h"] * u, mask="auto")
        x += (m["w"] + gap) * u
    return x


def width(s, gap=0.12, u=U):
    """Width text() would use for s."""
    total = 0
    for ch in s:
        if ch == " ":
            total += 0.7 * u
        elif ch in SUPER:
            total += -0.1 * u + width(SUPER[ch], gap, 0.5 * u)
        elif ch in SUB:
            total += -0.05 * u + width(SUB[ch], gap, 0.5 * u)
        elif ch in DRAWN:
            total += DRAWN[ch][0] * u + (width("u", gap, u) if ch == "μ" else 0)
        else:
            total += (META[ch]["w"] + gap) * u
    return total


def pair_color(ch):
    return BLACK if ch.isupper() else GREEN


def header(c, title, sub, page, pw=W, ph=H):
    c.setFillColor(HexColor("#F07F2D"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(M, ph - 55, title)
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", 10)
    c.drawString(M, ph - 72, sub)
    c.drawRightString(pw - M, ph - 72, "Name: ____________   Date: ____________")
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(pw / 2, 22, str(page))


def practice_page(c, page, title, sub, rows, start_y=None):
    """rows: list of (model, traces). model = [(seq, color), ...] drawn first;
    traces = gray candidates; the first that fits is repeated (max 2) while it fits."""
    header(c, title, sub, page)
    y = top if start_y is None else start_y
    for model, traces in rows:
        guide(c, y)
        x = M + 6
        for seq, col in model:
            x = text(c, x, y, seq, col) + 0.9 * U
        room = W - M - 4 - 1.2 * U
        t = next((t for t in traces if x + width(t) <= room), None)
        for _ in range(2):
            if t is None or x + width(t) > room:
                break
            x = text(c, x + 1.2 * U, y, t, TRACE)
        y -= ROW
    return y


c = canvas.Canvas(OUT, pagesize=A4)
c.setTitle("All the Letters and Numerals - Practice")
page = 1
letters = [chr(i) for i in range(65, 91)]
top = H - 115

# --- Each letter pair: model + 3 tracings, rest of the line blank --------
for start in range(0, 26, 13):
    header(c, "All the Letters and Numerals",
           "Trace the gray letters, then write your own on the rest of the line.", page)
    y = top
    for L in letters[start:start + 13]:
        guide(c, y)
        x = text(c, M + 6, y, L + L.lower(), pair_color, gap=0)
        for _ in range(3):
            x = text(c, x + 1.6 * U, y, L + L.lower(), TRACE, gap=0)
        y -= ROW
    c.showPage(); page += 1

# --- Numerals 1-10 -------------------------------------------------------
header(c, "Numerals 1-10", "Trace the gray numerals, then write your own.", page)
y = top
for i in range(1, 11):
    n = [str(i)]
    guide(c, y)
    x = text(c, M + 6, y, n, ORANGE)
    for _ in range(6):
        x = text(c, x + 1.8 * U, y, n, TRACE)
    y -= ROW
c.showPage(); page += 1

# --- Review page, laid out like the original ----------------------------
header(c, "All the Letters and Numerals - Review",
       "Trace each line, then copy it on the blank line below.", page)
y = top
nums = [str(i) for i in range(1, 11)]
for g in (letters[0:8], letters[8:17], letters[17:26]):
    for col in (pair_color, TRACE):
        guide(c, y)
        x = M + 6
        for L in g:
            x = text(c, x, y, L + L.lower(), col, gap=0) + 1.1 * U
        y -= ROW
    guide(c, y); y -= ROW
for col in (ORANGE, TRACE):
    guide(c, y)
    x = M + 6
    for n in nums:
        x = text(c, x, y, [n], col) + 1.3 * U
    y -= ROW
guide(c, y)
c.showPage(); page += 1

# --- Months ----------------------------------------------------------------
header(c, "Names of the Months", "Trace each month, then write it again.", page)
months = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
y = top
for mo in months:
    guide(c, y)
    x = text(c, M + 6, y, mo, pair_color)
    text(c, x + 2.5 * U, y, mo, TRACE)
    y -= ROW
c.showPage(); page += 1

# --- Days of the week -------------------------------------------------------
DAYS = [("Sun", "Sunday", "星期日"), ("Mon", "Monday", "星期一"), ("Tue", "Tuesday", "星期二"),
        ("Wed", "Wednesday", "星期三"), ("Thu", "Thursday", "星期四"),
        ("Fri", "Friday", "星期五"), ("Sat", "Saturday", "星期六")]
y = practice_page(c, page, "Days of the Week",
                  "Short form and full name. Trace the gray words.",
                  [([(ab, pair_color), (day, pair_color)], [day]) for ab, day, _ in DAYS])
c.setFillColor(HexColor("#888888")); c.setFont("SimHei", 8)
for k, (_, _, zh) in enumerate(DAYS):
    c.drawRightString(W - M, top - k * ROW + 2 * U + 3, zh)
y -= 14
c.setFillColor(HexColor("#555555")); c.setFont("Helvetica", 10)
c.drawString(M, y + 2 * U + 8, "Now write the seven days in order:")
while y > 50:
    guide(c, y); y -= ROW
c.showPage(); page += 1

# --- Write today's date --------------------------------------------------
header(c, "Write Today's Date", "Use the name of the month.", page)
c.setFillColor(HexColor("#555555")); c.setFont("Helvetica", 10)
c.drawString(M, top - 16 + 2 * U + 8, "Example - trace it:")
y = top - 16
guide(c, y)
text(c, M + 6, y, list("Monday, October 5, 2") + ["0", "2", "6"], TRACE)
y -= ROW
c.setFillColor(HexColor("#555555")); c.setFont("Helvetica", 10)
c.drawString(M, y + 2 * U + 8, "Circle the uppercase letter that starts the name of the month.")
y -= 14
while y > 50:
    guide(c, y); y -= ROW
c.showPage(); page += 1

# --- Periodic table ------------------------------------------------------
ELEMENTS = """H Hydrogen,He Helium,Li Lithium,Be Beryllium,B Boron,C Carbon,N Nitrogen,O Oxygen,
F Fluorine,Ne Neon,Na Sodium,Mg Magnesium,Al Aluminum,Si Silicon,P Phosphorus,S Sulfur,
Cl Chlorine,Ar Argon,K Potassium,Ca Calcium,Sc Scandium,Ti Titanium,V Vanadium,Cr Chromium,
Mn Manganese,Fe Iron,Co Cobalt,Ni Nickel,Cu Copper,Zn Zinc,Ga Gallium,Ge Germanium,
As Arsenic,Se Selenium,Br Bromine,Kr Krypton,Rb Rubidium,Sr Strontium,Y Yttrium,
Zr Zirconium,Nb Niobium,Mo Molybdenum,Tc Technetium,Ru Ruthenium,Rh Rhodium,Pd Palladium,
Ag Silver,Cd Cadmium,In Indium,Sn Tin,Sb Antimony,Te Tellurium,I Iodine,Xe Xenon,
Cs Cesium,Ba Barium,La Lanthanum,Ce Cerium,Pr Praseodymium,Nd Neodymium,Pm Promethium,
Sm Samarium,Eu Europium,Gd Gadolinium,Tb Terbium,Dy Dysprosium,Ho Holmium,Er Erbium,
Tm Thulium,Yb Ytterbium,Lu Lutetium,Hf Hafnium,Ta Tantalum,W Tungsten,Re Rhenium,
Os Osmium,Ir Iridium,Pt Platinum,Au Gold,Hg Mercury,Tl Thallium,Pb Lead,Bi Bismuth,
Po Polonium,At Astatine,Rn Radon,Fr Francium,Ra Radium,Ac Actinium,Th Thorium,
Pa Protactinium,U Uranium,Np Neptunium,Pu Plutonium,Am Americium,Cm Curium,Bk Berkelium,
Cf Californium,Es Einsteinium,Fm Fermium,Md Mendelevium,No Nobelium,Lr Lawrencium,
Rf Rutherfordium,Db Dubnium,Sg Seaborgium,Bh Bohrium,Hs Hassium,Mt Meitnerium,
Ds Darmstadtium,Rg Roentgenium,Cn Copernicium,Nh Nihonium,Fl Flerovium,Mc Moscovium,
Lv Livermorium,Ts Tennessine,Og Oganesson"""
ELEMENTS = [e.split() for e in ELEMENTS.replace("\n", "").split(",")]
assert len(ELEMENTS) == 118

CATEGORIES = [   # (label, fill, atomic numbers)
    ("Alkali metal", "#FBD3C4", [3, 11, 19, 37, 55, 87]),
    ("Alkaline earth metal", "#FCE6B8", [4, 12, 20, 38, 56, 88]),
    ("Transition metal", "#F6EFC4", list(range(21, 31)) + list(range(39, 49))
     + list(range(72, 81)) + list(range(104, 113))),
    ("Post-transition metal", "#D8EBC8", [13, 31, 49, 50, 81, 82, 83, 84, 113, 114, 115, 116]),
    ("Metalloid", "#C8E6DE", [5, 14, 32, 33, 51, 52]),
    ("Nonmetal", "#CFE3F6", [1, 6, 7, 8, 15, 16, 34]),
    ("Halogen", "#DCD6F2", [9, 17, 35, 53, 85, 117]),
    ("Noble gas", "#F2D3E6", [2, 10, 18, 36, 54, 86, 118]),
    ("Lanthanide", "#E6E6E6", list(range(57, 72))),
    ("Actinide", "#F0E0D0", list(range(89, 104))),
]
FILL = {z: col for _, col, zs in CATEGORIES for z in zs}


def position(z):
    """(row, column) in the 18-column table; rows 8/9 hold lanthanides/actinides."""
    if z == 1: return 0, 0
    if z == 2: return 0, 17
    for period, (start, end) in enumerate([(3, 10), (11, 18)], 1):
        if start <= z <= end:
            i = z - start
            return period, i if i < 2 else i + 10
    for period, start in ((3, 19), (4, 37)):
        if start <= z <= start + 17:
            return period, z - start
    for period, start in ((5, 55), (6, 87)):
        if not start <= z <= start + 31:
            continue
        if z - start < 2:
            return period, z - start
        if z - start <= 16:
            return period + 2, z - start + 1          # f-block rows, under columns 3-17
        return period, z - start - 14
    raise ValueError(z)


def periodic_table(c, page, trace):
    PW, PH = H, W                                   # landscape
    c.setPageSize((PW, PH))
    header(c, "Periodic Table of the Elements",
           "Trace the gray symbols." if trace else
           "Each box: atomic number and element symbol.", page, PW, PH)
    cw, ch = (PW - 2 * M) / 18, 44
    y_top = PH - 92
    u = 6.2                                         # line unit inside a cell
    for z, (sym, _name) in enumerate(ELEMENTS, 1):
        r, col = position(z)
        x = M + col * cw
        y = y_top - (r + 1) * ch - (10 if r >= 7 else 0)
        c.setFillColor(HexColor(FILL[z])); c.setStrokeColor(HexColor("#9A9A9A"))
        c.setLineWidth(0.5)
        c.rect(x, y, cw, ch, fill=1, stroke=1)
        base = y + 9
        c.setLineWidth(0.3)                         # mini four-line guide for the symbol
        c.setStrokeColor(BLUE); c.line(x + 2, base + 2 * u, x + cw - 2, base + 2 * u)
        c.setStrokeColor(RED); c.line(x + 2, base, x + cw - 2, base)
        text(c, x + 3, y + ch - 9, str(z), ORANGE, gap=0.08, u=3.0)
        sw = width(sym, gap=0, u=u)
        text(c, x + (cw - sw) / 2, base, sym, TRACE if trace else pair_color, gap=0, u=u)
    # f-block placeholders in column 3
    c.setFillColor(HexColor("#555555")); c.setFont("Helvetica", 6)
    for r, lbl in ((5, "57-71"), (6, "89-103")):
        c.drawCentredString(M + 2.5 * cw, y_top - (r + 1) * ch + ch / 2 - 2, lbl)
    # group numbers
    c.setFont("Helvetica", 6.5); c.setFillColor(HexColor("#888888"))
    for g in range(18):
        r0 = 0 if g in (0, 17) else 1 if g < 2 or g > 11 else 3
        c.drawCentredString(M + (g + 0.5) * cw, y_top - r0 * ch + 3, str(g + 1))
    # legend between main table and f-block
    lx, ly = M + 2.6 * cw, y_top - 1.15 * ch
    c.setFont("Helvetica", 7)
    for i, (label, col, _) in enumerate(CATEGORIES):
        xx, yy = lx + (i % 5) * 1.95 * cw, ly - (i // 5) * 12
        c.setFillColor(HexColor(col)); c.setStrokeColor(HexColor("#9A9A9A"))
        c.rect(xx, yy, 8, 8, fill=1, stroke=1)
        c.setFillColor(HexColor("#444444")); c.drawString(xx + 11, yy + 1, label)
    c.showPage()
    c.setPageSize(A4)


periodic_table(c, page, trace=False); page += 1
periodic_table(c, page, trace=True); page += 1

for i in range(0, 118, 12):
    rows = [([(str(z), ORANGE), (sym, pair_color), (name, pair_color)],
             [sym + " " + name, name, sym])
            for z, (sym, name) in enumerate(ELEMENTS[i:i + 12], i + 1)]
    practice_page(c, page, "Chemical Elements %d-%d" % (i + 1, min(i + 12, 118)),
                  "Atomic number, symbol and name. Trace the gray words.", rows)
    c.showPage(); page += 1

# --- The eight planets ---------------------------------------------------
PLANETS = ["Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]
y = practice_page(c, page, "The Eight Planets",
                  "In order from the Sun. Trace the gray names.",
                  [([(str(n), ORANGE), (p, pair_color)], [p]) for n, p in enumerate(PLANETS, 1)])
y -= 14
c.setFillColor(HexColor("#555555")); c.setFont("Helvetica", 10)
c.drawString(M, y + 2 * U + 8, "Now write all eight planets in order:")
while y > 50:
    guide(c, y); y -= ROW
c.showPage(); page += 1

# --- Countries: all 193 UN members + 2 observer states ------------------
COUNTRIES = [
    ("Africa", """Algeria, Angola, Benin, Botswana, Burkina Faso, Burundi, Cabo Verde, Cameroon,
     Central African Republic, Chad, Comoros, Democratic Republic of the Congo,
     Republic of the Congo, Djibouti, Egypt, Equatorial Guinea, Eritrea, Eswatini, Ethiopia,
     Gabon, Gambia, Ghana, Guinea, Guinea-Bissau, Ivory Coast, Kenya, Lesotho, Liberia, Libya,
     Madagascar, Malawi, Mali, Mauritania, Mauritius, Morocco, Mozambique, Namibia, Niger,
     Nigeria, Rwanda, Sao Tome and Principe, Senegal, Seychelles, Sierra Leone, Somalia,
     South Africa, South Sudan, Sudan, Tanzania, Togo, Tunisia, Uganda, Zambia, Zimbabwe"""),
    ("Asia", """Afghanistan, Armenia, Azerbaijan, Bahrain, Bangladesh, Bhutan, Brunei, Cambodia,
     China, Cyprus, Georgia, India, Indonesia, Iran, Iraq, Israel, Japan, Jordan, Kazakhstan,
     Kuwait, Kyrgyzstan, Laos, Lebanon, Malaysia, Maldives, Mongolia, Myanmar, Nepal,
     North Korea, Oman, Pakistan, Palestine, Philippines, Qatar, Saudi Arabia, Singapore,
     South Korea, Sri Lanka, Syria, Tajikistan, Thailand, Timor-Leste, Turkey, Turkmenistan,
     United Arab Emirates, Uzbekistan, Vietnam, Yemen"""),
    ("Europe", """Albania, Andorra, Austria, Belarus, Belgium, Bosnia and Herzegovina, Bulgaria,
     Croatia, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Iceland,
     Ireland, Italy, Latvia, Liechtenstein, Lithuania, Luxembourg, Malta, Moldova, Monaco,
     Montenegro, Netherlands, North Macedonia, Norway, Poland, Portugal, Romania, Russia,
     San Marino, Serbia, Slovakia, Slovenia, Spain, Sweden, Switzerland, Ukraine,
     United Kingdom, Vatican City"""),
    ("North America", """Antigua and Barbuda, Bahamas, Barbados, Belize, Canada, Costa Rica,
     Cuba, Dominica, Dominican Republic, El Salvador, Grenada, Guatemala, Haiti, Honduras,
     Jamaica, Mexico, Nicaragua, Panama, Saint Kitts and Nevis, Saint Lucia,
     Saint Vincent and the Grenadines, Trinidad and Tobago, United States"""),
    ("South America", """Argentina, Bolivia, Brazil, Chile, Colombia, Ecuador, Guyana, Paraguay,
     Peru, Suriname, Uruguay, Venezuela"""),
    ("Oceania", """Australia, Fiji, Kiribati, Marshall Islands, Micronesia, Nauru, New Zealand,
     Palau, Papua New Guinea, Samoa, Solomon Islands, Tonga, Tuvalu, Vanuatu"""),
]
COUNTRIES = [(r, [" ".join(n.split()) for n in names.split(",")]) for r, names in COUNTRIES]
assert [len(n) for _, n in COUNTRIES] == [54, 48, 44, 23, 12, 14]

LINE_END = W - M - 4


def split_name(name):
    """Break a name that is too long for one line into two at a space."""
    words = name.split(" ")
    for i in range(len(words) - 1, 0, -1):
        first = " ".join(words[:i])
        if M + 6 + width(first) <= LINE_END:
            return [first, " ".join(words[i:])]
    return [name]


def country_lines(name):
    """(text, color) rows: model, plus a gray row when no gray copy fits beside it."""
    lines = [name] if M + 6 + width(name) <= LINE_END else split_name(name)
    if len(lines) == 1 and M + 6 + 2 * width(name) + 1.2 * U <= LINE_END:
        return [(name, pair_color)]
    return [(ln, pair_color) for ln in lines] + [(ln, TRACE) for ln in lines]


y = None
for region, names in COUNTRIES:
    for k, name in enumerate(names):
        lines = country_lines(name)
        need = len(lines) * ROW + (30 if k == 0 else 0)
        if y is None or y - need + ROW < 50:
            if y is not None:
                c.showPage(); page += 1
            header(c, "Countries of the World",
                   "All 195 countries, by continent. Trace the gray names.", page)
            y = top - 4
            if k > 0:
                c.setFillColor(HexColor("#F07F2D")); c.setFont("Helvetica-Bold", 12)
                c.drawString(M, y + 2 * U + 6, region + " (continued)")
                y -= 14
        if k == 0:
            if y < top:                     # region starts mid-page: extra space above
                y -= 12
            c.setFillColor(HexColor("#F07F2D")); c.setFont("Helvetica-Bold", 12)
            c.drawString(M, y + 2 * U + 6, "%s - %d countries" % (region, len(names)))
            y -= 14
        for ln, col in lines:
            guide(c, y)
            x = text(c, M + 6, y, ln, col)
            for _ in range(2 if col is pair_color else 0):   # gray copies while they fit
                if x + 1.2 * U + width(ln) > LINE_END:
                    break
                x = text(c, x + 1.2 * U, y, ln, TRACE)
            y -= ROW
c.showPage(); page += 1

# --- Units used in middle and high school ----------------------------------

UNITS = [
    ("SI base units  国际单位制基本单位", [
        ("m", "meter", "长度 · 米"), ("kg", "kilogram", "质量 · 千克"),
        ("s", "second", "时间 · 秒"), ("A", "ampere", "电流 · 安培"),
        ("K", "kelvin", "热力学温度 · 开尔文"), ("mol", "mole", "物质的量 · 摩尔"),
        ("cd", "candela", "发光强度 · 坎德拉")]),
    ("Length, area and volume  长度、面积、体积", [
        ("km", "kilometer", "千米"), ("dm", "decimeter", "分米"),
        ("cm", "centimeter", "厘米"), ("mm", "millimeter", "毫米"),
        ("μm", "micrometer", "微米"), ("nm", "nanometer", "纳米"),
        ("ly", "light-year", "光年"), ("m²", "square meter", "面积 · 平方米"),
        ("cm²", "square centimeter", "平方厘米"), ("m³", "cubic meter", "体积 · 立方米"),
        ("dm³", "cubic decimeter", "立方分米"), ("cm³", "cubic centimeter", "立方厘米"),
        ("L", "liter", "升"), ("mL", "milliliter", "毫升")]),
    ("Mass and time  质量、时间", [
        ("t", "tonne", "吨"), ("g", "gram", "克"), ("mg", "milligram", "毫克"),
        ("h", "hour", "小时"), ("min", "minute", "分钟"), ("ms", "millisecond", "毫秒")]),
    ("Mechanics  力学", [
        ("m/s", "meter per second", "速度 · 米每秒"),
        ("km/h", "kilometer per hour", "速度 · 千米每时"),
        ("m/s²", "meter per second squared", "加速度 · 米每二次方秒"),
        ("kg/m³", "kilogram per cubic meter", "密度 · 千克每立方米"),
        ("g/cm³", "gram per cubic centimeter", "密度 · 克每立方厘米"),
        ("N", "newton", "力 · 牛顿"), ("N/kg", "newton per kilogram", "g 的单位 · 牛每千克"),
        ("N/m", "newton per meter", "劲度系数 · 牛每米"),
        ("Pa", "pascal", "压强 · 帕斯卡"), ("kPa", "kilopascal", "千帕"),
        ("MPa", "megapascal", "兆帕"), ("J", "joule", "功、能量 · 焦耳"),
        ("kJ", "kilojoule", "千焦"), ("W", "watt", "功率 · 瓦特"), ("kW", "kilowatt", "千瓦"),
        ("N·m", "newton meter", "力矩 · 牛米"), ("N·s", "newton second", "冲量 · 牛秒"),
        ("kg·m/s", "kilogram meter per second", "动量 · 千克米每秒"),
        ("rad", "radian", "角度 · 弧度"), ("rad/s", "radian per second", "角速度 · 弧度每秒"),
        ("Hz", "hertz", "频率 · 赫兹")]),
    ("Heat  热学", [
        ("°C", "degree Celsius", "温度 · 摄氏度"),
        ("J/(kg·°C)", "joule per kilogram degree Celsius", "比热容"),
        ("J/kg", "joule per kilogram", "热值 · 焦每千克"),
        ("J/m³", "joule per cubic meter", "热值（气体）· 焦每立方米")]),
    ("Electricity and magnetism  电磁学", [
        ("V", "volt", "电压 · 伏特"), ("kV", "kilovolt", "千伏"), ("mV", "millivolt", "毫伏"),
        ("mA", "milliampere", "毫安"), ("μA", "microampere", "微安"),
        ("Ω", "ohm", "电阻 · 欧姆"), ("kΩ", "kilohm", "千欧"), ("MΩ", "megohm", "兆欧"),
        ("C", "coulomb", "电荷量 · 库仑"), ("F", "farad", "电容 · 法拉"),
        ("μF", "microfarad", "微法"), ("N/C", "newton per coulomb", "电场强度 · 牛每库"),
        ("V/m", "volt per meter", "电场强度 · 伏每米"), ("T", "tesla", "磁感应强度 · 特斯拉"),
        ("Wb", "weber", "磁通量 · 韦伯"), ("H", "henry", "自感系数 · 亨利"),
        ("kW·h", "kilowatt hour", "电能 · 千瓦时"), ("eV", "electronvolt", "能量 · 电子伏特")]),
    ("Sound  声学", [("dB", "decibel", "声强级 · 分贝")]),
    ("Chemistry  化学", [
        ("mol/L", "mole per liter", "物质的量浓度 · 摩尔每升"),
        ("g/mol", "gram per mole", "摩尔质量 · 克每摩尔"),
        ("L/mol", "liter per mole", "气体摩尔体积 · 升每摩尔"),
        ("mol/(L·s)", "mole per liter second", "化学反应速率")]),
]


def unit_rows(sym, name, name_color=GREEN, sym_color=pair_color, trace_sym=True):
    """Rows for one entry: (model parts, gray trace candidates)."""
    room = W - M - 4 - 1.2 * U
    if not sym:                             # name only; gray copy below if none fits beside
        if M + 6 + 2 * width(name) + 1.2 * U <= room + 1.2 * U:
            return [([(name, name_color)], [name])]
        return [([(name, name_color)], []), ([(name, TRACE)], [])]
    one = M + 6 + width(sym) + 1.4 * U + width(name)
    if not trace_sym:                       # e.g. a number: trace only the name
        if one + 1.2 * U + width(name) <= room:
            return [([(sym, sym_color), (name, name_color)], [name])]
        return [([(sym, sym_color), (name, name_color)], []),   # gray copy on its own row
                ([(sym, TRACE), (name, TRACE)], [])]
    if one + 1.2 * U + width(sym) <= room:
        return [([(sym, sym_color), (name, name_color)], [sym + "  " + name, sym])]
    return [([(sym, sym_color)], [sym]), ([(name, name_color)], [name])]


def unit_row(c, y, model, traces):
    guide(c, y)
    x = M + 6
    for k, (seq, col) in enumerate(model):
        x = text(c, x + (1.4 * U if k else 0), y, seq, col)
    room = W - M - 4 - 1.2 * U
    t = next((t for t in traces if x + width(t) <= room), None)
    for _ in range(2):
        if t is None or x + width(t) > room:
            break
        x = text(c, x + 1.2 * U, y, t, TRACE)


def section_heading(c, y, label):
    """label is "English  中文"; English in Helvetica, Chinese in SimHei."""
    en, zh = label.split("  ", 1)
    c.setFillColor(HexColor("#F07F2D")); c.setFont("Helvetica-Bold", 12)
    c.drawString(M, y + 2 * U + 6, en)
    x = M + pdfmetrics.stringWidth(en, "Helvetica-Bold", 12) + 8
    c.setFont("SimHei", 11.5)
    c.drawString(x, y + 2 * U + 6, zh)


def symbol_section(c, page, title, sub, groups, name_color=GREEN, sym_color=pair_color,
                   trace_sym=True, tail=None):
    """Flow (symbol, name, 中文) entries over pages under headed groups; returns next page.

    tail: optional prompt; the rest of the last page becomes blank lines under it."""
    y = None
    for heading, entries in groups:
        for k, (sym, name, zh) in enumerate(entries):
            rows = unit_rows(sym, name, name_color, sym_color, trace_sym)
            need = len(rows) * ROW + (30 if k == 0 else 0)
            if y is None or y - need + ROW < 50:
                if y is not None:
                    c.showPage(); page += 1
                header(c, title, sub, page)
                y = top - 4
                if k > 0:
                    h_en, h_zh = heading.split("  ", 1)
                    section_heading(c, y, h_en + " (continued)  " + h_zh + "（续）")
                    y -= 14
            if k == 0:
                if y < top - 4:             # group starts mid-page: extra space above
                    y -= 12
                section_heading(c, y, heading)
                y -= 14
            c.setFillColor(HexColor("#888888")); c.setFont("SimHei", 7.5)
            c.drawRightString(W - M, y + 2 * U + 3, zh)
            for model, traces in rows:
                unit_row(c, y, model, traces)
                y -= ROW
    if tail:
        y -= 14
        c.setFillColor(HexColor("#555555")); c.setFont("Helvetica", 10)
        c.drawString(M, y + 2 * U + 8, tail)
        while y > 50:
            guide(c, y); y -= ROW
    c.showPage()
    return page + 1


page = symbol_section(c, page, "Units of Measurement",
                      "Middle and high school units. Trace the gray symbols and names.", UNITS)

# --- The 50 US states -------------------------------------------------------
STATES = """AL Alabama 亚拉巴马州|AK Alaska 阿拉斯加州|AZ Arizona 亚利桑那州|AR Arkansas 阿肯色州|
CA California 加利福尼亚州|CO Colorado 科罗拉多州|CT Connecticut 康涅狄格州|DE Delaware 特拉华州|
FL Florida 佛罗里达州|GA Georgia 佐治亚州|HI Hawaii 夏威夷州|ID Idaho 爱达荷州|IL Illinois 伊利诺伊州|
IN Indiana 印第安纳州|IA Iowa 艾奥瓦州|KS Kansas 堪萨斯州|KY Kentucky 肯塔基州|LA Louisiana 路易斯安那州|
ME Maine 缅因州|MD Maryland 马里兰州|MA Massachusetts 马萨诸塞州|MI Michigan 密歇根州|
MN Minnesota 明尼苏达州|MS Mississippi 密西西比州|MO Missouri 密苏里州|MT Montana 蒙大拿州|
NE Nebraska 内布拉斯加州|NV Nevada 内华达州|NH New Hampshire 新罕布什尔州|NJ New Jersey 新泽西州|
NM New Mexico 新墨西哥州|NY New York 纽约州|NC North Carolina 北卡罗来纳州|ND North Dakota 北达科他州|
OH Ohio 俄亥俄州|OK Oklahoma 俄克拉何马州|OR Oregon 俄勒冈州|PA Pennsylvania 宾夕法尼亚州|
RI Rhode Island 罗得岛州|SC South Carolina 南卡罗来纳州|SD South Dakota 南达科他州|TN Tennessee 田纳西州|
TX Texas 得克萨斯州|UT Utah 犹他州|VT Vermont 佛蒙特州|VA Virginia 弗吉尼亚州|WA Washington 华盛顿州|
WV West Virginia 西弗吉尼亚州|WI Wisconsin 威斯康星州|WY Wyoming 怀俄明州"""
STATES = [(e.split()[0], " ".join(e.split()[1:-1]), e.split()[-1])
          for e in STATES.replace("\n", "").split("|")]
assert len(STATES) == 50
page = symbol_section(c, page, "The 50 States of the USA",
                      "Postal abbreviation and state name. Trace the gray letters.",
                      [("United States, A to Z  美国 50 个州", STATES)], name_color=pair_color)

# --- Presidents of the United States ---------------------------------------
PRESIDENTS = """George Washington|乔治·华盛顿|1789–1797
John Adams|约翰·亚当斯|1797–1801
Thomas Jefferson|托马斯·杰斐逊|1801–1809
James Madison|詹姆斯·麦迪逊|1809–1817
James Monroe|詹姆斯·门罗|1817–1825
John Quincy Adams|约翰·昆西·亚当斯|1825–1829
Andrew Jackson|安德鲁·杰克逊|1829–1837
Martin Van Buren|马丁·范布伦|1837–1841
William Henry Harrison|威廉·亨利·哈里森|1841
John Tyler|约翰·泰勒|1841–1845
James K. Polk|詹姆斯·波尔克|1845–1849
Zachary Taylor|扎卡里·泰勒|1849–1850
Millard Fillmore|米勒德·菲尔莫尔|1850–1853
Franklin Pierce|富兰克林·皮尔斯|1853–1857
James Buchanan|詹姆斯·布坎南|1857–1861
Abraham Lincoln|亚伯拉罕·林肯|1861–1865
Andrew Johnson|安德鲁·约翰逊|1865–1869
Ulysses S. Grant|尤利西斯·格兰特|1869–1877
Rutherford B. Hayes|拉瑟福德·海斯|1877–1881
James A. Garfield|詹姆斯·加菲尔德|1881
Chester A. Arthur|切斯特·阿瑟|1881–1885
Grover Cleveland|格罗弗·克利夫兰|1885–1889
Benjamin Harrison|本杰明·哈里森|1889–1893
Grover Cleveland|格罗弗·克利夫兰|1893–1897
William McKinley|威廉·麦金莱|1897–1901
Theodore Roosevelt|西奥多·罗斯福|1901–1909
William Howard Taft|威廉·霍华德·塔夫脱|1909–1913
Woodrow Wilson|伍德罗·威尔逊|1913–1921
Warren G. Harding|沃伦·哈定|1921–1923
Calvin Coolidge|卡尔文·柯立芝|1923–1929
Herbert Hoover|赫伯特·胡佛|1929–1933
Franklin D. Roosevelt|富兰克林·罗斯福|1933–1945
Harry S. Truman|哈里·杜鲁门|1945–1953
Dwight D. Eisenhower|德怀特·艾森豪威尔|1953–1961
John F. Kennedy|约翰·肯尼迪|1961–1963
Lyndon B. Johnson|林登·约翰逊|1963–1969
Richard Nixon|理查德·尼克松|1969–1974
Gerald Ford|杰拉尔德·福特|1974–1977
Jimmy Carter|吉米·卡特|1977–1981
Ronald Reagan|罗纳德·里根|1981–1989
George H. W. Bush|乔治·赫伯特·沃克·布什|1989–1993
Bill Clinton|比尔·克林顿|1993–2001
George W. Bush|乔治·沃克·布什|2001–2009
Barack Obama|巴拉克·奥巴马|2009–2017
Donald Trump|唐纳德·特朗普|2017–2021
Joe Biden|乔·拜登|2021–2025
Donald Trump|唐纳德·特朗普|2025–"""
PRESIDENTS = [(str(n), name, zh + "  " + years) for n, (name, zh, years) in
              enumerate((ln.split("|") for ln in PRESIDENTS.splitlines()), 1)]
assert len(PRESIDENTS) == 47
page = symbol_section(c, page, "Presidents of the USA",
                      "Number, name and years in office. Trace the gray names.",
                      [("Presidents of the United States  美国历任总统", PRESIDENTS)],
                      name_color=pair_color, sym_color=ORANGE, trace_sym=False)

# --- Geologic time scale ------------------------------------------------------
# Ages in millions of years ago (ICS International Chronostratigraphic Chart v2023/06).
GEO_EPOCHS = [   # (name, 中文, start Ma, end Ma, ICS colour) youngest first
    ("Holocene", "全新世", "0.0117", "0", "#FEF2E0"),
    ("Pleistocene", "更新世", "2.58", "0.0117", "#FFF2AE"),
    ("Pliocene", "上新世", "5.333", "2.58", "#FFFF99"),
    ("Miocene", "中新世", "23.03", "5.333", "#FFFF00"),
    ("Oligocene", "渐新世", "33.9", "23.03", "#FEC07A"),
    ("Eocene", "始新世", "56.0", "33.9", "#FDB46C"),
    ("Paleocene", "古新世", "66.0", "56.0", "#FDA75F"),
]
GEO_PERIODS = [  # (name, 中文, start, end, colour, first row, last row)
    ("Quaternary", "第四纪", "2.58", "0", "#F9F97F", 0, 1),
    ("Neogene", "新近纪", "23.03", "2.58", "#FFE619", 2, 3),
    ("Paleogene", "古近纪", "66.0", "23.03", "#FD9A52", 4, 6),
    ("Cretaceous", "白垩纪", "145.0", "66.0", "#7FC64E", 7, 7),
    ("Jurassic", "侏罗纪", "201.4", "145.0", "#34B2C9", 8, 8),
    ("Triassic", "三叠纪", "251.9", "201.4", "#812B92", 9, 9),
    ("Permian", "二叠纪", "298.9", "251.9", "#F04028", 10, 10),
    ("Carboniferous", "石炭纪", "358.9", "298.9", "#67A599", 11, 11),
    ("Devonian", "泥盆纪", "419.2", "358.9", "#CB8C37", 12, 12),
    ("Silurian", "志留纪", "443.8", "419.2", "#B3E1B6", 13, 13),
    ("Ordovician", "奥陶纪", "485.4", "443.8", "#009270", 14, 14),
    ("Cambrian", "寒武纪", "538.8", "485.4", "#7FA056", 15, 15),
]
GEO_ERAS = [
    ("Cenozoic", "新生代", "66.0", "0", "#F2F91D", 0, 6),
    ("Mesozoic", "中生代", "251.9", "66.0", "#67C5CA", 7, 9),
    ("Paleozoic", "古生代", "538.8", "251.9", "#99C08D", 10, 15),
]
GEO_EONS = [
    ("Phanerozoic", "显生宙", "538.8", "0", "#9AD9DD", 0, 15),
    ("Proterozoic", "元古宙", "2500", "538.8", "#F73563", 16, 16),
    ("Archean", "太古宙", "4000", "2500", "#F0047F", 17, 17),
    ("Hadean", "冥古宙", "4600", "4000", "#AE027E", 18, 18),
]


def tint(hex_color, k=0.5):
    """Mix an ICS colour with white so handwriting on it stays readable."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return HexColor("#%02X%02X%02X" % tuple(int(v + (255 - v) * k) for v in (r, g, b)))


def geo_chart(c, page, trace):
    header(c, "Geologic Time Scale",
           "Trace the gray names." if trace else "Ages in millions of years ago (Ma).", page)
    cols = [M, M + 100, M + 195, M + 315, M + 425, W - M]   # eon|era|period|epoch|age
    head_y, rh = H - 100, 35
    ink = (150, 150, 150) if trace else BLACK
    c.setFillColor(HexColor("#555555"))
    for i, (en, zh) in enumerate([("Eon", "宙"), ("Era", "代"), ("Period", "纪"),
                                  ("Epoch", "世"), ("Start (Ma)", "起始/百万年前")]):
        c.setFont("Helvetica-Bold", 9); c.drawString(cols[i] + 4, head_y + 5, en)
        c.setFont("SimHei", 8)
        c.drawString(cols[i] + 8 + pdfmetrics.stringWidth(en, "Helvetica-Bold", 9), head_y + 5, zh)

    def box(x0, x1, r0, r1, fill, name, zh):
        y0, y1 = head_y - (r1 + 1) * rh, head_y - r0 * rh
        c.setFillColor(tint(fill)); c.setStrokeColor(HexColor("#777777")); c.setLineWidth(0.6)
        c.rect(x0, y0, x1 - x0, y1 - y0, fill=1, stroke=1)
        u = min(5.5, (x1 - x0 - 10) / width(name, u=1))
        base = (y0 + y1) / 2 - 0.2 * u
        text(c, x0 + 5, base, name, ink, u=u)
        c.setFillColor(HexColor("#555555")); c.setFont("SimHei", 7)
        c.drawString(x0 + 5, base - u - 8, zh)

    for name, zh, _, _, col, r0, r1 in GEO_EONS:
        box(cols[0], cols[1] if r0 == 0 else cols[4], r0, r1, col, name, zh)
    for name, zh, _, _, col, r0, r1 in GEO_ERAS:
        box(cols[1], cols[2], r0, r1, col, name, zh)
    for name, zh, _, _, col, r0, r1 in GEO_PERIODS:
        box(cols[2], cols[3] if r0 < 7 else cols[4], r0, r1, col, name, zh)
    for r, (name, zh, _, _, col) in enumerate(GEO_EPOCHS):
        box(cols[3], cols[4], r, r, col, name, zh)
    # start age of every row, at its lower boundary
    starts = [e[2] for e in GEO_EPOCHS] + [p[2] for p in GEO_PERIODS[3:]] + \
             [e[2] for e in GEO_EONS[1:]]
    c.setStrokeColor(HexColor("#777777")); c.setLineWidth(0.6)
    for r, age in enumerate(starts):
        yb = head_y - (r + 1) * rh
        c.line(cols[4], yb, cols[5], yb)
        text(c, cols[5] - 6 - width(age, u=4.5), yb + 5, age, ORANGE, u=4.5)
    c.line(cols[4], head_y, cols[5], head_y); c.line(cols[5], head_y, cols[5], head_y - 19 * rh)
    c.showPage()


geo_chart(c, page, trace=False); page += 1
geo_chart(c, page, trace=True); page += 1


def geo_entries(rows):
    return [("", name, "%s · %s–%s Ma" % (zh, start, "今" if end == "0" else end))
            for name, zh, start, end, *_ in rows]


page = symbol_section(c, page, "Geologic Time Scale",
                      "Eons, eras, periods and epochs. Trace the gray names.",
                      [("Eons  宙", geo_entries(GEO_EONS[::-1])),
                       ("Eras  代", geo_entries(GEO_ERAS[::-1])),
                       ("Periods  纪", geo_entries(GEO_PERIODS[::-1])),
                       ("Epochs of the Cenozoic  新生代的世", geo_entries(GEO_EPOCHS[::-1]))],
                      name_color=pair_color,
                      tail="Now write the twelve periods in order, oldest first:")

# --- Math vocabulary, primary to high school ----------------------------------
MATH_WORDS = [
    ("Primary: numbers and operations  小学：数与运算", """
number|数|digit|数字（位）|count|数数|add|加|addition|加法|subtract|减|subtraction|减法|
multiply|乘|multiplication|乘法|divide|除|division|除法|plus|加号；加|minus|减号；减|
times|乘以|equals|等于|sum|和|difference|差|product|积|quotient|商|remainder|余数|
odd number|奇数|even number|偶数|place value|数位；位值|ones|个位|tens|十位|
hundreds|百位|thousands|千位|round|四舍五入|estimate|估算|compare|比较|
greater than|大于|less than|小于|number line|数轴|fraction|分数|numerator|分子|
denominator|分母|decimal|小数|decimal point|小数点|percent|百分数|ratio|比|
proportion|比例|factor|因数|multiple|倍数|prime number|质数|composite number|合数|
greatest common factor|最大公因数|least common multiple|最小公倍数|
negative number|负数|positive number|正数"""),
    ("Primary: shapes and geometry  小学：图形与几何", """
point|点|line|直线|line segment|线段|ray|射线|angle|角|right angle|直角|
acute angle|锐角|obtuse angle|钝角|straight angle|平角|parallel|平行|
perpendicular|垂直|triangle|三角形|square|正方形；平方|rectangle|长方形|circle|圆|
oval|椭圆形|pentagon|五边形|hexagon|六边形|polygon|多边形|quadrilateral|四边形|
parallelogram|平行四边形|trapezoid|梯形|rhombus|菱形|cube|正方体；立方|
cuboid|长方体|cylinder|圆柱|cone|圆锥|sphere|球|pyramid|棱锥|prism|棱柱|
edge|棱|face|面|vertex|顶点|perimeter|周长|area|面积|volume|体积|
radius|半径|diameter|直径|circumference|圆周长|pi|圆周率|symmetry|对称|
axis of symmetry|对称轴"""),
    ("Primary: measurement and data  小学：测量与统计", """
length|长度|width|宽度|height|高度|weight|重量|capacity|容积|unit|单位|
measure|测量|ruler|直尺|protractor|量角器|compass|圆规|clock|钟|hour hand|时针|
minute hand|分针|money|钱|table|统计表|tally|计数符号|bar graph|条形统计图|
line graph|折线统计图|pie chart|扇形统计图|average|平均数|probability|可能性；概率"""),
    ("Middle school: numbers and algebra  初中：数与代数", """
integer|整数|rational number|有理数|irrational number|无理数|real number|实数|
absolute value|绝对值|opposite number|相反数|reciprocal|倒数|square root|平方根|
cube root|立方根|exponent|指数|power|乘方；幂|base|底数|
scientific notation|科学记数法|approximate|近似|variable|变量|constant|常量|
coefficient|系数|term|项|like terms|同类项|expression|式子|
algebraic expression|代数式|monomial|单项式|polynomial|多项式|binomial|二项式|
factorization|因式分解|formula|公式|equation|方程|linear equation|一次方程|
quadratic equation|二次方程|system of equations|方程组|solution|解|root|根|
inequality|不等式|discriminant|判别式|fractional equation|分式方程"""),
    ("Middle school: functions and coordinates  初中：函数与坐标", """
function|函数|independent variable|自变量|dependent variable|因变量|
linear function|一次函数|direct proportion|正比例|inverse proportion|反比例|
quadratic function|二次函数|slope|斜率|intercept|截距|coordinate|坐标|
coordinate plane|坐标平面|origin|原点|x-axis|x 轴|y-axis|y 轴|quadrant|象限|
ordered pair|有序数对|graph|图像|vertex of a parabola|抛物线顶点"""),
    ("Middle school: geometry  初中：几何", """
congruent|全等|similar|相似|isosceles triangle|等腰三角形|
equilateral triangle|等边三角形|right triangle|直角三角形|hypotenuse|斜边|
Pythagorean theorem|勾股定理|median|中线；中位数|altitude|高|
angle bisector|角平分线|perpendicular bisector|垂直平分线|interior angle|内角|
exterior angle|外角|complementary angles|余角|supplementary angles|补角|
vertical angles|对顶角|corresponding angles|同位角|alternate angles|内错角|
chord|弦|arc|弧|tangent|切线；正切|central angle|圆心角|inscribed angle|圆周角|
sector|扇形|translation|平移|rotation|旋转|reflection|轴对称；反射|
theorem|定理|proof|证明|definition|定义|axiom|公理|converse|逆命题|
sine|正弦|cosine|余弦"""),
    ("Middle school: statistics  初中：统计", """
data|数据|survey|调查|sample|样本|population|总体|frequency|频数|
histogram|频数分布直方图|mean|平均数|mode|众数|range|极差；值域|variance|方差|
standard deviation|标准差"""),
    ("High school: sets and logic  高中：集合与逻辑", """
set|集合|element|元素|subset|子集|proper subset|真子集|empty set|空集|
union|并集|intersection|交集|complement|补集|proposition|命题|
sufficient condition|充分条件|necessary condition|必要条件|
universal quantifier|全称量词|existential quantifier|存在量词"""),
    ("High school: functions  高中：函数", """
domain|定义域|inverse function|反函数|monotonic|单调的|increasing|增函数的|
decreasing|减函数的|odd function|奇函数|even function|偶函数|
periodic function|周期函数|maximum|最大值|minimum|最小值|
exponential function|指数函数|logarithm|对数|logarithmic function|对数函数|
power function|幂函数|zero of a function|函数零点"""),
    ("High school: trigonometry and vectors  高中：三角与向量", """
trigonometric function|三角函数|radian|弧度|unit circle|单位圆|period|周期|
amplitude|振幅|phase|相位|law of sines|正弦定理|law of cosines|余弦定理|
vector|向量|magnitude|模|dot product|数量积|unit vector|单位向量|
collinear|共线"""),
    ("High school: sequences and calculus  高中：数列与微积分", """
sequence|数列|arithmetic sequence|等差数列|geometric sequence|等比数列|
common difference|公差|common ratio|公比|general term|通项|series|级数|
mathematical induction|数学归纳法|limit|极限|derivative|导数|
tangent line|切线|extremum|极值|integral|积分"""),
    ("High school: analytic and solid geometry  高中：解析几何与立体几何", """
equation of a line|直线方程|distance formula|距离公式|conic section|圆锥曲线|
ellipse|椭圆|hyperbola|双曲线|parabola|抛物线|focus|焦点|directrix|准线|
eccentricity|离心率|asymptote|渐近线|major axis|长轴|minor axis|短轴|
plane|平面|space|空间|skew lines|异面直线|dihedral angle|二面角|
normal vector|法向量|projection|投影|surface area|表面积|frustum|台体"""),
    ("High school: counting, probability and statistics  高中：计数、概率与统计", """
permutation|排列|combination|组合|binomial theorem|二项式定理|
factorial|阶乘|event|事件|independent events|相互独立事件|
mutually exclusive|互斥|conditional probability|条件概率|
random variable|随机变量|distribution|分布|expected value|数学期望|
normal distribution|正态分布|binomial distribution|二项分布|
correlation|相关|regression|回归|percentile|百分位数"""),
    ("High school: complex numbers  高中：复数", """
complex number|复数|imaginary unit|虚数单位|real part|实部|
imaginary part|虚部|conjugate|共轭"""),
]


def word_entries(raw):
    parts = [p.strip() for p in raw.replace("\n", "").split("|") if p.strip()]
    assert len(parts) % 2 == 0, parts
    return [("", parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]


MATH_WORDS = [(heading, word_entries(raw)) for heading, raw in MATH_WORDS]
page = symbol_section(c, page, "Math Vocabulary",
                      "From primary to high school. Trace the gray words.", MATH_WORDS,
                      name_color=pair_color)

# --- Physics vocabulary, primary to high school -------------------------------
PHYSICS_WORDS = [
    ("Primary science: matter and energy  小学科学：物质与能量", """
matter|物质|solid|固体|liquid|液体|gas|气体|melt|融化|freeze|结冰|
evaporate|蒸发|condense|凝结|boil|沸腾|heat|热|temperature|温度|
thermometer|温度计|light|光|shadow|影子|mirror|镜子|sound|声音|vibration|振动|
echo|回声|magnet|磁铁|attract|吸引|repel|排斥|north pole|北极|south pole|南极|
electricity|电|circuit|电路|battery|电池|bulb|灯泡|switch|开关|wire|导线|
conductor|导体|insulator|绝缘体|energy|能量|solar energy|太阳能|wind energy|风能"""),
    ("Primary science: forces and machines  小学科学：力与机械", """
force|力|push|推|pull|拉|gravity|重力；引力|friction|摩擦力|motion|运动|
speed|速度；快慢|simple machine|简单机械|lever|杠杆|pulley|滑轮|
wheel and axle|轮轴|inclined plane|斜面|spring|弹簧"""),
    ("Middle school: measurement and motion  初中：测量与运动", """
physics|物理|measurement|测量|mass|质量|error|误差|reference object|参照物|
distance|路程|uniform motion|匀速直线运动|average speed|平均速度|
relative motion|相对运动"""),
    ("Middle school: sound  初中：声现象", """
sound wave|声波|medium|介质|pitch|音调|loudness|响度|timbre|音色|
ultrasound|超声波|infrasound|次声波|noise|噪声"""),
    ("Middle school: light  初中：光现象", """
light ray|光线|light source|光源|rectilinear propagation|光的直线传播|
reflection|反射|law of reflection|光的反射定律|plane mirror|平面镜|
refraction|折射|convex lens|凸透镜|concave lens|凹透镜|focal point|焦点|
focal length|焦距|real image|实像|virtual image|虚像|dispersion|色散|
spectrum|光谱|nearsightedness|近视|farsightedness|远视"""),
    ("Middle school: heat  初中：热学", """
melting|熔化|solidification|凝固|vaporization|汽化|liquefaction|液化|
sublimation|升华|deposition|凝华|melting point|熔点|boiling point|沸点|
internal energy|内能|heat transfer|热传递|conduction|传导|convection|对流|
radiation|辐射|specific heat capacity|比热容|heat value|热值|
heat engine|热机|efficiency|效率|thermal expansion|热膨胀"""),
    ("Middle school: forces and pressure  初中：力与压强", """
weight|重力|elastic force|弹力|resultant force|合力|balanced forces|平衡力|
inertia|惯性|Newton's first law|牛顿第一定律|density|密度|pressure|压强|
liquid pressure|液体压强|atmospheric pressure|大气压|
communicating vessels|连通器|buoyancy|浮力|Archimedes' principle|阿基米德原理|
fulcrum|支点|effort arm|动力臂|load arm|阻力臂|work|功|power|功率|
mechanical energy|机械能|kinetic energy|动能|potential energy|势能|
gravitational potential energy|重力势能|elastic potential energy|弹性势能"""),
    ("Middle school: electricity and magnetism  初中：电与磁", """
electric charge|电荷|static electricity|静电|current|电流|voltage|电压|
resistance|电阻|resistor|电阻器|rheostat|滑动变阻器|ammeter|电流表|
voltmeter|电压表|series circuit|串联电路|parallel circuit|并联电路|
short circuit|短路|open circuit|断路|Ohm's law|欧姆定律|
electric power|电功率|electrical energy|电能|Joule's law|焦耳定律|
fuse|保险丝|magnetic field|磁场|magnetic field line|磁感线|
electromagnet|电磁铁|electric motor|电动机|generator|发电机|
electromagnetic induction|电磁感应|electromagnetic wave|电磁波"""),
    ("Middle school: energy sources  初中：能源", """
renewable energy|可再生能源|nonrenewable energy|不可再生能源|
fossil fuel|化石燃料|nuclear energy|核能|nuclear fission|核裂变|
nuclear fusion|核聚变|conservation of energy|能量守恒"""),
    ("High school: kinematics  高中：运动学", """
particle|质点|displacement|位移|velocity|速度|acceleration|加速度|
scalar|标量|vector|矢量|instantaneous velocity|瞬时速度|
uniformly accelerated motion|匀变速直线运动|free fall|自由落体运动|
projectile motion|抛体运动|circular motion|圆周运动|angular velocity|角速度|
centripetal acceleration|向心加速度|period|周期"""),
    ("High school: dynamics and gravitation  高中：动力学与万有引力", """
Newton's second law|牛顿第二定律|Newton's third law|牛顿第三定律|
normal force|支持力|tension|拉力；张力|static friction|静摩擦力|
kinetic friction|滑动摩擦力|coefficient of friction|动摩擦因数|
equilibrium|平衡|centripetal force|向心力|weightlessness|失重|
overweight|超重|universal gravitation|万有引力|
gravitational constant|引力常量|satellite|卫星|orbit|轨道|
first cosmic velocity|第一宇宙速度"""),
    ("High school: energy and momentum  高中：能量与动量", """
work-energy theorem|动能定理|conservation of mechanical energy|机械能守恒|
momentum|动量|impulse|冲量|conservation of momentum|动量守恒|
collision|碰撞|elastic collision|弹性碰撞|inelastic collision|非弹性碰撞|recoil|反冲"""),
    ("High school: oscillations, waves and optics  高中：振动、波与光学", """
oscillation|振动|simple harmonic motion|简谐运动|simple pendulum|单摆|
amplitude|振幅|frequency|频率|resonance|共振|mechanical wave|机械波|
transverse wave|横波|longitudinal wave|纵波|wavelength|波长|
interference|干涉|diffraction|衍射|Doppler effect|多普勒效应|
refractive index|折射率|total internal reflection|全反射|polarization|偏振|laser|激光"""),
    ("High school: electricity and magnetism  高中：电磁学", """
Coulomb's law|库仑定律|point charge|点电荷|electric field|电场|
electric field strength|电场强度|electric field line|电场线|
electric potential|电势|potential difference|电势差|
equipotential surface|等势面|capacitor|电容器|capacitance|电容|
electromotive force|电动势|internal resistance|内阻|closed circuit|闭合电路|
magnetic flux|磁通量|magnetic induction|磁感应强度|Ampere force|安培力|
Lorentz force|洛伦兹力|Faraday's law|法拉第电磁感应定律|Lenz's law|楞次定律|
self-induction|自感|alternating current|交变电流|direct current|直流电|
transformer|变压器|effective value|有效值"""),
    ("High school: thermodynamics  高中：热学", """
molecule|分子|Brownian motion|布朗运动|diffusion|扩散|ideal gas|理想气体|
ideal gas law|理想气体状态方程|first law of thermodynamics|热力学第一定律|
second law of thermodynamics|热力学第二定律|entropy|熵|absolute zero|绝对零度"""),
    ("High school: modern physics  高中：近代物理", """
photon|光子|photoelectric effect|光电效应|work function|逸出功|quantum|量子|
wave-particle duality|波粒二象性|energy level|能级|atom|原子|nucleus|原子核|
electron|电子|proton|质子|neutron|中子|isotope|同位素|radioactivity|放射性|
half-life|半衰期|alpha decay|α 衰变|beta decay|β 衰变|binding energy|结合能|
mass-energy equation|质能方程|relativity|相对论"""),
]
PHYSICS_WORDS = [(heading, word_entries(raw)) for heading, raw in PHYSICS_WORDS]
page = symbol_section(c, page, "Physics Vocabulary",
                      "From primary to high school. Trace the gray words.", PHYSICS_WORDS,
                      name_color=pair_color)

# --- Chemistry vocabulary, primary to high school -----------------------------
CHEMISTRY_WORDS = [
    ("Primary science: materials and changes  小学科学：物质的变化", """
material|材料|property|性质|mixture|混合物|dissolve|溶解|solution|溶液|
physical change|物理变化|chemical change|化学变化|rust|生锈；铁锈|burn|燃烧|
air|空气|water vapor|水蒸气|filter|过滤|crystal|晶体|salt|盐|sugar|糖|
vinegar|醋|baking soda|小苏打|acid rain|酸雨|pollution|污染|recycle|回收利用"""),
    ("Middle school: matter and reactions  初中：物质与化学反应", """
chemistry|化学|substance|物质|pure substance|纯净物|element|元素|compound|化合物|
oxide|氧化物|physical property|物理性质|chemical property|化学性质|
chemical reaction|化学反应|combination reaction|化合反应|
decomposition reaction|分解反应|displacement reaction|置换反应|
double displacement reaction|复分解反应|combustion|燃烧|oxidation|氧化|
catalyst|催化剂|law of conservation of mass|质量守恒定律|
chemical equation|化学方程式|reactant|反应物|product|生成物|balance|配平"""),
    ("Middle school: atoms, ions and formulas  初中：原子、离子与化学式", """
ion|离子|cation|阳离子|anion|阴离子|relative atomic mass|相对原子质量|
relative molecular mass|相对分子质量|chemical formula|化学式|
element symbol|元素符号|valence|化合价|periodic table|元素周期表|
atomic number|原子序数|electron shell|电子层|outermost electrons|最外层电子"""),
    ("Middle school: air, water and solutions  初中：空气、水与溶液", """
noble gas|稀有气体|greenhouse effect|温室效应|hard water|硬水|soft water|软水|
distillation|蒸馏|electrolysis|电解|solute|溶质|solvent|溶剂|
saturated solution|饱和溶液|unsaturated solution|不饱和溶液|
solubility|溶解度|mass fraction|质量分数|crystallization|结晶|
emulsion|乳浊液|suspension|悬浊液"""),
    ("Middle school: acids, bases and salts  初中：酸、碱、盐", """
acid|酸|base|碱|alkali|碱（可溶性）|indicator|指示剂|litmus|石蕊|
phenolphthalein|酚酞|pH|酸碱度|acidic|酸性|alkaline|碱性|neutral|中性|
neutralization|中和反应|precipitate|沉淀|fertilizer|化肥"""),
    ("Middle school: metals  初中：金属", """
metal|金属|nonmetal|非金属|alloy|合金|ore|矿石|smelting|冶炼|corrosion|腐蚀|
reactivity series|金属活动性顺序|rust prevention|防锈"""),
    ("Middle school: fuels and everyday chemistry  初中：燃料与生活中的化学", """
fuel|燃料|natural gas|天然气|petroleum|石油|coal|煤|ignition point|着火点|
fire extinguishing|灭火|organic compound|有机化合物|
inorganic compound|无机化合物|carbohydrate|糖类|protein|蛋白质|fat|油脂|
vitamin|维生素|plastic|塑料|synthetic fiber|合成纤维|white pollution|白色污染"""),
    ("Middle school: lab equipment and skills  初中：实验仪器与操作", """
test tube|试管|beaker|烧杯|flask|烧瓶|conical flask|锥形瓶|alcohol lamp|酒精灯|
graduated cylinder|量筒|funnel|漏斗|dropper|胶头滴管|glass rod|玻璃棒|
pan balance|托盘天平|evaporating dish|蒸发皿|iron stand|铁架台|
water displacement|排水法|airtightness check|检查气密性"""),
    ("High school: amount of substance and solutions  高中：物质的量与溶液", """
amount of substance|物质的量|Avogadro constant|阿伏加德罗常数|
molar mass|摩尔质量|molar volume|摩尔体积|molar concentration|物质的量浓度|
standard conditions|标准状况|volumetric flask|容量瓶|colloid|胶体|
Tyndall effect|丁达尔效应|electrolyte|电解质|nonelectrolyte|非电解质|
strong electrolyte|强电解质|weak electrolyte|弱电解质|ionic equation|离子方程式"""),
    ("High school: redox and electrochemistry  高中：氧化还原与电化学", """
redox reaction|氧化还原反应|oxidizing agent|氧化剂|reducing agent|还原剂|
reduction|还原|oxidation state|氧化态|electron transfer|电子转移|
galvanic cell|原电池|electrolytic cell|电解池|electrode|电极|anode|阳极|
cathode|阴极|positive electrode|正极|negative electrode|负极|salt bridge|盐桥|
fuel cell|燃料电池|electroplating|电镀|electrochemical corrosion|电化学腐蚀"""),
    ("High school: structure and the periodic law  高中：物质结构与元素周期律", """
periodic law|元素周期律|group|族|main group|主族|transition element|过渡元素|
electron configuration|电子排布|atomic radius|原子半径|
electronegativity|电负性|ionization energy|电离能|chemical bond|化学键|
ionic bond|离子键|covalent bond|共价键|metallic bond|金属键|
polar molecule|极性分子|nonpolar molecule|非极性分子|hydrogen bond|氢键|
intermolecular force|分子间作用力|ionic crystal|离子晶体|
molecular crystal|分子晶体|covalent crystal|共价晶体|hybridization|杂化|
isomer|同分异构体|allotrope|同素异形体"""),
    ("High school: energy, rate and equilibrium  高中：化学反应原理", """
exothermic reaction|放热反应|endothermic reaction|吸热反应|enthalpy|焓|
enthalpy change|焓变|thermochemical equation|热化学方程式|Hess's law|盖斯定律|
reaction rate|化学反应速率|activation energy|活化能|effective collision|有效碰撞|
reversible reaction|可逆反应|chemical equilibrium|化学平衡|
equilibrium constant|平衡常数|Le Chatelier's principle|勒夏特列原理|
conversion rate|转化率|spontaneous reaction|自发反应"""),
    ("High school: ionic equilibria  高中：水溶液中的离子平衡", """
ionization|电离|ionization constant|电离常数|ion product of water|水的离子积|
hydrolysis|水解|buffer solution|缓冲溶液|titration|滴定|
acid-base titration|酸碱中和滴定|end point|滴定终点|
solubility product|溶度积|precipitation equilibrium|沉淀溶解平衡"""),
    ("High school: organic chemistry  高中：有机化学", """
hydrocarbon|烃|alkane|烷烃|alkene|烯烃|alkyne|炔烃|aromatic hydrocarbon|芳香烃|
benzene|苯|functional group|官能团|alcohol|醇|aldehyde|醛|carboxylic acid|羧酸|
ester|酯|esterification|酯化反应|substitution reaction|取代反应|
addition reaction|加成反应|elimination reaction|消去反应|
polymerization|聚合反应|polymer|高分子；聚合物|monomer|单体|homologue|同系物|
amino acid|氨基酸|starch|淀粉|cellulose|纤维素"""),
]
CHEMISTRY_WORDS = [(heading, word_entries(raw)) for heading, raw in CHEMISTRY_WORDS]
CHEMISTRY_FORMULAS = [
    ("H₂O", "water", "水"), ("O₂", "oxygen", "氧气"), ("H₂", "hydrogen", "氢气"),
    ("N₂", "nitrogen", "氮气"), ("CO₂", "carbon dioxide", "二氧化碳"),
    ("CO", "carbon monoxide", "一氧化碳"), ("SO₂", "sulfur dioxide", "二氧化硫"),
    ("H₂O₂", "hydrogen peroxide", "过氧化氢"), ("NH₃", "ammonia", "氨气"),
    ("HCl", "hydrochloric acid", "盐酸"), ("H₂SO₄", "sulfuric acid", "硫酸"),
    ("HNO₃", "nitric acid", "硝酸"), ("NaOH", "sodium hydroxide", "氢氧化钠"),
    ("Ca(OH)₂", "calcium hydroxide", "氢氧化钙"), ("NaCl", "sodium chloride", "氯化钠"),
    ("CaCO₃", "calcium carbonate", "碳酸钙"), ("CaO", "calcium oxide", "氧化钙（生石灰）"),
    ("Na₂CO₃", "sodium carbonate", "碳酸钠（纯碱）"),
    ("NaHCO₃", "sodium bicarbonate", "碳酸氢钠（小苏打）"),
    ("CuSO₄", "copper sulfate", "硫酸铜"), ("AgNO₃", "silver nitrate", "硝酸银"),
    ("Fe₂O₃", "ferric oxide", "氧化铁"), ("Fe₃O₄", "triiron tetroxide", "四氧化三铁"),
    ("KMnO₄", "potassium permanganate", "高锰酸钾"), ("KClO₃", "potassium chlorate", "氯酸钾"),
    ("CH₄", "methane", "甲烷"), ("C₂H₅OH", "ethanol", "乙醇"),
    ("CH₃COOH", "acetic acid", "乙酸"), ("C₆H₁₂O₆", "glucose", "葡萄糖"),
]
CHEMISTRY_WORDS.insert(8, ("Common chemical formulas  常见化学式", CHEMISTRY_FORMULAS))
page = symbol_section(c, page, "Chemistry Vocabulary",
                      "From primary to high school. Trace the gray words.", CHEMISTRY_WORDS,
                      name_color=pair_color)

# --- Biology vocabulary, primary to high school -------------------------------
BIOLOGY_WORDS = [
    ("Primary science: living things  小学科学：生物", """
living thing|生物|nonliving thing|非生物|plant|植物|animal|动物|root|根|stem|茎|
leaf|叶|flower|花|fruit|果实|seed|种子|germinate|发芽|mammal|哺乳动物|bird|鸟类|
fish|鱼类|insect|昆虫|reptile|爬行动物|amphibian|两栖动物|habitat|栖息地|
food chain|食物链|life cycle|生命周期|egg|卵|larva|幼虫|pupa|蛹|adult|成体|
skeleton|骨骼|muscle|肌肉|heart|心脏|lung|肺|stomach|胃|brain|脑|
senses|感官|magnifying glass|放大镜|microscope|显微镜"""),
    ("Middle school: cells and organisms  初中：细胞与生物体", """
biology|生物学|cell|细胞|cell membrane|细胞膜|cell wall|细胞壁|cytoplasm|细胞质|
nucleus|细胞核|chloroplast|叶绿体|mitochondria|线粒体|vacuole|液泡|
cell division|细胞分裂|tissue|组织|organ|器官|system|系统|organism|生物体|
unicellular organism|单细胞生物|specimen|标本|slide|玻片|eyepiece|目镜|
objective lens|物镜"""),
    ("Middle school: green plants  初中：绿色植物", """
photosynthesis|光合作用|respiration|呼吸作用|transpiration|蒸腾作用|
chlorophyll|叶绿素|stoma|气孔|xylem|木质部|phloem|韧皮部|pollination|传粉|
fertilization|受精|embryo|胚|seed coat|种皮|cotyledon|子叶|endosperm|胚乳|
moss|苔藓植物|fern|蕨类植物|gymnosperm|裸子植物|angiosperm|被子植物"""),
    ("Middle school: the human body  初中：人体生理", """
digestion|消化|digestive system|消化系统|small intestine|小肠|
large intestine|大肠|liver|肝脏|enzyme|酶|nutrient|营养物质|
circulatory system|循环系统|blood vessel|血管|artery|动脉|vein|静脉|
capillary|毛细血管|red blood cell|红细胞|white blood cell|白细胞|
platelet|血小板|plasma|血浆|respiratory system|呼吸系统|kidney|肾脏|urine|尿液|
nervous system|神经系统|neuron|神经元|reflex|反射|spinal cord|脊髓|
hormone|激素|endocrine system|内分泌系统|reproductive system|生殖系统|
puberty|青春期"""),
    ("Middle school: diversity and ecology  初中：生物多样性与生态", """
vertebrate|脊椎动物|invertebrate|无脊椎动物|bacteria|细菌|fungi|真菌|virus|病毒|
yeast|酵母菌|mold|霉菌|classification|分类|kingdom|界|genus|属|species|物种|
ecosystem|生态系统|producer|生产者|consumer|消费者|decomposer|分解者|
food web|食物网|biosphere|生物圈|biodiversity|生物多样性|
endangered species|濒危物种|nature reserve|自然保护区"""),
    ("Middle school: heredity, evolution and health  初中：遗传、进化与健康", """
heredity|遗传|variation|变异|gene|基因|chromosome|染色体|DNA|脱氧核糖核酸|
trait|性状|dominant trait|显性性状|recessive trait|隐性性状|fossil|化石|
evolution|进化|natural selection|自然选择|adaptation|适应|immunity|免疫|
vaccine|疫苗|antibody|抗体|antigen|抗原|infectious disease|传染病|
pathogen|病原体|antibiotic|抗生素|first aid|急救"""),
    ("High school: molecules and cells  高中：分子与细胞", """
nucleic acid|核酸|RNA|核糖核酸|lipid|脂质|ATP|腺苷三磷酸|
prokaryotic cell|原核细胞|eukaryotic cell|真核细胞|organelle|细胞器|
ribosome|核糖体|endoplasmic reticulum|内质网|Golgi apparatus|高尔基体|
lysosome|溶酶体|cytoskeleton|细胞骨架|osmosis|渗透作用|
active transport|主动运输|passive transport|被动运输|plasmolysis|质壁分离"""),
    ("High school: metabolism and the cell cycle  高中：代谢与细胞生命历程", """
substrate|底物|aerobic respiration|有氧呼吸|anaerobic respiration|无氧呼吸|
light reaction|光反应|dark reaction|暗反应|Calvin cycle|卡尔文循环|
cell cycle|细胞周期|mitosis|有丝分裂|meiosis|减数分裂|
cell differentiation|细胞分化|totipotency|全能性|stem cell|干细胞|
apoptosis|细胞凋亡|cancer cell|癌细胞"""),
    ("High school: genetics and evolution  高中：遗传与进化", """
allele|等位基因|genotype|基因型|phenotype|表型|homozygous|纯合的|
heterozygous|杂合的|law of segregation|分离定律|
law of independent assortment|自由组合定律|sex chromosome|性染色体|
double helix|双螺旋|replication|复制|transcription|转录|translation|翻译|
genetic code|遗传密码|codon|密码子|mutation|突变|gene mutation|基因突变|
genetic recombination|基因重组|chromosomal variation|染色体变异|
polyploid|多倍体|genetic disease|遗传病|gene pool|基因库|
gene frequency|基因频率|reproductive isolation|生殖隔离|speciation|物种形成|
coevolution|协同进化"""),
    ("High school: homeostasis and regulation  高中：稳态与调节", """
homeostasis|稳态|internal environment|内环境|tissue fluid|组织液|lymph|淋巴|
resting potential|静息电位|action potential|动作电位|synapse|突触|
neurotransmitter|神经递质|insulin|胰岛素|glucagon|胰高血糖素|
negative feedback|负反馈|lymphocyte|淋巴细胞|humoral immunity|体液免疫|
cellular immunity|细胞免疫|plant hormone|植物激素|auxin|生长素|
phototropism|向光性"""),
    ("High school: populations and ecosystems  高中：种群与生态系统", """
population|种群|population density|种群密度|carrying capacity|环境容纳量|
community|群落|succession|演替|trophic level|营养级|energy flow|能量流动|
material cycle|物质循环|carbon cycle|碳循环|ecological balance|生态平衡|
sustainable development|可持续发展"""),
    ("High school: biotechnology  高中：生物技术与工程", """
fermentation|发酵|genetic engineering|基因工程|restriction enzyme|限制酶|
plasmid|质粒|recombinant DNA|重组 DNA|PCR|聚合酶链式反应|
transgenic organism|转基因生物|cell engineering|细胞工程|
tissue culture|组织培养|cloning|克隆|embryo transfer|胚胎移植"""),
]
BIOLOGY_WORDS = [(heading, word_entries(raw)) for heading, raw in BIOLOGY_WORDS]
page = symbol_section(c, page, "Biology Vocabulary",
                      "From primary to high school. Trace the gray words.", BIOLOGY_WORDS,
                      name_color=pair_color)

# --- Earth science vocabulary, primary to high school -------------------------
EARTH_WORDS = [
    ("Primary science: Earth and sky  小学科学：地球与宇宙", """
Earth|地球|Sun|太阳|Moon|月球|star|恒星|planet|行星|solar system|太阳系|
day and night|昼夜|season|季节|summer|夏季|autumn|秋季|winter|冬季|
weather|天气|rain|雨|snow|雪|cloud|云|wind|风|rainbow|彩虹|thunder|雷|
lightning|闪电|rock|岩石|soil|土壤|sand|沙|mountain|山|river|河流|lake|湖泊|
ocean|海洋|island|岛屿|desert|沙漠|forest|森林|volcano|火山|earthquake|地震|
map|地图|globe|地球仪|north|北|south|南|east|东|west|西"""),
    ("Middle school: the Earth and maps  初中：地球与地图", """
latitude|纬度|longitude|经度|equator|赤道|meridian|经线|
prime meridian|本初子午线|Northern Hemisphere|北半球|
Southern Hemisphere|南半球|Eastern Hemisphere|东半球|Western Hemisphere|西半球|
Arctic Circle|北极圈|Antarctic Circle|南极圈|Tropic of Cancer|北回归线|
Tropic of Capricorn|南回归线|Earth's axis|地轴|Earth's rotation|地球自转|
Earth's revolution|地球公转|time zone|时区|
International Date Line|国际日期变更线|scale|比例尺|legend|图例|
compass rose|指向标|elevation|海拔|contour line|等高线|topographic map|地形图"""),
    ("Middle school: landforms and oceans  初中：地形与海洋", """
continent|大洲|plain|平原|plateau|高原|basin|盆地|hill|丘陵|valley|山谷|
peninsula|半岛|strait|海峡|bay|海湾|coast|海岸|delta|三角洲|glacier|冰川|
Pacific Ocean|太平洋|Atlantic Ocean|大西洋|Indian Ocean|印度洋|
Arctic Ocean|北冰洋|plate|板块|plate tectonics|板块构造学说|
continental drift|大陆漂移"""),
    ("Middle school: weather and climate  初中：天气与气候", """
climate|气候|precipitation|降水|humidity|湿度|weather forecast|天气预报|
typhoon|台风|hurricane|飓风|monsoon|季风|drought|干旱|flood|洪涝|
torrid zone|热带|temperate zone|温带|frigid zone|寒带|rainforest|雨林|
climate change|气候变化|global warming|全球变暖|air quality|空气质量"""),
    ("Middle school: people and resources  初中：人类与资源", """
natural resources|自然资源|water resources|水资源|mineral resources|矿产资源|
land use|土地利用|agriculture|农业|industry|工业|transportation|交通运输|
urbanization|城市化|migration|人口迁移"""),
    ("High school: the Earth in space  高中：宇宙中的地球", """
universe|宇宙|galaxy|星系|Milky Way|银河系|celestial body|天体|
solar radiation|太阳辐射|solar activity|太阳活动|sunspot|太阳黑子|
solar flare|耀斑|solar wind|太阳风|aurora|极光|
noon solar altitude|正午太阳高度|solstice|至日|summer solstice|夏至|
winter solstice|冬至|equinox|分日|vernal equinox|春分|autumnal equinox|秋分|
local time|地方时"""),
    ("High school: Earth's interior and landforms  高中：地球内部与地貌", """
crust|地壳|mantle|地幔|core|地核|outer core|外核|inner core|内核|
lithosphere|岩石圈|hydrosphere|水圈|atmosphere|大气圈|seismic wave|地震波|
Moho discontinuity|莫霍界面|Gutenberg discontinuity|古登堡界面|magma|岩浆|
igneous rock|岩浆岩|sedimentary rock|沉积岩|metamorphic rock|变质岩|
rock cycle|岩石圈物质循环|weathering|风化作用|erosion|侵蚀作用|
sedimentation|沉积作用|fold|褶皱|anticline|背斜|syncline|向斜|fault|断层|
mid-ocean ridge|洋中脊|trench|海沟|alluvial fan|冲积扇|karst|喀斯特地貌|
sand dune|沙丘"""),
    ("High school: the atmosphere  高中：大气", """
troposphere|对流层|stratosphere|平流层|ozone layer|臭氧层|
atmospheric circulation|大气环流|Coriolis effect|地转偏向力|
pressure belt|气压带|wind belt|风带|trade winds|信风|westerlies|西风带|
air mass|气团|cold front|冷锋|warm front|暖锋|cyclone|气旋|
anticyclone|反气旋|isobar|等压线|urban heat island|城市热岛"""),
    ("High school: the hydrosphere  高中：水圈", """
water cycle|水循环|runoff|径流|infiltration|下渗|groundwater|地下水|
drainage basin|流域|ocean current|洋流|warm current|暖流|cold current|寒流|
salinity|盐度|tide|潮汐|tsunami|海啸|El Nino|厄尔尼诺|La Nina|拉尼娜"""),
    ("High school: environment and geospatial technology  高中：环境与地理信息技术", """
natural disaster|自然灾害|landslide|滑坡|debris flow|泥石流|
desertification|荒漠化|soil erosion|水土流失|deforestation|森林砍伐|
carbon emissions|碳排放|carbon neutrality|碳中和|
environmental protection|环境保护|remote sensing|遥感|
GIS|地理信息系统|GPS|全球定位系统|BeiDou|北斗卫星导航系统"""),
]
EARTH_WORDS = [(heading, word_entries(raw)) for heading, raw in EARTH_WORDS]
page = symbol_section(c, page, "Earth Science Vocabulary",
                      "From primary to high school. Trace the gray words.", EARTH_WORDS,
                      name_color=pair_color)

c.save()
print("saved")
