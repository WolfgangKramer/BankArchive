"""
Created on 11.02.2020
__updated__ = "2024-02-23"
@author: Wolfgang Kramer

Extensions of project fints source code  copied and modified
    Pure-python FinTS (formerly known as HBCI) implementation https://pypi.python.org/pypi/fints
"""

from fints.fields import DataElementField, DataElementGroupField, CodeField
from fints.formals import DataElementGroup, KTI1
from fints.segments.base import ParameterSegment, ParameterSegment_22, FinTS3Segment
from fints.utils import RepresentableEnum


class ParameterAccountTurnoverPeriod(DataElementGroup):
    """
    Parameter not implemented in GitHub Project FinTS (see module fints.formals)
    """

    """ Parameter       Kontoumsaetze
                        Zeitraum
    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Geschaeftsvorfaelle
    """
    storage_period = DataElementField(
        type='num', max_length=4, _d='Speicherzeitraum')
    number_entries_allowed = DataElementField(
        type='jn', _d='Eingabe Anzahl Eintraege erlaubt')
    all_accounts = DataElementField(type='jn', _d='Alle Konten')


class SecuritiesReferenceType(RepresentableEnum):
    """
    Wertpapier Referenzart, version 2
      Wertpapierreferenz, ueber die z.B. eine Umsatzanfrage auf ein bestimmtes
      Papier eingeschraenkt werden kann.

    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Multibankfaehige
    """
    ISIN = '1'  # :     ISIN
    WKN = '2'  # :     Wertpapierkennziffer
    INTERNAL = '3'  # :     kreditinstitutsinterne Referenz
    INDEXNAME = '4'  # :      Indexname


class SecuritiesReference(DataElementGroup):
    """
    Referenzart Art der Referenzierung auf Wertpapierinformationen.
    Codierung: 1: ISIN 2: WKN 3: kreditinstitutsinterne Referenz 4: Indexname

    Wertpapiercode Wertpapiercode gemaess der Referenzart (DE Referenzart).
    Im Fall der ISIN erfolgt die Angabe 12-stellig alphanumerisch,
    im Fall der WKN 6-stellig numerisch (zukuenftig auch alphanumerisch).
    Es wird dem Kunden diejenige Referenz zurueckgemeldet, die er im Auftrag angegeben hat.
    """
    securities_reference_type = CodeField(
        enum=SecuritiesReferenceType, length=1, _d='Bezeichnung des TAN-Medium erforderlich')
    securities_code = DataElementField(
        type='an', max_length=30, required=True, _d='Wertpapiercode')


class HIKAZS6(ParameterSegment):
    """
    Segment not implemented in Project FinTS (see module fints.segments.statement)
    """

    """Kontoumsaetze Zeitraum, Bankparameterdaten, version 6

    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Multibankfaehige Geschaeftsvorfaelle
    """
    parameter = DataElementGroupField(
        type=ParameterAccountTurnoverPeriod, _d='Parameter Kontoumsaetze/Zeitraum')


class HIKAZS7(ParameterSegment):
    """
    Segment not implemented in Project FinTS (see module fints.segments.statement)
    """

    """Kontoumsaetze Zeitraum, Bankparameterdaten, version 7

    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Multibankfaehige Geschaeftsvorfaelle
    """
    parameter = DataElementGroupField(
        type=ParameterAccountTurnoverPeriod, _d='Parameter Kontoumsaetze/Zeitraum')


class HIWPDS5(ParameterSegment_22):
    """
    Segment not implemented in Project FinTS (see module fints.segments.depot)
    """
    pass


class HIWPDS6(ParameterSegment):
    """
    Segment not implemented in Project FinTS (see module fints.segments.depot)
    """
    pass


class HKCSE1(FinTS3Segment):
    """
    SEPA Terminierte SEPA-Ueberweisung , version 1

    Source: FinTS Financial Transaction Services, Schnittstellenspezifikation,
            Messages -- Multibankfaehige Geschaeftsvorfaelle
    """

    account = DataElementGroupField(
        type=KTI1, _d='Kontoverbindung international')
    sepa_descriptor = DataElementField(
        type='an', max_length=256, _d='SEPA Descriptor')
    sepa_pain_message = DataElementField(type='bin', _d='SEPA pain message')
