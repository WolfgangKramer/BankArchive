"""
Created on 30.03.2020
__updated__ = "2024-03-25"
@author: Wolfg
"""

import xml.etree.ElementTree as ET
import logging

from datetime import datetime
from xml.dom import minidom

from banking.declarations import (
    KEY_ACC_OWNER_NAME, KEY_ACC_IBAN,
    NOTPROVIDED,
    SEPA_CREDITOR_NAME, SEPA_CREDITOR_IBAN, SEPA_CREDITOR_BIC, SEPA_AMOUNT,
    SEPA_PURPOSE, SEPA_REFERENCE, SEPA_EXECUTION_DATE,
)
from banking.utils import only_alphanumeric


URN_PREFIX = "urn:iso:std:iso:20022:tech:xsd:"
SCHEMA_SCT = "pain.001.001.03"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
XMLS_SCT = URN_PREFIX + SCHEMA_SCT
SCHEMALOCATION_SCT = URN_PREFIX + SCHEMA_SCT + " " + SCHEMA_SCT + ".xsd"

logger = logging.getLogger(__name__)


def _logging(xml_string):
    xml_parse = minidom.parseString(xml_string)
    xml_tree = xml_parse.toprettyxml()
    logging.getLogger(__name__).debug(
        ">>>>> START SEPA Transfer XML-File" + 30 * ">" + "\n")
    logger.info(xml_tree)
    logging.getLogger(__name__).debug(
        ">>>>> END   SEPA Transfer XML-File" + 30 * ">" + "\n")


class SepaCreditTransfer():
    """
    Documentation:
    https://www.ebics.de/index.php?eID=tx_securedownloads&p=103&u=0&g=0&t=1589469664&hash=c989043a07bdb83368c6e5d12f30a0225cae9195&file=/fileadmin/unsecured/anlage3/anlage3_spec/Anlage_3_Datenformate_V3.4.pdf
    Anlage 3 er Schnittstellenspezifikation fuer die Datenfernuebertragung zwischen Kunde und
    Kreditinstitut gemaess DFUE-Abkommen  >Spezifikation der Datenformate<
                   Version 3.4 vom 28.04.2020   gueltig ab 22. November 2020
    """

    def __init__(self, bank, account_data, transfer_data):

        GrpHdr_node = self._group_header(bank, account_data, transfer_data)
        CstmrCdtTrfInitn_node = ET.Element("CstmrCdtTrfInitn")
        CstmrCdtTrfInitn_node.append(GrpHdr_node)
        PmtInf_node = self._payment_info(bank, account_data, transfer_data)
        CstmrCdtTrfInitn_node.append(PmtInf_node)
        CdtTrfTxInf_node = self._credit_transfer_transaction_info(
            bank, account_data, transfer_data)
        PmtInf_node.append(CdtTrfTxInf_node)
        root = self._message_root(bank, account_data, transfer_data)
        root.append(CstmrCdtTrfInitn_node)
        bank.sepa_credit_transfer_data = (
            b"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>" + ET.
            tostring(root, "utf-8"))
        _logging(bank.sepa_credit_transfer_data)

    def _message_root(self, bank, account_data, transfer_data):
        """
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03 pain.001.001.03.xsd">
        """
        root = ET.Element("Document")
        root.set("xmlns", XMLS_SCT)
        root.set("xmlns:xsi", XSI)
        root.set("xsi:schemaLocation", SCHEMALOCATION_SCT)
        ET.register_namespace("", XMLS_SCT)
        ET.register_namespace("xsi", XSI)
        return root

    def _group_header(self, bank, account_data, transfer_data):

        # GroupHeader Nodes
        GrpHdr_node = ET.Element("GrpHdr")
        MsgId_node = ET.Element("MsgId")
        CreDtTm_node = ET.Element("CreDtTm")
        NbOfTxs_node = ET.Element("NbOfTxs")
        CtrlSum_node = ET.Element("CtrlSum")
        InitgPty_node = ET.Element("InitgPty")
        InitgPty_Nm_node = ET.Element("Nm")
        # GroupHeader Data
        MsgId_node.text = (only_alphanumeric(str(datetime.now().date()) + "_" + str(
            datetime.now().time())))
        CreDtTm_node.text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        NbOfTxs_node.text = str(1)
        CtrlSum_node.text = transfer_data[SEPA_AMOUNT]
        InitgPty_Nm_node.text = account_data[KEY_ACC_OWNER_NAME]
        # GroupHeader Tree
        GrpHdr_node.append(MsgId_node)
        GrpHdr_node.append(CreDtTm_node)
        GrpHdr_node.append(NbOfTxs_node)
        GrpHdr_node.append(CtrlSum_node)
        GrpHdr_node.append(InitgPty_node)
        InitgPty_node.append(InitgPty_Nm_node)
        return GrpHdr_node

    def _payment_info(self, bank, account_data, transfer_data):

        # Payment Information Nodes
        PmtInf_node = ET.Element("PmtInf")
        PmtInfId_node = ET.Element("PmtInfId")
        PmtMtd_node = ET.Element("PmtMtd")
        NbOfTxs_node = ET.Element("NbOfTxs")
        CtrlSum_node = ET.Element("CtrlSum")
        PmtTpInf_node = ET.Element("PmtTpInf")
        PmtTpInf_SvcLvl_node = ET.Element("SvcLvl")
        PmtTpInf_SvcLvl_Cd_node = ET.Element("Cd")
        ReqdExctnDt_node = ET.Element("ReqdExctnDt")
        Dbtr_node = ET.Element("Dbtr")
        Dbtr_Nm_node = ET.Element("Nm")
        DbtrAcct_node = ET.Element("DbtrAcct")
        DbtrAcct_Id_node = ET.Element("Id")
        DbtrAcct_Id_Iban_node = ET.Element("IBAN")
        DbtrAgt_node = ET.Element("DbtrAgt")
        DbtrAgt_FinInstnId_node = ET.Element("FinInstnId")
        DbtrAgt_FinInstnId_BIC_node = ET.Element("BIC")
        ChrgBr_node = ET.Element("ChrgBr")

        # Payment Information Data
        PmtInfId_node.text = (only_alphanumeric("PAYMENT-" + str(
            datetime.now().date()) + "_" + str(datetime.now().time())))
        PmtMtd_node.text = "TRF"
        NbOfTxs_node.text = str(1)
        CtrlSum_node.text = transfer_data[SEPA_AMOUNT]
        PmtTpInf_SvcLvl_Cd_node.text = "SEPA"
        ReqdExctnDt_node.text = transfer_data[SEPA_EXECUTION_DATE]
        Dbtr_Nm_node.text = account_data[KEY_ACC_OWNER_NAME]
        DbtrAcct_Id_Iban_node.text = account_data[KEY_ACC_IBAN]
        DbtrAgt_FinInstnId_BIC_node.text = bank.bic
        ChrgBr_node.text = "SLEV"
        # Payment Information Tree
        PmtInf_node.append(PmtInfId_node)
        PmtInf_node.append(PmtMtd_node)
        PmtInf_node.append(NbOfTxs_node)
        PmtInf_node.append(CtrlSum_node)
        PmtInf_node.append(PmtTpInf_node)
        PmtTpInf_node.append(PmtTpInf_SvcLvl_node)
        PmtTpInf_SvcLvl_node.append(PmtTpInf_SvcLvl_Cd_node)
        PmtInf_node.append(ReqdExctnDt_node)
        PmtInf_node.append(Dbtr_node)
        Dbtr_node.append(Dbtr_Nm_node)
        PmtInf_node.append(DbtrAcct_node)
        DbtrAcct_node.append(DbtrAcct_Id_node)
        DbtrAcct_Id_node.append(DbtrAcct_Id_Iban_node)
        PmtInf_node.append(DbtrAgt_node)
        DbtrAgt_node.append(DbtrAgt_FinInstnId_node)
        DbtrAgt_FinInstnId_node.append(DbtrAgt_FinInstnId_BIC_node)
        PmtInf_node.append(ChrgBr_node)
        return PmtInf_node

    def _credit_transfer_transaction_info(self, bank, account_data, transfer_data):

        # Credit Transfer transaction Information Nodes
        CdtTrfTxInf_node = ET.Element("CdtTrfTxInf")
        PmtId_node = ET.Element("PmtId")
        PmtId_EndToEndId_node = ET.Element("EndToEndId")
        Amt_node = ET.Element("Amt")
        Amt_InstdAmt_node = ET.Element("InstdAmt")
        CdtrAgt_node = ET.Element("CdtrAgt")
        CdtrAgt_FinInstnId_node = ET.Element("FinInstnId")
        CdtrAgt_FinInstnId_BIC_node = ET.Element("BIC")
        Cdtr_node = ET.Element("Cdtr")
        Cdtr_Nm_node = ET.Element("Nm")
        CdtrAcct_node = ET.Element("CdtrAcct")
        CdtrAcct_Id_node = ET.Element("Id")
        CdtrAcct_Id_IBAN_node = ET.Element("IBAN")
        RmtInf_node = ET.Element("RmtInf")
        RmtInf_Ustrd_node = ET.Element("Ustrd")
        # Credit Transfer transaction Information Data
        if transfer_data[SEPA_REFERENCE] == "":
            transfer_data[SEPA_REFERENCE] = NOTPROVIDED
        PmtId_EndToEndId_node.text = transfer_data[SEPA_REFERENCE]
        Amt_InstdAmt_node.set("Ccy", "EUR")
        Amt_InstdAmt_node.text = transfer_data[SEPA_AMOUNT]
        CdtrAgt_FinInstnId_BIC_node.text = transfer_data[SEPA_CREDITOR_BIC]
        Cdtr_Nm_node.text = transfer_data[SEPA_CREDITOR_NAME]
        CdtrAcct_Id_IBAN_node.text = transfer_data[SEPA_CREDITOR_IBAN]
        if transfer_data[SEPA_PURPOSE] == "":
            transfer_data[SEPA_PURPOSE] = " "
        RmtInf_Ustrd_node.text = transfer_data[SEPA_PURPOSE]
        # Credit Transfer transaction Information Tree
        CdtTrfTxInf_node.append(PmtId_node)
        PmtId_node.append(PmtId_EndToEndId_node)
        CdtTrfTxInf_node.append(Amt_node)
        Amt_node.append(Amt_InstdAmt_node)
        CdtTrfTxInf_node.append(CdtrAgt_node)
        CdtrAgt_node.append(CdtrAgt_FinInstnId_node)
        CdtrAgt_FinInstnId_node.append(CdtrAgt_FinInstnId_BIC_node)
        CdtTrfTxInf_node.append(Cdtr_node)
        Cdtr_node.append(Cdtr_Nm_node)
        CdtTrfTxInf_node.append(CdtrAcct_node)
        CdtrAcct_node.append(CdtrAcct_Id_node)
        CdtrAcct_Id_node.append(CdtrAcct_Id_IBAN_node)
        CdtTrfTxInf_node.append(RmtInf_node)
        RmtInf_node.append(RmtInf_Ustrd_node)
        return CdtTrfTxInf_node
