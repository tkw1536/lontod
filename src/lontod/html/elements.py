"""pre-defined html elements."""

from abc import ABC

from .node import AttributeLike, ElementNode, NodeLike, VoidElementNode


class _Element(ElementNode, ABC):
    """A pre-defined element."""

    def __init__(self, *children: NodeLike, **attributes: AttributeLike) -> None:
        super().__init__(type(self).__name__, *children, **attributes)


def _element(tag_name: str) -> type[_Element]:
    """Create a new _Element class for the given tag."""

    class FactoryElement(_Element):
        """Factorized Element."""

    FactoryElement.__name__ = tag_name

    return FactoryElement


class _VoidElement(VoidElementNode, ABC):
    def __init__(self, **attributes: AttributeLike) -> None:
        super().__init__(type(self).__name__, **attributes)


def _void_element(tag_name: str) -> type[_VoidElement]:
    """Create a new _VoidElement class for the given void element."""

    class FactoryElement(_VoidElement):
        """Factorized Element."""

    FactoryElement.__name__ = tag_name

    return FactoryElement


# spellchecker:words HGROUP FIGCAPTION SAMP FENCEDFRAME NOSCRIPT COLGROUP DATALIST SELECTEDCONTENT FRAMESET NOBR NOEMBED NOFRAMES

# Main root
HTML = _element("html")

# Document metadata
BASE = _void_element("base")
HEAD = _element("head")
LINK = _void_element("link")
META = _void_element("meta")
STYLE = _element("style")
TITLE = _element("title")

# Sectioning root
BODY = _element("body")

# Content sectioning
ADDRESS = _element("address")
ARTICLE = _element("article")
ASIDE = _element("aside")
FOOTER = _element("footer")
HEADER = _element("header")
H1 = _element("h1")
H2 = _element("h2")
H3 = _element("h3")
H4 = _element("h4")
H5 = _element("h5")
H6 = _element("h6")
HGROUP = _element("hgroup")
MAIN = _element("main")
NAV = _element("nav")
SECTION = _element("section")
SEARCH = _element("search")

# Text content
BLOCKQUOTE = _element("blockquote")
DD = _element("dd")
DIV = _element("div")
DL = _element("dl")
DT = _element("dt")
FIGCAPTION = _element("figcaption")
FIGURE = _element("figure")
HR = _void_element("hr")
LI = _element("li")
MENU = _element("menu")
OL = _element("ol")
P = _element("p")
PRE = _element("pre")
UL = _element("ul")

# Inline text semantics
A = _element("a")
ABBR = _element("abbr")
B = _element("b")
BDI = _element("bdi")
BDO = _element("bdo")
BR = _void_element("br")
CITE = _element("cite")
CODE = _element("code")
DATA = _element("data")
DFN = _element("dfn")
EM = _element("em")
I = _element("i")  # noqa: E741
KBD = _element("kbd")
MARK = _element("mark")
Q = _element("q")
RP = _element("rp")
RT = _element("rt")
RUBY = _element("ruby")
S = _element("s")
SAMP = _element("samp")
SMALL = _element("small")
SPAN = _element("span")
STRONG = _element("strong")
SUB = _element("sub")
SUP = _element("sup")
TIME = _element("time")
U = _element("u")
VAR = _element("var")
WBR = _element("wbr")

# Image and multimedia
AREA = _void_element("area")
AUDIO = _element("audio")
IMG = _void_element("img")
MAP = _element("map")
TRACK = _void_element("track")
VIDEO = _element("video")

# Embedded content
EMBED = _void_element("embed")
FENCEDFRAME = _element("fencedframe")
IFRAME = _element("iframe")
OBJECT = _element("object")
PICTURE = _element("picture")
SOURCE = _void_element("source")

# SVG and MathML
SVG = _element("svg")
MATH = _element("math")

# Scripting
CANVAS = _element("canvas")
NOSCRIPT = _element("noscript")
SCRIPT = _element("script")

# Demarcating edits
DEL = _element("del")
INS = _element("ins")

# Table content
CAPTION = _element("caption")
COL = _void_element("col")
COLGROUP = _element("colgroup")
TABLE = _element("table")
TBODY = _element("tbody")
TD = _element("td")
TFOOT = _element("tfoot")
TH = _element("th")
THEAD = _element("thead")
TR = _element("tr")

# Forms
BUTTON = _element("button")
DATALIST = _element("datalist")
FIELDSET = _element("fieldset")
FORM = _element("form")
INPUT = _void_element("input")
LABEL = _element("label")
LEGEND = _element("legend")
METER = _element("meter")
OPTGROUP = _element("optgroup")
OPTION = _element("option")
OUTPUT = _element("output")
PROGRESS = _element("progress")
SELECT = _element("select")
SELECTEDCONTENT = _element("selectedcontent")
TEXTAREA = _element("textarea")

# Interactive elements
DETAILS = _element("details")
DIALOG = _element("dialog")
SUMMARY = _element("summary")

# Web Components
SLOT = _element("slot")
TEMPLATE = _element("template")

# Obsolete and deprecated elements
ACRONYM = _element("acronym")
BIG = _element("big")
CENTER = _element("center")
DIR = _element("dir")
FONT = _element("font")
FRAME = _element("frame")
FRAMESET = _element("frameset")
MARQUEE = _element("marquee")
NOBR = _element("nobr")
NOEMBED = _element("noembed")
NOFRAMES = _element("noframes")
PARAM = _void_element("param")
PLAINTEXT = _element("plaintext")
RB = _element("rb")
RTC = _element("rtc")
STRIKE = _element("strike")
TT = _element("tt")
XMP = _element("xmp")


__all__ = [
    "ABBR",
    "ACRONYM",
    "ADDRESS",
    "AREA",
    "ARTICLE",
    "ASIDE",
    "AUDIO",
    "BASE",
    "BDI",
    "BDO",
    "BIG",
    "BLOCKQUOTE",
    "BODY",
    "BR",
    "BUTTON",
    "CANVAS",
    "CAPTION",
    "CENTER",
    "CITE",
    "CODE",
    "COL",
    "COLGROUP",
    "DATA",
    "DATALIST",
    "DD",
    "DEL",
    "DETAILS",
    "DFN",
    "DIALOG",
    "DIR",
    "DIV",
    "DL",
    "DT",
    "EM",
    "EMBED",
    "FENCEDFRAME",
    "FIELDSET",
    "FIGCAPTION",
    "FIGURE",
    "FONT",
    "FOOTER",
    "FORM",
    "FRAME",
    "FRAMESET",
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "HEAD",
    "HEADER",
    "HGROUP",
    "HR",
    "HTML",
    "IFRAME",
    "IMG",
    "INPUT",
    "INS",
    "KBD",
    "LABEL",
    "LEGEND",
    "LI",
    "LINK",
    "MAIN",
    "MAP",
    "MARK",
    "MARQUEE",
    "MATH",
    "MENU",
    "META",
    "METER",
    "NAV",
    "NOBR",
    "NOEMBED",
    "NOFRAMES",
    "NOSCRIPT",
    "OBJECT",
    "OL",
    "OPTGROUP",
    "OPTION",
    "OUTPUT",
    "PARAM",
    "PICTURE",
    "PLAINTEXT",
    "PRE",
    "PROGRESS",
    "RB",
    "RP",
    "RT",
    "RTC",
    "RUBY",
    "SAMP",
    "SCRIPT",
    "SEARCH",
    "SECTION",
    "SELECT",
    "SELECTEDCONTENT",
    "SLOT",
    "SMALL",
    "SOURCE",
    "SPAN",
    "STRIKE",
    "STRONG",
    "STYLE",
    "SUB",
    "SUMMARY",
    "SUP",
    "SVG",
    "TABLE",
    "TBODY",
    "TD",
    "TEMPLATE",
    "TEXTAREA",
    "TFOOT",
    "TH",
    "THEAD",
    "TIME",
    "TITLE",
    "TR",
    "TRACK",
    "TT",
    "UL",
    "VAR",
    "VIDEO",
    "WBR",
    "XMP",
    "A",
    "B",
    "I",
    "P",
    "Q",
    "S",
    "U",
]
