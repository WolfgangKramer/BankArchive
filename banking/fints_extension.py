"""
Created on 11.02.2020
__updated__ = "2026-05-11"
@author: Wolfgang Kramer

Extensions of project fints source code  copied and modified
    Pure-python FinTS (formerly known as HBCI) implementation https://pypi.python.org/pypi/fints
"""



from fints.fields import DataElementField, DataElementGroupField, CodeField
from fints.formals import DataElementGroup, KTI1
from fints.segments.base import ParameterSegment, ParameterSegment_22, FinTS3Segment
from fints.utils import RepresentableEnum, doc_enum


@doc_enum
class DeliveryType(RepresentableEnum):
    """Art der Lieferung Payment Status Report """
    S = 'S'  # doc: schrittweise Lieferung
    V = 'V'  # doc: vollständige Lieferung


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


class HKCAZ1(FinTS3Segment):
    """Kontoumsätze anfordern/Zeitraum, version 5
    Segment not implemented in Project FinTS (see module fints.segments.statement)
    proprietäres Parametersegment vieler Banken.

    Parameter-Segment für (I)nformationssegment zu (CA) Kontoauszügen/Zusammenfassungen → „S“ = Service/Supported

     _additional_data = ['1', '1', '1', ['740', 'N', 'N', 'urn:iso:std:iso:20022:tech:xsd:camt.052.001.08']],

         Aufschlüsselung:
         Position    Bedeutung
         '1'    Parameter: Multimandantenfähig? oder Anzahl Konten unterstützt – institutsspezifisch
         '1'    Parameter: Unterstützte Historiearten – institutsspezifisch
         '1'    Parameter: Unterstützte Buchungsarten – institutsspezifisch
         ['740', 'N', 'N', 'urn:…camt.052…']    Formatblock für CAMT-Unterstützung
         Der CAMT-Block:
         Wert    Bedeutung
         '740'    Geschäftsvorfall-Nummer (GV-Code) für CAMT-Umsatzabruf
         'N'    Keine Sammlerbuchungen? (institutsspezifisch)
         'N'    Keine Verdichtungen?
         'urn:iso:std:iso:20022:tech:xsd:camt.052.001.08'    Unterstütztes XML-Format für „camt.052“ (Intraday-Umsätze)

         Das Segment sagt dir also:
          „Diese Bank unterstützt CAMT.052.001.08 für Kontoumsätze (GV 740).“

    """

    account = DataElementGroupField(type=KTI1, _d="Kontoverbindung international")
    supported_camt_messages = DataElementField(type='an', max_length=256, required=True, _d="Unterstützte CAMT messages ")
    all_accounts = DataElementField(type='jn', _d="Alle Konten")
    date_start = DataElementField(type='dat', required=False, _d="Von Datum")
    date_end = DataElementField(type='dat', required=False, _d="Bis Datum")
    max_number_responses = DataElementField(type='num', max_length=4, required=False, _d="Maximale Anzahl Einträge")
    touchdown_point = DataElementField(type='an', max_length=35, required=False, _d="Aufsetzpunkt")


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
