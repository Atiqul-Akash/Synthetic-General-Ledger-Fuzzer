"""Workday Financial Management & Accounting Center Exporter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom

from gl_fuzzer.models.journal import DebitCredit, JournalEntry


class WorkdayExporter:
    """Exports GL transactions formatted for Workday Accounting Center (SOAP XML and RaaS JSON)."""

    @classmethod
    def export(
        cls,
        entries: List[JournalEntry],
        output_dir: str | Path,
        prefix: str = "WORKDAY",
    ) -> Dict[str, Tuple[Path, str]]:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        xml_path = out_dir / f"{prefix}_SOAP.xml"
        json_path = out_dir / f"{prefix}_RAAS.json"

        # 1. Build Workday SOAP XML (<Submit_Accounting_Journal_Request>)
        root = ET.Element(
            "env:Envelope",
            {
                "xmlns:env": "http://schemas.xmlsoap.org/soap/envelope/",
                "xmlns:bsvc": "urn:com.workday/bsvc",
            },
        )
        body = ET.SubElement(root, "env:Body")
        req = ET.SubElement(body, "bsvc:Submit_Accounting_Journal_Request", {"bsvc:version": "v37.2"})

        for entry in entries:
            jdata = ET.SubElement(req, "bsvc:Accounting_Journal_Data")
            ET.SubElement(jdata, "bsvc:Journal_Number").text = entry.document_number
            ET.SubElement(jdata, "bsvc:Company_Reference").text = entry.company_code
            ET.SubElement(jdata, "bsvc:Journal_Date").text = entry.posting_date
            ET.SubElement(jdata, "bsvc:Description").text = entry.header_text or "Standard GL Entry"
            curr_ref = entry.lines[0].currency if entry.lines and entry.lines[0].currency else "USD"
            ET.SubElement(jdata, "bsvc:Currency_Reference").text = curr_ref
            ET.SubElement(jdata, "bsvc:Ledger_Type_Reference").text = "Standard"

            lines_elem = ET.SubElement(jdata, "bsvc:Journal_Lines")
            for line in entry.lines:
                line_elem = ET.SubElement(lines_elem, "bsvc:Journal_Line_Data")
                ET.SubElement(line_elem, "bsvc:Line_Number").text = str(line.line_number)
                ET.SubElement(line_elem, "bsvc:Ledger_Account_Reference").text = line.account_code
                ET.SubElement(line_elem, "bsvc:Debit_Credit").text = "Debit" if line.debit_credit == DebitCredit.DEBIT else "Credit"
                ET.SubElement(line_elem, "bsvc:Amount").text = f"{line.amount:.2f}"
                ET.SubElement(line_elem, "bsvc:Memo").text = line.line_text or line.account_name

                # Worktags
                worktags = ET.SubElement(line_elem, "bsvc:Worktags")
                if line.cost_center:
                    ET.SubElement(worktags, "bsvc:Cost_Center_Reference").text = line.cost_center
                if line.account_code.startswith("5") or line.account_code.startswith("6"):
                    ET.SubElement(worktags, "bsvc:Spend_Category_Reference").text = f"SC_{line.account_code}"
                elif line.account_code.startswith("4"):
                    ET.SubElement(worktags, "bsvc:Revenue_Category_Reference").text = f"RC_{line.account_code}"

        rough_str = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(rough_str)
        pretty_xml = parsed.toprettyxml(indent="  ", encoding="utf-8")

        with open(xml_path, "wb") as f:
            f.write(pretty_xml)

        xml_hash = hashlib.sha256(pretty_xml).hexdigest()

        # 2. Build Workday RaaS JSON payload
        raas_data = {
            "Report_Entry": [
                {
                    "Journal_Number": entry.document_number,
                    "Company": entry.company_code,
                    "Journal_Date": entry.posting_date,
                    "Fiscal_Year": entry.fiscal_year,
                    "Fiscal_Period": entry.fiscal_period,
                    "Header_Memo": entry.header_text,
                    "Source": entry.business_cycle,
                    "Journal_Lines": [
                        {
                            "Line": line.line_number,
                            "Ledger_Account": line.account_code,
                            "Account_Name": line.account_name,
                            "Type": "DEBIT" if line.debit_credit == DebitCredit.DEBIT else "CREDIT",
                            "Amount": float(line.amount),
                            "Currency": line.currency,
                            "Cost_Center": line.cost_center or "",
                            "Line_Memo": line.line_text,
                        }
                        for line in entry.lines
                    ],
                }
                for entry in entries
            ]
        }
        json_str = json.dumps(raas_data, indent=2, default=str)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_str)

        json_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        return {
            "WORKDAY_SOAP_XML": (xml_path, xml_hash),
            "WORKDAY_RAAS_JSON": (json_path, json_hash),
        }
