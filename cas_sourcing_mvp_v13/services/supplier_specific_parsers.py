from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import re

from bs4 import BeautifulSoup
from services.supplier_adapters import ADAPTERS

PRICE_RE = re.compile(r"(?:USD\s*)?(?:US\$|\$)\s?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,4})?|[0-9]+(?:\.[0-9]{1,4})?)|\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,4})?)\s?(?:USD|US\s?dollars)\b", re.I)
PACK_RE = re.compile(r"(?<![A-Za-z0-9])([0-9]+(?:\.[0-9]+)?)\s?(ug|µg|μg|mcg|microgram|micrograms|mg|milligram|milligrams|g|gram|grams|kg|kilogram|kilograms|ml|mL|milliliter|milliliters|L|l|liter|liters)\b", re.I)
SOLUTION_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s?mL\s*(?:x|\*)?\s*\d+(?:\.\d+)?\s?mM\s*(?:\(?\s*in\s*DMSO\s*\)?)?|\d+(?:\.\d+)?\s?mM\s*(?:x|\*)?\s*(\d+(?:\.\d+)?)\s?mL\s*(?:in\s*DMSO)?")
STOCK_RE = re.compile(r"(?i)(in\s*stock|out\s*of\s*stock|available|backorder|preorder|ships?\s*in\s*[^.;,|]{1,45}|usually\s*ships[^.;,|]{0,45}|lead\s*time[^.;,|]{0,45}|\d+[- ]?\d+\s*(?:days|weeks)|request\s+a?\s*quote|price\s+on\s+request)")
PRICE_NOISE_RE = re.compile(r"(?i)(free\s+shipping|orders?\s+over|minimum\s+order|cart\b|basket\b|subtotal|checkout|coupon|promo|discount|shipping\s+threshold|handling\s+fee|tax\b|recently\s+added|save\s+\d+%|reward|points)")
JSON_PRICE_KEY_RE = re.compile(r"(?i)(price|finalprice|final_price|amount|unitprice|unit_price|listprice|list_price|saleprice|sale_price|yourprice|your_price|regularprice|regular_price)")
JSON_PACK_KEY_RE = re.compile(r"(?i)(size|pack|package|quantity|qty|amount|unit|name|label|sku|variant|option)")

@dataclass(frozen=True)
class SupplierParserProfile:
    supplier: str
    row_selectors: tuple[str, ...]
    option_selectors: tuple[str, ...]
    table_markers: tuple[str, ...]
    size_headers: tuple[str, ...]
    price_headers: tuple[str, ...]
    stock_headers: tuple[str, ...]
    product_path_hints: tuple[str, ...]
    parser_notes: str


def _default_profile(supplier: str) -> SupplierParserProfile:
    return SupplierParserProfile(
        supplier=supplier,
        row_selectors=("tr", ".product-item", ".item", ".variant", ".price-row", ".package", ".pack-size", ".sku-row", "[data-price]", "[data-price-amount]", "[data-final-price]", "[data-product-id]", "[data-sku]"),
        option_selectors=("option", "select option", "[data-price]", "[data-price-amount]", "[data-final-price]"),
        table_markers=("size", "pack", "price", "stock", "availability", "qty", "quantity", "catalog"),
        size_headers=("size", "pack", "package", "amount", "qty", "quantity", "unit"),
        price_headers=("price", "usd", "amount", "cost", "your price", "list price", "unit price"),
        stock_headers=("stock", "availability", "lead", "ships", "global stock", "usa stock"),
        product_path_hints=("product", "products", "compound", "item", "catalog", "shop"),
        parser_notes="Generic profile-backed parser.",
    )

def _profile(supplier: str, **kwargs: Any) -> SupplierParserProfile:
    data = _default_profile(supplier).__dict__.copy(); data.update(kwargs); return SupplierParserProfile(**data)

SUPPLIER_PARSER_PROFILES: dict[str, SupplierParserProfile] = {
    "TargetMol": _profile("TargetMol", row_selectors=("tr", ".sku-row", ".price-table tr", ".product-pack tr", ".product-info tr", "[data-price]"), table_markers=("pack size", "price", "usa stock", "global stock", "stock"), product_path_hints=("compound", "product"), parser_notes="Pack Size / Price / USA Stock / Global Stock table parser."),
    "MedChemExpress": _profile("MedChemExpress", row_selectors=("tr", ".product-price tr", ".table-price tr", ".package tr", ".size-price tr", "[data-price]"), table_markers=("size", "price", "stock", "purity"), product_path_hints=("cas", "compound", "product"), parser_notes="MCE size/price/stock product-table parser."),
    "SelleckChem": _profile("SelleckChem", row_selectors=("tr", ".price-table tr", ".product-price tr", ".size_price tr", ".packaging tr", "[data-price]"), table_markers=("pack size", "price", "stock", "qty"), product_path_hints=("products", "compound"), parser_notes="Selleck pack-size/price row parser."),
    "Cayman Chemical": _profile("Cayman Chemical", row_selectors=("tr", ".product-price tr", ".item-price tr", ".pricing tr", ".variant tr", "[data-price]"), table_markers=("item", "size", "price", "availability"), product_path_hints=("product", "item"), parser_notes="Cayman item/size/availability parser."),
    "MolPort": _profile("MolPort", row_selectors=("tr", ".packing", ".offer", ".seller-offer", ".price", "[data-price]"), table_markers=("available packings", "supplier", "amount", "price", "shipping"), product_path_hints=("shop/compound", "compound"), parser_notes="MolPort marketplace offer/packing parser."),
    "Adooq": _profile("Adooq", product_path_hints=("product", "catalog"), parser_notes="Magento-style option/data-price parser."),
    "ApexBio": _profile("ApexBio", row_selectors=("tr", ".price-table tr", ".product-price tr", ".package tr", ".size-price tr", "[data-price]"), table_markers=("size", "price", "stock", "qty"), product_path_hints=("products", "catalog"), parser_notes="ApexBio rows like 10mg / $67 / In stock."),
    "GLP Bio": _profile("GLP Bio", product_path_hints=("product", "catalog"), parser_notes="GLP Bio multilingual-safe product row parser."),
    "AbMole": _profile("AbMole", product_path_hints=("product", "catalog"), parser_notes="AbMole parser with shipping-threshold price noise rejection."),
    "ChemFaces": _profile("ChemFaces", product_path_hints=("products", "product"), parser_notes="ChemFaces natural-products price-row parser."),
    "BioCrick": _profile("BioCrick", product_path_hints=("products", "product"), parser_notes="BioCrick natural-products price-row parser."),
    "CSNpharm": _profile("CSNpharm", product_path_hints=("products", "product"), parser_notes="CSNpharm size/price/stock parser."),
    "InvivoChem": _profile("InvivoChem", product_path_hints=("product", "catalog"), parser_notes="InvivoChem Magento-like variant parser."),
    "AdooQ Bioscience": _profile("AdooQ Bioscience", product_path_hints=("product", "catalog"), parser_notes="Alternate AdooQ domain parser."),
    "Biorbyt": _profile("Biorbyt", product_path_hints=("product", "products"), parser_notes="Biorbyt reagent parser."),
    "TCI Chemicals": _profile("TCI Chemicals", row_selectors=("tr", ".product-list tr", ".price-table tr", ".sku-row", ".variant", "[data-price]"), table_markers=("packaging", "package", "price", "stock", "delivery"), product_path_hints=("product", "products"), parser_notes="TCI regional product-table parser."),
    "Oakwood Chemical": _profile("Oakwood Chemical", product_path_hints=("product", "products"), parser_notes="Oakwood specialty catalog parser."),
    "Chem-Impex": _profile("Chem-Impex", product_path_hints=("products", "product"), parser_notes="Chem-Impex catalog parser with marketing text filter."),
    "Combi-Blocks": _profile("Combi-Blocks", product_path_hints=("product", "products", "cgi-bin"), parser_notes="Combi-Blocks building-block parser."),
    "BLD Pharm": _profile("BLD Pharm", product_path_hints=("product", "products"), parser_notes="BLD Pharm building-block parser."),
    "Ambeed": _profile("Ambeed", product_path_hints=("products", "product"), parser_notes="Ambeed JSON-LD/canonical product parser."),
    "A2B Chem": _profile("A2B Chem", product_path_hints=("product", "products", "search.aspx"), parser_notes="A2B Chem parser."),
    "Enamine": _profile("Enamine", product_path_hints=("catalog", "product"), parser_notes="Enamine quote/account mixed parser."),
    "Matrix Scientific": _profile("Matrix Scientific", product_path_hints=("product", "products"), parser_notes="Matrix Scientific parser."),
    "Santa Cruz Biotechnology": _profile("Santa Cruz Biotechnology", product_path_hints=("product", "products"), parser_notes="SCBT product-row parser."),
    "CymitQuimica": _profile("CymitQuimica", product_path_hints=("products", "product"), parser_notes="Cymit marketplace parser."),
    "Toronto Research Chemicals": _profile("Toronto Research Chemicals", product_path_hints=("product", "products"), parser_notes="TRC reference/specialty parser."),
    "Fisher Scientific": _profile("Fisher Scientific", product_path_hints=("shop", "products", "catalog"), parser_notes="Fisher parser: public rows if present, otherwise account-price classification."),
    "Thermo Fisher / Alfa Aesar": _profile("Thermo Fisher / Alfa Aesar", product_path_hints=("products", "product", "search"), parser_notes="Thermo/Alfa session/account price classifier."),
    "Sigma-Aldrich": _profile("Sigma-Aldrich", product_path_hints=("product", "search"), parser_notes="Sigma country/account price classifier."),
    "VWR / Avantor": _profile("VWR / Avantor", product_path_hints=("store", "product", "search"), parser_notes="VWR account price classifier."),
    "ChemicalBook": _profile("ChemicalBook", product_path_hints=("chemicalproduct", "product"), parser_notes="Directory parser; RFQ leads, not source-of-truth pricing."),
    "ChemBlink": _profile("ChemBlink", product_path_hints=("products", "product"), parser_notes="Directory parser; RFQ lead parser."),
    "ChemExper": _profile("ChemExper", product_path_hints=("search", "product"), parser_notes="Directory parser; RFQ lead parser."),
    "LookChem": _profile("LookChem", product_path_hints=("cas", "product"), parser_notes="Directory parser; RFQ lead parser."),
}
for _adapter in ADAPTERS:
    SUPPLIER_PARSER_PROFILES.setdefault(_adapter.name, _default_profile(_adapter.name))

def _safe_float(value: Any) -> float | None:
    try:
        v = float(str(value).replace(',', '').replace('$', '').replace('USD', '').strip())
        return v if 0 < v < 10_000_000 else None
    except Exception:
        return None

def _normalize_unit(unit: str | None) -> str | None:
    if not unit: return None
    u = str(unit).strip().lower().replace('μ','u').replace('µ','u')
    return {'mcg':'ug','microgram':'ug','micrograms':'ug','ug':'ug','milligram':'mg','milligrams':'mg','mg':'mg','gram':'g','grams':'g','g':'g','kilogram':'kg','kilograms':'kg','kg':'kg','milliliter':'mL','milliliters':'mL','ml':'mL','liter':'L','liters':'L','l':'L'}.get(u, unit)

def _pack_is_reasonable(size: float | None, unit: str | None) -> bool:
    return bool(size is not None and unit is not None and 0 < size <= {'ug':1_000_000_000,'mg':1_000_000,'g':100_000,'kg':10_000,'mL':1_000_000,'L':10_000}.get(unit,100_000))

def _parse_pack(text: Any) -> tuple[float | None, str | None]:
    txt = str(text or '').replace('μ','u').replace('µ','u')
    sm = SOLUTION_RE.search(txt)
    if sm:
        size = _safe_float(sm.group(1) or sm.group(2)); return (size,'mL') if _pack_is_reasonable(size,'mL') else (None,None)
    m = PACK_RE.search(txt)
    if not m: return None, None
    size = _safe_float(m.group(1)); unit = _normalize_unit(m.group(2))
    return (size, unit) if _pack_is_reasonable(size, unit) else (None, None)

def _parse_price(text: Any, context: str = '') -> float | None:
    txt = str(text or '')
    if PRICE_NOISE_RE.search(f'{context} {txt}'[:1800]): return None
    m = PRICE_RE.search(txt)
    return _safe_float(m.group(1) or m.group(2)) if m else None

def _stock(text: Any) -> str:
    m = STOCK_RE.search(str(text or '')); return m.group(1).title() if m else 'Not visible'

def _form(pack_unit: str | None, text: Any) -> str:
    unit = str(pack_unit or ''); hay = str(text or '').lower()
    if 'reference standard' in hay or 'analytical standard' in hay or '(standard)' in hay: return 'standard/reference'
    if unit in {'mL','L'} or 'in dmso' in hay or re.search(r'\b\d+(?:\.\d+)?\s?mm\b', hay): return 'solution'
    if unit in {'ug','mg','g','kg'}: return 'solid/mass'
    return 'unknown'

def _row(profile: SupplierParserProfile, method: str, text: str, pack_size: float | None, pack_unit: str | None, price: float | None, confidence: str) -> dict[str, Any] | None:
    if price is None or not _pack_is_reasonable(pack_size, pack_unit) or PRICE_NOISE_RE.search(text or ''): return None
    return {'method':f'supplier_parser:{profile.supplier}:{method}','pack_size':pack_size,'pack_unit':pack_unit,'price':price,'stock':_stock(text),'raw':[re.sub(r'\s+',' ',str(text or '')).strip()[:1200]],'price_pairing_confidence':confidence,'product_form':_form(pack_unit,text),'supplier_parser_name':_parser_name(profile.supplier),'supplier_parser_status':'supplier_specific_price_rows_found'}

def _parse_html_tables(profile: SupplierParserProfile, soup: BeautifulSoup) -> list[dict[str, Any]]:
    out=[]
    for table in soup.find_all('table'):
        table_text=table.get_text(' ',strip=True).lower()
        if not any(m.lower() in table_text for m in profile.table_markers): continue
        headers=[]
        for tr in table.find_all('tr'):
            cells=[c.get_text(' ',strip=True) for c in tr.find_all(['th','td'])]
            if not cells: continue
            row_text=' | '.join(cells); lower=[c.lower() for c in cells]
            if any(any(h in c for h in profile.price_headers) for c in lower) and any(any(h in c for h in profile.size_headers) for c in lower):
                headers=lower; continue
            pack_text=row_text; price_text=row_text; stock_text=row_text
            if headers and len(headers)==len(cells):
                for h,c in zip(headers,cells):
                    if any(w in h for w in profile.size_headers): pack_text=c
                    if any(w in h for w in profile.price_headers): price_text=c
                    if any(w in h for w in profile.stock_headers): stock_text += ' '+c
            pack_size,pack_unit=_parse_pack(pack_text); price=_parse_price(price_text,row_text) or _parse_price(row_text,row_text)
            r=_row(profile,'table_row',f'{row_text} | {stock_text}',pack_size,pack_unit,price,'HIGH')
            if r: out.append(r)
    return out

def _parse_options(profile: SupplierParserProfile, soup: BeautifulSoup) -> list[dict[str, Any]]:
    out=[]
    for node in soup.select(','.join(profile.option_selectors)):
        attrs=' '.join(f'{k}={v}' for k,v in getattr(node,'attrs',{}).items()); text=f"{node.get_text(' ',strip=True)} {attrs}"
        pack_size,pack_unit=_parse_pack(text); price=_parse_price(text,text)
        if price is None:
            for key in ('data-price','data-price-amount','data-final-price','price','data-amount'):
                if node.has_attr(key): price=_safe_float(node.get(key)); break
        r=_row(profile,'option_or_data_attr',text,pack_size,pack_unit,price,'HIGH')
        if r: out.append(r)
    return out

def _walk_json(obj: Any):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values(): yield from _walk_json(v)
    elif isinstance(obj,list):
        for item in obj: yield from _walk_json(item)

def _loads_json_candidates(text: str) -> list[Any]:
    txt=(text or '').strip(); candidates=[]
    if txt.startswith('{') or txt.startswith('['): candidates.append(txt)
    for m in re.finditer(r'(?s)(\{[^{}]{0,3000}(?:price|finalPrice|unitPrice|pack|size|sku)[^{}]{0,3000}\})', txt[:250000], re.I): candidates.append(m.group(1))
    parsed=[]
    for raw in candidates[:100]:
        try: parsed.append(json.loads(raw))
        except Exception: pass
    return parsed

def _parse_json(profile: SupplierParserProfile, soup: BeautifulSoup) -> list[dict[str, Any]]:
    out=[]
    for script in soup.find_all('script'):
        script_text=script.get_text(' ',strip=True)
        if not script_text or 'price' not in script_text.lower(): continue
        for root in _loads_json_candidates(script_text):
            for node in _walk_json(root):
                if not isinstance(node,dict): continue
                raw=json.dumps(node,ensure_ascii=False)[:1800]
                pack_sources=[v for k,v in node.items() if JSON_PACK_KEY_RE.search(str(k))]+[raw]
                price_sources=[v for k,v in node.items() if JSON_PRICE_KEY_RE.search(str(k))]+[raw]
                pack_size=pack_unit=price=None
                for src in pack_sources:
                    pack_size,pack_unit=_parse_pack(src)
                    if pack_size: break
                for src in price_sources:
                    price=_safe_float(src) if not isinstance(src,str) else _parse_price(src,raw)
                    if price: break
                r=_row(profile,'embedded_json',raw,pack_size,pack_unit,price,'HIGH')
                if r: out.append(r)
    return out

def _parse_row_containers(profile: SupplierParserProfile, soup: BeautifulSoup) -> list[dict[str, Any]]:
    out=[]
    for node in soup.select(','.join(profile.row_selectors)):
        text=node.get_text(' | ',strip=True)
        if len(text)<4: text=' '.join(f'{k}={v}' for k,v in getattr(node,'attrs',{}).items())
        if not text or PRICE_NOISE_RE.search(text): continue
        pack_size,pack_unit=_parse_pack(text); price=_parse_price(text,text)
        r=_row(profile,'row_container',text,pack_size,pack_unit,price,'MEDIUM')
        if r: out.append(r)
    return out

def _parse_text_ladders(profile: SupplierParserProfile, text: str) -> list[dict[str, Any]]:
    clean=re.sub(r'\s+',' ',(text or '').replace('μ','u').replace('µ','u'))
    markers=[m.start() for m in re.finditer(r'(?i)(pack\s*size|size\s*/?\s*price|size\s+price|available\s+packings|price\s+stock|product\s+items)',clean)]
    if not markers: return []
    out=[]; row_re=re.compile(r'(?P<pack>(?:\d+(?:\.\d+)?\s?(?:ug|mcg|mg|g|kg|mL|ml|L)|\d+(?:\.\d+)?\s?mL\s*(?:x|\*)?\s*\d+(?:\.\d+)?\s?mM(?:\s*\(?in\s*DMSO\)?)?))(?P<middle>.{0,120}?)(?P<price>\$\s*[0-9][0-9,]*(?:\.\d{1,2})?|[0-9][0-9,]*(?:\.\d{1,2})?\s*USD)',re.I)
    for start in markers[:6]:
        window=clean[start:start+9000]
        for m in row_re.finditer(window):
            raw=window[max(0,m.start()-80):min(len(window),m.end()+180)]
            pack_size,pack_unit=_parse_pack(m.group('pack')); price=_parse_price(m.group('price'),raw)
            r=_row(profile,'visible_text_ladder',raw,pack_size,pack_unit,price,'MEDIUM')
            if r: out.append(r)
    return out

def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank={'HIGH':3,'MEDIUM':2,'LOW':1}; rows=sorted(rows,key=lambda r:rank.get(str(r.get('price_pairing_confidence')),0),reverse=True)
    seen=set(); out=[]
    for row in rows:
        key=(round(float(row.get('pack_size') or 0),10),str(row.get('pack_unit') or '').lower(),round(float(row.get('price') or 0),4),str(row.get('product_form') or ''))
        if key in seen: continue
        seen.add(key); out.append(row)
    return out

def _parser_name(supplier: str) -> str:
    return 'parse_'+re.sub(r'[^a-z0-9]+','_',supplier.lower()).strip('_')

def parser_name_for_supplier(supplier: str | None) -> str:
    supplier=supplier or 'Unknown supplier'; profile=SUPPLIER_PARSER_PROFILES.get(supplier,_default_profile(supplier)); return _parser_name(profile.supplier)

def extract_supplier_specific_rows(supplier: str | None, soup: BeautifulSoup, text: str, url: str='') -> tuple[list[dict[str, Any]], str, str]:
    supplier=supplier or 'Unknown supplier'; profile=SUPPLIER_PARSER_PROFILES.get(supplier,_default_profile(supplier)); name=_parser_name(profile.supplier)
    try:
        rows=[]; rows.extend(_parse_html_tables(profile,soup)); rows.extend(_parse_options(profile,soup)); rows.extend(_parse_json(profile,soup)); rows.extend(_parse_row_containers(profile,soup)); rows.extend(_parse_text_ladders(profile,text)); rows=_dedupe(rows)
    except Exception as exc:
        return [], name, f'supplier_specific_parser_failed:{type(exc).__name__}'
    if rows: return rows, name, 'supplier_specific_price_rows_found'
    low=(text or '')[:25000].lower()
    if any(t in low for t in ['sign in','login','your price','account price','register to view']): return [], name, 'supplier_specific_checked_login_or_account_price'
    if any(t in low for t in ['request quote','request a quote','price on request','please inquire','inquire']): return [], name, 'supplier_specific_checked_quote_or_inquiry'
    return [], name, 'supplier_specific_checked_no_public_price_rows'

def supplier_specific_variant_rows(supplier: str | None, soup: BeautifulSoup, text: str) -> list[dict[str, Any]]:
    rows, _, _ = extract_supplier_specific_rows(supplier, soup, text, '')
    return rows

def supplier_parser_status(supplier: str | None, rows_found: int, page_text: str='') -> str:
    if rows_found>0: return 'supplier_specific_price_rows_found'
    low=(page_text or '')[:25000].lower()
    if any(t in low for t in ['sign in','login','your price','account price','register to view']): return 'supplier_specific_checked_login_or_account_price'
    if any(t in low for t in ['request quote','request a quote','price on request','please inquire','inquire']): return 'supplier_specific_checked_quote_or_inquiry'
    return 'supplier_specific_checked_no_public_price_rows'

def supplier_parser_registry_report() -> list[dict[str, str]]:
    return [{'supplier':a.name,'source_tier':a.source_tier,'expected_behavior':a.expected_behavior,'parser':parser_name_for_supplier(a.name),'parser_profile':SUPPLIER_PARSER_PROFILES[a.name].parser_notes} for a in ADAPTERS]
